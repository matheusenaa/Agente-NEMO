"""
NEMO IDE — AuthStore persistido no Supabase.

Igual ao AuthStore (validação/tokens/hash PBKDF2), mas os usuários vivem na
tabela `auth_users` e as sessões na `auth_sessions`. Assim contas e logins
sobrevivem a redeploy/restart em hosting de disco efêmero (Render).

Acesso exclusivo do backend (service role, ignora RLS); as tabelas não têm
policies — anon/authenticated são negados por RLS.
"""

from __future__ import annotations

import os
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from auth import (
    AuthError,
    AuthStore,
    SESSION_TTL_SECONDS,
    _secret,
    validate_registration,
)

try:  # mesmo guard do data_store.py
    from supabase import create_client  # type: ignore
    SUPABASE_PKG = True
except Exception:  # pragma: no cover
    SUPABASE_PKG = False


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SupabaseAuthStore(AuthStore):
    """Backend de autenticação com usuários/sessões no Supabase."""

    def __init__(self, root: Path):
        self.root = root
        self.secret = _secret(root)
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self._users: Dict[str, Dict[str, Any]] = {}
        self.admin_email = os.getenv("NEMO_ADMIN_EMAIL", "").strip().lower()
        self.enabled = False
        if not SUPABASE_PKG:
            return
        url = os.getenv("SUPABASE_URL", "").strip()
        service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        if not (url and service_key):
            return
        try:
            self.client = create_client(url.strip(), service_key.strip())
            self.enabled = True
        except Exception:
            self.enabled = False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _t(self, table: str):
        return self.client.table(table)

    @staticmethod
    def _maybe(data: Any) -> Optional[Dict[str, Any]]:
        """Resolve maybe_single().execute(): em alguns SDKs retorna None."""
        res = getattr(data, "data", data)
        return res if isinstance(res, dict) and res else None

    def _row(self, table: str, **eq) -> Optional[Dict[str, Any]]:
        q = self._t(table).select("*")
        for k, v in eq.items():
            q = q.eq(k, v)
        return self._maybe(q.maybe_single().execute())

    @staticmethod
    def _public(user: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not user:
            return None
        return {k: v for k, v in user.items() if k != "password_hash"}

    @staticmethod
    def _uid(name: str) -> str:
        base = "".join(c for c in (name or "").lower() if c.isalnum() or c == "_")[:8]
        return "u_" + secrets.token_hex(4) + ("_" + base if base else "")

    def _fresh_uid(self, name: str) -> str:
        while True:
            user_id = self._uid(name)
            if not self._row("auth_users", id=user_id):
                return user_id

    def _maybe_promote(self, user_id: str, email: str) -> None:
        """Bootstrap: NEMO_ADMIN_EMAIL registrado/logado vira admin automaticamente."""
        if self.admin_email and email and email.strip().lower() == self.admin_email:
            user = self._row("auth_users", id=user_id)
            if user and user.get("role") != "admin":
                self._t("auth_users").update({"role": "admin"}).eq("id", user_id).execute()

    # ------------------------------------------------------------------
    # Tokens (sessões persistidas)
    # ------------------------------------------------------------------
    def _issue_token(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        now = time.time()
        self._t("auth_sessions").insert({
            "token": token,
            "user_id": user_id,
            "created_at": _now_iso(),
            "expires_at": datetime.fromtimestamp(now + SESSION_TTL_SECONDS, tz=timezone.utc).isoformat(),
        }).execute()
        self.sessions[token] = {"user_id": user_id, "created_at": now, "expires_at": now + SESSION_TTL_SECONDS}
        return token

    def resolve_token(self, token: Optional[str]) -> Optional[Dict[str, Any]]:
        if not token:
            return None
        sess = self._row("auth_sessions", token=token)
        if not sess:
            return None
        if sess["expires_at"] < _now_iso():
            self.revoke_token(token)
            return None
        return self._public(self._row("auth_users", id=sess["user_id"]))

    def revoke_token(self, token: Optional[str]) -> None:
        if not token:
            return
        self.sessions.pop(token, None)
        try:
            self._t("auth_sessions").delete().eq("token", token).execute()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Usuários
    # ------------------------------------------------------------------
    def register(self, name: str, email: str, password: str) -> Tuple[Dict[str, Any], str]:
        validate_registration(name, email, password)
        email = (email or "").strip().lower()
        if self._row("auth_users", email=email):
            raise AuthError("Este e-mail já está cadastrado. Faça login.", 409)
        user_id = self._fresh_uid(name)
        record = {
            "id": user_id,
            "name": (name or "").strip(),
            "email": email,
            "password_hash": AuthStore._hash_password(password),
            "role": "user",
            "created_at": _now_iso(),
        }
        self._t("auth_users").insert(record).execute()
        self._maybe_promote(user_id, email)
        return self._public(self._row("auth_users", id=user_id)) or {}, self._issue_token(user_id)

    def login(self, email: str, password: str) -> Tuple[Dict[str, Any], str]:
        email = (email or "").strip().lower()
        user = self._row("auth_users", email=email)
        if not user or not AuthStore._verify_password(password or "", user.get("password_hash", "")):
            raise AuthError("E-mail ou senha incorretos.", 401)
        self._maybe_promote(user["id"], email)
        return self._public(self._row("auth_users", id=user["id"])) or {}, self._issue_token(user["id"])

    def oauth_login(self, provider: str, provider_id: str, email: str, name: str) -> Tuple[Dict[str, Any], str]:
        email = (email or "").strip().lower()
        user = self._row("auth_users", email=email)
        if not user:
            user_id = self._fresh_uid(name)
            user = {
                "id": user_id,
                "name": (name or "Novo usuário").strip(),
                "email": email,
                "role": "user",
                "oauth": provider,
                "oauth_id": provider_id,
                "created_at": _now_iso(),
            }
            self._t("auth_users").insert(user).execute()
        elif not user.get("oauth_id"):
            self._t("auth_users").update({"oauth": provider, "oauth_id": provider_id}).eq("id", user["id"]).execute()
            user["oauth"], user["oauth_id"] = provider, provider_id
        self._maybe_promote(user["id"], email)
        return self._public(self._row("auth_users", id=user["id"])) or {}, self._issue_token(user["id"])

    def is_admin(self, user_id: str) -> bool:
        user = self._row("auth_users", id=user_id)
        return bool(user) and user.get("role") == "admin"

    def admin_count(self) -> int:
        data = self._t("auth_users").select("role").eq("role", "admin").execute().data
        return len(data or [])

    def set_role(self, user_id: str, role: str) -> Optional[Dict[str, Any]]:
        if role not in ("user", "admin"):
            raise AuthError("Role inválida. Use 'user' ou 'admin'.", 400)
        user = self._row("auth_users", id=user_id)
        if not user:
            return None
        self._t("auth_users").update({"role": role}).eq("id", user_id).execute()
        user["role"] = role
        return self._public(user)

    def list_users(self) -> List[Dict[str, Any]]:
        data = self._t("auth_users").select("*").order("created_at", desc=False).execute().data
        return [self._public(u) or {} for u in (data or [])]

    def create_user(self, name: str, email: str, password: str, role: str = "user") -> Dict[str, Any]:
        """Cria uma conta pelo ADMIN (não emite sessão)."""
        validate_registration(name, email, password)
        email = (email or "").strip().lower()
        if self._row("auth_users", email=email):
            raise AuthError("Este e-mail já está cadastrado.", 409)
        user_id = self._fresh_uid(name)
        record = {
            "id": user_id,
            "name": (name or "").strip(),
            "email": email,
            "password_hash": AuthStore._hash_password(password),
            "role": role if role in ("user", "admin") else "user",
            "created_at": _now_iso(),
        }
        self._t("auth_users").insert(record).execute()
        return self._public(record) or {}

    def reset_password(self, user_id: str, password: str) -> Optional[Dict[str, Any]]:
        user = self._row("auth_users", id=user_id)
        if not user:
            return None
        if not password or len(password) < 6:
            raise AuthError("A senha deve ter pelo menos 6 caracteres.", 400)
        self._t("auth_users").update({"password_hash": AuthStore._hash_password(password)}).eq("id", user_id).execute()
        return self._public(user)

    def delete_user(self, user_id: str) -> bool:
        """Remove um usuário e as sessões dele (FK cascade remove as sessões)."""
        res = self._t("auth_users").delete().eq("id", user_id).execute()
        return bool(getattr(res, "data", None))