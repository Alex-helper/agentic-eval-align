from __future__ import annotations

import base64
import csv
import io
import json
import mimetypes
import re
import zipfile
from pathlib import Path
from typing import Any

from backend.models import MediaAttachment, MediaKind, Task

SUPPORTED_EXTENSIONS = {
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".csv",
    ".tsv",
    ".txt",
    ".md",
    ".markdown",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".pdf",
    ".docx",
    ".zip",
}

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
DEFAULT_TOOLS = ["search_docs"]


def _slug(name: str) -> str:
    stem = Path(name).stem
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", stem).strip("_").lower()
    return cleaned or "upload_task"


def _guess_mime(filename: str) -> str:
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


def _as_task_dict(item: dict[str, Any], fallback_id: str, source_format: str) -> Task:
    task_id = str(item.get("task_id") or item.get("id") or fallback_id)
    instruction = str(
        item.get("instruction")
        or item.get("prompt")
        or item.get("question")
        or item.get("query")
        or item.get("text")
        or ""
    ).strip()
    if not instruction:
        raise ValueError(f"Task `{task_id}` missing instruction/prompt/question.")

    tools = item.get("tools") or DEFAULT_TOOLS
    if isinstance(tools, str):
        tools = [t.strip() for t in tools.replace(";", ",").split(",") if t.strip()]

    expected = item.get("expected") or {}
    if isinstance(expected, str):
        try:
            expected = json.loads(expected)
        except json.JSONDecodeError:
            expected = {"keyword": expected}

    difficulty = item.get("difficulty") or "medium"
    if difficulty not in {"easy", "medium", "hard"}:
        difficulty = "medium"

    modalities = item.get("modalities") or ["text"]
    attachments = [MediaAttachment(**a) if isinstance(a, dict) else a for a in item.get("attachments") or []]
    return Task(
        task_id=task_id,
        instruction=instruction,
        tools=list(tools),
        expected=dict(expected),
        difficulty=difficulty,
        modalities=list(modalities),
        attachments=attachments,
        source_format=source_format,
    )


def _parse_json_bytes(raw: bytes, filename: str) -> list[Task]:
    text = raw.decode("utf-8-sig")
    data = json.loads(text)
    items = data if isinstance(data, list) else [data]
    return [_as_task_dict(item, f"{_slug(filename)}_{idx}", "json") for idx, item in enumerate(items)]


def _parse_jsonl_bytes(raw: bytes, filename: str) -> list[Task]:
    tasks: list[Task] = []
    for idx, line in enumerate(raw.decode("utf-8-sig").splitlines()):
        if not line.strip():
            continue
        item = json.loads(line)
        tasks.append(_as_task_dict(item, f"{_slug(filename)}_{idx}", "jsonl"))
    return tasks


def _parse_yaml_bytes(raw: bytes, filename: str) -> list[Task]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise ValueError("PyYAML is required for YAML uploads. pip install pyyaml") from exc
    data = yaml.safe_load(raw.decode("utf-8-sig"))
    items = data if isinstance(data, list) else [data]
    return [_as_task_dict(item, f"{_slug(filename)}_{idx}", "yaml") for idx, item in enumerate(items)]


def _parse_table_bytes(raw: bytes, filename: str, delimiter: str) -> list[Task]:
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    tasks: list[Task] = []
    for idx, row in enumerate(reader):
        normalized = { (k or "").strip().lower(): (v or "").strip() for k, v in row.items() }
        payload = {
            "task_id": normalized.get("task_id") or normalized.get("id") or f"{_slug(filename)}_{idx}",
            "instruction": (
                normalized.get("instruction")
                or normalized.get("prompt")
                or normalized.get("question")
                or normalized.get("query")
                or normalized.get("text")
            ),
            "tools": normalized.get("tools") or "search_docs",
            "expected": normalized.get("expected") or {},
            "difficulty": normalized.get("difficulty") or "medium",
        }
        if not payload["instruction"]:
            # treat whole row as instruction context
            payload["instruction"] = "Evaluate multimodal/table row: " + json.dumps(normalized, ensure_ascii=False)
        task = _as_task_dict(payload, f"{_slug(filename)}_{idx}", "csv" if delimiter == "," else "tsv")
        task.modalities = ["text", "table"]
        tasks.append(task)
    if not tasks:
        raise ValueError("CSV/TSV has no data rows.")
    return tasks


def _doc_task(filename: str, text: str, source_format: str, kind: MediaKind, mime: str) -> Task:
    excerpt = text.strip()
    if len(excerpt) > 12000:
        excerpt = excerpt[:12000] + "\n...[truncated]"
    attachment = MediaAttachment(
        kind=kind,
        filename=filename,
        mime=mime,
        text_excerpt=excerpt[:2000],
    )
    return Task(
        task_id=_slug(filename),
        instruction=(
            "Evaluate this uploaded document as a complex reasoning / Agent task. "
            "Extract requirements, identify needed tools, and produce a structured evaluation.\n\n"
            f"Document ({filename}):\n{excerpt}"
        ),
        tools=DEFAULT_TOOLS,
        expected={"keyword": "", "requires_knowledge": False},
        modalities=["text", kind.value],
        attachments=[attachment],
        source_format=source_format,
    )


def _parse_text_bytes(raw: bytes, filename: str) -> list[Task]:
    return [_doc_task(filename, raw.decode("utf-8-sig", errors="replace"), "text", MediaKind.TEXT, "text/plain")]


def _parse_markdown_bytes(raw: bytes, filename: str) -> list[Task]:
    return [_doc_task(filename, raw.decode("utf-8-sig", errors="replace"), "markdown", MediaKind.DOCUMENT, "text/markdown")]


def _parse_image_bytes(raw: bytes, filename: str) -> list[Task]:
    mime = _guess_mime(filename)
    b64 = base64.b64encode(raw).decode("ascii")
    width = height = None
    try:
        from PIL import Image

        with Image.open(io.BytesIO(raw)) as img:
            width, height = img.size
    except Exception:
        pass

    attachment = MediaAttachment(
        kind=MediaKind.IMAGE,
        filename=filename,
        mime=mime,
        text_excerpt=f"image bytes={len(raw)} width={width} height={height}",
        data_b64=b64,
        width=width,
        height=height,
    )
    return [
        Task(
            task_id=_slug(filename),
            instruction=(
                "Multimodal evaluation: inspect the attached image, identify any API/tool/workflow "
                "requirements implied by the visual content, and decide which tools should be called."
            ),
            tools=["search_docs"],
            expected={"requires_knowledge": True, "keyword": "api"},
            modalities=["image", "text"],
            attachments=[attachment],
            source_format="image",
        )
    ]


def _parse_pdf_bytes(raw: bytes, filename: str) -> list[Task]:
    text_parts: list[str] = []
    page_count = 0
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(raw))
        page_count = len(reader.pages)
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
    except Exception as exc:
        text_parts.append(f"[pdf parse warning: {exc}]")

    text = "\n".join(text_parts).strip() or f"[empty pdf text extracted from {filename}]"
    task = _doc_task(filename, text, "pdf", MediaKind.PDF, "application/pdf")
    task.attachments[0].page_count = page_count
    task.attachments[0].data_b64 = base64.b64encode(raw).decode("ascii") if len(raw) < 1_500_000 else None
    return [task]


def _parse_docx_bytes(raw: bytes, filename: str) -> list[Task]:
    try:
        from docx import Document
    except ImportError as exc:  # pragma: no cover
        raise ValueError("python-docx is required for DOCX uploads. pip install python-docx") from exc
    document = Document(io.BytesIO(raw))
    text = "\n".join(p.text for p in document.paragraphs if p.text.strip())
    return [_doc_task(filename, text or f"[empty docx: {filename}]", "docx", MediaKind.DOCUMENT, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")]


def _parse_zip_bytes(raw: bytes, filename: str) -> list[Task]:
    tasks: list[Task] = []
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        for info in zf.infolist():
            if info.is_dir() or info.filename.startswith("__MACOSX"):
                continue
            nested_name = Path(info.filename).name
            if Path(nested_name).suffix.lower() not in SUPPORTED_EXTENSIONS - {".zip"}:
                continue
            nested_raw = zf.read(info)
            tasks.extend(parse_bytes(nested_name, nested_raw))
    if not tasks:
        raise ValueError(f"ZIP `{filename}` contained no supported files.")
    for task in tasks:
        task.source_format = f"zip:{task.source_format}"
    return tasks


def parse_bytes(filename: str, raw: bytes) -> list[Task]:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext or '(none)'}. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
    if not raw:
        raise ValueError(f"Empty file: {filename}")

    if ext == ".json":
        return _parse_json_bytes(raw, filename)
    if ext == ".jsonl":
        return _parse_jsonl_bytes(raw, filename)
    if ext in {".yaml", ".yml"}:
        return _parse_yaml_bytes(raw, filename)
    if ext == ".csv":
        return _parse_table_bytes(raw, filename, ",")
    if ext == ".tsv":
        return _parse_table_bytes(raw, filename, "\t")
    if ext == ".txt":
        return _parse_text_bytes(raw, filename)
    if ext in {".md", ".markdown"}:
        return _parse_markdown_bytes(raw, filename)
    if ext in IMAGE_EXTS:
        return _parse_image_bytes(raw, filename)
    if ext == ".pdf":
        return _parse_pdf_bytes(raw, filename)
    if ext == ".docx":
        return _parse_docx_bytes(raw, filename)
    if ext == ".zip":
        return _parse_zip_bytes(raw, filename)
    raise ValueError(f"Unhandled extension: {ext}")


def parse_path(path: Path) -> list[Task]:
    return parse_bytes(path.name, path.read_bytes())


def supported_formats() -> dict[str, Any]:
    return {
        "extensions": sorted(SUPPORTED_EXTENSIONS),
        "groups": {
            "structured": [".json", ".jsonl", ".yaml", ".yml"],
            "table": [".csv", ".tsv"],
            "text": [".txt", ".md", ".markdown"],
            "image": sorted(IMAGE_EXTS),
            "document": [".pdf", ".docx"],
            "archive": [".zip"],
        },
        "notes": [
            "Structured files should include task_id/instruction/tools when possible.",
            "CSV aliases: id/prompt/question/query/text are accepted.",
            "Images are evaluated as multimodal tasks with visual context.",
            "ZIP archives are recursively parsed.",
            "All uploads stay local; nothing is sent to third-party storage.",
        ],
    }
