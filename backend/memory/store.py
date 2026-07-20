from __future__ import annotations

import json
from pathlib import Path
from time import time
from typing import Any

from backend.models import TraceEvent


ROOT = Path(__file__).resolve().parents[2]


class ShortTermMemory:
    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    def add(self, event_type: str, message: str, payload: dict[str, Any] | None = None) -> TraceEvent:
        event = TraceEvent(type=event_type, message=message, payload=payload or {}, timestamp=time())
        self.events.append(event)
        return event

    def summarize(self, max_events: int = 12) -> str:
        recent = self.events[-max_events:]
        return "\n".join(f"{idx + 1}. [{e.type}] {e.message}" for idx, e in enumerate(recent))


class LongTermMemory:
    def __init__(self, index_path: Path | None = None) -> None:
        self.index_path = index_path or ROOT / "data" / "graphrag_index" / "index.json"
        self.index = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.index_path.exists():
            return {"nodes": [], "communities": []}
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def search(self, query: str, k: int = 4) -> list[dict[str, Any]]:
        q = query.lower()
        scored: list[tuple[int, dict[str, Any]]] = []
        for node in self.index.get("nodes", []):
            text = f"{node.get('title','')} {node.get('content','')} {' '.join(node.get('tags', []))}".lower()
            score = sum(1 for token in q.split() if token in text)
            if score:
                scored.append((score, node))
        if not scored:
            return self.index.get("nodes", [])[:k]
        return [item for _, item in sorted(scored, key=lambda x: x[0], reverse=True)[:k]]

    def global_summary(self) -> str:
        communities = self.index.get("communities", [])
        return "\n".join(f"- {c.get('name')}: {c.get('summary')}" for c in communities)
