"""
Wikipedia retrieval client for RAG fallback.

Architecture inspired by Haystack's web search components:
- Clean document interface: results returned as list[SearchDocument]
- LLM-powered query decomposition (like Haystack's MultiQueryRetriever)
- Wikipedia opensearch for title matching + extracts for content
- No brittle regex keyword extraction — the LLM handles NLP

Flow:
  User query → LLM extracts search terms → Wikipedia opensearch per term
  → fetch article extracts → return as SearchDocument list
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

import requests

logger = logging.getLogger(__name__)

_USER_AGENT = "FinAgentBot/1.0 (financial-qa-system; educational use)"
_TIMEOUT = 5

_TERM_EXTRACTION_PROMPT = """\
Extract Wikipedia search terms from the user's question.

Rules:
- Return 1-5 short noun-phrase search terms that would match Wikipedia article titles
- Each term should be a concept, not a full question (e.g., "利率互换" not "什么是利率互换")
- For compound questions (A和B有什么区别), extract each topic separately: ["A", "B"]
- Remove parenthesized abbreviations — search the full name (e.g., "信用违约互换" not "CDS")
- For Chinese questions, prefer the Chinese term; also include the English term if it's a well-known financial concept
- Return ONLY a JSON array of strings, nothing else

Examples:
- "什么是信用违约互换（CDS）？" → ["信用违约互换", "credit default swap"]
- "开放式基金和封闭式基金有哪些核心区别？" → ["开放式基金", "封闭式基金", "open-end fund", "closed-end fund"]
- "什么是久期（Duration）和修正久期？" → ["久期", "修正久期", "duration (finance)", "Macaulay duration"]
- "为什么零息债券的久期等于它剩余到期年限？" → ["零息债券", "久期", "zero-coupon bond", "duration (finance)"]
- "What is quantitative easing?" → ["quantitative easing"]
- "What is the difference between revenue and net income?" → ["revenue (finance)", "net income"]

For English terms, prefer the exact Wikipedia article title when you know it (e.g., "duration (finance)" not "bond duration")."""


# ---------------------------------------------------------------------------
# Document model (inspired by Haystack's Document dataclass)
# ---------------------------------------------------------------------------

@dataclass
class SearchDocument:
    """A retrieved document with content and metadata.

    Follows Haystack's Document pattern: content + meta dict + score.
    """
    content: str
    meta: dict[str, Any] = field(default_factory=dict)
    score: float | None = None

    def to_knowledge_result(self) -> dict:
        """Convert to the dict format expected by _generate_knowledge_answer."""
        return {
            "text": self.content,
            "metadata": self.meta,
            "distance": self.score if self.score is not None else 0.5,
        }


# ---------------------------------------------------------------------------
# LLM client protocol (so we don't depend on OpenAI directly)
# ---------------------------------------------------------------------------

class LLMClient(Protocol):
    """Minimal protocol for an LLM chat completion client."""
    def chat_completions_create(self, messages: list[dict], **kwargs: Any) -> str: ...


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def search_wikipedia(
    query: str,
    language: str = "en",
    llm_extract_fn: Any = None,
) -> list[dict]:
    """Search Wikipedia using LLM-extracted search terms.

    Args:
        query: The user's natural language question.
        language: Wikipedia language code ("en", "zh", etc.)
        llm_extract_fn: A callable(query) -> list[str] that extracts search
            terms using an LLM. If None, falls back to basic text cleaning.

    Returns:
        List of dicts matching search_knowledge() shape:
        [{"text": ..., "metadata": {...}, "distance": ...}]
    """
    try:
        # Step 1: Extract search terms
        if llm_extract_fn is not None:
            search_terms = llm_extract_fn(query)
        else:
            search_terms = _basic_extract(query)

        logger.info(f"Wikipedia search: query={query!r} terms={search_terms!r} lang={language}")

        if not search_terms:
            return []

        # Step 2: Search Wikipedia for each term
        wiki = _WikipediaAPI(language)
        documents = wiki.search_and_fetch(search_terms)

        # Step 3: If primary search yielded nothing or too few, try English
        if not documents and language != "en":
            logger.info(f"{language} Wikipedia returned no results, trying English")
            wiki_en = _WikipediaAPI("en")
            # Prefer English terms, but try all if no English terms exist
            en_terms = [t for t in search_terms if not _is_cjk(t)]
            documents = wiki_en.search_and_fetch(en_terms or search_terms)

        logger.info(f"Wikipedia returned {len(documents)} documents")
        return [doc.to_knowledge_result() for doc in documents]

    except Exception:
        logger.exception(f"Wikipedia search failed for: {query}")
        return []


def get_term_extraction_prompt() -> str:
    """Return the system prompt for LLM-based search term extraction."""
    return _TERM_EXTRACTION_PROMPT


def parse_extracted_terms(llm_response: str) -> list[str]:
    """Parse the LLM response into a list of search terms."""
    text = llm_response.strip()
    # Handle markdown code blocks: ```json\n...\n``` or ```\n...\n```
    code_block = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if code_block:
        text = code_block.group(1).strip()
    try:
        terms = json.loads(text)
        if isinstance(terms, list):
            return [str(t).strip() for t in terms if str(t).strip()]
    except json.JSONDecodeError:
        pass
    # Fallback: split on commas or newlines
    return [t.strip().strip('"\'') for t in text.replace("\n", ",").split(",") if t.strip()]


# ---------------------------------------------------------------------------
# Wikipedia API wrapper
# ---------------------------------------------------------------------------

class _WikipediaAPI:
    """Encapsulates MediaWiki API calls for a specific language."""

    def __init__(self, language: str = "en"):
        self.base_url = f"https://{language}.wikipedia.org/w/api.php"
        self.language = language
        self._headers = {"User-Agent": _USER_AGENT}

    def search_and_fetch(self, terms: list[str], limit_per_term: int = 2) -> list[SearchDocument]:
        """Search for articles matching terms and fetch their extracts."""
        # Collect unique titles and their URLs
        seen: set[str] = set()
        titles: list[str] = []
        urls: list[str] = []

        for term in terms:
            found_titles, found_urls = self._opensearch(term, limit=limit_per_term)
            for title, url in zip(found_titles, found_urls):
                if title not in seen:
                    seen.add(title)
                    titles.append(title)
                    urls.append(url)

        if not titles:
            return []

        # Fetch extracts for up to 5 articles
        return self._fetch_extracts(titles[:5], urls[:5])

    def _opensearch(self, term: str, limit: int = 3) -> tuple[list[str], list[str]]:
        """Title-based search. Returns (titles, urls)."""
        resp = requests.get(
            self.base_url,
            params={
                "action": "opensearch",
                "search": term,
                "limit": limit,
                "namespace": 0,
                "format": "json",
            },
            headers=self._headers,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if len(data) < 4 or not data[1]:
            return [], []
        return data[1], data[3]

    def _fetch_extracts(self, titles: list[str], urls: list[str]) -> list[SearchDocument]:
        """Fetch intro extracts for the given article titles."""
        resp = requests.get(
            self.base_url,
            params={
                "action": "query",
                "titles": "|".join(titles),
                "prop": "extracts",
                "exintro": True,
                "explaintext": True,
                "format": "json",
            },
            headers=self._headers,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        pages = resp.json().get("query", {}).get("pages", {})
        title_to_url = dict(zip(titles, urls))

        documents: list[SearchDocument] = []
        for page in pages.values():
            if page.get("missing") is not None:
                continue
            extract = page.get("extract", "").strip()
            if not extract:
                continue

            title = page.get("title", "")
            url = title_to_url.get(title, "")
            extract = _truncate_at_sentence(extract, 2000)

            documents.append(SearchDocument(
                content=extract,
                meta={
                    "source": "wikipedia",
                    "source_label": f"Wikipedia: {title}",
                    "title": title,
                    "url": url,
                    "language": self.language,
                },
                score=0.5,
            ))

        return documents


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _basic_extract(query: str) -> list[str]:
    """Fallback term extraction without LLM — simple text cleaning."""
    stripped = re.sub(r"[（(][^）)]*[）)]", " ", query)
    stripped = re.sub(r"[？?！!。，,：:；;、·\n]", " ", stripped)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    return [stripped] if stripped else []


def _is_cjk(text: str) -> bool:
    """Check if text contains CJK characters."""
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def _truncate_at_sentence(text: str, max_chars: int) -> str:
    """Truncate text at a sentence boundary near max_chars."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    for sep in (". ", ".\n", "! ", "? ", "。", "！", "？"):
        last = truncated.rfind(sep)
        if last > max_chars // 2:
            return truncated[:last + len(sep)]
    return truncated
