"""Text chunking utilities for the RAG pipeline."""

import re
from typing import Optional


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
    source: Optional[str] = None,
) -> list[dict]:
    """
    Split text into overlapping chunks for embedding.

    Chunks at sentence boundaries when possible, targeting ~chunk_size tokens.
    Uses approximate token count (1 token ≈ 4 characters).

    Args:
        text: The text to chunk
        chunk_size: Target chunk size in tokens (approx)
        overlap: Number of tokens to overlap between chunks
        source: Optional source identifier to include in metadata

    Returns:
        List of dicts with 'text', 'chunk_index', and optional 'source'
    """
    # Approximate character counts (1 token ≈ 4 chars for English)
    char_size = chunk_size * 4
    char_overlap = overlap * 4

    # Clean whitespace
    text = re.sub(r"\n{3,}", "\n\n", text.strip())

    # Split into sentences for cleaner boundaries
    # Split on sentence-ending punctuation followed by whitespace/newline.
    # Include Chinese punctuation so translated documents chunk cleanly.
    sentence_pattern = re.compile(r"(?<=[.!?。！？])\s+|(?<=\n\n)")
    sentences = sentence_pattern.split(text)

    # Re-attach any split markers lost during split
    # Rebuild with original separators
    raw_sentences = re.split(r"((?<=[.!?。！？])\s+|(?<=\n\n))", text)
    sentences = []
    current = ""
    for part in raw_sentences:
        current += part
        # Check if we have a complete sentence-like unit
        if re.search(r"[.!?。！？]\s*$", current) or current.endswith("\n\n"):
            sentences.append(current)
            current = ""
    if current.strip():
        sentences.append(current)

    if not sentences:
        sentences = [text]

    chunks = []
    current_chunk = ""
    chunk_index = 0

    for sentence in sentences:
        if not sentence.strip():
            continue

        # If adding this sentence would exceed chunk size, save current chunk
        if len(current_chunk) + len(sentence) > char_size and current_chunk.strip():
            chunk_data = {"text": current_chunk.strip(), "chunk_index": chunk_index}
            if source:
                chunk_data["source"] = source
            chunks.append(chunk_data)
            chunk_index += 1

            # Start new chunk with overlap from end of current chunk
            if char_overlap > 0 and len(current_chunk) > char_overlap:
                current_chunk = current_chunk[-char_overlap:] + " " + sentence
            else:
                current_chunk = sentence
        else:
            current_chunk += " " + sentence if current_chunk else sentence

    # Don't forget the last chunk
    if current_chunk.strip():
        chunk_data = {"text": current_chunk.strip(), "chunk_index": chunk_index}
        if source:
            chunk_data["source"] = source
        chunks.append(chunk_data)

    return chunks


def chunk_markdown(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
    source: Optional[str] = None,
) -> list[dict]:
    """
    Chunk markdown text, preserving section structure.

    Attempts to split at markdown headers (##, ###) first, then
    falls back to sentence-level chunking within each section.
    """
    # Split on markdown headers (## or ###)
    header_pattern = re.compile(r"^(#{1,3}\s.+)$", re.MULTILINE)
    parts = header_pattern.split(text)

    sections = []
    current_header = ""
    current_body = ""

    for part in parts:
        if header_pattern.match(part.strip()):
            # Save previous section
            if current_body.strip():
                sections.append((current_header, current_body.strip()))
            current_header = part.strip()
            current_body = ""
        else:
            current_body += part

    # Last section
    if current_body.strip():
        sections.append((current_header, current_body.strip()))

    all_chunks = []
    for header, body in sections:
        # Prepend header to each chunk for context
        section_text = f"{header}\n\n{body}" if header else body
        section_chunks = chunk_text(section_text, chunk_size=chunk_size, overlap=overlap, source=source)
        all_chunks.extend(section_chunks)

    # Re-index
    for i, chunk in enumerate(all_chunks):
        chunk["chunk_index"] = i

    return all_chunks
