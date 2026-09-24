"""
Testes unitários do Web Search Service (web_search.py).
Valida parsing do DuckDuckGo, rate limit e fallback entre provedores.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import unittest
from unittest.mock import MagicMock, patch

from web_search import DuckDuckGoProvider, SearchResult, WebSearchError, WebSearchService

DDG_SAMPLE = """
<html><body>
<a class="result__a" href="https://site-um.com/pagina">Primeiro Resultado</a>
<a class="result__snippet">descrição do primeiro resultado</a> <a class="result__a">
</a>
<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fsite-dois.com">Segundo &amp; Resultado</a>
<a class="result__snippet"><b>segunda</b> descrição</a> <a class="result__a">
</a>
</body></html>
"""


class TestDuckDuckGoParse(unittest.TestCase):
    def test_parse_extracts_title_url_snippet(self):
        prov = DuckDuckGoProvider()
        results = prov._parse(DDG_SAMPLE, "nemo ia", 5)
        self.assertEqual(len(results), 2)
        first = results[0]
        self.assertEqual(first.title, "Primeiro Resultado")
        self.assertEqual(first.url, "https://site-um.com/pagina")
        self.assertIn("primeiro resultado", first.snippet)
        self.assertEqual(first.source, "duckduckgo")
        self.assertEqual(first.query, "nemo ia")

    def test_html_entities_unescaped(self):
        prov = DuckDuckGoProvider()
        results = prov._parse(DDG_SAMPLE, "q", 5)
        self.assertIn("Segundo & Resultado", results[1].title)

    def test_parse_respects_limit(self):
        prov = DuckDuckGoProvider()
        results = prov._parse(DDG_SAMPLE, "q", 1)
        self.assertEqual(len(results), 1)

    def test_http_error_raises(self):
        resp = MagicMock()
        resp.status_code = 500
        with patch("web_search.requests.get", return_value=resp):
            with self.assertRaises(WebSearchError):
                DuckDuckGoProvider().search("oi")


class TestWebSearchService(unittest.TestCase):
    def setUp(self):
        self.service = WebSearchService()
        self.service.rate_limit_per_minute = 3
        self.service._last_calls = {}

    def test_empty_query_raises(self):
        with self.assertRaises(WebSearchError):
            self.service.search("u1", "   ")

    def test_rate_limit_enforced(self):
        with patch.object(DuckDuckGoProvider, "search", return_value=[SearchResult("a", "http://a", "s")]):
            for _ in range(3):
                out = self.service.search("u1", "consulta")
                self.assertTrue(out["ok"])
            # 4ª chamada dentro do mesmo minuto → bloqueada
            with self.assertRaises(WebSearchError):
                self.service.search("u1", "consulta")

    def test_fallback_when_first_provider_fails(self):
        failing = MagicMock()
        failing.name = "tavily"
        failing.search.side_effect = WebSearchError("down")
        ok_ddg = MagicMock()
        ok_ddg.name = "duckduckgo"
        ok_ddg.search.return_value = [SearchResult("r", "http://r", "s")]

        self.service.providers = [failing, ok_ddg]
        out = self.service.search("u2", "pesquisa")
        self.assertTrue(out["ok"])
        self.assertEqual(out["provider"], "duckduckgo")

    def test_all_fail_returns_error_dict(self):
        broken = MagicMock()
        broken.name = "duckduckgo"
        broken.search.side_effect = WebSearchError("down")
        self.service.providers = [broken]
        out = self.service.search("u3", "pesquisa")
        self.assertFalse(out["ok"])
        self.assertIn("error", out)


if __name__ == "__main__":
    unittest.main()