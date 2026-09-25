"""
Testes de isolamento multiusuário (§56) + auditoria de chaves (§57) +
rate limit de IA por usuário (§35) + configuração de IA por agente (§40).

Garante que um usuário nunca enxerga dados, chaves ou atividade de outro
e que nenhuma chave bruta aparece nas respostas da API.
"""

import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import unittest

import nemo_server as ns
from fastapi.testclient import TestClient
from ai_providers import CompletionResult


def _ok_result(provider: str, model: str, content: str = "resposta simulada"):
    return CompletionResult(
        success=True, content=content, provider=provider, model_used=model,
        original_model=model, is_fallback=False, latency_ms=12.0,
        prompt_tokens=10, completion_tokens=5, total_tokens=15,
    )


def _chat_client(model: str = "openai/gpt-4o-mini", result=None):
    """Cliente OpenRouter falso para o endpoint /api/nemo/chat."""
    client = MagicMock()
    client.has_valid_key_format.return_value = True
    client.chat_completion.return_value = result or _ok_result("openrouter", model)
    return client


class TestMultiuserIsolation(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.tc = TestClient(ns.app)
        ns.AI_RATE_LIMITER._hits.clear()

    def _register(self, name: str, tag: str):
        email = f"{tag}-{uuid.uuid4().hex[:10]}@test.local"
        user, token = ns.AUTH_STORE.register(name, email, "senha123")
        return {"Authorization": f"Bearer {token}"}

    def _chat_ok(self, headers, agent="nemo"):
        with patch.object(ns, "get_client", return_value=_chat_client()):
            return self.tc.post("/api/nemo/chat",
                                json={"agent": agent, "message": "oi", "messages": [], "max_tokens": 200},
                                headers=headers)

    def test_isolation_conversation_task_memory_key(self):
        """Dados criados pelo usuário A não aparecem para o usuário B."""
        hA = self._register("Usuário A", "isoA")
        hB = self._register("Usuário B", "isoB")

        # A cria dados
        r = self.tc.post("/api/nemo/conversations", json={"agent": "nemo", "title": "Conversa secreta A"}, headers=hA)
        self.assertEqual(r.status_code, 200, r.text)
        r = self.tc.post("/api/nemo/tasks", json={"title": "Tarefa secreta A", "agentId": "nemo"}, headers=hA)
        self.assertEqual(r.status_code, 200, r.text)
        r = self.tc.post("/api/nemo/ai/memories", json={"agent": "nemo", "content": "Memória secreta A (senha: 1234)"}, headers=hA)
        self.assertEqual(r.status_code, 200, r.text)
        with patch.object(ns.AI_SERVICE, "test_key", return_value={"ok": True, "provider": "gemini", "model": "gemini-2.5-flash"}):
            r = self.tc.post("/api/nemo/ai/keys", json={"provider": "gemini", "api_key": "AIzaTESTESECRETA1234567890"}, headers=hA)
        self.assertEqual(r.status_code, 200, r.text)
        masked_a = r.json()["masked"]
        self.assertTrue(masked_a.startswith("**") and masked_a.endswith("7890"))
        with patch.object(ns, "get_client", return_value=_chat_client("openai/gpt-4o-mini")):
            self.tc.post("/api/nemo/chat", json={"agent": "nemo", "message": "leo", "messages": []}, headers=hA)

        # A confirma que vê tudo
        self.assertIn("Conversa secreta A", self.tc.get("/api/nemo/conversations", headers=hA).text)
        self.assertIn("Tarefa secreta A", self.tc.get("/api/nemo/tasks", headers=hA).text)
        self.assertIn("Memória secreta A", self.tc.get("/api/nemo/ai/memories", headers=hA).text)
        self.assertIn(masked_a, self.tc.get("/api/nemo/ai/config", headers=hA).text)

        # B NÃO vê nada de A
        self.assertNotIn("Conversa secreta A", self.tc.get("/api/nemo/conversations", headers=hB).text)
        self.assertNotIn("Tarefa secreta A", self.tc.get("/api/nemo/tasks", headers=hB).text)
        self.assertNotIn("Memória secreta A", self.tc.get("/api/nemo/ai/memories", headers=hB).text)
        self.assertNotIn(masked_a, self.tc.get("/api/nemo/ai/config", headers=hB).text)
        self.assertNotIn("Conversa secreta A", self.tc.get("/api/nemo/ai/activity", headers=hB).text)

    def test_keys_never_expose_plaintext(self):
        """Nenhuma resposta expõe a chave completa (auditoria §57)."""
        raw = "sk-or-v1-TESTESECRETA-abcdefghijklmnopqrstuvwxyz0123456789"
        hA = self._register("Usuário Chave", "keyA")
        hB = self._register("Outro Usuário", "keyB")
        with patch.object(ns.AI_SERVICE, "test_key", return_value={"ok": True, "provider": "openrouter", "model": "deepseek/deepseek-chat"}):
            r = self.tc.post("/api/nemo/ai/keys", json={"provider": "openrouter", "api_key": raw}, headers=hA)
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertNotIn(raw, str(body))

        configA = self.tc.get("/api/nemo/ai/config", headers=hA).text
        configB = self.tc.get("/api/nemo/ai/config", headers=hB).text
        self.assertNotIn(raw, configA)
        self.assertNotIn(raw, configB)

        # 'sk-or-v1-' deve estar mascarado (somente sufixo)
        self.assertIn("****************", configA)

    def test_ai_rate_limit_per_user(self):
        """Rate limit de IA por usuário (§35): após N requisições em 1min, bloqueia."""
        hA = self._register("Usuário Rate", "rateA")
        old_limiter = ns.AI_RATE_LIMITER
        ns.AI_RATE_LIMITER = ns._SlidingWindowRateLimit(3)
        try:
            for _ in range(3):
                r = self._chat_ok(hA)
                self.assertEqual(r.status_code, 200, r.text)
                self.assertFalse(r.json().get("rate_limited", False))
            r = self._chat_ok(hA)
            self.assertTrue(r.json()["rate_limited"])
            self.assertTrue(r.json()["offline"])
            # usuário B (outra chave) não é afetado
            hB = self._register("Outro Rate", "rateB")
            r = self._chat_ok(hB)
            self.assertFalse(r.json().get("rate_limited", False))
        finally:
            ns.AI_RATE_LIMITER = old_limiter

    def test_per_agent_ai_config(self):
        """Modelo do chat: request explícito > defaultModel do agente > padrão da categoria."""
        hA = self._register("Usuário Agente", "agtA")

        # Salva settings (round-trip das configurações de IA por usuário)
        r = self.tc.post("/api/nemo/ai/config", json={
            "default_provider": "gemini",
            "default_model": "gemini-2.5-flash",
            "agent_overrides": {"nemo": {"provider": "groq", "model": "llama-3.3-70b-versatile"}},
        }, headers=hA)
        self.assertEqual(r.status_code, 200, r.text)

        calls = []

        def fake_chat(**kwargs):
            calls.append(kwargs["model"])
            return _ok_result("openrouter", kwargs.get("model") or "openai/gpt-4o-mini")

        client = _chat_client()
        client.chat_completion.side_effect = fake_chat
        with patch.object(ns, "get_client", return_value=client):
            r = self.tc.post("/api/nemo/chat",
                             json={"agent": "nemo", "message": "oi", "messages": []}, headers=hA)
            self.assertEqual(r.status_code, 200, r.text)

            # request explícito TEM prioridade sobre o modelo do agente
            r = self.tc.post("/api/nemo/chat", json={
                "agent": "nemo", "message": "oi", "messages": [],
                "model": "deepseek/deepseek-chat",
            }, headers=hA)
            self.assertEqual(r.status_code, 200, r.text)

        expected_default = (ns._agent_persona("nemo") or {}).get("defaultModel") or ns.CATEGORY_MODEL_DEFAULT
        self.assertEqual(calls[0], expected_default)
        self.assertEqual(calls[1], "deepseek/deepseek-chat")

        # remoção do override (as settings continuam gerenciáveis)
        r = self.tc.post("/api/nemo/ai/config", json={"agent_overrides": {"nemo": {}}}, headers=hA)
        self.assertEqual(r.status_code, 200, r.text)
        cfg = self.tc.get("/api/nemo/ai/config", headers=hA).json()
        self.assertNotIn("nemo", (cfg["user"]["settings"].get("agent_overrides") or {}))

    def test_activity_logs_tokens(self):
        """Actividade de chat grava tokens (§34) e é isolada por usuário."""
        hA = self._register("Usuário Tokens", "tokA")
        hB = self._register("Outro Tokens", "tokB")
        with patch.object(ns, "get_client", return_value=_chat_client("openai/gpt-4o-mini")):
            r = self.tc.post("/api/nemo/chat", json={"agent": "analista", "message": "oi", "messages": []}, headers=hA)
        self.assertEqual(r.status_code, 200, r.text)

        actsA = self.tc.get("/api/nemo/ai/activity", headers=hA).json()["activity"]
        self.assertTrue(actsA, "deveria existir atividade")
        self.assertEqual(actsA[0]["total_tokens"], 15)
        self.assertEqual(actsA[0]["prompt_tokens"], 10)
        self.assertEqual(actsA[0]["completion_tokens"], 5)

        actsB = self.tc.get("/api/nemo/ai/activity", headers=hB).json()["activity"]
        self.assertNotIn("analista", [a["agent_id"] for a in actsB if a.get("operation") == "chat"])
        self.assertFalse(next((a for a in actsA if a["total_tokens"] == 15), None) is None)


if __name__ == "__main__":
    unittest.main()