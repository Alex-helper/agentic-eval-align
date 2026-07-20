from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.tools import TOOL_SCHEMAS, call_tool


class ToolCall(BaseModel):
    name: str
    arguments: dict


app = FastAPI(title="Agentic Eval MCP Tool Server")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/mcp/health")
async def health() -> dict:
    return {"status": "ok", "protocol": "streamable-http"}


@app.get("/mcp/tools")
async def tools() -> dict:
    return {"tools": TOOL_SCHEMAS}


@app.post("/mcp/call")
async def call(payload: ToolCall) -> dict:
    try:
        return {"name": payload.name, "result": call_tool(payload.name, payload.arguments)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
