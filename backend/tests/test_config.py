import unittest
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import get_provider_registry, get_settings


class ConfigTests(unittest.TestCase):
    def test_provider_registry_reports_configuration(self):
        with patch.dict(
            "os.environ",
            {
                "OPENAI_API_KEY": "test-openai",
                "OPENAI_MODEL": "gpt-test",
            },
            clear=False,
        ):
            get_settings.cache_clear()
            providers = {provider["name"]: provider for provider in get_provider_registry()}

        self.assertTrue(providers["openai"]["enabled"])
        self.assertEqual(providers["openai"]["model"], "gpt-test")
        self.assertFalse(providers["finnhub"]["enabled"])
        self.assertTrue(providers["yfinance"]["enabled"])
        get_settings.cache_clear()

    def test_settings_parse_allowed_origins_configuration(self):
        with patch.dict(
            "os.environ",
            {
                "ALLOWED_ORIGINS": "https://frontend.onrender.com, http://localhost:5173",
            },
            clear=False,
        ):
            get_settings.cache_clear()
            settings = get_settings()

        self.assertEqual(
            settings.allowed_origins,
            ("https://frontend.onrender.com", "http://localhost:5173"),
        )
        get_settings.cache_clear()
