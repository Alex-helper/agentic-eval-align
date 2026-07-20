from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from backend.ingest import parse_path
from backend.metrics_report import render_metrics_md
from backend.models import Task
from backend.suite import run_suite_ab

ROOT = Path(__file__).resolve().parent


def load_tasks(mode: str, path: str | None) -> list[Task]:
    if mode == "sample":
        files = sorted((ROOT / "data" / "samples").glob("*.json"))
        return [Task(**json.loads(file.read_text(encoding="utf-8"))) for file in files]
    if not path:
        raise SystemExit("--path is required for upload mode")
    return parse_path(Path(path))


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["sample", "upload"], default="sample")
    parser.add_argument("--path", help="Any supported multimodal file for upload mode")
    args = parser.parse_args()
    tasks = load_tasks(args.mode, args.path)
    artifact = await run_suite_ab(tasks, kind="suite" if args.mode == "sample" else "upload")
    out = ROOT / "evals" / "METRICS.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        render_metrics_md(results=artifact.results, compares=artifact.compares, metrics=artifact.metrics),
        encoding="utf-8",
    )
    print(f"wrote {out}")
    print(f"run_id={artifact.run_id}")
    if artifact.metrics:
        print(
            f"baseline={artifact.metrics.baseline_success_rate:.0%} "
            f"current={artifact.metrics.current_success_rate:.0%} "
            f"delta={artifact.metrics.success_rate_delta_pct}%"
        )


if __name__ == "__main__":
    asyncio.run(main())
