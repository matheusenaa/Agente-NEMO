"""
NEMO — Armazenamento seguro das API Keys dos usuários.

Missão §16-19, §57:
- NUNCA expor chave no frontend, logs ou Git;
- mostrar somente máscara (últimos 4) no painel;
- encriptar em repouso com Fernet (AES-128-CBC) derivado de AUTH_SECRET.

A KeyStore não guarda nada por conta própria: apenas encripta/desencripta.
A persistência fica no DataStore (Supabase Vault-compatível ou JSON local).
"""

from __future__ import annotations

import base64
import hashlib
from typing import Optional

try:
    from cryptography.fernet import Fernet, InvalidToken
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:  # pragma: no cover
    CRYPTOGRAPHY_AVAILABLE = False
    Fernet = None  # type: ignore
    InvalidToken = Exception  # type: ignore


class KeyStoreError(Exception):
    pass


def _fernet_key(secret: bytes) -> bytes:
    """Deriva uma chave Fernet (32 bytes base64) do segredo da aplicação."""
    return base64.urlsafe_b64encode(hashlib.sha256(secret or b"").digest())


class KeyStore:
    """Encripta/desencripta segredos com Fernet. Usa AUTH_SECRET como raiz."""

    def __init__(self, secret: bytes):
        self.available = CRYPTOGRAPHY_AVAILABLE
        if self.available:
            try:
                self._fernet = Fernet(_fernet_key(secret))
            except Exception:  # pragma: no cover
                self.available = False
                self._fernet = None
        else:
            self._fernet = None

    def encrypt(self, plaintext: str) -> str:
        if not self.available or self._fernet is None:
            raise KeyStoreError(
                "Criptografia indisponível. Instale a biblioteca 'cryptography': pip install cryptography"
            )
        return self._fernet.encrypt((plaintext or "").encode("utf-8")).decode("ascii")

    def decrypt(self, token: str) -> str:
        if not self.available or self._fernet is None:
            raise KeyStoreError(
                "Criptografia indisponível. Instale a biblioteca 'cryptography': pip install cryptography"
            )
        try:
            return self._fernet.decrypt(token.encode("ascii")).decode("utf-8")
        except (InvalidToken, Exception):
            raise KeyStoreError("Não foi possível desencriptar o segredo armazenado.")


def mask_key(key: str) -> str:
    """Máscara segura: '************ABCD' — nunca exibe a chave completa."""
    key = (key or "").strip()
    if not key:
        return ""
    if len(key) <= 4:
        return "*" * len(key)
    return "*" * max(1, len(key) - 4) + key[-4:]


def looks_like_placeholder(api_key: str) -> bool:
    api_key = (api_key or "").strip()
    if not api_key:
        return True
    for bad in ("sua_chave", "your_key", "preencha", "sk-...", "dummy"):
        if api_key.startswith(bad) or api_key == bad:
            return True
    return False