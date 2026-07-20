from __future__ import annotations

import ast
import operator
from typing import Any


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_docs",
            "description": "Search GraphRAG indexed API documentation.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Safely evaluate arithmetic expressions.",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        },
    },
]


def search_docs(query: str) -> dict[str, Any]:
    from backend.memory.store import LongTermMemory

    memory = LongTermMemory()
    return {"query": query, "results": memory.search(query)}


def calculator(expression: str) -> dict[str, Any]:
    allowed_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    def eval_node(node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in allowed_ops:
            return allowed_ops[type(node.op)](eval_node(node.left), eval_node(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in allowed_ops:
            return allowed_ops[type(node.op)](eval_node(node.operand))
        raise ValueError("unsupported expression")

    value = eval_node(ast.parse(expression, mode="eval").body)
    return {"expression": expression, "value": value}


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "search_docs":
        return search_docs(str(arguments.get("query", "")))
    if name == "calculator":
        return calculator(str(arguments.get("expression", "0")))
    raise ValueError(f"unknown tool: {name}")
