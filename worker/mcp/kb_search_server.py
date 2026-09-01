"""`kb_search` — in-process Claude Agent SDK MCP server (SAD §2 tool contract).

Read-only vector similarity search over `kb_articles` (pgvector cosine
distance). Registered via `create_sdk_mcp_server` so it runs in-process
(adapter default) rather than as a separate stdio/HTTP server — there is no
vendor tenant behind it, only PostgreSQL.

Embeds `query` with the configured embedding provider at call time (no
Anthropic/Claude call needed; this is a plain vector lookup). If the
embedding provider or DB is unavailable, returns a declared gap rather than
inventing SOP text (SAD §2 tool contract "Failure" row) — the Investigation
Activity must record that gap on the evidence pack, not skip HITL.
"""

from __future__ import annotations

from typing import Any

from claude_agent_sdk import McpSdkServerConfig, create_sdk_mcp_server, tool
from sqlalchemy import select

from backend.app.db.session import session_scope
from backend.app.models.kb_article import KbArticle
from worker.embeddings import EmbeddingUnavailableError, embed_text

_DEFAULT_TOP_K = 5
_MAX_TOP_K = 10
_EXCERPT_CHARS = 600


async def kb_search_direct(
    query: str, category: str | None = None, top_k: int = _DEFAULT_TOP_K
) -> dict[str, Any]:
    """Shared implementation for the model-facing tool *and* the Activity's automatic
    pre-call (SAD §2 step 2: "Automatically ... call kb_search ... Inject ... into
    Claude prompt context"). Kept independent of the `@tool`-wrapped MCP envelope so
    `worker.activities.investigate` can call it as plain Python, not a model tool use.
    """
    query = query.strip()
    top_k = max(1, min(top_k, _MAX_TOP_K))

    if not query:
        return {"hits": [], "query": "", "top_k": 0, "gap": "empty query"}

    try:
        query_embedding = await embed_text(query)
    except EmbeddingUnavailableError as exc:
        return {
            "hits": [],
            "query": query,
            "top_k": top_k,
            "gap": f"embedding provider unavailable: {exc}",
        }

    async with session_scope() as session:
        stmt = select(
            KbArticle.id,
            KbArticle.title,
            KbArticle.category,
            KbArticle.content,
            KbArticle.embedding.cosine_distance(query_embedding).label("distance"),
        ).order_by("distance").limit(top_k)
        if category:
            stmt = stmt.where(KbArticle.category == category)
        rows = (await session.execute(stmt)).all()

    hits = [
        {
            "id": str(row.id),
            "title": row.title,
            "category": row.category,
            "content_excerpt": row.content[:_EXCERPT_CHARS],
            "score": round(1.0 - float(row.distance), 4),
        }
        for row in rows
    ]
    return {"hits": hits, "query": query, "top_k": top_k}


@tool(
    "kb_search",
    "Semantic search over internal SOP/runbook articles (kb_articles). Read-only; "
    "Investigation phase only (PRD FR-P0-02/03).",
    {"query": str, "category": str, "top_k": int},
)
async def kb_search(args: dict[str, Any]) -> dict[str, Any]:
    import json

    payload = await kb_search_direct(
        query=str(args.get("query", "")),
        category=args.get("category") or None,
        top_k=int(args.get("top_k") or _DEFAULT_TOP_K),
    )
    return {"content": [{"type": "text", "text": json.dumps(payload)}]}


def build_kb_search_server() -> McpSdkServerConfig:
    return create_sdk_mcp_server(name="kb", version="1.0.0", tools=[kb_search])
