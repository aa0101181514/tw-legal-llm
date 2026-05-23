"""
TW Legal LLM (TLL) — thin MCP client.

This is a stdio MCP server that proxies tool calls to the TLL backend at
https://tll.dr-lawbot.com. It contains NO retrieval logic, NO ranking, and
makes NO LLM calls. Your AI client (Claude Desktop, Cursor, etc.) is
responsible for generating answers; this client only fetches judgments.

Hard rules (memory: project_tll_p0_spec_20260524):
  * NO retrieval internals (no ES / vector store / ranking) here.
  * NO LLM calls.
  * Pure proxy: receives MCP tool_calls, forwards to remote backend, returns response.

Usage (via Claude Desktop config):

    {
      "mcpServers": {
        "tw-legal-llm": {
          "command": "uvx",
          "args": ["--from", "git+https://github.com/aa0101181514/tw-legal-llm", "tw-legal-llm"],
          "env": { "TLL_API_KEY": "tll_xxxxx" }
        }
      }
    }
"""
from __future__ import annotations

import os
import sys
import json
import asyncio
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


BACKEND_URL = os.environ.get("TLL_BACKEND_URL", "https://tll.dr-lawbot.com")
API_KEY = os.environ.get("TLL_API_KEY", "")
REQUEST_TIMEOUT_SEC = float(os.environ.get("TLL_REQUEST_TIMEOUT", "30"))


# ──────────────────────────────────────────────────────────
# Tool schemas — these descriptions are PUBLIC. Do NOT add
# implementation details (no stack mentions).
# ──────────────────────────────────────────────────────────
SEARCH_TOOL = Tool(
    name="search_judgments",
    description=(
        "Search Taiwan court judgments by legal issue, keyword, case number, court name, "
        "or statute. Returns citation-ready judgment metadata and short excerpts. "
        "Do not cite judgments not returned by this tool."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search terms in Chinese (Traditional). Can be a legal issue, keyword, case number, court name, or statute reference.",
            },
            "search_type": {
                "type": "string",
                "enum": ["hybrid", "keyword", "phrase"],
                "description": "Search mode. Default 'hybrid'.",
                "default": "hybrid",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (1-20).",
                "default": 10,
                "minimum": 1,
                "maximum": 20,
            },
        },
        "required": ["query"],
    },
)

FULLTEXT_TOOL = Tool(
    name="get_judgment_fulltext",
    description=(
        "Retrieve available text for a judgment selected from search results. "
        "Use when more detail is needed for legal analysis. Citation must match "
        "exactly the citation_text from search_judgments."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "doc_id": {
                "type": "string",
                "description": "Judgment doc_id from a recent search_judgments result.",
            },
            "result_token": {
                "type": "string",
                "description": "result_token from the search_judgments response that returned this doc_id. Required to authorise fulltext lookup.",
            },
        },
        "required": ["doc_id", "result_token"],
    },
)


# ──────────────────────────────────────────────────────────
# Server
# ──────────────────────────────────────────────────────────
server: Server = Server("tw-legal-llm")


@server.list_tools()
async def _list_tools() -> list[Tool]:
    return [SEARCH_TOOL, FULLTEXT_TOOL]


async def _call_backend(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    """POST to backend with Bearer auth. Errors come back opaque."""
    if not API_KEY:
        return {"error": "missing_api_key", "message": "Set TLL_API_KEY environment variable."}
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "tw-legal-llm-client/0.1.0",
    }
    url = f"{BACKEND_URL}{path}"
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SEC) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException:
            return {"error": "timeout", "message": "Backend timed out."}
        except httpx.HTTPError as e:
            return {"error": "network_error", "message": str(e)[:200]}
    if resp.status_code >= 400:
        try:
            body = resp.json()
        except Exception:
            body = {"error": "backend_error", "message": resp.text[:200]}
        return body
    return resp.json()


@server.call_tool()
async def _call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    if name == "search_judgments":
        result = await _call_backend("/v1/search", arguments)
    elif name == "get_judgment_fulltext":
        result = await _call_backend("/v1/fulltext", arguments)
    else:
        result = {"error": "unknown_tool", "message": f"Unknown tool: {name}"}
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]


async def _amain() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    """Entrypoint used by `[project.scripts] tw-legal-llm = ...`."""
    if not API_KEY:
        print(
            "tw-legal-llm:沒有設定 TLL_API_KEY。請在 MCP 用戶端設定檔的 env 區塊加入。\n"
            "  申請早期試用 API key:aa.0101181514@gmail.com",
            file=sys.stderr,
        )
    asyncio.run(_amain())


if __name__ == "__main__":
    main()
