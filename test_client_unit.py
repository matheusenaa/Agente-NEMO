"""
Testes unitários automatizados para o OpenRouterClient e ModelsConfig.
Valida inicialização de headers, detecção de chave, mapeamento de fallbacks e retries.
"""

import sys
from pathlib import Path

# Garante que a raiz do projeto esteja no sys.path independente do ambiente
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import unittest
from unittest.mock import patch, MagicMock
from openai import NotFoundError

from models_config import get_all_models, get_model_by_id, ModelInfo
from openrouter_client import OpenRouterClient, CompletionResult
from nemo_server import _is_auth_error, _is_connection_error

class TestOpenRouterIntegration(unittest.TestCase):

    def test_models_config_integrity(self):
        """Verifica se todos os 10 modelos foram configurados corretamente."""
        models = get_all_models()
        self.assertEqual(len(models), 10)

        # Verifica presença dos 10 provedores/modelos solicitados
        expected_ids = [
            "claude-3.5-sonnet",
            "gpt-4o",
            "gpt-4o-mini",
            "gemini-flash-1.5",
            "gemini-pro-1.5",
            "llama-3.1-70b-instruct",
            "llama-3.1-405b-instruct",
            "mixtral-8x22b-instruct",
            "deepseek-chat",
            "qwen-2.5-72b-instruct"
        ]

        for model_id in expected_ids:
            m = get_model_by_id(model_id)
            self.assertIsNotNone(m, f"Modelo {model_id} não encontrado na configuração")
            self.assertTrue(len(m.primary_slug) > 0)

    def test_client_headers_and_initialization(self):
        """Verifica se os cabeçalhos obrigatórios do OpenRouter são configurados."""
        client = OpenRouterClient(
            api_key="sk-or-v1-mocked-key-for-testing",
            referer="http://test.local",
            app_title="NEMO Test Suite"
        )
        self.assertEqual(client.referer, "http://test.local")
        self.assertEqual(client.app_title, "NEMO Test Suite")
        self.assertEqual(client.default_headers["HTTP-Referer"], "http://test.local")
        self.assertEqual(client.default_headers["X-Title"], "NEMO Test Suite")
        self.assertTrue(client.has_valid_key_format())

    def test_key_format_validation(self):
        """Testa detecção de chave ausente ou placeholder."""
        invalid_keys = ["", "sua_chave_aqui", "your_key_here", "sk-or-v1-...", "short"]
        for key in invalid_keys:
            client = OpenRouterClient(api_key=key)
            self.assertFalse(client.has_valid_key_format())

        valid_client = OpenRouterClient(api_key="sk-or-v1-abcdef1234567890abcdef1234567890")
        self.assertTrue(valid_client.has_valid_key_format())

    def test_slug_resolution_exact_and_fallback(self):
        """Testa a lógica de resolução de slugs e fallback inteligente."""
        client = OpenRouterClient(api_key="test_key")
        # Injeta catálogo simulado
        client._live_models_cache = [
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "anthropic/claude-sonnet-4",
            "google/gemini-2.5-flash",
        ]

        # Modelo com slug primário ativo
        gpt_model = get_model_by_id("gpt-4o")
        slug, is_fb = client.resolve_model_slug(gpt_model)
        self.assertEqual(slug, "openai/gpt-4o")
        self.assertFalse(is_fb)

        # Modelo desatualizado que deve acionar fallback
        claude_model = get_model_by_id("claude-3.5-sonnet")
        slug, is_fb = client.resolve_model_slug(claude_model)
        self.assertEqual(slug, "anthropic/claude-sonnet-4")
        self.assertTrue(is_fb)

    def test_chat_completion_automatic_fallback_on_404(self):
        """Verifica se o cliente aciona automaticamente o próximo slug em caso de 404."""
        client = OpenRouterClient(api_key="sk-or-v1-mock-valid-key")

        # Simula resposta de sucesso para o segundo slug tentado
        mock_choice = MagicMock()
        mock_choice.message.content = "OK claude-sonnet-4"
        mock_choice.finish_reason = "stop"

        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 15
        mock_usage.completion_tokens = 5
        mock_usage.total_tokens = 20

        mock_success_response = MagicMock()
        mock_success_response.choices = [mock_choice]
        mock_success_response.usage = mock_usage

        def mock_create(model, **kwargs):
            if model == "anthropic/claude-3.5-sonnet":
                # Simula 404 do OpenRouter
                resp = MagicMock(status_code=404)
                raise NotFoundError(message="Model not found", response=resp, body=None)
            elif model == "anthropic/claude-sonnet-4":
                return mock_success_response
            raise ValueError(f"Modelo inesperado: {model}")

        with patch.object(client.client.chat.completions, "create", side_effect=mock_create):
            result = client.chat_completion(
                model="anthropic/claude-3.5-sonnet",
                messages=[{"role": "user", "content": "Test"}],
                fallback_slugs=["anthropic/claude-sonnet-4"]
            )

            self.assertTrue(result.success)
            self.assertEqual(result.model_used, "anthropic/claude-sonnet-4")
            self.assertTrue(result.is_fallback)
            self.assertEqual(result.content, "OK claude-sonnet-4")
            self.assertEqual(result.total_tokens, 20)

    def test_error_detectors_auth_and_connection(self):
        """Verifica que os detectores distinguem erro 401 (chave) de falha de rede."""
        # Casos que DEVEM ser tratados como erro de autenticação
        auth_cases = [
            "Erro da API OpenRouter (AuthenticationError): Invalid API key",
            "HTTP 401 Unauthorized para openrouter.ai",
            "openai.InvalidAPIKeyError: AuthenticationError",
            "Chave expirada (401)",
        ]
        for msg in auth_cases:
            self.assertTrue(_is_auth_error(msg), f"deveria detectar auth: {msg}")
            self.assertFalse(_is_connection_error(msg), f"não é erro de rede: {msg}")

        # Casos que DEVEM ser tratados como falha de rede
        conn_cases = [
            "Erro da API OpenRouter (APIConnectionError): Connection error.",
            "ConnectionError: timed out",
            "Falha de conexão com OpenRouter: ConnectionResetError(10054)",
            "não foi possível resolver o host openrouter.ai (DNS)",
        ]
        for msg in conn_cases:
            self.assertTrue(_is_connection_error(msg), f"deveria detectar rede: {msg}")
            self.assertFalse(_is_auth_error(msg), f"não é erro de auth: {msg}")

    def test_chat_offline_on_connection_blocked(self):
        """Rede bloqueada com chave válida → resposta graciosa offline, não erro cru."""
        import nemo_server as ns

        client = OpenRouterClient(api_key="sk-or-v1-mocked-key-for-testing")
        blocked = CompletionResult(
            success=False,
            content="",
            model_used="deepseek/deepseek-chat",
            original_model="deepseek/deepseek-chat",
            is_fallback=False,
            latency_ms=2200.0,
            error_message="Erro da API OpenRouter (APIConnectionError): Connection error.",
        )

        from fastapi.testclient import TestClient
        from nemo_server import app

        with patch.object(ns, "get_client", return_value=client):
            with patch.object(client, "chat_completion", return_value=blocked):
                tc = TestClient(app)
                resp = tc.post(
                    "/api/nemo/chat",
                    json={"agent": "analista", "message": "oi", "messages": [], "max_tokens": 200},
                )
                self.assertEqual(resp.status_code, 200)
                data = resp.json()
                self.assertTrue(data["ok"])
                self.assertTrue(data["offline"])
                self.assertTrue(data["is_fallback"])


if __name__ == "__main__":
    unittest.main()
