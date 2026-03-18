"""RAG pipeline: document ingestion and knowledge retrieval."""

import os
import logging
import hashlib
import json
from pathlib import Path
from .chunker import chunk_markdown
from .embeddings import embed_text, embed_batch
from .vector_store import add_documents, clear_collection, search, get_collection_count

logger = logging.getLogger(__name__)

KNOWLEDGE_BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge_base")
MANIFEST_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".chroma_db", "knowledge_manifest.json")


def _detect_language(path: Path) -> str:
    """Infer document language from file naming convention."""
    return "zh" if path.stem.endswith("_zh") else "en"


def _build_source_label(path: Path, language: str) -> str:
    """Build a human-readable source label for prompts and API responses."""
    base_name = path.stem[:-3] if language == "zh" and path.stem.endswith("_zh") else path.stem
    return f"{base_name} ({language})"


def _compute_manifest(md_files: list[Path]) -> dict:
    """Compute a manifest of knowledge-base files and contents."""
    files = []
    for path in sorted(md_files):
        content_hash = hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
        files.append(
            {
                "file_name": path.name,
                "language": _detect_language(path),
                "sha256": content_hash,
            }
        )
    return {"files": files}


def _load_manifest() -> dict | None:
    """Load the persisted knowledge-base manifest if it exists."""
    manifest_path = Path(MANIFEST_PATH)
    if not manifest_path.exists():
        return None

    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("Knowledge manifest is invalid JSON; forcing re-ingestion")
        return None


def _save_manifest(manifest: dict) -> None:
    """Persist the current manifest after successful ingestion."""
    manifest_path = Path(MANIFEST_PATH)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def ingest_document(file_path: str) -> int:
    """
    Ingest a single markdown document into the vector store.

    Reads the file, chunks it, embeds each chunk, and stores in ChromaDB.
    Returns the number of chunks ingested.
    """
    path = Path(file_path)
    if not path.exists():
        logger.error(f"Document not found: {file_path}")
        return 0

    source_name = path.stem
    language = _detect_language(path)
    source_label = _build_source_label(path, language)

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    if not text.strip():
        logger.warning(f"Empty document: {file_path}")
        return 0

    # Chunk the document
    chunks = chunk_markdown(
        text,
        chunk_size=500,
        overlap=50,
        source=source_name,
    )

    if not chunks:
        logger.warning(f"No chunks generated from: {file_path}")
        return 0

    # Generate embeddings for all chunks in one batch
    texts = [chunk["text"] for chunk in chunks]
    logger.info(f"Embedding {len(texts)} chunks from {source_name}...")
    embeddings = embed_batch(texts)

    # Build metadata and IDs
    metadatas = []
    ids = []
    for i, chunk in enumerate(chunks):
        metadatas.append({
            "source": source_name,
            "source_label": source_label,
            "language": language,
            "file_name": path.name,
            "chunk_index": chunk["chunk_index"],
            "file_path": str(path),
        })
        ids.append(f"{source_name}_chunk_{chunk['chunk_index']}")

    add_documents(texts=texts, embeddings=embeddings, metadatas=metadatas, ids=ids)
    logger.info(f"Ingested {len(chunks)} chunks from '{source_name}'")
    return len(chunks)


def ingest_all_documents(force: bool = False) -> int:
    """
    Ingest all markdown documents from the knowledge_base directory.

    If force=False and the collection already has documents, skip ingestion.
    Returns total number of chunks ingested.
    """
    knowledge_base = Path(KNOWLEDGE_BASE_DIR)
    if not knowledge_base.exists():
        logger.error(f"Knowledge base directory not found: {KNOWLEDGE_BASE_DIR}")
        return 0

    md_files = sorted(knowledge_base.glob("*.md"))
    if not md_files:
        logger.warning(f"No markdown files found in {KNOWLEDGE_BASE_DIR}")
        return 0

    current_manifest = _compute_manifest(md_files)

    if not force:
        count = get_collection_count()
        saved_manifest = _load_manifest()
        if count > 0 and saved_manifest == current_manifest:
            logger.info(f"Knowledge base already contains {count} chunks and manifest is unchanged; skipping ingestion")
            return count

        if count > 0:
            logger.info("Knowledge base files changed; clearing collection and re-ingesting")
            clear_collection()

    total_chunks = 0
    for md_file in md_files:
        logger.info(f"Ingesting: {md_file.name}")
        count = ingest_document(str(md_file))
        total_chunks += count

    _save_manifest(current_manifest)
    logger.info(f"Total ingestion complete: {total_chunks} chunks from {len(md_files)} documents")
    return total_chunks


def search_knowledge(query: str, n_results: int = 5, preferred_language: str | None = None) -> list[dict]:
    """
    Search the knowledge base for relevant chunks.

    Args:
        query: The user's question
        n_results: Number of chunks to retrieve

    Returns:
        List of result dicts with text, metadata, distance, and id
    """
    query_embedding = embed_text(query)
    results = []
    if preferred_language:
        results = search(
            query_embedding=query_embedding,
            n_results=n_results,
            where={"language": preferred_language},
        )

    if not results:
        results = search(query_embedding=query_embedding, n_results=n_results)

    # Filter out very low-relevance results (cosine distance > 0.7 means poor match)
    filtered = [r for r in results if r.get("distance") is None or r["distance"] < 0.7]

    return filtered
