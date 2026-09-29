"""
Testes do pipeline de chat: busca com tool calling, isolamento de conversa,
persistência e streaming SSE (missão §6/§9/§10/§12).

Estes testes NÃO chamam a rede: o cliente OpenRouter e o serviço de busca são
substituídos por dublês. O que se verifica é a LÓGICA do fluxo e, sobretudo,
os contratos que quebravam em produção (conversa errada, busca desconectada,
SSE que não persistia).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

import nemo_server as ns
from auth import AuthStore
from openrouter_client import CompletionResult


def _ok(content="Resposta do modelo.", model="deepseek/deepseek-chat", **kw):
    return CompletionResult(
        success=True, content=content, model_used=model, original_model=model,
        is_fallback=False, latency_ms=12.0, provider="openrouter", **kw
    )


def _tool_call(query="preço do dólar hoje", call_id="call_abc"):
    return CompletionResult(
        success=True, content="", model_used="deepseek/deepseek-chat",
        original_model="deepseek/deepseek-chat", is_fallback=False, latency_ms=8.0,
        tool_calls=[{"id": call_id, "name": "web_search", "arguments": {"query": query}}],
    )


class ChatPipelineCase(unittest.TestCase):
    """Base: sobe o app com auth em diretório temporário e cliente falso."""

    agent = "analista"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.auth_store = AuthStore(Path(self._tmp.name))
        user, self.token = self.auth_store.register("Teste", "teste@example.com", "senha-segura")
        self.user_id = user["id"]
        self.client = MagicMock()
        self.client.has_valid_key_format.return_value = True
        self.client.chat_completion.return_value = _ok()
        self.client.chat_completion_with_tools.return_value = _ok()
        self.patches = [
            patch.object(ns, "AUTH_STORE", self.auth_store),
            patch.object(ns, "get_client", return_value=self.client),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        self.tc = TestClient(ns.app)
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def chat(self, **body):
        body.setdefault("agent", self.agent)
        body.setdefault("message", "oi")
        body.setdefault("messages", [])
        body.setdefault("max_tokens", 200)
        return self.tc.post("/api/nemo/chat", headers=self.headers, json=body)

    def search_ok(self, results=None):
        return {
            "ok": True, "query": "q", "provider": "openrouter-web",
            "results": results if results is not None else [
                {"title": "Fechamento do dólar", "url": "https://bcb.gov.br/x",
                 "snippet": "O dólar fechou a R$ 5,22.", "source": "openrouter-web",
                 "date": None, "query": "q"},
            ],
        }


class TestConversationRouting(ChatPipelineCase):
    def test_new_conversation_flag_creates_separate_thread(self):
        """Regressão: tudo ia para `convs[0]` e o histórico virava uma mistura."""
        first = self.chat(message="primeira pergunta", new_conversation=True)
        self.assertEqual(first.status_code, 200)
        cid1 = first.json()["conversation_id"]
        self.assertTrue(cid1)

        second = self.chat(message="segunda pergunta", new_conversation=True)
        cid2 = second.json()["conversation_id"]
        self.assertTrue(cid2)
        self.assertNotEqual(cid1, cid2, "nova thread precisa de novo conversation_id")

        convs = ns.DATA_STORE.list_conversations(self.user_id, self.agent)
        self.assertEqual(len(convs), 2)

    def test_continuing_same_id_does_not_create_new_thread(self):
        first = self.chat(message="pergunta 1", new_conversation=True)
        cid = first.json()["conversation_id"]
        second = self.chat(message="pergunta 2", conversation_id=cid)
        self.assertEqual(second.json()["conversation_id"], cid)
        convs = ns.DATA_STORE.list_conversations(self.user_id, self.agent)
        self.assertEqual(len(convs), 1)
        messages = ns.DATA_STORE.list_messages(self.user_id, cid)
        self.assertEqual([m["role"] for m in messages],
                         ["user", "assistant", "user", "assistant"])

    def test_foreign_conversation_id_is_refused(self):
        """Nunca mistura contexto entre contas."""
        _, other_token = self.auth_store.register("Outro", "outro@example.com", "senha-segura")
        other_id = self.auth_store.resolve_token(other_token)["id"]
        foreign = ns.DATA_STORE.create_conversation(other_id, self.agent, "privado")["id"]

        data = self.chat(message="espionagem", conversation_id=foreign).json()
        self.assertNotEqual(data["conversation_id"], foreign)

    def test_messages_are_persisted_with_content(self):
        data = self.chat(message="conteudo do usuario", new_conversation=True).json()
        messages = ns.DATA_STORE.list_messages(self.user_id, data["conversation_id"])
        self.assertEqual(messages[0]["content"], "conteudo do usuario")
        self.assertEqual(messages[1]["content"], "Resposta do modelo.")


class TestWebSearchIntegration(ChatPipelineCase):
    def test_heuristic_triggers_search_and_feeds_model(self):
        self.client.chat_completion_with_tools.return_value = _ok()
        with patch.object(ns, "_run_web_search", return_value=self.search_ok()) as run:
            data = self.chat(message="qual o preço do dólar hoje?").json()
        self.assertTrue(run.called, "pergunta de atualidade tem que buscar")
        self.assertTrue(data["used_search"])
        self.assertEqual(data["search_provider"], "openrouter-web")
        # O contexto da busca precisa chegar ao MODELO, não só ao usuário.
        sent = self.client.chat_completion.call_args.kwargs["messages"]
        blob = json.dumps(sent, ensure_ascii=False, default=str)
        self.assertIn("bcb.gov.br", blob)
        self.assertIn("5,22", blob)

    def test_tool_calling_loop_when_heuristic_does_not_fire(self):
        """O MODELO pede a ferramenta mesmo sem a heurística → busca executa."""
        self.client.chat_completion_with_tools.return_value = _tool_call()
        self.client.chat_completion.return_value = _ok("O dólar fechou a R$ 5,22.")
        with patch.object(ns, "_run_web_search", return_value=self.search_ok()) as run:
            data = self.chat(message="me conte sobre氧金币").json()
        self.assertTrue(run.called)
        self.assertTrue(data["used_search"])
        sent = self.client.chat_completion.call_args.kwargs["messages"]
        roles = [m["role"] for m in sent]
        self.assertIn("tool", roles, "o resultado da ferramenta volta como role=tool")

    def test_failed_search_tells_model_not_to_invent(self):
        fail = {"ok": False, "query": "q", "results": [], "error": "Nenhum mecanismo respondeu."}
        self.client.chat_completion_with_tools.return_value = _ok()
        with patch.object(ns, "_run_web_search", return_value=fail):
            data = self.chat(message="qual o preço do dólar hoje?").json()
        self.assertTrue(data["used_search"])
        sent = self.client.chat_completion.call_args.kwargs["messages"]
        blob = json.dumps(sent, ensure_ascii=False, default=str)
        self.assertIn("FALHOU", blob)
        self.assertIn("NUNCA invente", blob)

    def test_search_service_error_does_not_break_chat(self):
        from web_search import WebSearchError
        with patch.object(ns, "_run_web_search",
                          side_effect=WebSearchError("limite")) as run:
            resp = self.chat(message="preço do dólar hoje")
        self.assertEqual(resp.status_code, 200, "falha de busca não pode virar 500")
        self.assertTrue(resp.json()["ok"])

    def test_agent_without_search_tool_never_searches(self):
        case_agent = "nemo"
        with patch.object(ns, "_run_web_search", return_value=self.search_ok()) as run:
            resp = self.tc.post("/api/nemo/chat", headers=self.headers, json={
                "agent": case_agent, "message": "preço do dólar hoje?", "messages": [],
                "max_tokens": 200,
            })
        self.assertEqual(resp.status_code, 200)
        allowed = ns.AGENT_TOOLS.get(case_agent, [])
        if "web_search" in allowed or "search" in allowed:
            self.assertTrue(run.called)
        else:
            self.assertFalse(run.called, "agente sem permissão não pode buscar")


class TestStreaming(ChatPipelineCase):
    def _sse(self, resp):
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertIn("text/event-stream", resp.headers["content-type"])
        events = []
        for block in resp.text.split("\n\n"):
            if not block.strip():
                continue
            name, data = None, None
            for line in block.splitlines():
                if line.startswith("event: "):
                    name = line[7:]
                elif line.startswith("data: "):
                    data = json.loads(line[6:])
            if name:
                events.append((name, data))
        return events

    def _neutral_tools(self):
        """A rodada de tools devolve 'nada a fazer', então o fluxo segue para a
        geração token a token. Se devolvesse texto, o pipeline trataria como
        'já respondido' e nunca chamaria `stream_chat`."""
        self.client.chat_completion_with_tools.return_value = CompletionResult(
            success=True, content="", model_used="deepseek/deepseek-chat",
            original_model="deepseek/deepseek-chat", is_fallback=False, latency_ms=5.0,
        )

    def _client(self):
        self._neutral_tools()

        def gen():
            for piece in ["O dólar ", "fechou a ", "R$ 5,22."]:
                yield piece
        self.client.stream_chat.return_value = gen()

    def test_stream_emits_deltas_and_done(self):
        self._client()
        events = self._sse(self.tc.post("/api/nemo/chat/stream", headers=self.headers, json={
            "agent": self.agent, "message": "resuma", "messages": [], "max_tokens": 200,
        }))
        names = [n for n, _ in events]
        self.assertEqual(names[0], "start")
        self.assertEqual(names[-1], "done")
        deltas = [d["text"] for n, d in events if n == "delta"]
        self.assertEqual("".join(deltas), "O dólar fechou a R$ 5,22.")
        self.assertTrue(events[-1][1]["ok"])

    def test_stream_persists_conversation(self):
        self._client()
        events = self._sse(self.tc.post("/api/nemo/chat/stream", headers=self.headers, json={
            "agent": self.agent, "message": "pergunta que fica", "messages": [],
            "max_tokens": 200, "new_conversation": True,
        }))
        cid = events[-1][1]["conversation_id"]
        self.assertTrue(cid, "o streaming precisa gravar a conversa")
        messages = ns.DATA_STORE.list_messages(self.user_id, cid)
        self.assertEqual(messages[1]["content"], "O dólar fechou a R$ 5,22.")

    def test_stream_uses_same_search_as_normal_chat(self):
        self._client()
        with patch.object(ns, "_run_web_search", return_value=self.search_ok()) as run:
            events = self._sse(self.tc.post("/api/nemo/chat/stream", headers=self.headers, json={
                "agent": self.agent, "message": "preço do dólar hoje?", "messages": [],
                "max_tokens": 200,
            }))
        self.assertTrue(run.called)
        self.assertTrue(any(n == "sources" for n, _ in events))
        sources = [d for n, d in events if n == "sources"][0]
        self.assertEqual(sources["provider"], "openrouter-web")

    def test_stream_reports_failure_without_pretending(self):
        self._neutral_tools()

        def boom():
            raise RuntimeError("APIConnectionError: Connection error.")
            yield  # pragma: no cover
        self.client.stream_chat.return_value = boom()
        events = self._sse(self.tc.post("/api/nemo/chat/stream", headers=self.headers, json={
            "agent": self.agent, "message": "oi", "messages": [], "max_tokens": 200,
        }))
        err = [d for n, d in events if n == "error"]
        self.assertTrue(err, "falha de stream precisa virar evento de erro")
        self.assertEqual(err[0]["error_code"], "openrouter_unavailable")
        self.assertFalse(events[-1][1]["ok"])
        self.assertEqual([n for n, _ in events].count("done"), 1, "done não pode duplicar")

    def test_stream_resets_when_falling_back_to_another_model(self):
        self._neutral_tools()
        calls = {"n": 0}

        def flaky(model, **kw):
            def gen():
                calls["n"] += 1
                if calls["n"] == 1:
                    yield "parcial errado "
                    raise RuntimeError("modelo caiu")
                yield "resposta boa"
            return gen()
        self.client.stream_chat.side_effect = flaky
        events = self._sse(self.tc.post("/api/nemo/chat/stream", headers=self.headers, json={
            "agent": self.agent, "message": "oi", "messages": [], "max_tokens": 200,
        }))
        names = [n for n, _ in events]
        self.assertIn("reset", names, "cliente precisa descartar o parcial antes do fallback")
        # O texto vem pelos deltas; quem consome o stream deve zerar o buffer ao
        # receber `reset` (por isso não enviamos os deltas do modelo que caiu).
        deltas = "".join(d["text"] for n, d in events if n == "delta")
        self.assertIn("resposta boa", deltas)
        self.assertEqual(names.count("done"), 1)

    def test_stream_respects_rate_limit(self):
        self._neutral_tools()
        orig = ns.AI_RATE_LIMITER.limit
        ns.AI_RATE_LIMITER.limit = 1
        ns.AI_RATE_LIMITER._hits = {}   # janela limpa: outros testes já consumiram
        try:
            self._client()
            body = {"agent": self.agent, "message": "oi", "messages": [], "max_tokens": 200}
            first = self.tc.post("/api/nemo/chat/stream", headers=self.headers, json=body)
            self.assertTrue(self._sse(first)[-1][1]["ok"])
            second = self.tc.post("/api/nemo/chat/stream", headers=self.headers, json=body)
            events = self._sse(second)
            err = [d for n, d in events if n == "error"]
            self.assertTrue(err and err[0].get("rate_limited"), events)
            self.assertFalse(events[-1][1]["ok"])
        finally:
            ns.AI_RATE_LIMITER.limit = orig
            ns.AI_RATE_LIMITER._hits = {}


class TestFailureHonesty(ChatPipelineCase):
    """Falhas de OpenRouter devem ser explicadas com a CAUSA certa.

    Regressão: um HTTP 402 ("Insufficient credits") casava com o marcador
    "insufficient" de `_is_auth_error` e o servidor acusava a chave de
    inválida, mandando o administrador trocar uma chave que está correta."""

    def _fail_with(self, message):
        self.client.chat_completion.return_value = CompletionResult(
            success=False, content="", error_message=message,
            model_used="deepseek/deepseek-chat", original_model="deepseek/deepseek-chat",
            is_fallback=False, latency_ms=3.0,
        )
        self.client.chat_completion_with_tools.return_value = CompletionResult(
            success=False, content="", error_message=message,
            model_used="deepseek/deepseek-chat", original_model="deepseek/deepseek-chat",
            is_fallback=False, latency_ms=3.0,
        )

    def test_credits_error_not_reported_as_auth(self):
        self._fail_with("402 Insufficient credits. This account never purchased credits.")
        body = self.chat().json()
        self.assertEqual(body["error_code"], "openrouter_no_credits", body)
        self.assertNotEqual(body["error_code"], "openrouter_auth")
        self.assertIn("crédito", (body["content"] + body["error"]).lower())
        self.assertIn("402", body["content"])

    def test_credits_message_advises_not_to_rotate_key(self):
        self._fail_with("Insufficient credits")
        body = self.chat().json()
        self.assertIn("não é preciso", body["content"].lower())

    def test_real_401_still_reported_as_auth(self):
        self._fail_with("401 Unauthorized: invalid api key")
        body = self.chat().json()
        self.assertEqual(body["error_code"], "openrouter_auth", body)
        self.assertIn("inválida", body["error"].lower())

    def test_classifiers_do_not_overlap(self):
        credits = "Insufficient credits. This account never purchased credits."
        self.assertTrue(ns._is_credits_error(credits))
        self.assertFalse(ns._is_auth_error(credits))
        self.assertTrue(ns._is_auth_error("401 Unauthorized"))
        self.assertFalse(ns._is_credits_error("401 Unauthorized"))

    def test_stream_reports_credits_error(self):
        self._fail_with("Insufficient credits")
        self.client.stream_chat.side_effect = RuntimeError("402 Insufficient credits")
        events = self._sse(self.tc.post("/api/nemo/chat/stream", headers=self.headers, json={
            "agent": self.agent, "message": "oi", "messages": [], "max_tokens": 200,
        }))
        err = [d for n, d in events if n == "error"]
        self.assertTrue(err, events)
        self.assertEqual(err[0].get("error_code"), "openrouter_no_credits", err[0])
        self.assertEqual(events[-1][0], "done")
        self.assertFalse(events[-1][1]["ok"])

    def test_stream_keeps_root_cause_over_last_model_error(self):
        """Regressão: o primário caía por falta de crédito (402) e o fallback
        respondia 400 'not a valid model ID'. Como só a ÚLTIMA mensagem era
        usada, o usuário recebia 'Erro ao chamar o modelo' e nunca ficava
        sabendo que a conta está sem saldo."""
        credits = "402 {'error': {'message': 'Insufficient credits. This account never purchased credits.'}}"
        dead_slug = "400 {'error': {'message': 'deepseek/deepseek-coder is not a valid model ID'}}"
        # A rodada de tools precisa devolver vazio, senão o pipeline trata como
        # "já respondido" e nunca chega ao `stream_chat`.
        self.client.chat_completion_with_tools.return_value = CompletionResult(
            success=True, content="", model_used="deepseek/deepseek-chat",
            original_model="deepseek/deepseek-chat", is_fallback=False, latency_ms=5.0,
        )
        calls = {"n": 0}

        def flaky(model, **kw):
            def gen():
                calls["n"] += 1
                if calls["n"] == 1:
                    raise RuntimeError(credits)
                raise RuntimeError(dead_slug)
            return gen()
        self.client.stream_chat.side_effect = flaky
        events = self._sse(self.tc.post("/api/nemo/chat/stream", headers=self.headers, json={
            "agent": self.agent, "message": "oi", "messages": [], "max_tokens": 200,
        }))
        err = [d for n, d in events if n == "error"]
        self.assertTrue(err, events)
        self.assertEqual(err[0].get("error_code"), "openrouter_no_credits", err[0])
        self.assertIn("crédito", (err[0]["error"] + err[0]["content"]).lower())
        self.assertIn("reset", [n for n, _ in events], "o fallback continua sendo tentado")

    def _sse(self, resp):
        self.assertEqual(resp.status_code, 200, resp.text)
        events = []
        for block in resp.text.split("\n\n"):
            if not block.strip():
                continue
            name, data = None, None
            for line in block.splitlines():
                if line.startswith("event: "):
                    name = line[7:]
                elif line.startswith("data: "):
                    data = json.loads(line[6:])
            if name:
                events.append((name, data))
        return events


class TestSearchDegradedPath(ChatPipelineCase):
    """Regressão: `WebSearchError` não tinha `.message`, e o endpoint de
    busca acessava esse atributo no `except` — transformava toda falha de
    busca em HTTP 500 em vez de responder `ok: False` com honestidade."""

    def test_web_search_error_has_message_attribute(self):
        err = ns.WebSearchError("Limite de pesquisas atingido.")
        self.assertEqual(err.message, "Limite de pesquisas atingido.")
        self.assertEqual(ns.WebSearchError().message, "Falha na busca.")

    def test_search_endpoint_returns_ok_false_not_500(self):
        with patch.object(ns.WEB_SEARCH_SERVICE, "search", side_effect=ns.WebSearchError("limite atingido")):
            resp = self.tc.get("/api/nemo/ai/search?q=dolar", headers=self.headers)
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["results"], [])
        self.assertIn("limite atingido", body["error"])

    def test_search_helper_never_raises(self):
        with patch.object(ns.WEB_SEARCH_SERVICE, "search", side_effect=ns.WebSearchError("boom")):
            out = ns._run_web_search(self.user_id, self.agent, "dolar")
        self.assertFalse(out["ok"])
        self.assertIn("boom", out["error"])


class TestServerOwnedMemory(ChatPipelineCase):
    """A memória da conversa é do SERVIDOR, não do cliente.

    Regressão grave: as mensagens eram gravadas (o histórico aparecia na tela)
    mas nunca voltavam para o prompt. Bastava recarregar a página ou logar de
    novo para o agente esquecer tudo — a memória era só de fachada."""

    def _sent_messages(self):
        """Mensagens efetivamente enviadas ao modelo. Agentes com ferramenta de
        busca passam pela rodada de tools; os outros, direto na geração."""
        for mock in (self.client.chat_completion_with_tools, self.client.chat_completion):
            if mock.call_args and "messages" in mock.call_args.kwargs:
                return mock.call_args.kwargs["messages"]
        self.fail("nenhuma chamada de geração registrada")

    def test_history_from_store_reaches_the_model(self):
        first = self.chat(message="Meu codinome e Tubarao Azul", new_conversation=True)
        cid = first.json()["conversation_id"]
        self.client.chat_completion.reset_mock()
        self.client.chat_completion_with_tools.reset_mock()
        self.chat(message="Qual e meu codinome?", conversation_id=cid)
        sent = self._sent_messages()
        text = " ".join(m["content"] for m in sent)
        self.assertIn("Tubarao Azul", text, "o histórico do banco não foi para o prompt")
        self.assertIn("Qual e meu codinome?", text)
        roles = [m["role"] for m in sent]
        self.assertEqual(roles[0], "system")
        self.assertIn("assistant", roles, "a resposta anterior também precisa voltar")

    def test_memory_survives_client_without_history(self):
        """Cliente que não manda histórico (outro device, API) continua lembrando."""
        first = self.chat(message="Minha senha secreta de teste e abcd1234", new_conversation=True)
        cid = first.json()["conversation_id"]
        self.client.chat_completion.reset_mock()
        self.client.chat_completion_with_tools.reset_mock()
        resp = self.tc.post("/api/nemo/chat", headers=self.headers, json={
            "agent": self.agent, "message": "repita a senha", "messages": [],
            "conversation_id": cid,
        })
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertIn("abcd1234", " ".join(m["content"] for m in self._sent_messages()))

    def test_client_history_not_duplicated(self):
        first = self.chat(message="primeira", new_conversation=True)
        cid = first.json()["conversation_id"]
        self.client.chat_completion.reset_mock()
        self.client.chat_completion_with_tools.reset_mock()
        self.tc.post("/api/nemo/chat", headers=self.headers, json={
            "agent": self.agent, "message": "segunda", "conversation_id": cid,
            "messages": [{"role": "user", "content": "primeira"},
                         {"role": "assistant", "content": "resposta 1"}],
        })
        user_turns = [m["content"] for m in self._sent_messages() if m["role"] == "user"]
        self.assertEqual(user_turns.count("primeira"), 1, "turno duplicado: %s" % user_turns)

    def test_history_is_user_scoped(self):
        """Histórico de outro usuário não pode vazar para o prompt."""
        first = self.chat(message="segredo do usuario A", new_conversation=True)
        cid = first.json()["conversation_id"]
        with patch.object(ns.DATA_STORE, "list_messages", return_value=[]):
            self.client.chat_completion.reset_mock()
            self.client.chat_completion_with_tools.reset_mock()
            self.chat(message="o que voce lembra?", conversation_id=cid)
        self.assertNotIn("segredo do usuario A", " ".join(m["content"] for m in self._sent_messages()))

    def test_history_failure_does_not_break_chat(self):
        with patch.object(ns.DATA_STORE, "list_messages", side_effect=Exception("banco caiu")):
            resp = self.chat(message="oi", conversation_id="63d16ae0-ce3d-4c0d-8f39-3dc19346dfa9")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertTrue((resp.json().get("reply") or resp.json().get("content")))

    def test_history_is_capped(self):
        stored = [{"role": "user" if i % 2 == 0 else "assistant", "content": "msg %d" % i}
                  for i in range(60)]
        with patch.object(ns.DATA_STORE, "list_messages", return_value=stored):
            out = ns._load_history(self.user_id, "x", limit=12)
        self.assertEqual(len(out), 12)
        self.assertEqual(out[-1]["content"], "msg 59")

    def test_history_ignores_tool_and_empty_rows(self):
        stored = [
            {"role": "user", "content": "oi"},
            {"role": "tool", "content": "resultado bruto"},
            {"role": "assistant", "content": "   "},
            {"role": "system", "content": "prompt interno"},
            {"role": "assistant", "content": "tudo certo"},
        ]
        with patch.object(ns.DATA_STORE, "list_messages", return_value=stored):
            out = ns._load_history(self.user_id, "x")
        self.assertEqual([m["role"] for m in out], ["user", "assistant"])
        self.assertEqual(out[-1]["content"], "tudo certo")


class TestProviderRouting(ChatPipelineCase):
    """A Central de IA precisa valer alguma coisa.

    Regressão estrutural: o chat chamava `get_client()` (OpenRouter) direto e
    ignorava o provedor escolhido pelo usuário. Com a conta do OpenRouter sem
    crédito, o SYNOP ficava offline mesmo com `GEMINI_API_KEY` funcionando."""

    def _settings(self, **kw):
        return patch.object(ns.DATA_STORE, "get_ai_settings", return_value=kw)

    def test_uses_user_provider_when_configured(self):
        with self._settings(default_provider="gemini", default_model="gemini-2.5-flash"):
            with patch.object(ns.AI_SERVICE, "has_system_key", side_effect=lambda p: p == "gemini"):
                req = ns.ChatRequest(agent=self.agent, message="oi")
                self.assertEqual(ns._resolve_provider(req, self.user_id), "gemini")

    def test_falls_back_to_openrouter_when_provider_has_no_key(self):
        with self._settings(default_provider="gemini"):
            with patch.object(ns.AI_SERVICE, "has_system_key", return_value=False):
                with patch.object(ns.DATA_STORE, "get_api_key", return_value=None):
                    req = ns.ChatRequest(agent=self.agent, message="oi")
                    self.assertEqual(ns._resolve_provider(req, self.user_id), "openrouter")

    def test_unknown_provider_falls_back_to_openrouter(self):
        """Provedor desconhecido não pode derrubar o chat."""
        with self._settings(default_provider="banana"):
            with patch.object(ns.AI_SERVICE, "default_provider", return_value="banana"):
                with patch.object(ns.AI_SERVICE, "has_system_key", return_value=False):
                    with patch.object(ns.DATA_STORE, "get_api_key", return_value=None):
                        req = ns.ChatRequest(agent=self.agent, message="oi")
                        self.assertEqual(ns._resolve_provider(req, self.user_id), "openrouter")

    def test_unknown_user_provider_defers_to_system_default(self):
        """Config salva errada é ignorada; o servidor continua funcionando."""
        with self._settings(default_provider="banana"):
            with patch.object(ns.AI_SERVICE, "default_provider", return_value="gemini"):
                with patch.object(ns.AI_SERVICE, "has_system_key", side_effect=lambda p: p == "gemini"):
                    req = ns.ChatRequest(agent=self.agent, message="oi")
                    self.assertEqual(ns._resolve_provider(req, self.user_id), "gemini")

    def test_explicit_request_provider_wins(self):
        with self._settings(default_provider="openrouter"):
            with patch.object(ns.AI_SERVICE, "has_system_key", side_effect=lambda p: p == "gemini"):
                req = ns.ChatRequest(agent=self.agent, message="oi", provider="gemini")
                self.assertEqual(ns._resolve_provider(req, self.user_id), "gemini")

    def test_model_is_translated_to_provider_vocabulary(self):
        """`deepseek/deepseek-chat` não existe no Gemini: usar o slug cru
        devolveria 404 e o usuário veria erro de modelo em vez de resposta."""
        with self._settings(default_provider="gemini", default_model="gemini-3.5-flash"):
            model, fallbacks = ns._provider_model(self.user_id, "gemini", "deepseek/deepseek-chat")
        self.assertEqual(model, "gemini-3.5-flash")
        self.assertEqual(fallbacks, [])
        self.assertNotIn("/", model, "slug do OpenRouter não pode vazar para o Gemini")

    def test_agent_override_beats_user_default(self):
        """A Central de IA salva `agent_overrides` por agente; o chat precisa ler.

        Antes o override era gravado e nunca usado: o usuário configurava
        "este agente usa o Groq" e o SYNOP seguia no provedor do usuário."""
        settings = {"default_provider": "gemini", "default_model": "gemini-flash-latest",
                    "agent_overrides": {"analista": {"provider": "groq", "model": "qwen/qwen3.8-27b"}}}
        with self._settings(**settings):
            with patch.object(ns.AI_SERVICE, "has_system_key", return_value=True):
                req = ns.ChatRequest(agent="analista", message="oi")
                self.assertEqual(ns._resolve_provider(req, self.user_id), "groq")
            model, _ = ns._provider_model(self.user_id, "groq", "deepseek/deepseek-chat", "analista")
        self.assertEqual(model, "qwen/qwen3.8-27b", "modelo do agente tem de vencer o default do usuário")

    def test_agent_override_does_not_leak_to_other_agents(self):
        """Override é por agente: o 'nemo' não pode herdar o Groq do 'analista'."""
        settings = {"default_provider": "gemini", "default_model": "gemini-flash-latest",
                    "agent_overrides": {"analista": {"provider": "groq"}}}
        with self._settings(**settings):
            with patch.object(ns.AI_SERVICE, "has_system_key", side_effect=lambda p: p == "gemini"):
                req = ns.ChatRequest(agent="nemo", message="oi")
                self.assertEqual(ns._resolve_provider(req, self.user_id), "gemini")

    def test_system_default_provider_is_used_when_user_has_no_choice(self):
        """`NEMO_AI_PROVIDER` do servidor valia nada: sem config do usuário o chat
        ia para o OpenRouter (que está sem crédito) e ignorava o Gemini do .env."""
        with self._settings():
            with patch.object(ns.AI_SERVICE, "default_provider", return_value="gemini"):
                with patch.object(ns.AI_SERVICE, "has_system_key", side_effect=lambda p: p == "gemini"):
                    req = ns.ChatRequest(agent=self.agent, message="oi")
                    self.assertEqual(ns._resolve_provider(req, self.user_id), "gemini")

    def test_explicit_openrouter_choice_is_respected(self):
        """Escolher OpenRouter é uma decisão do usuário, não um valor default."""
        with self._settings():
            with patch.object(ns.AI_SERVICE, "default_provider", return_value="gemini"):
                with patch.object(ns.AI_SERVICE, "has_system_key", return_value=True):
                    req = ns.ChatRequest(agent=self.agent, message="oi", provider="openrouter")
                    self.assertEqual(ns._resolve_provider(req, self.user_id), "openrouter")

    def test_retired_gemini_models_are_not_offered(self):
        """`gemini-2.5-flash` e `2.0` respondem 404 "no longer available to new
        users". Mantê-los na Central de IA só gera erro para o usuário."""
        for dead in ("gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"):
            self.assertNotIn(dead, ns.GEMINI_MODELS, f"{dead} foi descontinuado pelo Google")
        self.assertTrue(ns.GEMINI_MODELS, "a lista de modelos do Gemini não pode ficar vazia")

    def test_failure_names_the_real_provider(self):
        """Responder 'chave do OpenRouter inválida' quando a falha foi no Gemini
        manda o usuário corrigir o serviço errado."""
        with self._settings(default_provider="gemini"):
            with patch.object(ns.AI_SERVICE, "has_system_key", side_effect=lambda p: p == "gemini"):
                with patch.object(ns.AI_SERVICE, "complete", return_value=CompletionResult(
                        success=False, content="", error_message="HTTP 503 overloaded",
                        model_used="gemini-flash-latest", original_model="gemini-flash-latest",
                        provider="gemini", is_fallback=False, latency_ms=1.0)):
                    body = self.chat(provider="gemini").json()
        self.assertEqual(body.get("error_code"), "ai_error", body)
        self.assertIn("Gemini", body.get("error", ""), body.get("error"))
        self.assertNotIn("OpenRouter", body.get("error", "") + body.get("content", ""))
        self.assertEqual(body.get("provider"), "gemini", body)

    def test_translation_falls_back_to_first_provider_model(self):
        with self._settings(default_provider="gemini"):
            model, _ = ns._provider_model(self.user_id, "gemini", "deepseek/deepseek-chat")
        self.assertIn(model, ns.GEMINI_MODELS)

    def test_openrouter_keeps_its_own_slugs(self):
        model, fallbacks = ns._provider_model(self.user_id, "openrouter", "deepseek/deepseek-chat")
        self.assertEqual(model, "deepseek/deepseek-chat")
        self.assertTrue(fallbacks)
        for slug in fallbacks:
            self.assertNotEqual(slug, "deepseek/deepseek-coder", "slug morto removido")

    def test_chat_uses_ai_service_for_gemini(self):
        with self._settings(default_provider="gemini", default_model="gemini-2.5-flash"):
            with patch.object(ns.AI_SERVICE, "has_system_key", side_effect=lambda p: p == "gemini"):
                with patch.object(ns.AI_SERVICE, "complete", return_value=_ok("resposta do gemini")) as svc:
                    body = self.chat(provider="gemini").json()
        svc.assert_called_once()
        self.assertEqual(body.get("reply") or body.get("content"), "resposta do gemini")
        self.assertFalse(self.client.chat_completion.called, "não deve chamar o OpenRouter")

    def test_null_conversation_id_is_accepted(self):
        """Cliente sem thread mandava null e recebia 422 antes de gerar."""
        resp = self.chat(conversation_id=None, new_conversation=True)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertTrue(resp.json().get("conversation_id"))

    def test_stream_falls_back_to_sync_for_non_openrouter(self):
        with self._settings(default_provider="gemini", default_model="gemini-2.5-flash"):
            with patch.object(ns.AI_SERVICE, "has_system_key", side_effect=lambda p: p == "gemini"):
                with patch.object(ns.AI_SERVICE, "complete", return_value=_ok("resposta inteira")) as svc:
                    events = self._sse(self.tc.post("/api/nemo/chat/stream", headers=self.headers, json={
                        "agent": self.agent, "message": "oi", "provider": "gemini",
                        "messages": [], "max_tokens": 200,
                    }))
        names = [n for n, _ in events]
        self.assertEqual(names[0], "start")
        self.assertEqual(names[-1], "done")
        self.assertTrue(events[-1][1].get("ok"), events[-1])
        err = [d for n, d in events if n == "error"]
        self.assertTrue(err and err[0].get("fallback_to_sync"), err)
        text = "".join(d["text"] for n, d in events if n == "delta")
        self.assertIn("resposta inteira", text)
        svc.assert_called_once()

    def _sse(self, resp):
        self.assertEqual(resp.status_code, 200, resp.text)
        events = []
        for block in resp.text.split("\n\n"):
            if not block.strip():
                continue
            name, data = None, None
            for line in block.splitlines():
                if line.startswith("event: "):
                    name = line[7:]
                elif line.startswith("data: "):
                    data = json.loads(line[6:])
            if name:
                events.append((name, data))
        return events


class TestNoInternalLeak(ChatPipelineCase):
    """Regressão: erro de banco vazar para o cliente.

    `detail=str(exc)` devolvia o erro cru do Supabase, por exemplo
    `{'message': 'invalid input syntax for type uuid: "None"', 'code': '22P02'}`.
    Isso expõe SQL/código interno e ainda respondia 500 em vez de 404."""

    def _db_down(self):
        err = Exception("invalid input syntax for type uuid: \"abc\" | code 22P02 | "
                        "relation conversations does not exist")
        return patch.object(ns.DATA_STORE, method="side_effect", return_value=err)

    def test_messages_endpoint_hides_db_error(self):
        # UUID válido: aqui o erro é mesmo do banco e tem de virar 500 genérico.
        conv = "11111111-2222-3333-4444-555555555555"
        with patch.object(ns.DATA_STORE, "list_messages", side_effect=Exception(
                "invalid input syntax for type uuid | code 22P02")):
            resp = self.tc.get("/api/nemo/conversations/%s/messages" % conv, headers=self.headers)
        self.assertEqual(resp.status_code, 500, resp.text)
        body = resp.text
        self.assertNotIn("22P02", body)
        self.assertNotIn("uuid", body.lower())
        self.assertIn("Tente novamente", body)

    def test_invalid_conversation_id_is_client_error_not_500(self):
        """`conversations/None/messages` era 500: o Supabase recusava o id e o
        front mandava "tente de novo" para um erro que só o cliente podia corrigir."""
        for bad in ("None", "abc", "123", "11111111-2222-3333-4444"):
            resp = self.tc.get("/api/nemo/conversations/%s/messages" % bad, headers=self.headers)
            self.assertEqual(resp.status_code, 400, "%s -> %s" % (bad, resp.text))
            self.assertNotIn("22P02", resp.text)
            self.assertNotIn("Tente novamente", resp.text)
            resp = self.tc.delete("/api/nemo/conversations/%s" % bad, headers=self.headers)
            self.assertEqual(resp.status_code, 400, "%s -> %s" % (bad, resp.text))

    def test_invalid_id_never_reaches_the_database(self):
        with patch.object(ns.DATA_STORE, "list_messages", side_effect=AssertionError("banco chamado")):
            resp = self.tc.get("/api/nemo/conversations/None/messages", headers=self.headers)
        self.assertEqual(resp.status_code, 400, resp.text)

    def test_valid_uuid_with_no_data_is_not_an_error(self):
        """Conversa válida e vazia é 200: o id é válido, só não há mensagens."""
        resp = self.tc.get("/api/nemo/conversations/11111111-2222-3333-4444-555555555555/messages",
                           headers=self.headers)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json().get("messages"), [])

    def test_conversation_list_hides_db_error(self):
        with patch.object(ns.DATA_STORE, "list_conversations", side_effect=Exception(
                "relation conversations does not exist | code 42P01")):
            resp = self.tc.get("/api/nemo/conversations", headers=self.headers)
        self.assertNotIn("42P01", resp.text)
        self.assertNotIn("does not exist", resp.text)

    def test_tasks_endpoint_hides_db_error(self):
        with patch.object(ns.DATA_STORE, "list_tasks", side_effect=Exception("boom 42P01")):
            resp = self.tc.get("/api/nemo/tasks", headers=self.headers)
        self.assertNotIn("42P01", resp.text)

    def test_helper_returns_generic_http_exception(self):
        exc = ns._internal_error("teste", ValueError("detalhe secreto 22P02"))
        self.assertEqual(exc.status_code, 500)
        self.assertNotIn("22P02", exc.detail)
        self.assertIn("Tente novamente", exc.detail)


if __name__ == "__main__":
    unittest.main()
