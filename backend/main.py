"""FastAPI application entry point for the Financial Asset Q&A System."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI  # noqa: E402 — must load env before app imports
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from api.routes import router as api_router  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _run_startup_ingestion():
    """Ingest knowledge base documents on startup (skips if already done)."""
    try:
        from rag.pipeline import ingest_all_documents
        logger.info("Checking knowledge base ingestion status...")
        total = ingest_all_documents(force=False)
        if total > 0:
            logger.info(f"Knowledge base ready with {total} chunks")
    except Exception as e:
        logger.warning(f"Knowledge base ingestion failed (RAG may not work): {e}")
        logger.warning("Ensure OPENAI_API_KEY is set for RAG functionality")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler: runs startup tasks before serving."""
    logger.info("Starting Financial Asset Q&A System...")
    _run_startup_ingestion()
    logger.info("Backend ready. Serving requests.")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Financial Asset Q&A API",
    description="LLM-powered financial question answering with market data and RAG",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS: allow frontend dev server and production origins
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Mount API router
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "service": "Financial Asset Q&A API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/health",
    }
