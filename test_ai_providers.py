"""
Testes unitários da camada abstrata de IA (ai_providers.py).
Valida provedores, mapeamento de erros, fallbacks limitados e catálogo.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import unittest
from unittest.mock import MagicMock, patch

import ai_providers
from ai_providers import (
    AIProviderService, CompletionResult, GeminiProvider, GroqProvider,
    OpenAICompatibleProvider, PROVIDER_META, MAX_FALLBACKS,
)


def _resp(status_code: int, json_body):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body
    resp.text = str(json_body)
    return resp


class TestErrorMapping(unittest.TestCase):
    def test_gemini_401_message(self):
        p = GeminiProvider("a" * 20)
        r = p._error(_resp(401, {"error": {"message": "API key not valid"}}), "gemini-2.5-flash", 10.0)
        self.assertFalse(r.success)
        self.assertIn("inválida", r.error_message)

    def test_gemini_404_message(self):
        p = GeminiProvider("a" * 20)
        r = p._error(_resp(404, {}), "gemini-2.5-flash", 10.0)
        self.assertIn("não encontrado", r.error_message)

    def test_openai_compatible_401(self):
        p = OpenAICompatibleProvider("groq", "chave12345")
        r = p._error(_resp(403, {}), "llama-3.3-70b-versatile", 5.0)
        self.assertIn("inválida", r.error_message)


class TestGeminiComplete(unittest.TestCase):
    def test_success_parses_content_and_usage(self):
        body = {
            "candidates": [{"content": {"parts": [{"text": "Olá do Gemini"}]}, "finishReason": "STOP"}],
            "usageMetadata": {"promptTokenCount": 12, "candidatesTokenCount": 4, "totalTokenCount": 16},
        }
        with patch("ai_providers.requests.post", return_value=_resp(200, body)) as mock_post:
            p = GeminiProvider("chave-de-40-caracteres-12345678")
            res = p.complete("gemini-2.5-flash", [{"role": "user", "content": "oi"}])
            self.assertTrue(res.success)
            self.assertEqual(res.content, "Olá do Gemini")
            self.assertEqual(res.total_tokens, 16)
            self.assertEqual(res.provider, "gemini")
            mock_post.assert_called_once()

    def test_system_instruction_is_sent(self):
        body = {"candidates": [{"content": {"parts": [{"text": "ok"}]}}], "usageMetadata": {}}
        with patch("ai_providers.requests.post", return_value=_resp(200, body)) as mock_post:
            p = GeminiProvider("chave-de-40-caracteres-12345678")
            p.complete("gemini-2.5-flash",
                       [{"role": "system", "content": "Você é o NEMO"}, {"role": "user", "content": "oi"}])
            _, kwargs = mock_post.call_args
            self.assertIn("systemInstruction", kwargs["json"])

    def test_connection_error_graceful(self):
        import requests
        with patch("ai_providers.requests.post", side_effect=requests.ConnectionError("boom")):
            p = GeminiProvider("chave-de-40-caracteres-12345678")
            res = p.complete("gemini-2.5-flash", [{"role": "user", "content": "oi"}])
            self.assertFalse(res.success)
            self.assertIn("Falha de conexão", res.error_message)


class TestGroqComplete(unittest.TestCase):
    def test_success_parse(self):
        body = {
            "choices": [{"message": {"content": "OK llama-3.3-70b-versatile"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 9, "completion_tokens": 6, "total_tokens": 15},
        }
        with patch("ai_providers.requests.post", return_value=_resp(200, body)):
            p = GroqProvider("gsk_abcdef123456")
            res = p.complete("llama-3.3-70b-versatile", [{"role": "user", "content": "teste"}])
            self.assertTrue(res.success)
            self.assertEqual(res.content, "OK llama-3.3-70b-versatile")


class TestProviderCatalog(unittest.TestCase):
    def test_catalog_has_all_providers(self):
        svc = AIProviderService()
        catalog = svc.provider_catalog()
        ids = {p["id"] for p in catalog}
        self.assertEqual(ids, {"gemini", "groq", "openai", "openrouter"})
        for p in catalog:
            self.assertNotIn("key", p)  # nunca expõe chave
            self.assertTrue(p["name"])

    def test_existing_system_key_detected(self):
        svc = AIProviderService()
        svc.system_keys = {"openrouter": "sk-or-v1-abcdefghijklmnopqrstuvwxyz1234"}
        self.assertTrue(svc.has_system_key("openrouter"))
        self.assertFalse(svc.has_system_key("gemini"))

    def test_default_provider_falls_back_to_openrouter(self):
        svc = AIProviderService()
        with patch.object(ai_providers.os, "getenv", return_value=""):
            self.assertEqual(svc.default_provider(), "openrouter")


class TestFallbackChain(unittest.TestCase):
    def _svc_no_user_key_but_system_openrouter(self):
        svc = AIProviderService()
        svc.system_keys = {
            "gemini": "", "groq": "", "openai": "",
            "openrouter": "sk-or-v1-abcdefghijklmnopqrstuvwxyz1234",
        }
        return svc

    def test_fallback_to_next_provider_when_first_has_no_key(self):
        svc = self._svc_no_user_key_but_system_openrouter()
        provider = MagicMock()
        provider.complete.return_value = CompletionResult(
            success=True, content="OK openrouter", model_used="deepseek/deepseek-chat",
            provider="openrouter", original_model="deepseek/deepseek-chat",
        )
        with patch.object(svc, "_build_provider", return_value=provider):
            res = svc.complete("gemini", "gemini-2.5-flash", [{"role": "user", "content": "oi"}],
                               fallback_providers=["openrouter"])
        self.assertTrue(res.success)
        self.assertEqual(res.provider, "openrouter")
        self.assertTrue(res.is_fallback)  # gemini sem chave → fallback acionado

    def test_chain_is_limited_by_max_fallbacks(self):
        svc = self._svc_no_user_key_but_system_openrouter()
        with patch.object(svc, "_build_provider") as build:
            svc.complete(
                "gemini", "gemini-2.5-flash", [{"role": "user", "content": "oi"}],
                fallback_providers=["openai", "groq", "openrouter", "gemini"],
            )
            # MAX_FALLBACKS = 3: gemini, openai, groq — openrouter/gemini não entram
            calls = build.call_count
        self.assertLessEqual(calls, MAX_FALLBACKS)

    def test_all_fail_returns_last_error(self):
        svc = self._svc_no_user_key_but_system_openrouter()
        # openai tem chave de sistema válida para o erro simulado do provedor ser o último
        svc.system_keys["openai"] = "sk-fake-openai-1234567890"
        provider = MagicMock()
        provider.complete.return_value = CompletionResult(
            success=False, content="", model_used="gpt-4o-mini", provider="openai",
            original_model="gpt-4o-mini", error_message="erro simulado",
        )
        with patch.object(svc, "_build_provider", return_value=provider):
            res = svc.complete("openai", "gpt-4o-mini", [{"role": "user", "content": "oi"}])
        self.assertFalse(res.success)
        self.assertEqual(res.error_message, "erro simulado")


class TestTestKey(unittest.TestCase):
    def test_test_key_strips_result(self):
        svc = AIProviderService()
        provider = MagicMock()
        provider.complete.return_value = CompletionResult(
            success=True, content="OK gemini-2.5-flash", model_used="gemini-2.5-flash",
            provider="gemini", original_model="gemini-2.5-flash", latency_ms=320.0,
        )
        with patch.object(svc, "_build_provider", return_value=provider):
            out = svc.test_key("gemini", "chave-valida-40-caract")
        self.assertTrue(out["ok"])
        self.assertNotIn("error", out)


if __name__ == "__main__":
    unittest.main()