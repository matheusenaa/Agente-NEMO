# -*- coding: utf-8 -*-
"""
Retentativa em erro transitório dos provedores de IA.

Regressão real: o Gemini respondeu 503 "high demand" (pico de demanda) e o
usuário recebeu erro de provedor. O problema passaria sozinho em segundos —
uma retentativa curta evita mostrar a falha.
"""

import unittest
from unittest.mock import MagicMock, patch

import ai_providers as ap


def _resp(status, payload=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload if payload is not None else {}
    return r


OK_GEMINI = {"candidates": [{"content": {"parts": [{"text": "ola"}]}, "finishReason": "STOP"}],
             "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 2}}
OK_OPENAI = {"choices": [{"message": {"content": "ola"}, "finish_reason": "stop"}],
             "usage": {"prompt_tokens": 5, "completion_tokens": 2}}


class TestTransientRetry(unittest.TestCase):
    def setUp(self):
        # sem espera real entre as retentativas
        patcher = patch.object(ap.time, "sleep")
        self.sleep = patcher.start()
        self.addCleanup(patcher.stop)

    def test_gemini_retries_503_then_succeeds(self):
        prov = ap.GeminiProvider("chave-de-teste-com-tamanho")
        with patch.object(ap.requests, "post", side_effect=[_resp(503), _resp(200, OK_GEMINI)]) as post:
            res = prov.complete("gemini-flash-latest", [{"role": "user", "content": "oi"}])
        self.assertTrue(res.success, res.error_message)
        self.assertEqual(res.content, "ola")
        self.assertEqual(post.call_count, 2, "deveria repetir uma vez")
        self.assertEqual(self.sleep.call_count, 1, "espera entre tentativas")

    def test_gemini_retries_429(self):
        prov = ap.GeminiProvider("chave-de-teste-com-tamanho")
        with patch.object(ap.requests, "post", side_effect=[_resp(429), _resp(200, OK_GEMINI)]):
            res = prov.complete("gemini-flash-latest", [{"role": "user", "content": "oi"}])
        self.assertTrue(res.success, res.error_message)

    def test_gemini_gives_up_after_limit(self):
        prov = ap.GeminiProvider("chave-de-teste-com-tamanho")
        boom = [_resp(503) for _ in range(ap.TRANSIENT_RETRIES + 1)]
        with patch.object(ap.requests, "post", side_effect=boom) as post:
            res = prov.complete("gemini-flash-latest", [{"role": "user", "content": "oi"}])
        self.assertFalse(res.success)
        self.assertEqual(post.call_count, ap.TRANSIENT_RETRIES + 1, "não pode entrar em laço infinito")

    def test_gemini_does_not_retry_404(self):
        """404 é erro de configuração (modelo morto): repetir só atrasa."""
        prov = ap.GeminiProvider("chave-de-teste-com-tamanho")
        with patch.object(ap.requests, "post", return_value=_resp(404)) as post:
            res = prov.complete("gemini-2.5-flash", [{"role": "user", "content": "oi"}])
        self.assertFalse(res.success)
        self.assertEqual(post.call_count, 1)
        self.assertEqual(self.sleep.call_count, 0)

    def test_gemini_does_not_retry_400(self):
        prov = ap.GeminiProvider("chave-de-teste-com-tamanho")
        with patch.object(ap.requests, "post", return_value=_resp(400)) as post:
            res = prov.complete("gemini-flash-latest", [{"role": "user", "content": "oi"}])
        self.assertFalse(res.success)
        self.assertEqual(post.call_count, 1)

    def test_openai_compatible_retries_503(self):
        prov = ap.OpenAICompatibleProvider("groq", "chave-de-teste")
        with patch.object(ap.requests, "post", side_effect=[_resp(503), _resp(200, OK_OPENAI)]):
            res = prov.complete("llama-3.3-70b", [{"role": "user", "content": "oi"}])
        self.assertTrue(res.success, res.error_message)
        self.assertEqual(res.content, "ola")

    def test_openai_compatible_does_not_retry_401(self):
        prov = ap.OpenAICompatibleProvider("groq", "chave-de-teste")
        with patch.object(ap.requests, "post", return_value=_resp(401)) as post:
            res = prov.complete("llama-3.3-70b", [{"role": "user", "content": "oi"}])
        self.assertFalse(res.success)
        self.assertEqual(post.call_count, 1)

    def test_network_error_is_not_retried(self):
        """Conexão recusada não é pico de demanda: reportar logo é melhor."""
        prov = ap.GeminiProvider("chave-de-teste-com-tamanho")
        with patch.object(ap.requests, "post", side_effect=ap.requests.ConnectionError("recusado")) as post:
            res = prov.complete("gemini-flash-latest", [{"role": "user", "content": "oi"}])
        self.assertFalse(res.success)
        self.assertIn("conexão", res.error_message.lower())
        self.assertEqual(post.call_count, 1)

    def test_429_is_not_hammered(self):
        """Cota/minuto não volta em 2s: 3 tentativas só atrasam a resposta honesta."""
        prov = ap.GeminiProvider("chave-de-teste-com-tamanho")
        with patch.object(ap.requests, "post", return_value=_resp(429)) as post:
            res = prov.complete("gemini-flash-latest", [{"role": "user", "content": "oi"}])
        self.assertFalse(res.success)
        self.assertEqual(post.call_count, 1 + ap.RATE_LIMIT_RETRIES)
        self.assertLess(post.call_count, 1 + ap.TRANSIENT_RETRIES,
                        "429 não pode gastar as mesmas tentativas de um 503")

    def test_503_gets_full_retries(self):
        prov = ap.GeminiProvider("chave-de-teste-com-tamanho")
        with patch.object(ap.requests, "post", return_value=_resp(503)) as post:
            prov.complete("gemini-flash-latest", [{"role": "user", "content": "oi"}])
        self.assertEqual(post.call_count, 1 + ap.TRANSIENT_RETRIES)

    def test_retries_are_bounded(self):
        self.assertLessEqual(ap.TRANSIENT_RETRIES, 3, "retentativa demais vira lentidão")
        self.assertLessEqual(ap.RATE_LIMIT_RETRIES, 1)
        self.assertTrue(all(0 < s <= 5 for s in ap.RETRY_BACKOFF))
        self.assertFalse(ap._should_retry(400, 0), "erro de config não é transitório")
        self.assertFalse(ap._should_retry(401, 0))
        self.assertFalse(ap._should_retry(404, 0))
        self.assertTrue(ap._should_retry(503, 0))
        self.assertFalse(ap._should_retry(503, ap.TRANSIENT_RETRIES), "não pode passar do limite")


if __name__ == "__main__":
    unittest.main()
