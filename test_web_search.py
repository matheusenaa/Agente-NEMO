"""
Testes unitários do Web Search Service (web_search.py).

O provedor original (scraping do HTML do DuckDuckGo) foi REMOVIDO: o
html.duckduckgo.com responde HTTP 202 com página de desafio anti-bot e nunca
traz resultados — era a causa da busca "responder 200 e não ter nada", que
levava o agente a alucinar. Estes testes cobrem os provedores que existem hoje
e, principalmente, a regra de honestidade: nunca devolver resultado irrelevante
ou inventado.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import unittest
from unittest.mock import MagicMock, patch

from web_search import (
    BraveProvider,
    OpenRouterWebProvider,
    SearchResult,
    TavilyProvider,
    WebSearchError,
    WebSearchService,
    WikipediaProvider,
)


def _openrouter_response(annotations, content="resumo"):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"choices": [{"message": {"content": content, "annotations": annotations}}]}
    return resp


class TestOpenRouterWebProvider(unittest.TestCase):
    def setUp(self):
        self.provider = OpenRouterWebProvider("sk-or-v1-chave-valida-de-teste")

    def test_unavailable_with_placeholder_key(self):
        self.assertFalse(OpenRouterWebProvider("").available())
        self.assertFalse(OpenRouterWebProvider("sua_chave_aqui").available())
        with self.assertRaises(WebSearchError):
            OpenRouterWebProvider("").search("dolar")

    def test_parses_nested_url_citation(self):
        """Regressão: o formato real é {type, url_citation: {url, title, content}}.

        Uma versão anterior fazia `ann.get("url_citation").strip()` e quebrava com
        AttributeError, caindo silenciosamente na Wikipédia — que devolvia
        artigos sem nenhuma relação com a pergunta.
        """
        payload = [{
            "type": "url_citation",
            "url_citation": {
                "url": "https://www.bcb.gov.br/fechamentodolar",
                "title": "Fechamento diário do dólar",
                "content": "O dólar fechou a R$ 5,22 em 28/09/2026.",
            },
        }]
        with patch("web_search.requests.post", return_value=_openrouter_response(payload)):
            results = self.provider.search("preço do dólar hoje")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].url, "https://www.bcb.gov.br/fechamentodolar")
        self.assertIn("5,22", results[0].snippet)
        self.assertEqual(results[0].source, "openrouter-web")

    def test_content_of_citation_is_kept_not_summary(self):
        payload = [{
            "url_citation": {"url": "https://x.com", "title": "T", "content": "trecho real da pagina"},
        }]
        with patch("web_search.requests.post", return_value=_openrouter_response(payload, content="resumo do modelo")):
            results = self.provider.search("q")
        self.assertEqual(results[0].snippet, "trecho real da pagina")

    def test_no_annotations_but_content_returns_unconfirmed_result(self):
        with patch("web_search.requests.post", return_value=_openrouter_response([], content="algo")):
            results = self.provider.search("q")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].url, "", "sem citation não há URL verificável")

    def test_empty_response_raises(self):
        with patch("web_search.requests.post", return_value=_openrouter_response([], content="")):
            with self.assertRaises(WebSearchError):
                self.provider.search("q")

    def test_http_error_raises(self):
        resp = MagicMock()
        resp.status_code = 500
        with patch("web_search.requests.post", return_value=resp):
            with self.assertRaises(WebSearchError):
                self.provider.search("q")

    def test_request_error_raises(self):
        import requests
        with patch("web_search.requests.post", side_effect=requests.RequestException("boom")):
            with self.assertRaises(WebSearchError):
                self.provider.search("q")


class TestWikipediaProvider(unittest.TestCase):
    def setUp(self):
        self.provider = WikipediaProvider("pt")

    def _resp(self, hits):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"query": {"search": hits}}
        return resp

    def test_refuses_recency_questions(self):
        """Regressão do bug real: "preço do dólar hoje" retornava
        "Pandemia de COVID-19 no Brasil" e o agente narrava aquilo."""
        for query in ("preço do dólar hoje no Brasil", "resultado do Vasco hoje", "cotação do euro agora"):
            with self.assertRaises(WebSearchError):
                self.provider.search(query)

    def test_drops_offtopic_hits(self):
        hits = [
            {"title": "Pandemia de COVID-19 no Brasil", "snippet": "doença respiratória", "timestamp": "2020-01-01"},
        ]
        with patch("web_search.requests.get", return_value=self._resp(hits)):
            with self.assertRaises(WebSearchError):
                self.provider.search("biografia de Marie Curie")

    def test_keeps_relevant_hits(self):
        hits = [
            {"title": "Marie Curie", "snippet": "Marie Curie foi uma física e química polonesa.", "timestamp": "2024-05-05"},
        ]
        with patch("web_search.requests.get", return_value=self._resp(hits)):
            results = self.provider.search("biografia de Marie Curie")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Marie Curie")
        self.assertEqual(results[0].date, "2024-05-05")
        self.assertIn("wikipedia.org", results[0].url)

    def test_http_error_raises(self):
        resp = MagicMock()
        resp.status_code = 503
        with patch("web_search.requests.get", return_value=resp):
            with self.assertRaises(WebSearchError):
                self.provider.search("Marie Curie")


class TestKeyedProviders(unittest.TestCase):
    def test_tavily_parses_results(self):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"results": [{"title": "T", "url": "http://t", "content": "C"}]}
        with patch("web_search.requests.post", return_value=resp):
            out = TavilyProvider("k").search("q")
        self.assertEqual(out[0].snippet, "C")

    def test_tavily_http_error_raises(self):
        resp = MagicMock()
        resp.status_code = 401
        with patch("web_search.requests.post", return_value=resp):
            with self.assertRaises(WebSearchError):
                TavilyProvider("k").search("q")

    def test_brave_parses_results(self):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"web": {"results": [{"title": "T", "url": "http://b", "description": "D"}]}}
        with patch("web_search.requests.get", return_value=resp):
            out = BraveProvider("k").search("q")
        self.assertEqual(out[0].snippet, "D")

    def test_brave_http_error_raises(self):
        resp = MagicMock()
        resp.status_code = 429
        with patch("web_search.requests.get", return_value=resp):
            with self.assertRaises(WebSearchError):
                BraveProvider("k").search("q")


class TestWebSearchService(unittest.TestCase):
    def setUp(self):
        self.service = WebSearchService()
        self.service.rate_limit_per_minute = 3
        self.service._last_calls = {}

    def _stub(self, name, results=None, error=None):
        stub = MagicMock()
        stub.name = name
        if error is not None:
            stub.search.side_effect = error
        else:
            stub.search.return_value = results if results is not None else [SearchResult("a", "http://a", "s")]
        return stub

    def test_empty_query_raises(self):
        with self.assertRaises(WebSearchError):
            self.service.search("u1", "   ")

    def test_rate_limit_enforced(self):
        self.service.providers = [self._stub("tavily")]
        for _ in range(3):
            self.assertTrue(self.service.search("u1", "consulta")["ok"])
        with self.assertRaises(WebSearchError):
            self.service.search("u1", "consulta")

    def test_rate_limit_is_per_user(self):
        self.service.providers = [self._stub("tavily")]
        for _ in range(3):
            self.service.search("u1", "consulta")
        self.assertTrue(self.service.search("outro-usuario", "consulta")["ok"])

    def test_fallback_when_first_provider_fails(self):
        self.service.providers = [
            self._stub("tavily", error=WebSearchError("down")),
            self._stub("openrouter-web"),
        ]
        out = self.service.search("u2", "pesquisa")
        self.assertTrue(out["ok"])
        self.assertEqual(out["provider"], "openrouter-web")

    def test_fallback_skips_empty_result(self):
        self.service.providers = [self._stub("tavily", results=[]), self._stub("brave")]
        out = self.service.search("u2", "pesquisa")
        self.assertEqual(out["provider"], "brave")

    def test_all_fail_returns_error_dict(self):
        """§9: honestidade. Sem resultado, diz que não tem — não inventa."""
        self.service.providers = [self._stub("tavily", error=WebSearchError("down"))]
        out = self.service.search("u3", "pesquisa")
        self.assertFalse(out["ok"])
        self.assertEqual(out["results"], [])
        self.assertEqual(out["provider"], "none")
        self.assertIn("error", out)

    def test_result_shape(self):
        self.service.providers = [self._stub("tavily")]
        out = self.service.search("u4", "pesquisa", 3)
        self.assertEqual(out["query"], "pesquisa")
        self.assertIn("results", out)
        self.assertIn("snippet", out["results"][0])

    def test_default_chain_has_no_duckduckgo(self):
        names = self.service.available_providers()
        self.assertNotIn("duckduckgo", names)
        self.assertIn("wikipedia", names)


if __name__ == "__main__":
    unittest.main()
