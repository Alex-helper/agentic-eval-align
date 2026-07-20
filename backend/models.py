from __future__ import annotations

from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def new_run_id() -> str:
    return f"run_{uuid4().hex[:12]}"


class MediaKind(str, Enum):
    IMAGE = "image"
    PDF = "pdf"
    TEXT = "text"
    TABLE = "table"
    DOCUMENT = "document"
    AUDIO = "audio"
    UNKNOWN = "unknown"


class MediaAttachment(BaseModel):
    kind: MediaKind
    filename: str
    mime: str = "application/octet-stream"
    text_excerpt: str = ""
    data_b64: str | None = None
    page_count: int | None = None
    width: int | None = None
    height: int | None = None


class Task(BaseModel):
    task_id: str
    instruction: str
    tools: list[str] = Field(default_factory=lambda: ["search_docs"])
    expected: dict[str, Any] = Field(default_factory=dict)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    modalities: list[str] = Field(default_factory=lambda: ["text"])
    attachments: list[MediaAttachment] = Field(default_factory=list)
    source_format: str = "json"


class TraceEvent(BaseModel):
    type: str
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: float


class StageTiming(BaseModel):
    planning_ms: float = 0.0
    retrieval_ms: float = 0.0
    tool_ms: float = 0.0
    llm_ms: float = 0.0
    scoring_ms: float = 0.0
    total_ms: float = 0.0
    first_event_ms: float = 0.0


class RunConfigSnapshot(BaseModel):
    model: str
    base_url: str
    llm_configured: bool
    mcp_base_url: str
    pipeline: Literal["naive", "full"] = "full"
    notes: str = ""


class ErrorType(str, Enum):
    TOOL_SELECTION = "tool_selection"
    TOOL_ARGUMENT = "tool_argument"
    KNOWLEDGE_MISS = "knowledge_miss"
    REASONING_GAP = "reasoning_gap"
    STATE_LOSS = "state_loss"
    FINAL_FORMAT = "final_format"
    MULTIMODAL_PARSE = "multimodal_parse"


class ErrorReport(BaseModel):
    task_id: str
    root_cause: str
    error_type: ErrorType
    failed_step: int
    confidence: float
    fix_hint: str


class DPOPair(BaseModel):
    prompt: str
    chosen: str
    rejected: str
    source_trace_id: str
    error_type: str
    run_id: str | None = None


class EvalResult(BaseModel):
    task_id: str
    success: bool
    score: float
    answer: str
    trace: list[TraceEvent]
    error_report: dict[str, Any] | None = None
    dpo_pair: dict[str, Any] | None = None
    modalities: list[str] = Field(default_factory=list)
    source_format: str = "json"
    pipeline: Literal["naive", "full"] = "full"
    timings: StageTiming = Field(default_factory=StageTiming)
    tool_transport: str = "none"
    knowledge_hit: bool = False
    tool_success: bool = False


class TaskCompare(BaseModel):
    task_id: str
    baseline: EvalResult
    current: EvalResult
    improved: bool
    delta_score: float


class SuiteMetrics(BaseModel):
    task_count: int
    baseline_success_rate: float
    current_success_rate: float
    success_rate_delta_pct: float
    baseline_avg_score: float
    current_avg_score: float
    tool_success_rate: float
    knowledge_hit_rate: float
    avg_total_ms: float
    avg_first_event_ms: float


class RunArtifact(BaseModel):
    run_id: str
    created_at: float
    kind: Literal["single", "suite", "upload"] = "single"
    config: RunConfigSnapshot
    tasks: list[Task] = Field(default_factory=list)
    results: list[EvalResult] = Field(default_factory=list)
    compares: list[TaskCompare] = Field(default_factory=list)
    metrics: SuiteMetrics | None = None
    dpo_pairs: list[DPOPair] = Field(default_factory=list)
    notes: str = ""
