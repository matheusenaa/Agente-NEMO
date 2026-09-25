import tempfile
import unittest
from pathlib import Path

from auth import ADMIN_EMAIL, AuthError, AuthStore


class TestAuthBootstrap(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.store = AuthStore(self.root)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_bootstrap_creates_first_admin(self):
        user, created = self.store.bootstrap_admin("Administrador", ADMIN_EMAIL, "senha-segura")

        self.assertTrue(created)
        self.assertEqual(user["role"], "admin")
        self.assertNotIn("password_hash", user)
        self.assertTrue(self.store.has_admin())
        self.assertTrue(AuthStore(self.root).is_admin(user["id"]))

    def test_bootstrap_promotes_existing_user_with_valid_password(self):
        user, token = self.store.register("Usuário", ADMIN_EMAIL, "senha-segura")
        promoted, created = self.store.bootstrap_admin("Pessoa", ADMIN_EMAIL, "senha-segura")

        self.assertFalse(created)
        self.assertEqual(promoted["id"], user["id"])
        self.assertEqual(promoted["role"], "admin")
        self.assertTrue(self.store.is_admin(user["id"]))
        self.assertTrue(token)

    def test_bootstrap_rejects_wrong_password_for_existing_user(self):
        self.store.register("Usuário", ADMIN_EMAIL, "senha-segura")

        with self.assertRaises(AuthError) as error:
            self.store.bootstrap_admin("Pessoa", ADMIN_EMAIL, "senha-errada")

        self.assertEqual(error.exception.status, 401)
        self.assertFalse(self.store.has_admin())

    def test_bootstrap_rejects_non_admin_email(self):
        with self.assertRaises(AuthError) as error:
            self.store.bootstrap_admin("Outro", "outro@example.com", "senha-segura")

        self.assertEqual(error.exception.status, 403)

    def test_bootstrap_rejects_second_admin(self):
        self.store.bootstrap_admin("Administrador", ADMIN_EMAIL, "senha-segura")
        other, _ = self.store.register("Pessoa", "pessoa@example.com", "senha-segura")

        with self.assertRaises(AuthError) as error:
            self.store.set_role(other["id"], "admin")

        self.assertEqual(error.exception.status, 409)

    def test_last_admin_cannot_be_demoted(self):
        user, _ = self.store.bootstrap_admin("Administrador", ADMIN_EMAIL, "senha-segura")

        with self.assertRaises(AuthError) as error:
            self.store.set_role(user["id"], "user")

        self.assertEqual(error.exception.status, 409)

    def test_register_normalizes_and_rejects_duplicate_email(self):
        user, _ = self.store.register("Pessoa", "  Pessoa@Example.COM ", "senha-segura")

        self.assertEqual(user["email"], "pessoa@example.com")
        with self.assertRaises(AuthError) as error:
            self.store.register("Outra", "PESSOA@example.com", "outra-senha")
        self.assertEqual(error.exception.status, 409)

    def test_sessions_persist_and_revoke(self):
        user, token = self.store.register("Pessoa", "pessoa@example.com", "senha-segura")
        reloaded = AuthStore(self.root)

        self.assertEqual(reloaded.resolve_token(token)["id"], user["id"])
        reloaded.revoke_token(token)
        self.assertIsNone(AuthStore(self.root).resolve_token(token))

    def test_oauth_state_is_one_time(self):
        state, nonce = self.store.create_oauth_state("google")

        self.assertEqual(self.store.consume_oauth_state(state, "google")["nonce"], nonce)
        self.assertIsNone(self.store.consume_oauth_state(state, "google"))

    def test_oauth_requires_verified_email(self):
        with self.assertRaises(AuthError) as error:
            self.store.oauth_login("google", "google-123", "pessoa@example.com", "Pessoa", email_verified=False)

        self.assertEqual(error.exception.status, 403)


if __name__ == "__main__":
    unittest.main()
