"""
Testes das funcionalidades da missão 60 (§8 perfil do usuário, §26 histórico:
continuar/excluir/pesquisar conversas) e §38 health com modelo padrão.

Funcionam tanto com o storage Local (fallback) quanto com o Supabase,
valendo como uma camada de integração leve por cima da API.
"""

import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import unittest

import nemo_server as ns
from fastapi.testclient import TestClient


class TestProfileAndConversations(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.tc = TestClient(ns.app)

    def _register(self, tag: str):
        email = f"{tag}-{uuid.uuid4().hex[:10]}@test.local"
        user, token = ns.AUTH_STORE.register("Tester " + tag, email, "senha123")
        return {"Authorization": f"Bearer {token}"}, user["id"]

    def test_health_exposes_default_model(self):
        h = self.tc.get("/api/nemo/health").json()
        ai = h.get("ai") or {}
        self.assertTrue(ai.get("default_provider"))
        self.assertTrue(ai.get("default_model"))

    def test_profile_roundtrip(self):
        h, _ = self._register("perf")
        r = self.tc.get("/api/nemo/profile", headers=h).json()
        self.assertTrue(r["ok"])
        self.assertIn("email", r["profile"])
        r2 = self.tc.post("/api/nemo/profile", headers=h,
                          json={"name": "Marina", "language": "pt-BR", "avatar": "🐬"}).json()
        self.assertTrue(r2["ok"])
        got = self.tc.get("/api/nemo/profile", headers=h).json()["profile"]
        self.assertEqual(got["name"], "Marina")
        self.assertEqual(got["language"], "pt-BR")

    def test_conversation_search_and_delete(self):
        h, uid = self._register("conv")
        conv = self.tc.post("/api/nemo/conversations", headers=h,
                            json={"agent": "rebeca", "title": "Pesquisa de concorrentes"}).json()["conversation"]
        ns.DATA_STORE.append_message(uid, conv["id"], "user",
                                     "CUSTO-2026-XYZ preços atuais de cloud computing", {})
        nas = self.tc.get("/api/nemo/conversations?q=cloud", headers=h).json()["conversations"]
        self.assertEqual([c["id"] for c in nas], [conv["id"]])
        nada = self.tc.get("/api/nemo/conversations?q=zzzquerido", headers=h).json()["conversations"]
        self.assertEqual(nada, [])
        d = self.tc.delete(f"/api/nemo/conversations/{conv['id']}", headers=h)
        self.assertEqual(d.status_code, 200)
        d2 = self.tc.delete(f"/api/nemo/conversations/{conv['id']}", headers=h)
        self.assertEqual(d2.status_code, 404)

    def test_conversation_isolation_delete(self):
        hA, _ = self._register("cA")
        hB, _ = self._register("cB")
        conv = self.tc.post("/api/nemo/conversations", headers=hA,
                            json={"agent": "nemo", "title": "segredo do A"}).json()["conversation"]
        r = self.tc.delete(f"/api/nemo/conversations/{conv['id']}", headers=hB)
        self.assertEqual(r.status_code, 404)
        lista_b = self.tc.get("/api/nemo/conversations", headers=hB).json()["conversations"]
        self.assertNotIn(conv["id"], [c["id"] for c in lista_b])
        rA = self.tc.get("/api/nemo/conversations", headers=hA).json()["conversations"]
        self.assertIn(conv["id"], [c["id"] for c in rA])


if __name__ == "__main__":
    unittest.main()