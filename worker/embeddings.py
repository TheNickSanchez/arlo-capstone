"""Embedding client for `kb_articles` / `kb_search` (SAD §4 AD-14; 1536-d).

OpenAI-compatible `/embeddings` endpoint (SAD Assumptions: "Default embedding
path is OpenAI-compatible; an Anthropic/org gateway is used only if it emits
the same dimension"). `EMBEDDING_API_KEY` / `EMBEDDING_BASE_URL` /
`EMBEDDING_MODEL` are env names only (never defaulted to a real secret).
"""

from __future__ import annotations

import httpx

from backend.app.config import settings
from backend.app.models.kb_article import EMBEDDING_DIM


class EmbeddingUnavailableError(RuntimeError):
    """Provider unreachable, misconfigured, or returned the wrong dimension."""


async def embed_text(text: str) -> list[float]:
    if not settings.embedding_api_key or not settings.embedding_base_url:
        raise EmbeddingUnavailableError(
            "EMBEDDING_API_KEY / EMBEDDING_BASE_URL not configured"
        )

    url = settings.embedding_base_url.rstrip("/") + "/embeddings"
    headers = {"Authorization": f"Bearer {settings.embedding_api_key}"}
    body = {"model": settings.embedding_model, "input": text}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=body, headers=headers)
            response.raise_for_status()
            payload = response.json()
        embedding = payload["data"][0]["embedding"]
    except Exception as exc:
        raise EmbeddingUnavailableError(f"embedding request failed: {exc}") from exc

    if len(embedding) != EMBEDDING_DIM:
        raise EmbeddingUnavailableError(
            f"embedding provider returned dim={len(embedding)}, expected {EMBEDDING_DIM}"
        )
    return embedding
