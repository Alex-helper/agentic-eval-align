from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse

from backend.agents.supervisor import SupervisorAgent
from backend.agents.assistant import ComplexAssistant, assistant_stream
from backend.ingest import parse_bytes, supported_formats
from backend.llm_client import LLMClient
from backend.mcp_client import MCPClient
from backend.metrics_report import aggregate_metrics, render_metrics_md
from backend.models import DPOPair, RunArtifact, RunConfigSnapshot, Task, new_run_id
from backend.runs import RunStore, now_ts
from backend.stream_handler import evaluate_stream
from backend.suite import run_suite_ab
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
load_dotenv(ENV_FILE, encoding="utf-8-sig")
SAMPLES = ROOT / "data" / "samples"
PROVIDERS_CATALOG = Path.home() / ".cursor" / "skills" / "global-api-env" / "providers.json"

app = FastAPI(title="Agentic Eval Align", version="0.5.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[dict[str, str]] = Field(default_factory=list)


class ComplexTaskRequest(BaseModel):
    instruction: str = Field(min_length=1)
    tools: list[str] = Field(default_factory=lambda: ["search_docs", "calculator"])
    expected: dict = Field(default_factory=dict)


class ConfigReq(BaseModel):
    api_key: str
    base_url: str = "https://api.deepseek.com/v1"
    model: str = "deepseek-chat"
    provider_id: str = "deepseek"
    region: str = "cn"


def _upsert_env(path: Path, updates: dict[str, str]) -> None:
    text = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    lines = text.splitlines()
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            out.append(line)
            continue
        key = raw.split("=", 1)[0].strip().lstrip("\ufeff")
        if key in updates:
            if key not in seen:
                out.append(f"{key}={updates[key]}")
                seen.add(key)
            continue
        out.append(line)
    for key, val in updates.items():
        if key not in seen:
            out.append(f"{key}={val}")
    path.write_bytes(("\n".join(out).rstrip() + "\n").encode("utf-8"))


def load_sample_tasks() -> list[Task]:
    return [Task(**json.loads(path.read_text(encoding="utf-8"))) for path in sorted(SAMPLES.glob("*.json"))]


@app.get("/api/providers-catalog")
async def providers_catalog() -> dict:
    if not PROVIDERS_CATALOG.exists():
        return {"error": "providers catalog missing", "providers": [], "regions": []}
    return json.loads(PROVIDERS_CATALOG.read_text(encoding="utf-8"))


@app.get("/api/config")
async def get_config() -> dict:
    load_dotenv(ENV_FILE, override=True, encoding="utf-8-sig")
    key = os.getenv("OPENAI_API_KEY", "") or os.getenv("DEEPSEEK_API_KEY", "")
    return {
        "api_key": key,
        "base_url": os.getenv("OPENAI_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com/v1",
        "model": os.getenv("MODEL_NAME") or os.getenv("DEEPSEEK_MODEL") or "deepseek-chat",
        "provider_id": os.getenv("API_PROVIDER_ID", "deepseek"),
        "region": os.getenv("API_REGION", "cn"),
        "configured": bool(key) and not key.startswith("sk-xxx"),
        "writable": True,
    }


@app.post("/api/config")
async def save_config(req: ConfigReq) -> dict:
    _upsert_env(
        ENV_FILE,
        {
            "API_PROVIDER_ID": (req.provider_id or "deepseek").strip(),
            "API_REGION": (req.region or "cn").strip(),
            "OPENAI_API_KEY": req.api_key.strip(),
            "OPENAI_BASE_URL": (req.base_url or "https://api.deepseek.com/v1").strip(),
            "MODEL_NAME": (req.model or "deepseek-chat").strip(),
        },
    )
    load_dotenv(ENV_FILE, override=True, encoding="utf-8-sig")
    os.environ["OPENAI_API_KEY"] = req.api_key.strip()
    os.environ["OPENAI_BASE_URL"] = (req.base_url or "https://api.deepseek.com/v1").strip()
    os.environ["MODEL_NAME"] = (req.model or "deepseek-chat").strip()
    return {"ok": True}


@app.get("/api/mcp/tools")
async def mcp_tools() -> dict:
    mcp = MCPClient()
    health = await mcp.health()
    listed = await mcp.list_tools()
    return {"mcp": health, **listed}

@app.get("/api/health")
async def health() -> dict:
    client = LLMClient()
    mcp = await MCPClient().health()
    return {
        "status": "ok",
        "service": "agentic-eval-align",
        "llm_configured": client.configured(),
        "model": client.model,
        "base_url": client.base_url,
        "mcp": mcp,
        "upload_formats": supported_formats()["extensions"],
    }


@app.get("/api/formats")
async def formats() -> dict:
    return supported_formats()


@app.get("/api/tasks/sample")
async def sample_tasks() -> list[dict]:
    return [task.model_dump() for task in load_sample_tasks()]


@app.post("/api/evaluate")
async def evaluate(task: Task) -> dict:
    run_id = new_run_id()
    llm = LLMClient()
    mcp = MCPClient()
    result = await SupervisorAgent(llm=llm, mcp=mcp).run(task, run_id=run_id)
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
    return {**result.model_dump(), "run_id": run_id, "artifact": artifact.model_dump()}


@app.post("/api/evaluate/stream")
async def evaluate_stream_endpoint(task: Task) -> StreamingResponse:
    return StreamingResponse(evaluate_stream(task), media_type="text/event-stream")


@app.post("/api/evaluate/suite")
async def evaluate_suite() -> dict:
    artifact = await run_suite_ab(load_sample_tasks(), kind="suite")
    md = render_metrics_md(results=artifact.results, compares=artifact.compares, metrics=artifact.metrics)
    (ROOT / "evals" / "METRICS.md").write_text(md, encoding="utf-8")
    return artifact.model_dump()


@app.post("/api/evaluate/upload")
async def evaluate_upload(files: list[UploadFile] = File(...)) -> dict:
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required.")

    tasks: list[Task] = []
    parsed_files: list[dict] = []
    errors: list[dict] = []

    for file in files:
        filename = file.filename or "upload.bin"
        raw = await file.read()
        try:
            parsed = parse_bytes(filename, raw)
            tasks.extend(parsed)
            parsed_files.append(
                {
                    "filename": filename,
                    "task_count": len(parsed),
                    "source_formats": sorted({t.source_format for t in parsed}),
                    "modalities": sorted({m for t in parsed for m in t.modalities}),
                }
            )
        except Exception as exc:
            errors.append({"filename": filename, "error": str(exc)})

    if not tasks and errors:
        raise HTTPException(status_code=400, detail={"message": "No tasks could be parsed.", "errors": errors})

    artifact = await run_suite_ab(tasks, kind="upload")
    return {
        "count": len(artifact.results),
        "success_count": sum(1 for r in artifact.results if r.success),
        "success_rate": artifact.metrics.current_success_rate if artifact.metrics else 0.0,
        "parsed_files": parsed_files,
        "errors": errors,
        "supported_formats": supported_formats()["extensions"],
        "run_id": artifact.run_id,
        "artifact": artifact.model_dump(),
        "results": [r.model_dump() for r in artifact.results],
        "compares": [c.model_dump() for c in artifact.compares],
        "metrics": artifact.metrics.model_dump() if artifact.metrics else None,
    }


@app.post("/api/ingest/preview")
async def ingest_preview(files: list[UploadFile] = File(...)) -> dict:
    preview = []
    errors = []
    for file in files:
        filename = file.filename or "upload.bin"
        raw = await file.read()
        try:
            tasks = parse_bytes(filename, raw)
            preview.extend(
                [
                    {
                        "task_id": t.task_id,
                        "instruction": t.instruction[:240],
                        "tools": t.tools,
                        "modalities": t.modalities,
                        "source_format": t.source_format,
                        "attachment_names": [a.filename for a in t.attachments],
                    }
                    for t in tasks
                ]
            )
        except Exception as exc:
            errors.append({"filename": filename, "error": str(exc)})
    return {"count": len(preview), "tasks": preview, "errors": errors, "formats": supported_formats()}


@app.get("/api/runs")
async def list_runs(limit: int = 20) -> dict:
    return {"runs": RunStore().list(limit=limit)}


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    artifact = RunStore().get(run_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="run not found")
    return artifact.model_dump()


@app.get("/api/runs/{run_id}/export.json")
async def export_run_json(run_id: str) -> dict:
    artifact = RunStore().get(run_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="run not found")
    return artifact.model_dump()


@app.get("/api/runs/{run_id}/export.md")
async def export_run_md(run_id: str) -> PlainTextResponse:
    md = RunStore().export_markdown(run_id)
    if md is None:
        raise HTTPException(status_code=404, detail="run not found")
    return PlainTextResponse(md, media_type="text/markdown")


@app.get("/api/runs/{run_id}/export.dpo.jsonl")
async def export_run_dpo(run_id: str) -> PlainTextResponse:
    text = RunStore().export_dpo_jsonl(run_id)
    if text is None:
        raise HTTPException(status_code=404, detail="run not found")
    return PlainTextResponse(text or "", media_type="application/x-ndjson")


@app.post("/api/runs/{run_id}/rerun")
async def rerun(run_id: str) -> dict:
    previous = RunStore().get(run_id)
    if not previous:
        raise HTTPException(status_code=404, detail="run not found")
    artifact = await run_suite_ab(previous.tasks, kind=previous.kind)
    return artifact.model_dump()


@app.get("/api/metrics/latest")
async def latest_metrics() -> dict:
    runs = RunStore().list(limit=1)
    if not runs:
        path = ROOT / "evals" / "METRICS.md"
        return {"source": "file", "markdown": path.read_text(encoding="utf-8") if path.exists() else ""}
    artifact = RunStore().get(runs[0]["run_id"])
    return {
        "source": "run",
        "run_id": artifact.run_id if artifact else None,
        "metrics": artifact.metrics.model_dump() if artifact and artifact.metrics else None,
        "compares": [c.model_dump() for c in artifact.compares] if artifact else [],
    }


@app.post("/api/assistant/chat")
async def assistant_chat(req: AssistantChatRequest) -> dict:
    result = await ComplexAssistant().chat(req.message, req.history)
    return result


@app.post("/api/assistant/stream")
async def assistant_stream_endpoint(req: AssistantChatRequest) -> StreamingResponse:
    return StreamingResponse(assistant_stream(req.message, req.history), media_type="text/event-stream")


@app.post("/api/tasks/complex")
async def run_complex_task(req: ComplexTaskRequest) -> dict:
    """Execute a free-form complex multi-step task via Full Supervisor."""
    task = Task(
        task_id=f"complex_{new_run_id()[-8:]}",
        instruction=req.instruction,
        tools=req.tools or ["search_docs", "calculator"],
        expected=req.expected or {"requires_knowledge": True},
        difficulty="hard",
        modalities=["text"],
        source_format="complex",
    )
    run_id = new_run_id()
    llm = LLMClient()
    mcp = MCPClient()
    # First run interactive complex assistant for multi-step tool planning
    assistant_result = await ComplexAssistant(llm=llm, mcp=mcp).chat(req.instruction)
    # Then run formal evaluator for auditable artifact
    result = await SupervisorAgent(llm=llm, mcp=mcp).run(task, run_id=run_id)
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
            notes="complex multi-step task",
        ),
        tasks=[task],
        results=[result],
        metrics=aggregate_metrics([result]),
        dpo_pairs=[DPOPair(**result.dpo_pair)] if result.dpo_pair else [],
        notes=assistant_result.get("reply", "")[:2000],
    )
    RunStore().save(artifact)
    return {
        "run_id": run_id,
        "assistant": assistant_result,
        "evaluation": result.model_dump(),
        "artifact": artifact.model_dump(),
    }
