from __future__ import annotations

from backend.agents.naive import NaiveAgent
from backend.agents.supervisor import SupervisorAgent
from backend.llm_client import LLMClient
from backend.mcp_client import MCPClient
from backend.metrics_report import compare_pipelines
from backend.models import DPOPair, RunArtifact, RunConfigSnapshot, Task, new_run_id
from backend.runs import RunStore, now_ts


async def run_suite_ab(tasks: list[Task], kind: str = "suite") -> RunArtifact:
    run_id = new_run_id()
    llm = LLMClient()
    mcp = MCPClient()
    naive = NaiveAgent(llm=llm)
    full = SupervisorAgent(llm=llm, mcp=mcp)

    baseline = [await naive.run(task, run_id=run_id) for task in tasks]
    current = [await full.run(task, run_id=run_id) for task in tasks]
    compares, metrics = compare_pipelines(baseline, current)
    dpo_pairs = [DPOPair(**r.dpo_pair) for r in current if r.dpo_pair]

    artifact = RunArtifact(
        run_id=run_id,
        created_at=now_ts(),
        kind=kind,  # type: ignore[arg-type]
        config=RunConfigSnapshot(
            model=llm.model,
            base_url=llm.base_url,
            llm_configured=llm.configured(),
            mcp_base_url=mcp.base_url,
            pipeline="full",
            notes="naive vs full A/B on shared scorer",
        ),
        tasks=tasks,
        results=current,
        compares=compares,
        metrics=metrics,
        dpo_pairs=dpo_pairs,
    )
    RunStore().save(artifact)
    return artifact
