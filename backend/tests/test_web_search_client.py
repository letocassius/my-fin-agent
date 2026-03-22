import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rag.web_search_client import _build_search_queries, _expand_terms


class WebSearchClientTests(unittest.TestCase):
    def test_expand_terms_adds_finance_aliases(self):
        terms = _expand_terms(
            "什么是信用违约互换（CDS）？它和信用违约期权有什么区别？",
            ["信用违约互换", "信用违约期权"],
        )
        self.assertIn("credit default swap", terms)
        self.assertIn("credit default option", terms)

    def test_build_search_queries_keeps_original_query(self):
        queries = _build_search_queries(
            "什么是信用违约互换（CDS）？",
            ["信用违约互换", "credit default swap"],
            "zh",
        )
        self.assertEqual(queries[0], "什么是信用违约互换（CDS）？")
        self.assertTrue(any("credit default swap" in query for query in queries))


if __name__ == "__main__":
    unittest.main()
