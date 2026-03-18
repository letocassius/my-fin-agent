"""Centralized application and provider configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class ProviderStatus:
    name: str
    enabled: bool
    configured: bool
    required: bool
    api_key_env: str | None = None
    base_url: str | None = None
    model: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    openai_model: str
    embedding_model: str
    finnhub_api_key: str | None
    alpha_vantage_api_key: str | None

    @property
    def provider_statuses(self) -> list[ProviderStatus]:
        return [
            ProviderStatus(
                name="openai",
                enabled=bool(self.openai_api_key),
                configured=bool(self.openai_api_key),
                required=True,
                api_key_env="OPENAI_API_KEY",
                model=self.openai_model,
                notes="Used for query routing and answer generation.",
            ),
            ProviderStatus(
                name="openai_embeddings",
                enabled=bool(self.openai_api_key),
                configured=bool(self.openai_api_key),
                required=True,
                api_key_env="OPENAI_API_KEY",
                model=self.embedding_model,
                notes="Used for RAG embeddings and ingestion.",
            ),
            ProviderStatus(
                name="yfinance",
                enabled=True,
                configured=True,
                required=False,
                notes="Primary market data source. No API key required.",
            ),
            ProviderStatus(
                name="finnhub",
                enabled=bool(self.finnhub_api_key),
                configured=bool(self.finnhub_api_key),
                required=False,
                api_key_env="FINNHUB_API_KEY",
                notes="Optional provider for richer news and basic financials.",
            ),
            ProviderStatus(
                name="alpha_vantage",
                enabled=bool(self.alpha_vantage_api_key),
                configured=bool(self.alpha_vantage_api_key),
                required=False,
                api_key_env="ALPHA_VANTAGE_API_KEY",
                notes="Reserved optional fallback provider.",
            ),
        ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5.1"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        finnhub_api_key=os.getenv("FINNHUB_API_KEY") or None,
        alpha_vantage_api_key=os.getenv("ALPHA_VANTAGE_API_KEY") or None,
    )


def get_provider_registry() -> list[dict]:
    return [
        {
            "name": status.name,
            "enabled": status.enabled,
            "configured": status.configured,
            "required": status.required,
            "api_key_env": status.api_key_env,
            "base_url": status.base_url,
            "model": status.model,
            "notes": status.notes,
        }
        for status in get_settings().provider_statuses
    ]
