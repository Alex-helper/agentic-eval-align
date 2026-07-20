from __future__ import annotations

import json
import re
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any
from uuid import uuid4

from backend.llm_client import LLMClient
from backend.mcp_client import MCPClient
from backend.memory.store import LongTermMemory, ShortTermMemory
from backend.tools import TOOL_SCHEMAS

EventCallback = Callable[[str, str, dict[str, Any]], Awaitable[None] | None]


COMPLEX_SYSTEM = """你是 TraceAlign Lab 的可视化 Agent 助手。
你可以：
1) 回答关于评测、GraphRAG、MCP、DPO、错误分析的问题；
2) 把用户的复杂任务拆成多步计划，并调用工具执行。

可用工具：
- search_docs(query): 检索 API/知识图谱文档
- calculator(expression): 安全算术计算

当用户给出需要多步推理/工具的任务时，先输出简洁计划，再逐步执行。
最终用中文给出结构化结论：计划、执行步骤、结果、风险。"""


class ComplexAssistant:
    """Interactive multi-step agent for chat + complex task execution."""

    def __init__(
        self,
        llm: LLMClient | None = None,
        mcp: MCPClient | None = None,
        on_event: EventCallback | None = None,
        max_steps: int = 6,
    ) -> None:
        self.llm = llm or LLMClient()
        self.mcp = mcp or MCPClient()
        self.long_term = LongTermMemory()
        self.on_event = on_event
        self.max_steps = max_steps

    async def _emit(self, memory: ShortTermMemory, event_type: str, message: str, payload: dict | None = None):
        memory.add(event_type, message, payload)
        if self.on_event:
            maybe = self.on_event(event_type, message, payload or {})
            if maybe is not None and hasattr(maybe, "__await__"):
                await maybe

    def _parse_tool_intent(self, text: str) -> list[dict[str, Any]]:
        """Extract tool calls from model text: TOOL:name|{json} or TOOL:name|arg."""
        calls: list[dict[str, Any]] = []
        for match in re.finditer(r"TOOL:(\w+)\s*\|\s*(.+)", text):
            name = match.group(1).strip()
            raw = match.group(2).strip()
            try:
                args = json.loads(raw)
            except json.JSONDecodeError:
                if name == "calculator":
                    args = {"expression": raw}
                else:
                    args = {"query": raw}
            calls.append({"name": name, "arguments": args})
        # Heuristic: if user/task mentions calc numbers without explicit TOOL
        if not calls and re.search(r"\d+\s*[\+\-\*/]\s*\d+", text):
            expr = re.search(r"([\d\.\s\+\-\*/\(\)]+)", text)
            if expr:
                calls.append({"name": "calculator", "arguments": {"expression": expr.group(1).strip()}})
        return calls

    def _needs_tools(self, message: str) -> bool:
        keys = [
            "计算",
            "检索",
            "文档",
            "API",
            "invoice",
            "tax",
            "workflow",
            "risk",
            "auth",
            "执行",
            "多步",
            "复杂",
            "评测",
            "工具",
        ]
        return any(k.lower() in message.lower() for k in keys)

    async def chat(self, message: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
        memory = ShortTermMemory()
        session_id = f"chat_{uuid4().hex[:10]}"
        history = history or []
        t0 = time.perf_counter()

        await self._emit(memory, "planning", "助手开始理解用户意图", {"session_id": session_id})

        knowledge = self.long_term.search(message)
        global_summary = self.long_term.global_summary()
        await self._emit(
            memory,
            "retrieval",
            "已检索相关知识",
            {"hits": knowledge[:3], "global_summary": global_summary[:400]},
        )

        plan_prompt = (
            f"用户消息：{message}\n"
            f"相关知识：{json.dumps(knowledge[:3], ensure_ascii=False)}\n"
            "若需要工具，用如下格式声明（可多行）：\n"
            'TOOL:search_docs|{"query":"..."}\n'
            'TOOL:calculator|{"expression":"..."}\n'
            "否则直接回答。"
        )
        messages = [{"role": "system", "content": COMPLEX_SYSTEM}]
        for item in history[-8:]:
            messages.append({"role": item.get("role", "user"), "content": item.get("content", "")})
        messages.append({"role": "user", "content": plan_prompt})

        plan_resp = await self.llm.chat(messages, tools=TOOL_SCHEMAS)
        await self._emit(
            memory,
            "analysis",
            "已生成初步计划/回复",
            {"model": plan_resp.model, "fallback": plan_resp.used_fallback},
        )

        tool_results: list[dict[str, Any]] = []
        calls = self._parse_tool_intent(plan_resp.content) if self._needs_tools(message) or "TOOL:" in plan_resp.content else []
        if not calls and self._needs_tools(message):
            calls = [{"name": "search_docs", "arguments": {"query": message[:300]}}]

        for idx, call in enumerate(calls[: self.max_steps]):
            await self._emit(
                memory,
                "tool_call",
                f"步骤 {idx + 1}: 调用 {call['name']}",
                {"step": idx + 1, "call": call},
            )
            payload = await self.mcp.call(call["name"], call.get("arguments") or {})
            tool_results.append(payload)
            await self._emit(
                memory,
                "tool_result",
                f"步骤 {idx + 1}: {call['name']} 完成 via {payload.get('transport')}",
                payload,
            )

        if tool_results:
            synthesize = (
                f"用户目标：{message}\n"
                f"计划草稿：{plan_resp.content}\n"
                f"工具结果：{json.dumps(tool_results, ensure_ascii=False)[:4000]}\n"
                "请输出最终中文答复，包含：1) 任务拆解 2) 执行过程 3) 最终结论 4) 下一步建议。"
            )
            final = await self.llm.chat(
                [
                    {"role": "system", "content": COMPLEX_SYSTEM},
                    {"role": "user", "content": synthesize},
                ]
            )
            reply = final.content
            await self._emit(memory, "success", "复杂任务执行完成", {"model": final.model})
        else:
            reply = plan_resp.content
            await self._emit(memory, "success", "对话回复完成", {})

        elapsed_ms = (time.perf_counter() - t0) * 1000
        return {
            "session_id": session_id,
            "reply": reply,
            "trace": [e.model_dump() for e in memory.events],
            "tool_results": tool_results,
            "knowledge_hits": len(knowledge),
            "elapsed_ms": elapsed_ms,
            "complex": bool(tool_results) or self._needs_tools(message),
        }


async def assistant_stream(message: str, history: list[dict[str, str]] | None = None) -> AsyncIterator[str]:
    import asyncio
    import json as _json

    queue: asyncio.Queue[tuple[str, dict] | None] = asyncio.Queue()

    async def on_event(event_type: str, msg: str, payload: dict) -> None:
        await queue.put((event_type, {"message": msg, "payload": payload}))

    async def runner() -> None:
        try:
            result = await ComplexAssistant(on_event=on_event).chat(message, history)
            await queue.put(("done", result))
        except Exception as exc:  # pragma: no cover
            await queue.put(("error", {"message": str(exc)}))
        finally:
            await queue.put(None)

    task = asyncio.create_task(runner())
    yield f"event: planning\ndata: {_json.dumps({'message': '助手已接入'}, ensure_ascii=False)}\n\n"
    while True:
        item = await queue.get()
        if item is None:
            break
        event, data = item
        yield f"event: {event}\ndata: {_json.dumps(data, ensure_ascii=False)}\n\n"
    await task
