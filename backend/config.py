"""Centralized application and provider configuration.

Exposes ``get_settings()`` (cached singleton) and ``get_provider_registry()``
which lists every configured provider without leaking secrets.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

DEFAULT_ALLOWED_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)


def _parse_allowed_origins(raw_value: str | None) -> tuple[str, ...]:
    if raw_value is None:
        return DEFAULT_ALLOWED_ORIGINS

    origins = tuple(origin.strip().rstrip("/") for origin in raw_value.split(",") if origin.strip())
    return origins or DEFAULT_ALLOWED_ORIGINS


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
    finnhub_api_key: str | None
    alpha_vantage_api_key: str | None
    allowed_origins: tuple[str, ...]

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
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5.4"),
        finnhub_api_key=os.getenv("FINNHUB_API_KEY") or None,
        alpha_vantage_api_key=os.getenv("ALPHA_VANTAGE_API_KEY") or None,
        allowed_origins=_parse_allowed_origins(os.getenv("ALLOWED_ORIGINS")),
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
