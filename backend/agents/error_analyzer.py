from __future__ import annotations

from backend.models import ErrorReport, ErrorType, TraceEvent


class ErrorAnalyzer:
    """Self-developed fine-grained trajectory error analyzer."""

    def analyze(self, task_id: str, trace: list[TraceEvent], expected: dict | None = None) -> ErrorReport:
        expected = expected or {}
        text = " ".join(f"{e.type} {e.message} {e.payload}" for e in trace).lower()

        if "unknown tool" in text or "tool not allowed" in text:
            error_type = ErrorType.TOOL_SELECTION
            cause = "Agent selected an unavailable tool."
            hint = "Constrain tool choice to the declared task schema."
        elif "unsupported expression" in text or "argument" in text:
            error_type = ErrorType.TOOL_ARGUMENT
            cause = "Tool arguments failed validation."
            hint = "Generate arguments from JSON schema before calling the tool."
        elif expected.get("requires_knowledge") and "search_docs" not in text:
            error_type = ErrorType.KNOWLEDGE_MISS
            cause = "Agent answered without retrieving required GraphRAG knowledge."
            hint = "Call search_docs before reasoning on API-specific requirements."
        elif "state" in text or "lost" in text:
            error_type = ErrorType.STATE_LOSS
            cause = "Long-horizon task state was not preserved."
            hint = "Summarize short-term memory before the next worker step."
        elif "format" in text:
            error_type = ErrorType.FINAL_FORMAT
            cause = "Final answer did not follow expected format."
            hint = "Validate final answer against expected output schema."
        else:
            error_type = ErrorType.REASONING_GAP
            cause = "Reasoning chain missed at least one required verification step."
            hint = "Add verifier worker pass before final answer."

        failed_step = max(1, min(len(trace), next((i + 1 for i, e in enumerate(trace) if e.type == "error"), len(trace))))
        return ErrorReport(
            task_id=task_id,
            root_cause=cause,
            error_type=error_type,
            failed_step=failed_step,
            confidence=0.82,
            fix_hint=hint,
        )
