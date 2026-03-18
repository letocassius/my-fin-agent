"""ChromaDB vector store wrapper for the RAG pipeline."""

import os
import logging
from typing import Optional
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)

# Persist ChromaDB to a local directory
CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".chroma_db")
COLLECTION_NAME = "financial_knowledge"

_client: chromadb.PersistentClient | None = None
_collection = None


def get_chroma_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=CHROMA_PERSIST_DIR,
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def get_collection():
    global _collection
    if _collection is None:
        client = get_chroma_client()
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def add_documents(
    texts: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict],
    ids: list[str],
) -> None:
    """
    Add documents with their embeddings to the vector store.

    Args:
        texts: List of text chunks
        embeddings: Corresponding embedding vectors
        metadatas: Metadata dicts for each chunk (source, chunk_index, etc.)
        ids: Unique IDs for each chunk
    """
    collection = get_collection()

    if not texts:
        logger.warning("add_documents called with empty texts list")
        return

    if len(texts) != len(embeddings) != len(metadatas) != len(ids):
        raise ValueError("texts, embeddings, metadatas, and ids must have the same length")

    # ChromaDB upsert to handle re-ingestion gracefully
    collection.upsert(
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids,
    )
    logger.info(f"Upserted {len(texts)} documents into ChromaDB collection '{COLLECTION_NAME}'")


def search(
    query_embedding: list[float],
    n_results: int = 5,
    where: Optional[dict] = None,
) -> list[dict]:
    """
    Perform vector similarity search against the knowledge base.

    Args:
        query_embedding: The query vector
        n_results: Number of results to return
        where: Optional metadata filter (ChromaDB where clause)

    Returns:
        List of result dicts with: text, metadata, distance, id
    """
    collection = get_collection()

    count = collection.count()
    if count == 0:
        logger.warning("ChromaDB collection is empty — knowledge base not yet ingested")
        return []

    # Cap n_results at collection size
    n_results = min(n_results, count)

    query_kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        query_kwargs["where"] = where

    results = collection.query(**query_kwargs)

    # Flatten results into a list of dicts
    output = []
    if results["documents"] and results["documents"][0]:
        for i, doc in enumerate(results["documents"][0]):
            output.append({
                "text": doc,
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else None,
                "id": results["ids"][0][i] if results["ids"] else None,
            })

    return output


def get_collection_count() -> int:
    """Return the number of documents in the collection."""
    collection = get_collection()
    return collection.count()


def get_all_metadatas() -> list[dict]:
    """Return all stored metadatas from the collection."""
    collection = get_collection()
    count = collection.count()
    if count == 0:
        return []

    results = collection.get(include=["metadatas"])
    return results.get("metadatas", []) or []


def clear_collection() -> None:
    """Delete and recreate the collection (for re-ingestion)."""
    global _collection
    client = get_chroma_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    _collection = None
    get_collection()  # Recreate
    logger.info(f"Cleared and recreated collection '{COLLECTION_NAME}'")
