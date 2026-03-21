"""FastAPI application entry point for the Financial Asset Q&A System."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI  # noqa: E402 — must load env before app imports
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from api.routes import router as api_router  # noqa: E402
from config import get_settings  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler: runs startup tasks before serving."""
    logger.info("Starting Financial Asset Q&A System...")
    logger.info("Backend ready. Serving requests.")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Financial Asset Q&A API",
    description="LLM-powered financial question answering with market data and RAG",
    version="0.1.0",
    lifespan=lifespan,
)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
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
