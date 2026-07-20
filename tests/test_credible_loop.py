from __future__ import annotations

import asyncio
import json
from pathlib import Path

from backend.agents.error_analyzer import ErrorAnalyzer
from backend.agents.naive import NaiveAgent
from backend.agents.supervisor import SupervisorAgent
from backend.mcp_client import MCPClient
from backend.metrics_report import compare_pipelines, score_task
from backend.models import Task, TraceEvent
from backend.runs import RunStore
from backend.suite import run_suite_ab


def test_score_task_requires_tools():
    success, score, hit = score_task(
        task_source_format="json",
        expected={"keyword": "auth"},
        answer="no tools",
        answer_parts=[],
        knowledge=[],
        llm_content="guess",
    )
    assert success is False
    assert score < 1


def test_error_analyzer_tool_selection():
    report = ErrorAnalyzer().analyze(
        "t1",
        [TraceEvent(type="error", message="Tool not allowed: foo", payload={}, timestamp=1.0)],
        {},
    )
    assert report.error_type.value == "tool_selection"


def test_mcp_fallback_local():
    client = MCPClient(base_url="http://127.0.0.1:59999")

    async def _run():
        result = await client.call("calculator", {"expression": "1+2"})
        assert result["fallback"] is True
        assert result["transport"] == "fallback_local"
        assert result["result"]["value"] == 3

    asyncio.run(_run())


def test_suite_ab_and_export(tmp_path: Path | None = None):
    tasks = [
        Task(
            task_id="ab_auth",
            instruction="Recover from expired token using Auth API docs",
            tools=["search_docs"],
            expected={"keyword": "auth", "requires_knowledge": True},
        )
    ]

    async def _run():
        artifact = await run_suite_ab(tasks, kind="suite")
        assert artifact.run_id
        assert artifact.metrics is not None
        assert len(artifact.compares) == 1
        store = RunStore()
        loaded = store.get(artifact.run_id)
        assert loaded is not None
        md = store.export_markdown(artifact.run_id)
        assert md and "Agent 任务成功率" in md

    asyncio.run(_run())


def test_realtime_supervisor_emits_before_done():
    events: list[str] = []

    async def on_event(event_type: str, message: str, payload: dict):
        events.append(event_type)

    async def _run():
        agent = SupervisorAgent(on_event=on_event)
        result = await agent.run(
            Task(
                task_id="stream_task",
                instruction="Find billing tax rule",
                tools=["search_docs"],
                expected={"keyword": "billing", "requires_knowledge": True},
            )
        )
        assert "planning" in events
        assert "retrieval" in events
        assert "tool_call" in events
        assert result.pipeline == "full"
        assert result.timings.first_event_ms >= 0

    asyncio.run(_run())


if __name__ == "__main__":
    test_score_task_requires_tools()
    test_error_analyzer_tool_selection()
    test_mcp_fallback_local()
    test_suite_ab_and_export()
    test_realtime_supervisor_emits_before_done()
    print("all tests passed")
