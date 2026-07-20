from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

from backend.models import MediaAttachment, MediaKind, Task

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", encoding="utf-8-sig")


@dataclass
class LLMResponse:
    content: str
    model: str
    used_fallback: bool = False


class LLMClient:
    """DeepSeek via OpenAI-compatible API — same env vars as sibling projects."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None):
        self.api_key = (
            api_key
            or os.getenv("OPENAI_API_KEY", "")
            or os.getenv("DEEPSEEK_API_KEY", "")
        ).strip()
        self.base_url = (
            base_url
            or os.getenv("OPENAI_BASE_URL")
            or os.getenv("DEEPSEEK_BASE_URL")
            or "https://api.deepseek.com/v1"
        ).rstrip("/")
        self.model = (
            model
            or os.getenv("MODEL_NAME")
            or os.getenv("DEEPSEEK_MODEL")
            or "deepseek-chat"
        ).strip()
        self.timeout = float(os.getenv("LLM_TIMEOUT_SEC") or os.getenv("LLM_TIMEOUT_SECONDS") or "60")
        self.max_retries = int(os.getenv("LLM_MAX_RETRIES", "2"))

    def configured(self) -> bool:
        return bool(self.api_key) and not self.api_key.startswith("sk-xxx")

    def build_user_content(self, task: Task, memory_summary: str) -> str | list[dict[str, Any]]:
        text = (
            f"{task.instruction}\n\n"
            f"Modalities: {', '.join(task.modalities) or 'text'}\n"
            f"Source format: {task.source_format}\n"
            f"Memory:\n{memory_summary}\n"
        )
        image_parts: list[dict[str, Any]] = []
        for att in task.attachments:
            if att.kind == MediaKind.IMAGE and att.data_b64:
                mime = att.mime or "image/png"
                image_parts.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{att.data_b64}"},
                    }
                )
            elif att.text_excerpt:
                text += f"\nAttachment[{att.kind.value}:{att.filename}]: {att.text_excerpt[:1500]}\n"

        if not image_parts:
            return text
        return [{"type": "text", "text": text}, *image_parts]

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        if not self.configured():
            return self._fallback(messages, reason="missing_api_key")

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
        }
        if tools:
            payload["tools"] = tools

        last_error = ""
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    content = data["choices"][0]["message"].get("content", "") or ""
                    return LLMResponse(content=content, model=self.model)
            except Exception as exc:  # pragma: no cover - network dependent
                last_error = str(exc)
                if resp_is_vision_error(last_error):
                    messages = strip_images(messages)
                    payload["messages"] = messages
                if attempt < self.max_retries:
                    await asyncio.sleep(0.6 * (attempt + 1))

        return self._fallback(messages, reason=f"retry_exhausted:{last_error[:120]}")

    def _fallback(self, messages: list[dict[str, Any]], reason: str) -> LLMResponse:
        user = ""
        for m in reversed(messages):
            if m.get("role") != "user":
                continue
            content = m.get("content")
            if isinstance(content, str):
                user = content
            elif isinstance(content, list):
                user = " ".join(str(p.get("text", "")) for p in content if isinstance(p, dict))
            break
        content = (
            "DEMO_FALLBACK: 已在无外部 API 情况下完成可复现推理。"
            f" 输入摘要：{user[:180]}。建议按工具 schema 检索知识、计算结果并校验最终格式。"
            f" fallback_reason={reason}"
        )
        return LLMResponse(content=content, model="demo-fallback", used_fallback=True)


def resp_is_vision_error(message: str) -> bool:
    lowered = message.lower()
    return any(token in lowered for token in ("image_url", "vision", "multimodal", "unsupported"))


def strip_images(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for msg in messages:
        content = msg.get("content")
        if not isinstance(content, list):
            cleaned.append(msg)
            continue
        texts = [p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"]
        cleaned.append({**msg, "content": "\n".join(texts) + "\n[images stripped for text-only model]"})
    return cleaned


def attachment_summary(attachments: list[MediaAttachment]) -> str:
    if not attachments:
        return "none"
    return "; ".join(f"{a.kind.value}:{a.filename}" for a in attachments)
