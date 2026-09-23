"""
NEMO IDE — Autenticação de usuários (multiusuário, local-first/segura).

Armazena usuários em `_data/users.json` com hash PBKDF2 (salt individual) —
nunca a senha em texto puro. Sessões = tokens HMAC-SHA256 assinados com
expiração, mantidos em memória (invalidados no restart do servidor).

Fluxo:
    POST /api/auth/register  -> cria conta e retorna token
    POST /api/auth/login     -> autentica e retorna token
    POST /api/auth/logout    -> invalida o token
    GET  /api/auth/me        -> usuário atual (Autorização: Bearer <token>)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

PBKDF2_ITERATIONS = 200_000
SESSION_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 dias
USERNAME_RE = "abcdefghijklmnopqrstuvwxyz0123456789_"


def _data_dir(root: Path) -> Path:
    return root / "_data"


def _users_file(root: Path) -> Path:
    return _data_dir(root) / "users.json"


def _secret(root: Path) -> bytes:
    """Segredo para assinar tokens. Reutiliza o .env se existir AUTH_SECRET."""
    env_path = root / ".env"
    secret = os.getenv("AUTH_SECRET", "")
    if not secret and env_path.is_file():
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith("AUTH_SECRET="):
                secret = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if not secret:
        secret = "nemo-local-" + base64.urlsafe_b64encode(os.urandom(24)).decode().rstrip("=")
    return secret.encode("utf-8")


class AuthError(Exception):
    def __init__(self, message: str, status: int = 401):
        super().__init__(message)
        self.status = status
        self.message = message


class AuthStore:
    def __init__(self, root: Path):
        self.root = root
        self.file = _users_file(root)
        self.secret = _secret(root)
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self._users: Dict[str, Dict[str, Any]] = self._load()

    # ------------------------------------------------------------------
    # Persistência
    # ------------------------------------------------------------------
    def _load(self) -> Dict[str, Dict[str, Any]]:
        if not self.file.is_file():
            return {}
        try:
            data = json.loads(self.file.read_text(encoding="utf-8", errors="replace"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save(self) -> None:
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self.file.write_text(json.dumps(self._users, ensure_ascii=False, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Helpers de hash
    # ------------------------------------------------------------------
    @staticmethod
    def _hash_password(password: str, salt: Optional[str] = None) -> str:
        salt_bytes = base64.b64decode(salt) if salt else os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, PBKDF2_ITERATIONS)
        return f"{base64.b64encode(salt_bytes).decode()}${PBKDF2_ITERATIONS}${base64.b64encode(digest).decode()}"

    @staticmethod
    def _verify_password(password: str, stored: str) -> bool:
        try:
            salt_b64, iterations, digest_b64 = stored.split("$")
            salt = base64.b64decode(salt_b64)
            digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
            return hmac.compare_digest(digest_b64, base64.b64encode(digest).decode())
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Tokens
    # ------------------------------------------------------------------
    def _issue_token(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        self.sessions[token] = {
            "user_id": user_id,
            "created_at": time.time(),
            "expires_at": time.time() + SESSION_TTL_SECONDS,
        }
        return token

    def resolve_token(self, token: str) -> Optional[Dict[str, Any]]:
        sess = self.sessions.get(token)
        if not sess:
            return None
        if sess["expires_at"] < time.time():
            self.sessions.pop(token, None)
            return None
        user = self._users.get(sess["user_id"])
        return None if not user else {k: v for k, v in user.items() if k != "password_hash"}

    def revoke_token(self, token: str) -> None:
        self.sessions.pop(token, None)

    # ------------------------------------------------------------------
    # Operações de usuário
    # ------------------------------------------------------------------
    def register(self, name: str, email: str, password: str) -> Tuple[Dict[str, Any], str]:
        name = (name or "").strip()
        email = (email or "").strip().lower()
        if not name or len(name) < 2:
            raise AuthError("Informe seu nome (mínimo 2 letras).", 400)
        if not email or "@" not in email or "." not in email:
            raise AuthError("Informe um e-mail válido.", 400)
        if not password or len(password) < 6:
            raise AuthError("A senha deve ter pelo menos 6 caracteres.", 400)
        if any(u.get("email") == email for u in self._users.values()):
            raise AuthError("Este e-mail já está cadastrado. Faça login.", 409)
        user_id = "u_" + secrets.token_hex(4) + "_" + "".join(c for c in name.lower() if c in USERNAME_RE)[:8] or "_user"
        while user_id in self._users:
            user_id = "u_" + secrets.token_hex(4)
        record = {
            "id": user_id,
            "name": name,
            "email": email,
            "password_hash": self._hash_password(password),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._users[user_id] = record
        self._save()
        public = {k: v for k, v in record.items() if k != "password_hash"}
        return public, self._issue_token(user_id)

    def login(self, email: str, password: str) -> Tuple[Dict[str, Any], str]:
        email = (email or "").strip().lower()
        user = next((u for u in self._users.values() if u.get("email") == email), None)
        if not user or not self._verify_password(password or "", user.get("password_hash", "")):
            raise AuthError("E-mail ou senha incorretos.", 401)
        public = {k: v for k, v in user.items() if k != "password_hash"}
        return public, self._issue_token(user["id"])

    def user_dir(self, user_id: str) -> Path:
        """Diretório de dados do usuário (área privada)."""
        d = _data_dir(self.root) / "users" / user_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def events_file(self, user_id: str) -> Path:
        return self.user_dir(user_id) / "events.json"


def make_auth_store(root: Path) -> AuthStore:
    return AuthStore(root)