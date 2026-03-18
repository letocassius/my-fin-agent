"""API route handlers for the financial Q&A system."""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.router import route_query
from config import get_provider_registry

logger = logging.getLogger(__name__)

router = APIRouter()


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="The user's financial question")


class QueryResponse(BaseModel):
    answer: str
    data_section: str | None = None
    analysis_section: str
    sources: list[str] = []
    query_type: str  # "market" or "knowledge"
    ticker: str | None = None
    latency_ms: float | None = None
    source_type: str | None = None  # "local_kb", "wikipedia", or "none"


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class ProviderResponse(BaseModel):
    name: str
    enabled: bool
    configured: bool
    required: bool
    api_key_env: str | None = None
    base_url: str | None = None
    model: str | None = None
    notes: str | None = None


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        service="fin-agent-backend",
        version="0.1.0",
    )


@router.get("/providers", response_model=list[ProviderResponse])
async def list_providers():
    """List backend provider configuration without exposing secrets."""
    return [ProviderResponse(**provider) for provider in get_provider_registry()]


@router.post("/query", response_model=QueryResponse)
async def handle_query(request: QueryRequest):
    """
    Main query endpoint. Accepts a financial question and returns a structured answer.

    The backend classifies the query as either:
    - market: Fetches live data from yfinance and formats a structured response
    - knowledge: Retrieves relevant chunks from the knowledge base and generates a grounded answer
    """
    start = time.monotonic()

    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    logger.info(f"Received query: {request.query!r}")

    try:
        result = route_query(request.query)
    except ValueError as e:
        # Configuration errors (missing API keys, etc.)
        logger.error(f"Configuration error: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error processing query: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    latency_ms = round((time.monotonic() - start) * 1000, 1)
    logger.info(f"Query processed in {latency_ms}ms (type={result.get('query_type')})")

    return QueryResponse(
        answer=result.get("answer", ""),
        data_section=result.get("data_section"),
        analysis_section=result.get("analysis_section", ""),
        sources=result.get("sources", []),
        query_type=result.get("query_type", "knowledge"),
        ticker=result.get("ticker"),
        latency_ms=latency_ms,
        source_type=result.get("source_type"),
    )
