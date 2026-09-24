"""
Testes unitários da camada de dados (data_store.py).
Valida o LocalStore (fallback JSON): conversas, memórias, chaves criptografadas,
tarefas, preferências de IA, atividade e busca. Nunca depende de rede/Supabase.
"""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import unittest

from data_store import LocalStore, make_data_store, _read_json
from ai_keys import KeyStore


class _Local:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = LocalStore(Path(self.tmp.name), b"segredo-teste")
        self.user = "u_test_1"

    def cleanup(self):
        self.tmp.cleanup()

    def _f(self, name: str) -> Path:
        return Path(self.tmp.name) / "_data" / "users" / self.user / name


class TestConversations(unittest.TestCase):
    def setUp(self):
        self.ctx = _Local()

    def tearDown(self):
        self.ctx.cleanup()

    def test_create_and_append(self):
        conv = self.ctx.store.create_conversation(self.ctx.user, "analista", "Projeto NEMO")
        self.assertTrue(conv["id"])
        self.ctx.store.append_message(self.ctx.user, conv["id"], "user", "oi", {})
        self.ctx.store.append_message(self.ctx.user, conv["id"], "assistant", "olá", {})
        messages = self.ctx.store.list_messages(self.ctx.user, conv["id"])
        self.assertEqual([m["role"] for m in messages], ["user", "assistant"])

    def test_list_filters_by_agent(self):
        c1 = self.ctx.store.create_conversation(self.ctx.user, "analista", "A")
        self.ctx.store.create_conversation(self.ctx.user, "redator", "B")
        list_all = self.ctx.store.list_conversations(self.ctx.user)
        self.assertEqual(len(list_all), 2)
        list_agent = self.ctx.store.list_conversations(self.ctx.user, "analista")
        self.assertEqual([c["id"] for c in list_agent], [c1["id"]])


class TestMemories(unittest.TestCase):
    def setUp(self):
        self.ctx = _Local()

    def tearDown(self):
        self.ctx.cleanup()

    def test_save_list_delete(self):
        mem = self.ctx.store.save_memory(self.ctx.user, "analista", "Prefere relatórios curtos", "pref")
        self.assertTrue(mem["id"])
        found = self.ctx.store.list_memories(self.ctx.user, "analista")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["content"], "Prefere relatórios curtos")
        self.assertFalse(self.ctx.store.delete_memory(self.ctx.user, "m_inexistente"))
        self.assertTrue(self.ctx.store.delete_memory(self.ctx.user, mem["id"]))
        self.assertEqual(self.ctx.store.list_memories(self.ctx.user), [])


class TestApiKeys(unittest.TestCase):
    def setUp(self):
        self.ctx = _Local()

    def tearDown(self):
        self.ctx.cleanup()

    def test_roundtrip_encrypted_at_rest(self):
        self.ctx.store.save_api_key(self.ctx.user, "gemini", "token-criptografado", "********7890")
        raw = _read_json(self.ctx._f("ai_keys.json"), {})
        stored = raw["gemini"]
        self.assertNotIn("sk-", raw["gemini"]["encrypted"])  # nunca texto puro
        listed = self.ctx.store.list_api_keys(self.ctx.user)
        self.assertEqual(listed[0]["provider"], "gemini")
        self.assertEqual(listed[0]["masked"], "********7890")

    def test_get_api_key_decrypts(self):
        ks = self.ctx.store.keystore
        enc = ks.encrypt("sk-gemini-real-123456")
        self.ctx.store.save_api_key(self.ctx.user, "gemini", enc, "********3456")
        self.assertEqual(self.ctx.store.get_api_key(self.ctx.user, "gemini"), "sk-gemini-real-123456")

    def test_delete(self):
        self.ctx.store.save_api_key(self.ctx.user, "groq", "x", "****")
        self.assertFalse(self.ctx.store.delete_api_key(self.ctx.user, "gemini"))
        self.assertTrue(self.ctx.store.delete_api_key(self.ctx.user, "groq"))


class TestSettingsAndTasksAndActivity(unittest.TestCase):
    def setUp(self):
        self.ctx = _Local()

    def tearDown(self):
        self.ctx.cleanup()

    def test_ai_settings_merge(self):
        self.ctx.store.save_ai_settings(self.ctx.user, {"default_provider": "gemini"})
        self.ctx.store.save_ai_settings(self.ctx.user, {"default_model": "gemini-2.5-flash"})
        settings = self.ctx.store.get_ai_settings(self.ctx.user)
        self.assertEqual(settings["default_provider"], "gemini")
        self.assertEqual(settings["default_model"], "gemini-2.5-flash")

    def test_tasks_save_update_delete(self):
        task = {"id": "t1", "title": "Relatório", "priority": "high", "agent_id": "analista", "status": "pending"}
        self.ctx.store.save_task(self.ctx.user, task)
        self.assertEqual(len(self.ctx.store.list_tasks(self.ctx.user)), 1)
        task["status"] = "done"
        self.ctx.store.save_task(self.ctx.user, task)  # upsert pelo id
        self.assertEqual(self.ctx.store.list_tasks(self.ctx.user)[0]["status"], "done")
        self.assertTrue(self.ctx.store.delete_task(self.ctx.user, "t1"))
        self.assertEqual(self.ctx.store.list_tasks(self.ctx.user), [])

    def test_activity_and_search(self):
        self.ctx.store.log_activity(self.ctx.user, "nemo", "chat", "ok", "gemini", "gemini-2.5-flash", 12.5)
        acts = self.ctx.store.list_activity(self.ctx.user)
        self.assertEqual(acts[0]["operation"], "chat")
        self.ctx.store.save_search(self.ctx.user, "pesquisador", "imovirtual", "duckduckgo", [{"url": "x"}])
        searches = _read_json(self.ctx._f("searches.json"), [])
        self.assertEqual(len(searches), 1)


class TestFactory(unittest.TestCase):
    def test_factory_returns_local_without_env(self):
        tmp = tempfile.TemporaryDirectory()
        with unittest.mock.patch.dict("os.environ", {}, clear=False):
            store = make_data_store(Path(tmp.name), b"segredo")
        self.assertIsInstance(store, LocalStore)
        self.assertTrue(store.enabled)
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()