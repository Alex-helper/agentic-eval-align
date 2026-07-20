from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from backend.agents.supervisor import SupervisorAgent
from backend.llm_client import LLMClient
from backend.models import Task, new_run_id
from backend.runs import RunStore, now_ts
from backend.models import RunArtifact, RunConfigSnapshot
from backend.mcp_client import MCPClient
from backend.metrics_report import aggregate_metrics
from backend.models import DPOPair


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def evaluate_stream(task: Task) -> AsyncIterator[str]:
    """True incremental SSE: events emit as the supervisor executes."""
    queue: asyncio.Queue[tuple[str, dict] | None] = asyncio.Queue()
    run_id = new_run_id()
    llm = LLMClient()
    mcp = MCPClient()

    async def on_event(event_type: str, message: str, payload: dict) -> None:
        await queue.put((event_type, {"message": message, "payload": payload, "task_id": task.task_id, "run_id": run_id}))

    async def runner() -> None:
        try:
            supervisor = SupervisorAgent(llm=llm, mcp=mcp, on_event=on_event)
            result = await supervisor.run(task, run_id=run_id)
            artifact = RunArtifact(
                run_id=run_id,
                created_at=now_ts(),
                kind="single",
                config=RunConfigSnapshot(
                    model=llm.model,
                    base_url=llm.base_url,
                    llm_configured=llm.configured(),
                    mcp_base_url=mcp.base_url,
                    pipeline="full",
                ),
                tasks=[task],
                results=[result],
                metrics=aggregate_metrics([result]),
                dpo_pairs=[DPOPair(**result.dpo_pair)] if result.dpo_pair else [],
            )
            RunStore().save(artifact)
            await queue.put(("done", {**result.model_dump(), "run_id": run_id, "artifact": artifact.model_dump()}))
        except Exception as exc:  # pragma: no cover
            await queue.put(("error", {"message": str(exc), "run_id": run_id}))
        finally:
            await queue.put(None)

    task_handle = asyncio.create_task(runner())
    yield sse("planning", {"message": "SSE channel opened", "task_id": task.task_id, "run_id": run_id})

    while True:
        item = await queue.get()
        if item is None:
            break
        event, data = item
        yield sse(event, data)

    await task_handle
