import sys
from pathlib import Path
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.modules.setdefault("openai", SimpleNamespace(OpenAI=object))
sys.modules.setdefault("yfinance", SimpleNamespace(Ticker=object))
sys.modules.setdefault("pandas", SimpleNamespace())

from agents.router import (
    _extract_candidate_ticker,
    _extract_response_sources,
    _looks_like_market_query,
    _post_process_classification,
)


class RouterHeuristicsTests(unittest.TestCase):
    def test_chinese_price_question_is_forced_to_market_and_resolves_alias(self):
        classification = {
            "query_type": "knowledge",
            "ticker": None,
            "period": "1mo",
            "reasoning": "model misclassified it",
        }

        result = _post_process_classification("今天天同花顺的股价是多少", classification)

        self.assertEqual(result["query_type"], "market")
        self.assertEqual(result["ticker"], "300033.SZ")

    def test_numeric_a_share_ticker_is_normalized(self):
        self.assertEqual(_extract_candidate_ticker("300033最近一周股价变化"), "300033.SZ")
        self.assertEqual(_extract_candidate_ticker("600519今天股价"), "600519.SS")

    def test_chinese_concept_question_stays_knowledge(self):
        self.assertFalse(_looks_like_market_query("什么是市盈率"))

    def test_extract_response_sources_from_web_search_annotations(self):
        response = SimpleNamespace(
            output=[
                SimpleNamespace(
                    action=SimpleNamespace(
                        sources=[
                            SimpleNamespace(title="Example A", url="https://example.com/a"),
                        ]
                    ),
                    content=[
                        SimpleNamespace(
                            annotations=[
                                SimpleNamespace(
                                    type="url_citation",
                                    title="Example B",
                                    url="https://example.com/b",
                                )
                            ]
                        )
                    ],
                )
            ]
        )

        sources = _extract_response_sources(response)
        self.assertEqual(
            sources,
            [
                "Example A (https://example.com/a)",
                "Example B (https://example.com/b)",
            ],
        )


if __name__ == "__main__":
    unittest.main()
