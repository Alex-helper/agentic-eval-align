from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from backend.agents.dpo_generator import DPOGenerator
from backend.agents.error_analyzer import ErrorAnalyzer
from backend.llm_client import LLMClient, attachment_summary
from backend.mcp_client import MCPClient
from backend.memory.store import LongTermMemory, ShortTermMemory
from backend.metrics_report import score_task
from backend.models import EvalResult, StageTiming, Task
from backend.tools import TOOL_SCHEMAS

EventCallback = Callable[[str, str, dict[str, Any]], Awaitable[None] | None]


class SupervisorAgent:
    """Full pipeline: GraphRAG + MCP tools + LLM + error/DPO optimizer."""

    def __init__(
        self,
        llm: LLMClient | None = None,
        mcp: MCPClient | None = None,
        on_event: EventCallback | None = None,
    ) -> None:
        self.llm = llm or LLMClient()
        self.mcp = mcp or MCPClient()
        self.long_term = LongTermMemory()
        self.error_analyzer = ErrorAnalyzer()
        self.dpo_generator = DPOGenerator()
        self.on_event = on_event

    async def _emit(self, memory: ShortTermMemory, event_type: str, message: str, payload: dict | None = None):
        event = memory.add(event_type, message, payload)
        if self.on_event:
            maybe = self.on_event(event_type, message, payload or {})
            if maybe is not None and hasattr(maybe, "__await__"):
                await maybe
        return event

    async def run(self, task: Task, run_id: str | None = None) -> EvalResult:
        t0 = time.perf_counter()
        timings = StageTiming()
        memory = ShortTermMemory()
        first_emitted = False

        def mark_first():
            nonlocal first_emitted
            if not first_emitted:
                timings.first_event_ms = (time.perf_counter() - t0) * 1000
                first_emitted = True

        t_plan = time.perf_counter()
        await self._emit(
            memory,
            "planning",
            f"Supervisor received task {task.task_id}",
            {
                "tools": task.tools,
                "modalities": task.modalities,
                "source_format": task.source_format,
                "attachments": attachment_summary(task.attachments),
                "pipeline": "full",
            },
        )
        mark_first()
        timings.planning_ms = (time.perf_counter() - t_plan) * 1000

        query = task.instruction
        if task.attachments:
            query += " " + " ".join(a.text_excerpt for a in task.attachments if a.text_excerpt)

        t_ret = time.perf_counter()
        knowledge = self.long_term.search(query)
        global_summary = self.long_term.global_summary()
        await self._emit(
            memory,
            "retrieval",
            "GraphRAG Local+Global Search completed",
            {"hits": knowledge, "global_summary": global_summary},
        )
        timings.retrieval_ms = (time.perf_counter() - t_ret) * 1000

        if task.attachments:
            await self._emit(
                memory,
                "multimodal",
                f"Ingested {len(task.attachments)} attachment(s)",
                {
                    "files": [a.filename for a in task.attachments],
                    "kinds": [a.kind.value for a in task.attachments],
                },
            )

        answer_parts: list[str] = []
        tool_transport = "none"
        tool_success = False
        tools = task.tools or ["search_docs"]
        t_tool = time.perf_counter()

        # Complex / hard tasks: multi-hop retrieval queries derived from instruction clauses.
        search_queries = [query[:500]]
        if task.difficulty == "hard" or task.source_format == "complex" or "；" in task.instruction or ";" in task.instruction:
            parts = [p.strip() for p in task.instruction.replace("；", ";").split(";") if p.strip()]
            extra = []
            for part in parts:
                if any(k in part.lower() for k in ["auth", "billing", "risk", "workflow", "search", "tax", "token"]):
                    extra.append(part[:200])
            if extra:
                search_queries = extra[:4]
            await self._emit(
                memory,
                "planning",
                f"复杂任务拆解为 {len(search_queries)} 个检索子步骤",
                {"sub_queries": search_queries},
            )

        for tool in tools:
            if tool not in {"search_docs", "calculator"}:
                await self._emit(memory, "error", f"Tool not allowed: {tool}", {"tool": tool})
                continue
            if tool == "search_docs":
                for step_i, sq in enumerate(search_queries, start=1):
                    payload = await self.mcp.call("search_docs", {"query": sq})
                    tool_transport = payload.get("transport", "unknown")
                    result = payload.get("result", {})
                    tool_success = tool_success or bool(result)
                    hits = result.get("results", []) if isinstance(result, dict) else []
                    answer_parts.append(f"step{step_i}_hits={len(hits)}")
                    await self._emit(
                        memory,
                        "tool_call",
                        f"多跳步骤 {step_i}: search_docs via {tool_transport}",
                        {**payload, "ok": True, "query": sq},
                    )
            else:
                args = {"expression": task.expected.get("expression", "1+1")}
                payload = await self.mcp.call(tool, args)
                tool_transport = payload.get("transport", "unknown")
                result = payload.get("result", {})
                tool_success = tool_success or bool(result)
                answer_parts.append(f"calc={result.get('value') if isinstance(result, dict) else result}")
                await self._emit(
                    memory,
                    "tool_call",
                    f"Called tool {tool} via {tool_transport}",
                    {**payload, "ok": True},
                )
        timings.tool_ms = (time.perf_counter() - t_tool) * 1000

        t_llm = time.perf_counter()
        user_content = self.llm.build_user_content(task, memory.summarize())
        system_prompt = (
            "You are an evaluator agent for complex multi-step reasoning and multimodal Agent tasks. "
            "Use retrieved knowledge, tool results, and any attached image/document context. "
            "For hard tasks, explicitly list: plan → steps → evidence → final answer."
        )
        llm_response = await self.llm.chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            tools=TOOL_SCHEMAS,
        )
        await self._emit(
            memory,
            "analysis",
            "LLM reasoning completed",
            {
                "model": llm_response.model,
                "fallback": llm_response.used_fallback,
                "multimodal": "image" in task.modalities,
            },
        )
        timings.llm_ms = (time.perf_counter() - t_llm) * 1000

        t_score = time.perf_counter()
        answer = " | ".join(answer_parts + [llm_response.content])
        success, score, knowledge_hit = score_task(
            task_source_format=task.source_format,
            expected=task.expected,
            answer=answer,
            answer_parts=answer_parts,
            knowledge=knowledge,
            llm_content=llm_response.content,
        )
        timings.scoring_ms = (time.perf_counter() - t_score) * 1000
        timings.total_ms = (time.perf_counter() - t0) * 1000

        error_report = None
        dpo_pair = None
        if not success:
            report = self.error_analyzer.analyze(task.task_id, memory.events, task.expected)
            pair = self.dpo_generator.generate(task, memory.events, report, run_id=run_id)
            self.dpo_generator.append(pair)
            error_report = report.model_dump()
            dpo_pair = pair.model_dump()
            await self._emit(
                memory,
                "optimizer",
                "Generated ErrorReport and DPO preference pair",
                {"error_report": error_report, "dpo_pair": dpo_pair},
            )
        else:
            await self._emit(memory, "success", "Task passed evaluator checks", {"score": score})

        return EvalResult(
            task_id=task.task_id,
            success=success,
            score=score,
            answer=answer,
            trace=memory.events,
            error_report=error_report,
            dpo_pair=dpo_pair,
            modalities=task.modalities,
            source_format=task.source_format,
            pipeline="full",
            timings=timings,
            tool_transport=tool_transport,
            knowledge_hit=knowledge_hit,
            tool_success=tool_success,
        )
