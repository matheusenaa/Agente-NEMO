"""
Testes de administração: painel admin (somente ADMIN), criação de contas pelo
admin, promoção/rebaixamento de role, redefinição de senha, proteção do último
admin e bloqueio de cadastro aberto.

Roda contra o backend ativo (Supabase ou Local) — cobre os dois caminhos.
"""

import os
import sys
import uuid
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import unittest

import nemo_server as ns
from fastapi.testclient import TestClient


class TestAdmin(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.tc = TestClient(ns.app)
        cls._created_ids: list = []

    @classmethod
    def tearDownClass(cls) -> None:
        for user_id in cls._created_ids:
            try:
                ns.AUTH_STORE.delete_user(user_id)
            except Exception:
                pass
        cls._created_ids.clear()

    def _register(self, name: str, tag: str):
        email = f"{tag}-{uuid.uuid4().hex[:10]}@test.local"
        user, token = ns.AUTH_STORE.register(name, email, "senha123")
        self._created_ids.append(user["id"])
        return user, token, {"Authorization": f"Bearer {token}"}

    def test_non_admin_cannot_access_admin_panel(self):
        _, _, h0 = self._register("Comum", "noadmin")
        assert self.tc.get("/api/admin/users", headers=h0).status_code == 403
        assert self.tc.post("/api/admin/users", headers=h0,
                            json={"name": "X", "email": "x@y.z", "password": "123456"}).status_code == 403

    def test_admin_crud_and_single_admin_rule(self):
        """Na política de admin único do audit, só o PRIMEIRO admin é promovido."""
        admin_user, admin_token, hA = self._register("Adm", "admcrud")

        outros_admins = [u for u in ns.AUTH_STORE.list_users()
                         if u["role"] == "admin" and u["id"] != admin_user["id"]]
        if outros_admins:
            self.skipTest("já existe outro admin no banco; admin único impede promover outro")

        # Primeiro admin: bootstrap via store (o endpoint /api/auth/bootstrap usa
        # o ADMIN_EMAIL real, que os testes não podem criar/alterar).
        promoted = ns.AUTH_STORE.set_role(admin_user["id"], "admin")
        assert promoted and promoted["role"] == "admin"

        created = self.tc.post("/api/admin/users", headers=hA, json={
            "name": "Usuario", "email": f"cr{uuid.uuid4().hex[:6]}@test.local", "password": "abc123456"}).json()["user"]
        self._created_ids.append(created["id"])
        assert created["role"] == "user"

        # admin único: promover um segundo admin → 409
        r = self.tc.put("/api/admin/users/role", headers=hA,
                        json={"userId": created["id"], "role": "admin"})
        assert r.status_code == 409

        r = self.tc.put("/api/admin/users/role", headers=hA,
                        json={"userId": created["id"], "role": "user"})
        assert r.status_code == 200

        r = self.tc.put(f"/api/admin/users/{created['id']}/password", headers=hA, json={"password": "troquei123"})
        assert r.status_code == 200
        assert ns.AUTH_STORE.login(created["email"], "troquei123")[0]["id"] == created["id"]
        with self.assertRaises(Exception):
            ns.AUTH_STORE.login(created["email"], "abc123456")

        # último admin não pode ser rebaixado (era o único do banco)
        guard = self.tc.put("/api/admin/users/role", headers=hA,
                            json={"userId": admin_user["id"], "role": "user"})
        assert guard.status_code == 409

    def test_open_registration_can_be_disabled(self):
        with patch.dict(os.environ, {"NEMO_OPEN_REGISTRATION": "0"}):
            r = self.tc.post("/api/auth/register", json={
                "name": "Fora", "email": f"x{uuid.uuid4().hex[:6]}@test.local", "password": "123456"})
            assert r.status_code == 403

    def test_sessions_persist_across_store_restart(self):
        """Sessões no Supabase sobrevivem a restart; no local são voláteis."""
        if type(ns.AUTH_STORE).__name__ != "SupabaseAuthStore":
            self.skipTest("sessões do backend local são em memória (por design)")
        import importlib
        mod = importlib.import_module("auth_supabase")
        fresh = mod.SupabaseAuthStore(ROOT)
        user, token = fresh.register(f"sess{uuid.uuid4().hex[:6]}", f"s{uuid.uuid4().hex[:10]}@test.local", "senha123")
        self._created_ids.append(user["id"])
        again = mod.SupabaseAuthStore(ROOT)
        resolved = again.resolve_token(token)
        assert resolved and resolved["id"] == user["id"]
        again.revoke_token(token)
        assert again.resolve_token(token) is None


if __name__ == "__main__":
    unittest.main()