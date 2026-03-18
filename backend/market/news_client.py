"""News retrieval client using yfinance and web search fallback."""

import yfinance as yf
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def search_news(query: str, ticker: str = None) -> list[dict]:
    """
    Fetch recent news for a ticker or query.

    Returns a list of news article dicts with title, publisher, link,
    publish_time, and summary (if available).
    """
    articles = []

    if ticker:
        # Try Finnhub first (provides article summaries + precise timestamps)
        try:
            from market.finnhub_client import get_finnhub_news
            finnhub_articles = get_finnhub_news(ticker)
            if finnhub_articles:
                return finnhub_articles[:10]
        except Exception as e:
            logger.debug(f"Finnhub news unavailable for {ticker}, falling back to yfinance: {e}")

        try:
            stock = yf.Ticker(ticker.upper())
            raw_news = stock.news

            if raw_news:
                for item in raw_news[:10]:  # Limit to 10 articles
                    pub_time = item.get("providerPublishTime")
                    if pub_time:
                        try:
                            pub_dt = datetime.fromtimestamp(pub_time, tz=timezone.utc)
                            pub_str = pub_dt.strftime("%Y-%m-%d %H:%M UTC")
                        except Exception:
                            pub_str = str(pub_time)
                    else:
                        pub_str = None

                    article = {
                        "title": item.get("title", ""),
                        "publisher": item.get("publisher", ""),
                        "link": item.get("link", ""),
                        "publish_time": pub_str,
                        "type": item.get("type", ""),
                        "ticker": ticker.upper(),
                    }

                    # Include thumbnail if available
                    thumbnail = item.get("thumbnail")
                    if thumbnail and isinstance(thumbnail, dict):
                        resolutions = thumbnail.get("resolutions", [])
                        if resolutions:
                            article["image_url"] = resolutions[0].get("url")

                    # Related tickers
                    related = item.get("relatedTickers", [])
                    if related:
                        article["related_tickers"] = related

                    articles.append(article)

        except Exception as e:
            logger.warning(f"yfinance news fetch failed for {ticker}: {e}")

    return articles


def format_news_for_context(news_articles: list[dict]) -> str:
    """
    Format news articles into a readable string for LLM context.
    """
    if not news_articles:
        return "No recent news articles found."

    lines = []
    for i, article in enumerate(news_articles, 1):
        lines.append(f"{i}. [{article.get('publish_time', 'Unknown date')}] {article.get('title', 'No title')}")
        if article.get("publisher"):
            lines.append(f"   Source: {article['publisher']}")
        if article.get("link"):
            lines.append(f"   URL: {article['link']}")
        if article.get("summary"):
            summary = article["summary"][:300] + ("..." if len(article["summary"]) > 300 else "")
            lines.append(f"   Summary: {summary}")
        lines.append("")

    return "\n".join(lines)
