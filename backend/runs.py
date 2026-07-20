from __future__ import annotations

import json
import time
from pathlib import Path

from backend.models import RunArtifact

ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = ROOT / "data" / "runs"


class RunStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or RUNS_DIR
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, artifact: RunArtifact) -> Path:
        path = self.root / f"{artifact.run_id}.json"
        path.write_text(json.dumps(artifact.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
        index = self._load_index()
        index = [item for item in index if item.get("run_id") != artifact.run_id]
        index.insert(
            0,
            {
                "run_id": artifact.run_id,
                "created_at": artifact.created_at,
                "kind": artifact.kind,
                "task_count": len(artifact.tasks),
                "success_rate": artifact.metrics.current_success_rate if artifact.metrics else None,
                "pipeline": artifact.config.pipeline,
            },
        )
        self._write_index(index[:100])
        return path

    def get(self, run_id: str) -> RunArtifact | None:
        path = self.root / f"{run_id}.json"
        if not path.exists():
            return None
        return RunArtifact(**json.loads(path.read_text(encoding="utf-8")))

    def list(self, limit: int = 20) -> list[dict]:
        return self._load_index()[:limit]

    def export_markdown(self, run_id: str) -> str | None:
        artifact = self.get(run_id)
        if not artifact:
            return None
        from backend.metrics_report import render_metrics_md

        return render_metrics_md(
            results=artifact.results,
            compares=artifact.compares or None,
            metrics=artifact.metrics,
        )

    def export_dpo_jsonl(self, run_id: str) -> str | None:
        artifact = self.get(run_id)
        if not artifact:
            return None
        return "\n".join(json.dumps(p.model_dump(), ensure_ascii=False) for p in artifact.dpo_pairs)

    def _load_index(self) -> list[dict]:
        path = self.root / "index.json"
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_index(self, items: list[dict]) -> None:
        (self.root / "index.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def now_ts() -> float:
    return time.time()
