"""
NEMO IDE — Autenticação de usuários (multiusuário, local-first/segura).

Armazena usuários em `_data/users.json` com hash PBKDF2 (salt individual) —
 nunca a senha em texto puro. Sessões persistem em `_data/sessions.json`; o
 navegador usa cookie HttpOnly e o backend mantém compatibilidade com Bearer.


Fluxo:
    POST /api/auth/register  -> cria conta e sessão
    POST /api/auth/login     -> autentica e cria sessão
    POST /api/auth/logout    -> invalida a sessão
    GET  /api/auth/me        -> usuário atual da sessão
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import tempfile
import threading
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PBKDF2_ITERATIONS = 200_000
SESSION_TTL_SECONDS = 60 * 60 * 24 * 7
SHORT_SESSION_TTL_SECONDS = 60 * 60 * 12
OAUTH_STATE_TTL_SECONDS = 60 * 10
ADMIN_EMAIL = "matheusenaa@gmail.com"
USERNAME_RE = "abcdefghijklmnopqrstuvwxyz0123456789_"
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
USER_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def normalize_email(value: str) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).strip().casefold()


def is_valid_email(value: str) -> bool:
    email = normalize_email(value)
    return bool(email and len(email) <= 254 and EMAIL_RE.fullmatch(email) and ".." not in email)


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=str(path.parent), prefix=f".{path.name}.",
            suffix=".tmp", delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(content)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
        os.replace(temporary_path, path)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    finally:
        if temporary_path and temporary_path.exists():
            try:
                temporary_path.unlink()
            except OSError:
                pass


def _normalize_oauth_accounts(record: Dict[str, Any]) -> Dict[str, str]:
    accounts = record.get("oauth_accounts")
    if isinstance(accounts, dict):
        return {str(provider): str(provider_id) for provider, provider_id in accounts.items() if provider_id}
    provider = record.get("oauth")
    provider_id = record.get("oauth_id")
    return {str(provider): str(provider_id)} if provider and provider_id else {}


def _data_dir(root: Path) -> Path:
    return root / "_data"


def _users_file(root: Path) -> Path:
    return _data_dir(root) / "users.json"


def _sessions_file(root: Path) -> Path:
    return _data_dir(root) / "sessions.json"


def _oauth_states_file(root: Path) -> Path:
    return _data_dir(root) / "oauth_states.json"


def _secret(root: Path) -> bytes:
    """Segredo para assinar tokens. Reutiliza o .env ou o armazenamento local seguro."""
    env_path = root / ".env"
    secret = os.getenv("AUTH_SECRET", "")
    if not secret and env_path.is_file():
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith("AUTH_SECRET="):
                secret = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if secret in {"preencha_com_um_segredo_aleatorio_forte", "change_me", "changeme", "secret"} or len(secret) < 32:
        secret = ""
    if not secret:
        secret_path = _data_dir(root) / "auth_secret"
        try:
            secret = secret_path.read_text(encoding="utf-8").strip()
        except OSError:
            secret = ""
        if not secret:
            secret = "nemo-local-" + base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("=")
            _atomic_write(secret_path, secret)
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
        self.sessions_file = _sessions_file(root)
        self.oauth_states_file = _oauth_states_file(root)
        self.secret = _secret(root)
        self._lock = threading.RLock()
        self._users: Dict[str, Dict[str, Any]] = self._load()
        self.sessions: Dict[str, Dict[str, Any]] = self._load_sessions()
        self.oauth_states: Dict[str, Dict[str, Any]] = self._load_oauth_states()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if not self.file.is_file():
            return {}
        try:
            data = json.loads(self.file.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            return {}
        if not isinstance(data, dict):
            return {}
        users: Dict[str, Dict[str, Any]] = {}
        for user_id, value in data.items():
            if not isinstance(value, dict):
                continue
            record = dict(value)
            record["id"] = str(record.get("id") or user_id)
            email = normalize_email(record.get("email", ""))
            record["email"] = email
            record["role"] = "admin" if record.get("role") == "admin" else "user"
            record["oauth_accounts"] = _normalize_oauth_accounts(record)
            users[str(user_id)] = record
        return users

    def _load_sessions(self) -> Dict[str, Dict[str, Any]]:
        if not self.sessions_file.is_file():
            return {}
        try:
            data = json.loads(self.sessions_file.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            return {}
        if not isinstance(data, dict):
            return {}
        now = time.time()
        return {
            str(key): value
            for key, value in data.items()
            if isinstance(value, dict)
            and value.get("user_id") in self._users
            and isinstance(value.get("expires_at"), (int, float))
            and value["expires_at"] > now
        }

    def _load_oauth_states(self) -> Dict[str, Dict[str, Any]]:
        if not self.oauth_states_file.is_file():
            return {}
        try:
            data = json.loads(self.oauth_states_file.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            return {}
        if not isinstance(data, dict):
            return {}
        now = time.time()
        return {
            str(key): value
            for key, value in data.items()
            if isinstance(value, dict)
            and isinstance(value.get("expires_at"), (int, float))
            and value["expires_at"] > now
        }

    def _save(self) -> None:
        with self._lock:
            _atomic_write(self.file, json.dumps(self._users, ensure_ascii=False, indent=2))

    def _save_sessions(self) -> None:
        with self._lock:
            _atomic_write(self.sessions_file, json.dumps(self.sessions, ensure_ascii=False, indent=2))

    def _save_oauth_states(self) -> None:
        with self._lock:
            _atomic_write(self.oauth_states_file, json.dumps(self.oauth_states, ensure_ascii=False, indent=2))

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

    @staticmethod
    def _public_user(user: Dict[str, Any]) -> Dict[str, Any]:
        return {key: value for key, value in user.items() if key != "password_hash"}

    def _token_key(self, token: str) -> str:
        return hmac.new(self.secret, token.encode("utf-8"), hashlib.sha256).hexdigest()

    def _issue_token(self, user_id: str, remember: bool = True) -> str:
        with self._lock:
            if user_id not in self._users:
                raise AuthError("Usuário não encontrado.", 401)
            token = secrets.token_urlsafe(32)
            self.sessions[self._token_key(token)] = {
                "user_id": user_id,
                "created_at": time.time(),
                "expires_at": time.time() + (SESSION_TTL_SECONDS if remember else SHORT_SESSION_TTL_SECONDS),
            }
            self._save_sessions()
            return token

    @staticmethod
    def session_max_age(remember: bool) -> int:
        return SESSION_TTL_SECONDS if remember else SHORT_SESSION_TTL_SECONDS

    def resolve_token(self, token: str) -> Optional[Dict[str, Any]]:
        if not token:
            return None
        key = self._token_key(token)
        with self._lock:
            session = self.sessions.get(key)
            if not session:
                return None
            if session.get("expires_at", 0) < time.time():
                self.sessions.pop(key, None)
                self._save_sessions()
                return None
            user = self._users.get(session.get("user_id", ""))
            return None if not user else self._public_user(user)

    def revoke_token(self, token: str) -> None:
        if not token:
            return
        with self._lock:
            if self.sessions.pop(self._token_key(token), None) is not None:
                self._save_sessions()

    def create_oauth_state(self, provider: str) -> Tuple[str, str]:
        nonce = secrets.token_urlsafe(32)
        digest = hmac.new(self.secret, nonce.encode("utf-8"), hashlib.sha256).hexdigest()
        state = f"{nonce}.{digest}"
        with self._lock:
            now = time.time()
            self.oauth_states = {
                key: value for key, value in self.oauth_states.items()
                if value.get("expires_at", 0) > now
            }
            self.oauth_states[digest] = {
                "nonce": nonce,
                "provider": provider,
                "created_at": now,
                "expires_at": now + OAUTH_STATE_TTL_SECONDS,
            }
            self._save_oauth_states()
        return state, nonce

    def consume_oauth_state(self, state: str, provider: str) -> Optional[Dict[str, Any]]:
        if "." not in state:
            return None
        nonce, _, signature = state.rpartition(".")
        expected = hmac.new(self.secret, nonce.encode("utf-8"), hashlib.sha256).hexdigest()
        if not nonce or not hmac.compare_digest(expected, signature):
            return None
        with self._lock:
            record = self.oauth_states.pop(signature, None)
            if record is not None:
                self._save_oauth_states()
            if not record or record.get("nonce") != nonce:
                return None
            if record.get("provider") != provider or record.get("expires_at", 0) < time.time():
                return None
            return record

    def duplicate_emails(self) -> List[str]:
        with self._lock:
            counts: Dict[str, int] = {}
            for user in self._users.values():
                email = normalize_email(user.get("email", ""))
                if email:
                    counts[email] = counts.get(email, 0) + 1
            return sorted(email for email, count in counts.items() if count > 1)

    # ------------------------------------------------------------------
    # Operações de usuário
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_registration(name: str, email: str, password: str) -> Tuple[str, str, str]:
        name = (name or "").strip()
        email = normalize_email(email)
        if not name or len(name) < 2 or len(name) > 120:
            raise AuthError("Informe seu nome (entre 2 e 120 caracteres).", 400)
        if not is_valid_email(email):
            raise AuthError("Informe um e-mail válido.", 400)
        if not password or len(password) < 8:
            raise AuthError("A senha deve ter pelo menos 8 caracteres.", 400)
        return name, email, password

    def register(self, name: str, email: str, password: str, remember: bool = True) -> Tuple[Dict[str, Any], str]:
        name, email, password = self._validate_registration(name, email, password)
        with self._lock:
            if any(normalize_email(user.get("email", "")) == email for user in self._users.values()):
                raise AuthError("Este e-mail já está cadastrado. Faça login.", 409)
            suffix = "".join(character for character in name.casefold() if character in USERNAME_RE)[:8] or "user"
            user_id = f"u_{secrets.token_hex(4)}_{suffix}"
            while user_id in self._users:
                user_id = f"u_{secrets.token_hex(4)}"
            record = {
                "id": user_id,
                "name": name,
                "email": email,
                "password_hash": self._hash_password(password),
                "role": "user",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._users[user_id] = record
            self._save()
            return self._public_user(record), self._issue_token(user_id, remember)

    def login(self, email: str, password: str, remember: bool = True) -> Tuple[Dict[str, Any], str]:
        email = normalize_email(email)
        with self._lock:
            candidates = [user for user in self._users.values() if normalize_email(user.get("email", "")) == email]
            user: Optional[Dict[str, Any]] = None
            if len(candidates) == 1:
                user = candidates[0]
            elif len(candidates) > 1:
                matches = [candidate for candidate in candidates if self._verify_password(password or "", candidate.get("password_hash", ""))]
                if len(matches) == 1:
                    user = matches[0]
                else:
                    raise AuthError("Há contas duplicadas para este e-mail. Fale com o administrador.", 409)
            if not user or not self._verify_password(password or "", user.get("password_hash", "")):
                raise AuthError("E-mail ou senha incorretos.", 401)
            return self._public_user(user), self._issue_token(user["id"], remember)

    @staticmethod
    def role_of(user: Optional[Dict[str, Any]]) -> str:
        """Role do usuário (default 'user'). Contas sem o campo são tratadas como USER."""
        return "admin" if (user or {}).get("role") == "admin" else "user"

    def is_admin(self, user_id: str) -> bool:
        with self._lock:
            user = self._users.get(user_id)
            return bool(user) and user.get("role") == "admin"

    def has_admin(self) -> bool:
        with self._lock:
            return any(self.role_of(user) == "admin" for user in self._users.values())

    def admin_count(self) -> int:
        with self._lock:
            return sum(1 for user in self._users.values() if self.role_of(user) == "admin")

    def bootstrap_admin(self, name: str, email: str, password: str) -> Tuple[Dict[str, Any], bool]:
        """Cria o primeiro administrador ou promove a conta local definida."""
        name, email, password = self._validate_registration(name, email, password)
        if email != normalize_email(ADMIN_EMAIL):
            raise AuthError(f"O e-mail do administrador inicial deve ser {ADMIN_EMAIL}.", 403)
        with self._lock:
            if self.has_admin():
                raise AuthError("Já existe uma conta ADM. Use a gestão de usuários para alterar roles.", 409)
            candidates = [user for user in self._users.values() if normalize_email(user.get("email", "")) == email]
            if len(candidates) > 1:
                raise AuthError("Há contas duplicadas para o e-mail do administrador. Resolva antes do bootstrap.", 409)
            if candidates:
                existing = candidates[0]
                if not existing.get("password_hash") or not self._verify_password(password, existing["password_hash"]):
                    raise AuthError("A senha da conta existente está incorreta.", 401)
                existing["role"] = "admin"
                self._save()
                return self._public_user(existing), False

            suffix = "".join(character for character in name.casefold() if character in USERNAME_RE)[:8] or "admin"
            user_id = f"u_{secrets.token_hex(4)}_{suffix}"
            while user_id in self._users:
                user_id = f"u_{secrets.token_hex(4)}"
            record = {
                "id": user_id,
                "name": name,
                "email": email,
                "password_hash": self._hash_password(password),
                "role": "admin",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._users[user_id] = record
            self._save()
            return self._public_user(record), True

    def set_role(self, user_id: str, role: str) -> Optional[Dict[str, Any]]:
        """Promove/rebaixa um usuário. Retorna o usuário público atualizado."""
        if role not in ("user", "admin"):
            raise AuthError("Role inválida. Use 'user' ou 'admin'.", 400)
        with self._lock:
            user = self._users.get(user_id)
            if not user:
                return None
            current_role = self.role_of(user)
            if current_role == "admin" and role == "user" and self.admin_count() <= 1:
                raise AuthError("Não é possível rebaixar o único administrador.", 409)
            if current_role != "admin" and role == "admin" and self.has_admin():
                raise AuthError("Já existe uma conta ADM. Não crie um segundo administrador.", 409)
            if current_role == role:
                return self._public_user(user)
            user["role"] = role
            self._save()
            return self._public_user(user)

    def list_users(self) -> List[Dict[str, Any]]:
        """Lista todos os usuários (sem hashes) — uso administrativo."""
        with self._lock:
            return [self._public_user(user) for user in self._users.values()]

    def user_dir(self, user_id: str) -> Path:
        """Diretório de dados do usuário (área privada)."""
        if not USER_ID_RE.fullmatch(user_id or ""):
            raise AuthError("Identificador de usuário inválido.", 400)
        directory = _data_dir(self.root) / "users" / user_id
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def events_file(self, user_id: str) -> Path:
        return self.user_dir(user_id) / "events.json"

    def oauth_login(
        self,
        provider: str,
        provider_id: str,
        email: str,
        name: str,
        email_verified: bool = True,
    ) -> Tuple[Dict[str, Any], str]:
        if not provider_id:
            raise AuthError("O provedor não informou uma identidade válida.", 502)
        email = normalize_email(email)
        if not is_valid_email(email):
            raise AuthError("O provedor não informou um e-mail válido.", 502)
        if not email_verified:
            raise AuthError("O e-mail do provedor não está verificado.", 403)
        name = (name or "Novo usuário").strip()[:120] or "Novo usuário"
        with self._lock:
            user: Optional[Dict[str, Any]] = None
            for candidate in self._users.values():
                accounts = _normalize_oauth_accounts(candidate)
                if accounts.get(provider) == provider_id:
                    user = candidate
                    break
            if user is None:
                candidates = [candidate for candidate in self._users.values() if normalize_email(candidate.get("email", "")) == email]
                if len(candidates) > 1:
                    raise AuthError("Há contas duplicadas para este e-mail. Resolva o vínculo OAuth com o administrador.", 409)
                user = candidates[0] if candidates else None
            changed = False
            if user is None:
                suffix = "".join(character for character in provider.casefold() if character in USERNAME_RE)[:8] or "oauth"
                user_id = f"u_{secrets.token_hex(4)}_{suffix}"
                while user_id in self._users:
                    user_id = f"u_{secrets.token_hex(4)}"
                user = {
                    "id": user_id,
                    "name": name,
                    "email": email,
                    "role": "user",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                self._users[user_id] = user
                changed = True
            accounts = _normalize_oauth_accounts(user)
            if accounts.get(provider) != provider_id:
                accounts[provider] = provider_id
                user["oauth_accounts"] = accounts
                user["oauth"] = provider
                user["oauth_id"] = provider_id
                changed = True
            if changed:
                self._save()
            return self._public_user(user), self._issue_token(user["id"])


def make_auth_store(root: Path) -> AuthStore:
    return AuthStore(root)