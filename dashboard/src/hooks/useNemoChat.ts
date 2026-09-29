import { useCallback } from "react";
import { useIdeStore } from "@/store/useIdeStore";
import { nemoApi, type ChatHistoryMessage } from "@/api/nemo";
import { getAgent } from "@/data/agents";
import { FUNNY_PHRASES, pickPhrase } from "@/data/statusPhrases";

const OFFLINE_RESPONSES: Record<string, string> = {
  nemo:
    "Não consegui falar com o modelo (servidor NEMO offline). Rode `python nemo_server.py` e configure sua chave no `.env` para eu responder de verdade.\n\nEnquanto isso, registrei sua solicitação em **Tarefas** e nos logs. 🐟",
  default:
    "Servidor de IA offline. Use `python nemo_server.py` para ativar o chat com os modelos OpenRouter.",
};

/**
 * Tempo máximo de espera por resposta sem nenhum token. Não é o timeout
 * total da chamada (a busca na web pode demorar), e sim o tempo PARADO: se o
 * modelo parar de enviar texto por mais que isso, caímos no caminho sem
 * streaming para não deixar a conversa travada para sempre.
 */
const STREAM_STALL_MS = 75_000;

export function useNemoChat() {
  const threads = useIdeStore((s) => s.threads);
  const addUserMessage = useIdeStore((s) => s.addUserMessage);
  const insertAgentMessage = useIdeStore((s) => s.insertAgentMessage);
  const patchMessage = useIdeStore((s) => s.patchMessage);
  const setLiveStatus = useIdeStore((s) => s.setLiveStatus);
  const addTask = useIdeStore((s) => s.addTask);
  const updateTask = useIdeStore((s) => s.updateTask);
  const addLog = useIdeStore((s) => s.addLog);
  const addHistory = useIdeStore((s) => s.addHistory);
  const notify = useIdeStore((s) => s.notify);
  const funnyStatus = useIdeStore((s) => s.config.funnyStatus);
  // A conversa vive no store (persistido): sem isso, um F5 faria o próximo
  // envio começar outra thread e o histórico apareceria cortado.
  const setChatConversation = useIdeStore((s) => s.setChatConversation);

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
      // Histórico da conversa com esse agente (sem a última msg do usuário duplicar)
      const history: ChatHistoryMessage[] = (threads[agentId] ?? [])
        .filter((m) => m.content.trim().length > 0 && m.status !== "typing" && m.status !== "sending")
        .map((m): ChatHistoryMessage => ({ role: m.role === "agent" ? "assistant" : "user", content: m.content }))
        .slice(-12);

      const currentConversation = useIdeStore.getState().chatConversations[agentId] ?? "";
      const isFirstMessage = !currentConversation;
      const startedAt = Date.now();
      let ok = false;
      let offline = false;
      let usedStream = false;
      let buffer = "";
      let searchProvider = "";

      const commit = (finalContent: string, extra?: Record<string, unknown>) => {
        const store = useIdeStore.getState();
        const msg = store.threads[agentId]?.find((m) => m.id === msgId);
        // O que já foi renderizado + o que o servidor devolveu (evita duplicar).
        const streamed = msg?.content ?? "";
        const content2 = finalContent && finalContent !== streamed ? streamed + finalContent : finalContent || streamed;
        patchMessage(agentId, msgId, {
          content: content2,
          status: "done",
          ...extra,
        });
        return content2;
      };

      try {
        // ---- Caminho 1: streaming progressivo (preferido) ----
        const controller = new AbortController();
        let lastTokenAt = Date.now();

        // Os handlers são callbacks: o TS não enxerga as atribuições feitas
        // dentro deles, então coletamos os eventos numa lista e só lemos depois
        // que o stream terminou.
        type StreamEvent =
          | { kind: "done"; ok: boolean; conversation_id?: string; model_used?: string; used_search?: boolean }
          | { kind: "error"; content?: string; error_code?: string; fallback_to_sync?: boolean }
          | { kind: "sources"; provider?: string };
        const events: StreamEvent[] = [];

        const stall = window.setInterval(() => {
          if (usedStream && Date.now() - lastTokenAt > STREAM_STALL_MS) controller.abort();
        }, 5000);

        try {
          await nemoApi.chatStream(
            agentId,
            content,
            history,
            {
              model: agent.defaultModel,
              conversationId: currentConversation,
              newConversation: isFirstMessage,
              signal: controller.signal,
            },
            {
              onDelta: (text) => {
                lastTokenAt = Date.now();
                usedStream = true;
                buffer += text;
                // Atualização incremental: o texto aparece enquanto é gerado.
                patchMessage(agentId, msgId, { content: buffer, status: "streaming" });
              },
              onReset: ({ model }) => {
                // O modelo caiu e vamos tentar outro: o parcial vai sumir.
                buffer = "";
                useIdeStore.setState((s) => ({
                  threads: {
                    ...s.threads,
                    [agentId]: (s.threads[agentId] ?? []).map((m) =>
                      m.id === msgId ? { ...m, content: "", status: "streaming" as const } : m,
                    ),
                  },
                }));
                setLiveStatus({ busy: true, label: `🔁 Alternando para ${model ?? "outro modelo"}...` });
              },
              onStatus: ({ message }) => {
                if (message) setLiveStatus({ busy: true, label: message });
              },
              onSources: ({ provider }) => {
                searchProvider = provider ?? "";
                if (provider) addLog({ tone: "info", agentId, text: `Busca na web via ${provider}` });
              },
    onError: (err) => {
      events.push({
        kind: "error",
        content: err.content,
        error_code: err.error_code,
        fallback_to_sync: err.fallback_to_sync,
      });
    },
              onDone: (info) => {
                events.push({
                  kind: "done",
                  ok: Boolean(info.ok),
                  conversation_id: info.conversation_id,
                  model_used: info.model_used,
                  used_search: info.used_search,
                });
              },
            },
          );
        } finally {
          window.clearInterval(stall);
        }

        const doneEvent = events.find((e): e is Extract<StreamEvent, { kind: "done" }> => e.kind === "done");
        const errorEvent = events.find((e): e is Extract<StreamEvent, { kind: "error" }> => e.kind === "error");
        if (doneEvent?.conversation_id) setChatConversation(agentId, doneEvent.conversation_id);

        const finished = commit(buffer, {
          meta: {
            model: doneEvent?.model_used,
            latencyMs: Date.now() - startedAt,
            usedSearch: doneEvent?.used_search,
            searchProvider,
          },
        });

        // O servidor emite `error` também para avisar que o provedor não
        // transmite palavra a palavra e já respondeu de uma vez
        // (`fallback_to_sync`). Isso é informativo: marcar como falha fazia
        // TODO chat no Groq/Gemini - os únicos provedores com crédito - mostrar
        // erro mesmo tendo a resposta na tela.
        const recovered = Boolean(errorEvent?.fallback_to_sync) && Boolean(doneEvent?.ok);
        if (errorEvent && !recovered) {
          ok = false;
          patchMessage(agentId, msgId, {
            content: errorEvent.content || "Não consegui concluir a solicitação.",
            error: errorEvent.content,
            status: "error",
          });
          notify({ icon: agent.icon, text: `${agent.name}: ${errorEvent.error_code ?? "erro"}`, tone: "error" });
        } else if (doneEvent?.ok) {
          ok = true;
          if (recovered && errorEvent?.content) {
            // a resposta chegou inteira; o aviso do servidor entra no log
            patchMessage(agentId, msgId, { status: "done" });
            addLog({ tone: "info", agentId, text: errorEvent.content });
          }
          notify({ icon: agent.icon, text: `${agent.name} respondeu`, tone: "ok" });
          addLog({
            tone: "info",
            agentId,
            text: `${agent.name}: respondido (${doneEvent.model_used ?? "?"}, ${Date.now() - startedAt}ms)`,
          });
        } else {
          ok = false;
          patchMessage(agentId, msgId, { content: finished || "Resposta vazia.", status: "error" });
          notify({ icon: agent.icon, text: `${agent.name}: resposta vazia`, tone: "warn" });
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : "Servidor NEMO indisponível.";

        // O streaming é um extra: se ele falhar, tentamos o caminho simples.
        // Só caímos no texto offline quando nem os dois funcionam.
        if (usedStream) {
          const contentSoFar = useIdeStore.getState().threads[agentId]?.find((m) => m.id === msgId)?.content ?? "";
          if (contentSoFar.trim()) {
            ok = true;
            addLog({ tone: "warn", agentId, text: `${agent.name}: conexão caiu, mas parte da resposta foi salva.` });
          } else {
            ok = false;
            patchMessage(agentId, msgId, { content: message, error: message, status: "error" });
          }
        } else {
          try {
            const res = await nemoApi.chat(agentId, content, history, agent.defaultModel, currentConversation, isFirstMessage);
            if (res.ok) {
              ok = true;
              offline = !!res.offline;
              if (res.conversation_id) setChatConversation(agentId, res.conversation_id);
              commit(res.content, {
                meta: {
                  model: res.model_used,
                  latencyMs: res.latency_ms,
                  isFallback: !!res.is_fallback && !res.offline,
                  promptTokens: res.prompt_tokens,
                  completionTokens: res.completion_tokens,
                  usedSearch: res.used_search,
                  searchProvider: res.search_provider,
                },
              });
              notify({ icon: agent.icon, text: `${agent.name} respondeu`, tone: "ok" });
            } else {
              ok = false;
              const text = res.content ?? res.error ?? "Erro desconhecido.";
              patchMessage(agentId, msgId, { content: text, error: res.error, status: "error" });
              notify({ icon: agent.icon, text: `${agent.name}: ${res.error_code ?? "erro"}`, tone: res.offline ? "warn" : "error" });
            }
          } catch {
            ok = false;
            patchMessage(agentId, msgId, {
              content: OFFLINE_RESPONSES[agentId] ?? OFFLINE_RESPONSES.default,
              error: message,
              status: "error",
            });
            addLog({ tone: "error", agentId, text: `Servidor NEMO não respondeu: ${message.slice(0, 140)}` });
            notify({ icon: agent.icon, text: "Servidor NEMO indisponível", tone: "error" });
          }
        }
      }

      window.clearInterval(im);
      setLiveStatus({ busy: false, label: ok && !offline ? "🎯 Resolvido" : "😎 Tudo sob controle", phrase: "" });

      if (taskId) {
        window.setTimeout(() => updateTask(taskId, ok ? { status: "done" } : { status: "error" }), ok ? 1000 : 300);
      }
    },
    [threads, addUserMessage, addHistory, addLog, insertAgentMessage, patchMessage, setLiveStatus, addTask, updateTask, notify, funnyStatus, setChatConversation],
  );

  /** Começa uma thread nova: o próximo envio não continua a conversa antiga. */
  const startNewThread = useCallback(
    (agentId: string) => setChatConversation(agentId, ""),
    [setChatConversation],
  );

  return { send, startNewThread };
}
