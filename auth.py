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
from typing import Any, Dict, List, Optional, Tuple

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


ADMIN_BOOTSTRAP_EMAIL = os.getenv("NEMO_ADMIN_EMAIL", "").strip().lower()


def validate_registration(name: str, email: str, password: str) -> None:
    """Validação comum a register e criação por admin (nos dois backends)."""
    name = (name or "").strip()
    email = (email or "").strip().lower()
    if not name or len(name) < 2:
        raise AuthError("Informe seu nome (mínimo 2 letras).", 400)
    if not email or "@" not in email or "." not in email:
        raise AuthError("Informe um e-mail válido.", 400)
    if not password or len(password) < 6:
        raise AuthError("A senha deve ter pelo menos 6 caracteres.", 400)


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
        validate_registration(name, email, password)
        email = (email or "").strip().lower()
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
            "role": "user",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._users[user_id] = record
        self._maybe_promote(record)
        self._save()
        public = {k: v for k, v in record.items() if k != "password_hash"}
        return public, self._issue_token(user_id)

    def login(self, email: str, password: str) -> Tuple[Dict[str, Any], str]:
        email = (email or "").strip().lower()
        user = next((u for u in self._users.values() if u.get("email") == email), None)
        if not user or not self._verify_password(password or "", user.get("password_hash", "")):
            raise AuthError("E-mail ou senha incorretos.", 401)
        self._maybe_promote(user)
        public = {k: v for k, v in user.items() if k != "password_hash"}
        return public, self._issue_token(user["id"])

    # ------------------------------------------------------------------
    # Roles (USER / ADMIN)
    # ------------------------------------------------------------------
    @staticmethod
    def role_of(user: Optional[Dict[str, Any]]) -> str:
        """Role do usuário (default 'user'). Contas sem o campo são tratadas como USER."""
        return "admin" if (user or {}).get("role") == "admin" else "user"

    def is_admin(self, user_id: str) -> bool:
        user = self._users.get(user_id)
        return bool(user) and user.get("role") == "admin"

    def set_role(self, user_id: str, role: str) -> Optional[Dict[str, Any]]:
        """Promove/rebaixa um usuário. Retorna o usuário público atualizado."""
        if role not in ("user", "admin"):
            raise AuthError("Role inválida. Use 'user' ou 'admin'.", 400)
        user = self._users.get(user_id)
        if not user:
            return None
        user["role"] = role
        self._save()
        return {k: v for k, v in user.items() if k != "password_hash"}

    def list_users(self) -> List[Dict[str, Any]]:
        """Lista todos os usuários (sem hashes) — uso administrativo."""
        return [{k: v for k, v in u.items() if k != "password_hash"} for u in self._users.values()]

    def create_user(self, name: str, email: str, password: str, role: str = "user") -> Dict[str, Any]:
        """Cria uma conta pelo ADMIN (não emite sessão)."""
        validate_registration(name, email, password)
        email = (email or "").strip().lower()
        if any(u.get("email") == email for u in self._users.values()):
            raise AuthError("Este e-mail já está cadastrado.", 409)
        user_id = "u_" + secrets.token_hex(4) + "_" + "".join(c for c in name.lower() if c in USERNAME_RE)[:8] or "_user"
        while user_id in self._users:
            user_id = "u_" + secrets.token_hex(4)
        record = {
            "id": user_id,
            "name": (name or "").strip(),
            "email": email,
            "password_hash": self._hash_password(password),
            "role": role if role in ("user", "admin") else "user",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._users[user_id] = record
        self._save()
        return {k: v for k, v in record.items() if k != "password_hash"}

    def reset_password(self, user_id: str, password: str) -> Optional[Dict[str, Any]]:
        user = self._users.get(user_id)
        if not user or not password or len(password) < 6:
            raise AuthError("A senha deve ter pelo menos 6 caracteres.", 400)
        user["password_hash"] = self._hash_password(password)
        self._save()
        return {k: v for k, v in user.items() if k != "password_hash"}

    def delete_user(self, user_id: str) -> bool:
        """Remove um usuário (usado pelo admin/limpeza). False se não existir."""
        if user_id not in self._users:
            return False
        del self._users[user_id]
        self._save()
        for token, sess in list(self.sessions.items()):
            if sess.get("user_id") == user_id:
                self.sessions.pop(token, None)
        return True

    def admin_count(self) -> int:
        return sum(1 for u in self._users.values() if u.get("role") == "admin")

    def _maybe_promote(self, user: Dict[str, Any]) -> None:
        """Bootstrap: NEMO_ADMIN_EMAIL registrado/logado vira admin automaticamente."""
        if ADMIN_BOOTSTRAP_EMAIL and user.get("email") and user["email"].lower() == ADMIN_BOOTSTRAP_EMAIL:
            if user.get("role") != "admin":
                user["role"] = "admin"
                self._save()

    def user_dir(self, user_id: str) -> Path:
        """Diretório de dados do usuário (área privada)."""
        d = _data_dir(self.root) / "users" / user_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def events_file(self, user_id: str) -> Path:
        return self.user_dir(user_id) / "events.json"

    # ------------------------------------------------------------------
    # Login social (OAuth)
    # ------------------------------------------------------------------
    def oauth_login(self, provider: str, provider_id: str, email: str, name: str) -> Tuple[Dict[str, Any], str]:
        """Encontra ou cria um usuário a partir do perfil OAuth e emite token.

        O e-mail é a chave de vínculo: se já existir uma conta local com o mesmo
        e-mail, o login social reutiliza essa conta (preservando eventuais
        privilégios de admin). Caso contrário cria uma nova conta com role
        "user" e marca a origem do provedor.
        """
        email = (email or "").strip().lower()
        name = (name or "Novo usuário").strip()
        user = next((u for u in self._users.values() if u.get("email") == email), None)
        if not user:
            user_id = "u_" + secrets.token_hex(4) + "_" + provider
            while user_id in self._users:
                user_id = "u_" + secrets.token_hex(4) + "_" + provider
            user = {
                "id": user_id,
                "name": name,
                "email": email,
                "role": "user",
                "oauth": provider,
                "oauth_id": provider_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._users[user_id] = user
            self._save()
        elif not user.get("oauth_id"):
            user["oauth"] = provider
            user["oauth_id"] = provider_id
            self._save()
        public = {k: v for k, v in user.items() if k != "password_hash"}
        return public, self._issue_token(user["id"])


def make_auth_store(root: Path) -> AuthStore:
    """Supabase (usuários/sessões no banco) quando configurado; senão AuthStore local."""
    try:
        from auth_supabase import SupabaseAuthStore

        sb = SupabaseAuthStore(root)
        if sb.enabled:
            return sb
    except Exception:
        pass
    return AuthStore(root)