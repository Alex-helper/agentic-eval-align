from __future__ import annotations

import json
from pathlib import Path

from backend.models import DPOPair, ErrorReport, Task, TraceEvent

ROOT = Path(__file__).resolve().parents[2]


class DPOGenerator:
    """Generate DPO preference pairs from failed trajectories."""

    def __init__(self, output_path: Path | None = None) -> None:
        self.output_path = output_path or ROOT / "data" / "dpo_data" / "dpo_pairs.jsonl"
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        task: Task,
        trace: list[TraceEvent],
        report: ErrorReport,
        run_id: str | None = None,
    ) -> DPOPair:
        rejected = "\n".join(f"[{e.type}] {e.message}" for e in trace)
        chosen = (
            f"Task: {task.instruction}\n"
            f"Fix strategy: {report.fix_hint}\n"
            "Correct trajectory:\n"
            "1. Retrieve relevant GraphRAG knowledge when the task depends on API documentation.\n"
            "2. Select only tools declared in the task schema.\n"
            "3. Validate tool arguments before execution.\n"
            "4. Verify final answer against expected constraints.\n"
        )
        return DPOPair(
            prompt=task.instruction,
            chosen=chosen,
            rejected=rejected,
            source_trace_id=task.task_id,
            error_type=report.error_type.value,
            run_id=run_id,
        )

    def append(self, pair: DPOPair) -> None:
        with self.output_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(pair.model_dump(), ensure_ascii=False) + "\n")
