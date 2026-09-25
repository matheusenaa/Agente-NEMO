"""
Testes unitários do cofre de chaves (ai_keys.py).
Valida criptografia Fernet, derivação por AUTH_SECRET, máscara e placeholders.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import unittest

from ai_keys import KeyStore, KeyStoreError, looks_like_placeholder, mask_key, _fernet_key


class TestMaskKey(unittest.TestCase):
    def test_mask_short_and_empty(self):
        self.assertEqual(mask_key(""), "")
        self.assertEqual(mask_key(None), "")
        self.assertEqual(mask_key("abcd"), "****")

    def test_mask_keeps_only_last_four(self):
        masked = mask_key("sk-or-v1-abcdef1234567890")
        self.assertEqual(masked[-4:], "7890")
        self.assertNotIn("abcdef123456", masked)
        self.assertTrue(masked.startswith("*"))

    def test_mask_strips_whitespace(self):
        self.assertEqual(mask_key("  chave1234  ")[-4:], "1234")


class TestPlaceholder(unittest.TestCase):
    def test_placeholder_detection(self):
        for bad in ("", "sua_chave_aqui", "your_key_here", "preencha", "sk-...", "dummy"):
            self.assertTrue(looks_like_placeholder(bad), bad)

    def test_real_key_not_placeholder(self):
        self.assertFalse(looks_like_placeholder("sk-or-v1-9f3a3c1e2b847d0f5a6b7c8d9e0f1a2b3c4d5e6f"))


class TestKeyStore(unittest.TestCase):
    def test_roundtrip_encrypt_decrypt(self):
        ks = KeyStore(b"segredo-de-teste")
        if not ks.available:
            self.skipTest("cryptography não instalada")
        token = ks.encrypt("sk-gemini-123456")
        self.assertNotIn("sk-gemini", token)  # nunca em texto puro
        self.assertEqual(ks.decrypt(token), "sk-gemini-123456")

    def test_autonomous_key_derivation_is_stable(self):
        # A mesma AUTH_SECRET produz a mesma chave Fernet (persistência entre restarts)
        k1 = _fernet_key(b"auth-secret-x")
        k2 = _fernet_key(b"auth-secret-x")
        self.assertEqual(k1, k2)

    def test_wrong_secret_cannot_decrypt(self):
        ks = KeyStore(b"segredo-certo")
        if not ks.available:
            self.skipTest("cryptography não instalada")
        token = ks.encrypt("valor-secreto")
        other = KeyStore(b"segredo-errado")
        with self.assertRaises(KeyStoreError):
            other.decrypt(token)

    def test_encrypt_fails_without_crypto(self):
        ks = KeyStore(b"x")
        if ks.available:
            self.skipTest("cryptography está instalada; não testável neste ambiente")
        with self.assertRaises(KeyStoreError):
            ks.encrypt("qualquer")


if __name__ == "__main__":
    unittest.main()