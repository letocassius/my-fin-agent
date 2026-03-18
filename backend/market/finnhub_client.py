"""Finnhub client for news with summaries and basic financial metrics."""

import logging
from datetime import datetime, timedelta, timezone
from config import get_settings

logger = logging.getLogger(__name__)


def _get_client():
    """Return a Finnhub client if FINNHUB_API_KEY is set, else None."""
    api_key = get_settings().finnhub_api_key
    if not api_key:
        return None
    try:
        import finnhub
        return finnhub.Client(api_key=api_key)
    except Exception as e:
        logger.warning(f"Failed to create Finnhub client: {e}")
        return None


def get_finnhub_news(ticker: str, days_back: int = 7) -> list[dict]:
    """
    Fetch recent company news from Finnhub with article summaries.

    Returns a list of normalized article dicts. Falls back to [] if
    FINNHUB_API_KEY is absent or the call fails.
    """
    client = _get_client()
    if client is None:
        return []

    try:
        to_date = datetime.now(tz=timezone.utc)
        from_date = to_date - timedelta(days=days_back)

        articles = client.company_news(
            ticker.upper(),
            _from=from_date.strftime("%Y-%m-%d"),
            to=to_date.strftime("%Y-%m-%d"),
        )

        if not articles:
            return []

        result = []
        for item in articles[:10]:
            ts = item.get("datetime")
            if ts:
                try:
                    pub_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
                except Exception:
                    pub_str = str(ts)
            else:
                pub_str = None

            result.append({
                "title": item.get("headline", ""),
                "publisher": item.get("source", ""),
                "link": item.get("url", ""),
                "publish_time": pub_str,
                "summary": item.get("summary", ""),
                "ticker": ticker.upper(),
                "source": "finnhub",
            })

        return result

    except Exception as e:
        logger.warning(f"Finnhub news fetch failed for {ticker}: {e}")
        return []


def get_basic_financials(ticker: str) -> dict:
    """
    Fetch basic financial metrics and EPS history from Finnhub.

    Returns a dict with PE ratios, quarterly EPS actuals, and EPS surprises.
    Falls back to {} if FINNHUB_API_KEY is absent or the call fails.
    """
    client = _get_client()
    if client is None:
        return {}

    try:
        data = client.company_basic_financials(ticker.upper(), "all")
        if not data:
            return {}

        metric = data.get("metric", {})
        series = data.get("series", {})
        quarterly = series.get("quarterly", {})

        # Extract last 4 quarterly EPS actuals
        eps_quarterly = []
        for entry in (quarterly.get("epsActual") or [])[-4:]:
            eps_quarterly.append({
                "period": entry.get("period"),
                "eps": entry.get("v"),
            })

        # Extract last 4 EPS surprises
        eps_surprise_pct = []
        for entry in (quarterly.get("epsSurprisePct") or [])[-4:]:
            eps_surprise_pct.append({
                "period": entry.get("period"),
                "surprise_pct": entry.get("v"),
            })

        return {
            "ticker": ticker.upper(),
            "pe_ttm": metric.get("peTTM"),
            "pe_annual": metric.get("peAnnual"),
            "eps_quarterly": eps_quarterly,
            "eps_surprise_pct": eps_surprise_pct,
            "source": "finnhub",
        }

    except Exception as e:
        logger.warning(f"Finnhub basic financials failed for {ticker}: {e}")
        return {}
