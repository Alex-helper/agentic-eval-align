from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from backend.llm_client import LLMClient
from backend.memory.store import ShortTermMemory
from backend.metrics_report import score_task
from backend.models import EvalResult, StageTiming, Task

EventCallback = Callable[[str, str, dict[str, Any]], Awaitable[None] | None]


class NaiveAgent:
    """Baseline: no GraphRAG, no MCP tools, single LLM guess."""

    def __init__(self, llm: LLMClient | None = None, on_event: EventCallback | None = None) -> None:
        self.llm = llm or LLMClient()
        self.on_event = on_event

    async def _emit(self, memory: ShortTermMemory, event_type: str, message: str, payload: dict | None = None):
        memory.add(event_type, message, payload)
        if self.on_event:
            maybe = self.on_event(event_type, message, payload or {})
            if maybe is not None and hasattr(maybe, "__await__"):
                await maybe

    async def run(self, task: Task, run_id: str | None = None) -> EvalResult:
        t0 = time.perf_counter()
        timings = StageTiming()
        memory = ShortTermMemory()

        await self._emit(
            memory,
            "planning",
            f"Naive baseline received task {task.task_id}",
            {"pipeline": "naive", "tools": []},
        )
        timings.first_event_ms = (time.perf_counter() - t0) * 1000
        timings.planning_ms = timings.first_event_ms

        await self._emit(memory, "retrieval", "Skipped GraphRAG (naive baseline)", {"hits": []})
        await self._emit(memory, "tool_call", "Skipped MCP tools (naive baseline)", {"transport": "none"})

        t_llm = time.perf_counter()
        llm_response = await self.llm.chat(
            [
                {
                    "role": "system",
                    "content": "You are a naive baseline agent. Answer without tools or retrieval.",
                },
                {"role": "user", "content": task.instruction},
            ]
        )
        await self._emit(
            memory,
            "analysis",
            "Naive LLM answer completed",
            {"model": llm_response.model, "fallback": llm_response.used_fallback},
        )
        timings.llm_ms = (time.perf_counter() - t_llm) * 1000

        answer = llm_response.content
        success, score, knowledge_hit = score_task(
            task_source_format=task.source_format,
            expected=task.expected,
            answer=answer,
            answer_parts=[],
            knowledge=[],
            llm_content=llm_response.content,
        )
        # Naive path intentionally fails structured agent tasks that require tools/knowledge.
        if task.expected.get("requires_knowledge") or task.tools:
            success = False
            score = 0.2
        timings.total_ms = (time.perf_counter() - t0) * 1000

        if success:
            await self._emit(memory, "success", "Naive baseline passed", {"score": score})
        else:
            await self._emit(
                memory,
                "error",
                "Naive baseline failed without retrieval/tools",
                {"score": score},
            )

        return EvalResult(
            task_id=task.task_id,
            success=success,
            score=score,
            answer=answer,
            trace=memory.events,
            modalities=task.modalities,
            source_format=task.source_format,
            pipeline="naive",
            timings=timings,
            tool_transport="none",
            knowledge_hit=knowledge_hit,
            tool_success=False,
        )
