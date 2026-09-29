import { useCallback } from "react";
import { useIdeStore } from "@/store/useIdeStore";
import { nemoApi, type ChatHistoryMessage } from "@/api/nemo";
import { getAgent } from "@/data/agents";
import { FUNNY_PHRASES, pickPhrase } from "@/data/statusPhrases";

/**
 * Mensagem exibida quando a requisição nem chegou ao servidor (DNS, conexão
 * recusada, servidor derrubado). Antes era a resposta para QUALQUER falha —
 * inclusive HTTP 401, 404, 422 e 500 — então um erro do backend mandava o
 * usuário "rode o servidor" (§36: não mascarar falha com resposta genérica).
 */
function describeNetworkError(error: unknown): string {
  const raw = error instanceof Error ? error.message : String(error ?? "");
  if (/Failed to fetch|NetworkError|Load failed|ERR_CONNECTION/i.test(raw)) {
    return "Não consegui alcançar o servidor do SYNOP. Verifique se ele está rodando (janela do backend ativa) e se a sua conexão com a internet funciona.";
  }
  return raw || "Falha de comunicação com o servidor.";
}

export function useNemoChat() {
  const threads = useIdeStore((s) => s.threads);
  const conversationIds = useIdeStore((s) => s.conversationIds);
  const addUserMessage = useIdeStore((s) => s.addUserMessage);
  const insertAgentMessage = useIdeStore((s) => s.insertAgentMessage);
  const patchMessage = useIdeStore((s) => s.patchMessage);
  const setLiveStatus = useIdeStore((s) => s.setLiveStatus);
  const setConversationId = useIdeStore((s) => s.setConversationId);
  const addTask = useIdeStore((s) => s.addTask);
  const updateTask = useIdeStore((s) => s.updateTask);
  const addLog = useIdeStore((s) => s.addLog);
  const addHistory = useIdeStore((s) => s.addHistory);
  const notify = useIdeStore((s) => s.notify);
  const funnyStatus = useIdeStore((s) => s.config.funnyStatus);

  const send = useCallback(
    async (agentId: string, content: string) => {
      const agent = getAgent(agentId);
      addUserMessage(agentId, content);
      addLog({ tone: "agent", agentId, text: `${agent.name} iniciou: ${content.slice(0, 70)}` });
      addHistory({ kind: "chat", title: agent.name, agentId: agent.id, detail: content.slice(0, 120) });

      const taskId =
        content.trim().length > 10
          ? addTask({ title: content.trim().slice(0, 60), priority: "normal", agentId, status: "running" })
          : null;

      setLiveStatus({ agentId, busy: true, label: "🧠 Pensando...", phrase: funnyStatus ? pickPhrase(FUNNY_PHRASES, "") : "" });
      const thinkLabels = ["🧠 Pensando...", "🔎 Investigando...", "📂 Lendo arquivos...", "💻 Codificando..."];
      const im = window.setInterval(() => {
        setLiveStatus({
          label: pickPhrase(thinkLabels, useIdeStore.getState().liveStatus.label),
        });
      }, 2600);

      const msgId = insertAgentMessage(agentId, { role: "agent", agentId, content: "" });
      let ok = false;
      let offline = false;
      // Histórico da conversa com esse agente (sem a última msg do usuário duplicar)
      const history: ChatHistoryMessage[] = (threads[agentId] ?? [])
        .filter((m) => m.content.trim().length > 0 && m.status !== "typing" && m.status !== "sending")
        .map((m): ChatHistoryMessage => ({ role: m.role === "agent" ? "assistant" : "user", content: m.content }))
        .slice(-12);
      try {
        const res = await nemoApi.chat(agentId, content, history, agent.defaultModel, conversationIds[agentId]);
        if (res.conversation_id) setConversationId(agentId, res.conversation_id);
        if (res.ok) {
          ok = true;
          offline = !!res.offline;
          patchMessage(agentId, msgId, {
            content: res.content,
            status: "done",
            meta: {
              model: res.model_used,
              latencyMs: res.latency_ms,
              isFallback: !!res.is_fallback && !res.offline,
              promptTokens: res.prompt_tokens,
              completionTokens: res.completion_tokens,
            },
          });
          if (res.search?.used) {
            addLog({
              tone: res.search.ok ? "info" : "warn",
              agentId,
              text: res.search.ok
                ? `${agent.name}: buscou "${res.search.query}" em ${res.search.provider} (${res.search.results} resultados)`
                : `${agent.name}: busca na web falhou (${res.search.error ?? "sem retorno"})`,
            });
          }
          addLog({ tone: res.is_fallback ? "warn" : "info", agentId, text: res.is_fallback ? `${agent.name}: resposta via fallback (${res.model_used})` : `${agent.name}: respondido (${res.model_used}, ${res.latency_ms ?? 0}ms)` });
          notify({ icon: agent.icon, text: `${agent.name} respondeu`, tone: res.is_fallback ? "warn" : "ok" });
        } else {
          // O texto real vem do backend (erro do modelo, chave, limite...):
          // mostrar a mensagem do servidor em vez de um texto genérico.
          const message = res.content ?? res.error ?? "Erro desconhecido.";
          patchMessage(agentId, msgId, { content: message, error: res.error, status: "error" });
          addLog({ tone: res.offline ? "warn" : "error", agentId, text: `${agent.name}: ${message.slice(0, 140)}` });
          notify({ icon: agent.icon, text: `${agent.name}: ${res.error_code ?? "erro"}`, tone: res.offline ? "warn" : "error" });
        }
      } catch (error) {
        const message = describeNetworkError(error);
        patchMessage(agentId, msgId, { content: message, error: message, status: "error" });
        addLog({ tone: "error", agentId, text: `Servidor NEMO não respondeu: ${message.slice(0, 140)}` });
        notify({ icon: agent.icon, text: "Servidor NEMO indisponível", tone: "error" });
      }

      window.clearInterval(im);
      setLiveStatus({ busy: false, label: ok && !offline ? "🎯 Resolvido" : "😎 Tudo sob controle", phrase: "" });

      if (taskId) {
        window.setTimeout(() => updateTask(taskId, ok ? { status: "done" } : { status: "error" }), ok ? 1000 : 300);
      }
    },
    [
      threads,
      conversationIds,
      addUserMessage,
      addHistory,
      addLog,
      insertAgentMessage,
      patchMessage,
      setLiveStatus,
      setConversationId,
      addTask,
      updateTask,
      notify,
      funnyStatus,
    ],
  );

  return { send };
}
