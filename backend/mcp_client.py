from __future__ import annotations

import os
from typing import Any

import httpx

from backend.tools import call_tool as local_call_tool


class MCPClient:
    """HTTP client for the local MCP tool server. Falls back to in-process tools."""

    def __init__(self, base_url: str | None = None, timeout: float = 8.0) -> None:
        self.base_url = (base_url or os.getenv("MCP_BASE_URL", "http://127.0.0.1:8100")).rstrip("/")
        self.timeout = timeout

    async def health(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{self.base_url}/mcp/health")
                resp.raise_for_status()
                data = resp.json()
                return {"ok": True, "transport": "mcp_http", "base_url": self.base_url, **data}
        except Exception as exc:
            return {"ok": False, "transport": "fallback_local", "base_url": self.base_url, "error": str(exc)}

    async def list_tools(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{self.base_url}/mcp/tools")
                resp.raise_for_status()
                return {"transport": "mcp_http", "tools": resp.json().get("tools", [])}
        except Exception as exc:
            return {"transport": "fallback_local", "error": str(exc), "tools": []}

    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/mcp/call",
                    json={"name": name, "arguments": arguments},
                )
                resp.raise_for_status()
                payload = resp.json()
                return {
                    "transport": "mcp_http",
                    "name": name,
                    "result": payload.get("result", payload),
                    "fallback": False,
                }
        except Exception as exc:
            result = local_call_tool(name, arguments)
            return {
                "transport": "fallback_local",
                "name": name,
                "result": result,
                "fallback": True,
                "error": str(exc),
            }
