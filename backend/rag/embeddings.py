"""OpenAI embeddings wrapper."""

from __future__ import annotations

import logging

from openai import OpenAI

from config import get_settings

logger = logging.getLogger(__name__)

_client: OpenAI | None = None
EMBEDDING_DIMENSIONS = 1536


def get_client() -> OpenAI:
    global _client
    if _client is None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def embed_text(text: str) -> list[float]:
    """
    Generate an embedding vector for a single text string.

    Returns a list of floats (1536 dimensions for text-embedding-3-small).
    """
    client = get_client()
    text = text.replace("\n", " ").strip()
    if not text:
        raise ValueError("Cannot embed empty text")

    response = client.embeddings.create(
        input=[text],
        model=get_settings().embedding_model,
    )
    return response.data[0].embedding


def embed_batch(texts: list[str]) -> list[list[float]]:
    """
    Generate embedding vectors for a list of texts.

    Returns a list of embedding vectors.
    Batches requests to stay within API limits.
    """
    client = get_client()
    cleaned = [t.replace("\n", " ").strip() for t in texts]

    if not cleaned:
        return []

    # OpenAI allows up to 2048 inputs per request for this model
    BATCH_SIZE = 100
    all_embeddings = []

    for i in range(0, len(cleaned), BATCH_SIZE):
        batch = cleaned[i : i + BATCH_SIZE]
        response = client.embeddings.create(
            input=batch,
            model=get_settings().embedding_model,
        )
        # Response data is sorted by index
        batch_embeddings = [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
        all_embeddings.extend(batch_embeddings)

    return all_embeddings
