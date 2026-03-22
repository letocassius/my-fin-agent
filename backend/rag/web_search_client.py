"""Public web retrieval fallback for knowledge questions.

Uses DuckDuckGo HTML search and simple page extraction to obtain
externally sourced context when Wikipedia recall is insufficient.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://html.duckduckgo.com/html/"
_USER_AGENT = "FinAgentBot/1.0 (financial-qa-system; educational use)"
_TIMEOUT = 8
_MAX_RESULTS = 5

FINANCE_TERM_ALIASES: dict[str, list[str]] = {
    "cds": ["credit default swap", "信用违约互换"],
    "信用违约互换": ["credit default swap", "CDS"],
    "信用违约期权": ["credit default option", "credit option"],
    "信用风险缓释凭证": ["credit risk mitigation warrant"],
    "信用风险缓释工具": ["credit risk mitigation"],
}


@dataclass
class SearchDocument:
    content: str
    meta: dict[str, Any] = field(default_factory=dict)
    score: float | None = None

    def to_knowledge_result(self) -> dict:
        return {
            "text": self.content,
            "metadata": self.meta,
            "distance": self.score if self.score is not None else 0.5,
        }


def search_public_web(
    query: str,
    *,
    llm_extract_fn: Any = None,
    language: str = "en",
) -> list[dict]:
    """Search the public web and fetch snippets for the top results."""
    try:
        terms = _expand_terms(query, llm_extract_fn(query) if llm_extract_fn is not None else [])
        queries = _build_search_queries(query, terms, language)
        logger.info(f"Public web search: query={query!r} expanded_terms={terms!r} lang={language}")

        seen_urls: set[str] = set()
        documents: list[SearchDocument] = []
        for search_query in queries:
            for candidate in _search_duckduckgo(search_query):
                url = candidate["url"]
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                doc = _fetch_page(candidate["title"], url)
                if doc is not None:
                    documents.append(doc)
                if len(documents) >= _MAX_RESULTS:
                    return [doc.to_knowledge_result() for doc in documents]

        return [doc.to_knowledge_result() for doc in documents]
    except Exception:
        logger.exception(f"Public web search failed for: {query}")
        return []


def _expand_terms(query: str, extracted_terms: list[str]) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()

    def add(term: str) -> None:
        normalized = term.strip()
        key = normalized.lower()
        if not normalized or key in seen:
            return
        seen.add(key)
        terms.append(normalized)

    add(query)
    for term in extracted_terms:
        add(term)

    haystacks = [query.lower(), *(term.lower() for term in extracted_terms)]
    for alias_key, alias_values in FINANCE_TERM_ALIASES.items():
        if any(alias_key in haystack for haystack in haystacks):
            add(alias_key)
            for alias in alias_values:
                add(alias)

    return terms[:8]


def _build_search_queries(query: str, terms: list[str], language: str) -> list[str]:
    queries: list[str] = []
    seen: set[str] = set()

    def add(search_query: str) -> None:
        normalized = search_query.strip()
        key = normalized.lower()
        if not normalized or key in seen:
            return
        seen.add(key)
        queries.append(normalized)

    add(query)
    if terms:
        add(" ".join(terms[:3]))
        add(" finance ".join(terms[:2]))
    if language == "zh":
        add(f"{query} 金融")
    else:
        add(f"{query} finance")

    return queries[:4]


def _search_duckduckgo(query: str) -> list[dict[str, str]]:
    from bs4 import BeautifulSoup

    response = requests.get(
        _SEARCH_URL,
        params={"q": query},
        headers={"User-Agent": _USER_AGENT},
        timeout=_TIMEOUT,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    results: list[dict[str, str]] = []
    for anchor in soup.select("a.result__a, a.result-link"):
        title = anchor.get_text(" ", strip=True)
        href = anchor.get("href", "").strip()
        if not title or not href:
            continue
        if not href.startswith("http"):
            continue
        parsed = urlparse(href)
        if not parsed.netloc:
            continue
        results.append({"title": title, "url": href})
        if len(results) >= _MAX_RESULTS:
            break

    return results


def _fetch_page(title: str, url: str) -> SearchDocument | None:
    from bs4 import BeautifulSoup

    try:
        response = requests.get(
            url,
            headers={"User-Agent": _USER_AGENT},
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
    except Exception as exc:
        logger.debug(f"Skipping {url}: {exc}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    paragraphs: list[str] = []
    for tag in soup.find_all(["p", "article", "main"]):
        text = re.sub(r"\s+", " ", tag.get_text(" ", strip=True)).strip()
        if len(text) < 80:
            continue
        paragraphs.append(text)
        if sum(len(p) for p in paragraphs) > 1800:
            break

    if not paragraphs:
        return None

    content = "\n\n".join(paragraphs)[:2200]
    return SearchDocument(
        content=content,
        meta={
            "source": "public_web",
            "source_label": title,
            "title": title,
            "url": url,
        },
        score=0.6,
    )
