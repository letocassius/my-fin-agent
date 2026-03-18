"""
Standalone ingestion script for loading knowledge base documents into ChromaDB.

Can be run directly: python -m rag.ingest
Or called from main.py on startup.
"""

import logging
import sys
import os

# Allow running as script
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from rag.pipeline import ingest_all_documents
from rag.vector_store import get_collection_count

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_ingestion(force: bool = False) -> None:
    """Run the ingestion pipeline."""
    logger.info("Starting knowledge base ingestion...")
    count_before = get_collection_count()

    if count_before > 0 and not force:
        logger.info(f"Collection already has {count_before} chunks. Use force=True to re-ingest.")
        return

    total = ingest_all_documents(force=force)
    count_after = get_collection_count()
    logger.info(f"Ingestion complete. Collection now has {count_after} chunks.")


if __name__ == "__main__":
    force_flag = "--force" in sys.argv
    run_ingestion(force=force_flag)
