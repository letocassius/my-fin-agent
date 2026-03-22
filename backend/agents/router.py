"""LLM agent router: classifies queries and dispatches to market or knowledge handlers.

Uses OpenAI with structured tool use for market data retrieval, and external
knowledge retrieval for conceptual knowledge queries.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from openai import OpenAI

from .prompts import (
    KNOWLEDGE_AGENT_EXTERNAL_PROMPT,
    KNOWLEDGE_AGENT_WEB_SEARCH_PROMPT,
    MARKET_AGENT_PROMPT,
    ROUTER_PROMPT,
)
from config import get_settings
from market.news_client import format_news_for_context, search_news
from market.yfinance_client import (
    get_current_price,
    get_financial_statements,
    get_price_history,
    get_technical_indicators,
)
from rag.wikipedia_client import (
    get_term_extraction_prompt,
    parse_extracted_terms,
    search_wikipedia,
)
from rag.web_search_client import search_public_web

logger = logging.getLogger(__name__)

COMPANY_TICKER_ALIASES = {
    "同花顺": "300033.SZ",
    "东方财富": "300059.SZ",
    "贵州茅台": "600519.SS",
    "宁德时代": "300750.SZ",
    "比亚迪": "002594.SZ",
    "招商银行": "600036.SS",
    "中国平安": "601318.SS",
    "腾讯": "0700.HK",
    "腾讯控股": "0700.HK",
    "阿里巴巴": "BABA",
    "百度": "BIDU",
    "京东": "JD",
    "拼多多": "PDD",
    "苹果": "AAPL",
    "特斯拉": "TSLA",
    "英伟达": "NVDA",
    "微软": "MSFT",
}

MARKET_INTENT_PATTERNS = [
    r"(?:今天|今日|现在|目前|当前).{0,8}(?:股价|价格|市值|行情)",
    r"(?:股价|价格|市值|行情).{0,8}(?:多少|几多|是什么|怎么样)",
    r"(?:涨了多少|跌了多少|涨跌|涨幅|跌幅|走势|表现)",
    r"(?:最近|近).{0,6}(?:一周|一日|一天|五天|5天|一个月|1个月|一年|1年).{0,8}(?:股价|价格|走势|表现|变化)",
]

TICKER_PATTERNS = [
    r"\b[A-Z]{1,5}\b",
    r"\b\d{6}\.(?:SS|SZ)\b",
    r"\b\d{4}\.HK\b",
]

MARKET_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_price",
            "description": (
                "Fetches current price and key statistics for a stock ticker symbol. "
                "Returns price, change, change_pct, volume, market_cap, PE ratio, and more."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol (e.g., AAPL, BABA, TSLA)",
                    }
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_price_history",
            "description": (
                "Fetches historical OHLCV price data for a stock ticker. "
                "Returns period change, trend classification (uptrend/downtrend/sideways), and data points."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol",
                    },
                    "period": {
                        "type": "string",
                        "description": (
                            "Time period for history. Options: '1d', '5d', '1mo', '3mo', '6mo', "
                            "'1y', '2y', '5y', 'ytd'. Default: '1mo'."
                        ),
                        "default": "1mo",
                    },
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_news",
            "description": (
                "Searches for recent news articles related to a stock ticker. "
                "Useful for understanding price movements, catalysts, and market sentiment."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol",
                    },
                    "query": {
                        "type": "string",
                        "description": "Optional search query to refine news results",
                    },
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_technical_indicators",
            "description": (
                "SMA-20/50, RSI-14, MACD (12/26/9), Bollinger Bands (20, 2σ). "
                "Each indicator includes a signal interpretation. "
                "Use for overbought/oversold, trend momentum, mean-reversion signals."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol",
                    }
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_financial_statements",
            "description": (
                "Annual or quarterly income statement, balance sheet, cash flow. "
                "Use for revenue trends, debt levels, free cash flow, EPS history. "
                "Set quarterly=true for recent quarters."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol",
                    },
                    "quarterly": {
                        "type": "boolean",
                        "description": "If true, returns quarterly data instead of annual",
                        "default": False,
                    },
                },
                "required": ["ticker"],
            },
        },
    },
]


def _get_openai_client() -> OpenAI:
    settings = get_settings()
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    return OpenAI(api_key=settings.openai_api_key)


def _chat_completion(
    client: OpenAI,
    messages: list[dict[str, Any]],
    *,
    response_format: dict[str, str] | None = None,
    tools: list[dict[str, Any]] | None = None,
    max_completion_tokens: int = 2048,
) -> Any:
    kwargs: dict[str, Any] = {
        "model": get_settings().openai_model,
        "messages": messages,
        "max_completion_tokens": max_completion_tokens,
    }
    if response_format is not None:
        kwargs["response_format"] = response_format
    if tools is not None:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
        kwargs["parallel_tool_calls"] = True
    return client.chat.completions.create(**kwargs)


def _extract_text_content(message: Any) -> str:
    content = message.content
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        text_parts = []
        for item in content:
            text_value = getattr(item, "text", None)
            if text_value:
                text_parts.append(text_value)
        return "\n".join(text_parts).strip()
    return ""


def _extract_candidate_ticker(query: str) -> str | None:
    for pattern in TICKER_PATTERNS:
        match = re.search(pattern, query, flags=re.IGNORECASE)
        if not match:
            continue
        ticker = match.group(0).upper()
        if re.fullmatch(r"\d{6}", ticker):
            if ticker.startswith(("6", "9")):
                return f"{ticker}.SS"
            return f"{ticker}.SZ"
        return ticker

    digit_match = re.search(r"(?<!\d)(\d{6})(?!\d)", query)
    if digit_match:
        ticker = digit_match.group(1)
        if ticker.startswith(("6", "9")):
            return f"{ticker}.SS"
        return f"{ticker}.SZ"
    return None


def _extract_company_alias_ticker(query: str) -> str | None:
    for company_name, ticker in COMPANY_TICKER_ALIASES.items():
        if company_name in query:
            return ticker
    return None


def _looks_like_market_query(query: str) -> bool:
    query_lower = query.lower()
    english_market_keywords = [
        "price",
        "stock",
        "ticker",
        "performance",
        "trend",
        "surge",
        "drop",
        "rally",
        "fell",
        "market cap",
        "$",
    ]
    if any(keyword in query_lower for keyword in english_market_keywords):
        return True
    return any(re.search(pattern, query) for pattern in MARKET_INTENT_PATTERNS)


def _post_process_classification(query: str, classification: dict[str, Any]) -> dict[str, Any]:
    query_type = classification.get("query_type", "knowledge")
    ticker = classification.get("ticker")

    inferred_ticker = _extract_candidate_ticker(query) or _extract_company_alias_ticker(query)
    if not ticker and inferred_ticker:
        classification["ticker"] = inferred_ticker
        ticker = inferred_ticker

    if _looks_like_market_query(query):
        classification["query_type"] = "market"
        classification.setdefault("period", "1mo")
        if not classification.get("reasoning"):
            classification["reasoning"] = "Heuristic market classification"

    if classification.get("query_type") == "market" and not ticker and inferred_ticker:
        classification["ticker"] = inferred_ticker

    return classification


def _classify_query(query: str, client: OpenAI) -> dict:
    """Use OpenAI to classify the query as market or knowledge."""
    response = _chat_completion(
        client,
        [
            {"role": "system", "content": ROUTER_PROMPT},
            {"role": "user", "content": query},
        ],
        response_format={"type": "json_object"},
        max_completion_tokens=512,
    )

    content = _extract_text_content(response.choices[0].message)

    try:
        return _post_process_classification(query, json.loads(content))
    except json.JSONDecodeError:
        logger.warning(f"Router returned non-JSON: {content}")
        is_market = _looks_like_market_query(query)
        fallback = {
            "query_type": "market" if is_market else "knowledge",
            "ticker": None,
            "period": "1mo",
            "reasoning": "Fallback classification",
        }
        return _post_process_classification(query, fallback)


def _execute_tool_call(tool_name: str, tool_input: dict) -> str:
    """Execute a tool call and return the result as a JSON string."""
    try:
        if tool_name == "get_stock_price":
            result = get_current_price(tool_input["ticker"])
        elif tool_name == "get_price_history":
            result = get_price_history(tool_input["ticker"], tool_input.get("period", "1mo"))
            if "data" in result and isinstance(result["data"], list):
                data = result["data"]
                if len(data) > 10:
                    result["data_sample"] = data[:3] + [{"...": f"({len(data) - 6} more data points)"}] + data[-3:]
                    del result["data"]
                else:
                    result["data_sample"] = data
                    del result["data"]
        elif tool_name == "search_news":
            articles = search_news(query=tool_input.get("query", ""), ticker=tool_input.get("ticker"))
            result = {
                "ticker": tool_input.get("ticker"),
                "article_count": len(articles),
                "articles": articles[:8],
                "formatted": format_news_for_context(articles[:8]),
            }
        elif tool_name == "get_technical_indicators":
            result = get_technical_indicators(tool_input["ticker"])
        elif tool_name == "get_financial_statements":
            result = get_financial_statements(
                tool_input["ticker"],
                quarterly=tool_input.get("quarterly", False),
            )
            for stmt_key in ("income_statement", "balance_sheet", "cash_flow"):
                if stmt_key in result and isinstance(result[stmt_key], dict):
                    for metric in result[stmt_key]:
                        if isinstance(result[stmt_key][metric], dict) and len(result[stmt_key][metric]) > 4:
                            result[stmt_key][metric] = dict(list(result[stmt_key][metric].items())[:4])
        else:
            result = {"error": f"Unknown tool: {tool_name}"}

        return json.dumps(result, default=str)
    except Exception as e:
        logger.exception(f"Tool execution error ({tool_name}): {e}")
        return json.dumps({"error": str(e)})


def _run_market_agent(query: str, ticker: str, client: OpenAI) -> dict:
    """Run the market data agent with OpenAI tool use."""
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": MARKET_AGENT_PROMPT},
        {"role": "user", "content": query},
    ]

    for _ in range(5):
        response = _chat_completion(client, messages, tools=MARKET_TOOLS, max_completion_tokens=2048)
        message = response.choices[0].message
        tool_calls = message.tool_calls or []

        if not tool_calls:
            return _parse_market_response(_extract_text_content(message), ticker)

        messages.append(message.model_dump(exclude_none=True))

        for tool_call in tool_calls:
            arguments = tool_call.function.arguments or "{}"
            try:
                tool_input = json.loads(arguments)
            except json.JSONDecodeError:
                tool_input = {}
            logger.info(f"Tool call: {tool_call.function.name}({tool_input})")
            result_str = _execute_tool_call(tool_call.function.name, tool_input)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result_str,
                }
            )

    fallback = "Unable to complete market analysis after multiple tool rounds."
    return {
        "answer": fallback,
        "data_section": None,
        "analysis_section": fallback,
        "query_type": "market",
        "ticker": ticker,
        "sources": ["Yahoo Finance (yfinance)"],
    }


def _parse_market_response(text: str, ticker: str | None) -> dict:
    """Parse the market agent response into data and analysis sections."""
    data_section = None
    analysis_section = text.strip()

    if "## DATA" in text and "## ANALYSIS" in text:
        parts = text.split("## ANALYSIS", 1)
        analysis_section = parts[1].strip() if len(parts) > 1 else text

        data_parts = parts[0].split("## DATA", 1)
        data_section = data_parts[1].strip() if len(data_parts) > 1 else None

    return {
        "answer": text.strip(),
        "data_section": data_section,
        "analysis_section": analysis_section,
        "query_type": "market",
        "ticker": ticker,
        "sources": ["Yahoo Finance (yfinance)"] + (["Finnhub"] if "finnhub" in text.lower() or "Summary:" in text else []),
        "source_type": "market",
    }


def _run_knowledge_agent(query: str, client: OpenAI) -> dict:
    """Run the knowledge agent using external retrieval."""
    preferred_language = "zh" if re.search(r"[\u4e00-\u9fff]", query) else None

    # Build LLM-powered term extraction function
    def llm_extract(q: str) -> list[str]:
        resp = _chat_completion(
            client,
            [
                {"role": "system", "content": get_term_extraction_prompt()},
                {"role": "user", "content": q},
            ],
            max_completion_tokens=256,
        )
        raw = _extract_text_content(resp.choices[0].message)
        terms = parse_extracted_terms(raw)
        logger.info(f"LLM extracted search terms: {terms}")
        return terms

    wiki_language = "zh" if preferred_language == "zh" else "en"
    wiki_results = search_wikipedia(query, language=wiki_language, llm_extract_fn=llm_extract)

    if wiki_results:
        return _generate_knowledge_answer(query, wiki_results, client)

    web_results = search_public_web(query, llm_extract_fn=llm_extract, language=wiki_language)
    if web_results:
        return _generate_knowledge_answer(query, web_results, client)

    web_search_answer = _run_knowledge_web_search_agent(query, client)
    if web_search_answer is not None:
        return web_search_answer

    answer = "External knowledge sources did not return information relevant to this query."
    return {
        "answer": answer,
        "data_section": None,
        "analysis_section": answer,
        "query_type": "knowledge",
        "ticker": None,
        "sources": [],
        "source_type": "knowledge",
    }


def _run_knowledge_web_search_agent(query: str, client: OpenAI) -> dict | None:
    """Use OpenAI's built-in web search as a final external retrieval fallback."""
    try:
        response = client.responses.create(
            model=get_settings().openai_model,
            input=query,
            instructions=KNOWLEDGE_AGENT_WEB_SEARCH_PROMPT,
            tools=[
                {
                    "type": "web_search",
                    "user_location": {
                        "type": "approximate",
                        "country": "US",
                        "timezone": "America/New_York",
                    },
                }
            ],
            include=["web_search_call.action.sources"],
        )
    except Exception as exc:
        logger.warning(f"OpenAI web search fallback failed: {exc}")
        return None

    answer = getattr(response, "output_text", "").strip()
    if not answer:
        return None

    sources = _extract_response_sources(response)
    return {
        "answer": answer,
        "data_section": None,
        "analysis_section": answer,
        "query_type": "knowledge",
        "ticker": None,
        "sources": sources,
        "source_type": "knowledge",
    }


def _extract_response_sources(response: Any) -> list[str]:
    """Extract cited source titles/URLs from a Responses API web-search result."""
    sources: list[str] = []
    seen: set[str] = set()

    for item in getattr(response, "output", []) or []:
        action = getattr(item, "action", None)
        for source in getattr(action, "sources", []) or []:
            title = getattr(source, "title", None) or "Source"
            url = getattr(source, "url", None) or ""
            display = f"{title} ({url})" if url else title
            if display not in seen:
                seen.add(display)
                sources.append(display)

        content = getattr(item, "content", None) or []
        for part in content:
            annotations = getattr(part, "annotations", None) or []
            for annotation in annotations:
                if getattr(annotation, "type", None) != "url_citation":
                    continue
                title = getattr(annotation, "title", None) or "Source"
                url = getattr(annotation, "url", None) or ""
                display = f"{title} ({url})" if url else title
                if display not in seen:
                    seen.add(display)
                    sources.append(display)

    return sources


def _generate_knowledge_answer(
    query: str,
    results: list[dict],
    client: OpenAI,
) -> dict:
    """Generate an answer from retrieved knowledge results."""
    context_parts = []
    sources = set()
    for i, result in enumerate(results, 1):
        metadata = result.get("metadata", {}) or {}
        source = metadata.get("title") or metadata.get("source_label") or metadata.get("source", "unknown")
        url = metadata.get("url", "")
        source_display = f"{source} ({url})" if url else source
        sources.add(source_display)
        context_parts.append(f"--- Excerpt {i} (Source: {source}) ---\n{result['text']}")

    context = "\n\n".join(context_parts)
    system_prompt = f"{KNOWLEDGE_AGENT_EXTERNAL_PROMPT}\n\n## Retrieved Context\n\n{context}"

    response = _chat_completion(
        client,
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ],
        max_completion_tokens=2048,
    )
    answer = _extract_text_content(response.choices[0].message)

    return {
        "answer": answer,
        "data_section": None,
        "analysis_section": answer,
        "query_type": "knowledge",
        "ticker": None,
        "sources": sorted(list(sources)),
        "source_type": "knowledge",
    }


def route_query(query: str) -> dict:
    """Classify a query and route it to the appropriate agent."""
    client = _get_openai_client()

    logger.info(f"Routing query: {query!r}")
    classification = _classify_query(query, client)
    query_type = classification.get("query_type", "knowledge")
    ticker = classification.get("ticker")

    logger.info(
        f"Classification: type={query_type}, ticker={ticker}, period={classification.get('period', '1mo')}"
    )
    logger.info(f"Routing reasoning: {classification.get('reasoning', '')}")

    if query_type == "market":
        if not ticker:
            return _run_knowledge_agent(query, client)
        return _run_market_agent(query, ticker, client)
    return _run_knowledge_agent(query, client)
