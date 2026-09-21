import { useCallback, useRef } from "react";
import { useIdeStore } from "@/store/useIdeStore";
import { nemoApi } from "@/api/nemo";
import { getAgent } from "@/data/agents";
import { FUNNY_PHRASES, pickPhrase } from "@/data/statusPhrases";

const OFFLINE_RESPONSES: Record<string, string> = {
  nemo:
    "Não consegui falar com o modelo (servidor NEMO offline). Rode `python nemo_server.py` e configure sua chave no `.env` para eu responder de verdade.\n\nEnquanto isso, registrei sua solicitação em **Tasks** e nos logs. 🐟",
  default:
    "Servidor de IA offline. Use `python nemo_server.py` para ativar o chat com os modelos OpenRouter.",
};

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
  const phraseRef = useRef<string>("");

  const send = useCallback(
    async (agentId: string, content: string) => {
      const agent = getAgent(agentId);
      addUserMessage(agentId, content);
      addLog({ tone: "agent", agentId, text: `${agent.name} iniciou: ${content.slice(0, 70)}` });
      addHistory({ kind: "chat", title: agent.name, agentId: agent.id, detail: content.slice(0, 120) });

      setLiveStatus({ agentId, busy: true, label: "🧠 Pensando...", phrase: "" });
      const thinkLabels = ["🧠 Pensando...", "🔎 Investigando...", "📂 Lendo arquivos...", "💻 Codificando..."];
      const im = window.setInterval(() => {
        setLiveStatus({
          label: pickPhrase(thinkLabels, useIdeStore.getState().liveStatus.label),
          phrase: funnyStatus ? pickPhrase(FUNNY_PHRASES, phraseRef.current) : "",
        });
      }, 2600);
      phraseRef.current = "";

      const msgId = insertAgentMessage(agentId, { role: "agent", agentId, content: "" });
      let ok = false;
      let offline = false;
      // Histórico da conversa com esse agente (sem a última msg do usuário duplicar)
      const history: string[] = (threads[agentId] ?? [])
        .map((m) => m.content)
        .filter((c) => c && c !== content)
        .slice(-12);
      try {
        const res = await nemoApi.chat(agentId, content, history, agent.defaultModel);
        if (res.ok) {
          ok = true;
          offline = !!res.offline;
          patchMessage(agentId, msgId, {
            content: res.content,
            status: "done",
            meta: { model: res.model_used, latencyMs: res.latency_ms, isFallback: res.is_fallback, promptTokens: res.prompt_tokens, completionTokens: res.completion_tokens },
          });
          addLog({ tone: "warn", agentId, text: res.offline ? `Chave OpenRouter inválida/expirada — resposta offline gerada` : `${agent.name}: respondido (${res.model_used}, ${res.latency_ms ?? 0}ms)` });
          notify({ icon: agent.icon, text: `${agent.name} respondeu`, tone: res.offline ? "warn" : "ok" });
        } else {
          patchMessage(agentId, msgId, { content: res.error ?? "Erro desconhecido.", status: "error" });
          addLog({ tone: "error", agentId, text: `${agent.name}: ${(res.error ?? "").slice(0, 140)}` });
        }
      } catch {
        patchMessage(agentId, msgId, { content: OFFLINE_RESPONSES[agentId] ?? OFFLINE_RESPONSES.default, status: "done" });
        addLog({ tone: "warn", agentId, text: "Servidor NEMO não respondeu — resposta offline gerada" });
      }

      window.clearInterval(im);
      setLiveStatus({ busy: false, label: ok && !offline ? "🎯 Resolvido" : "😎 Tudo sob controle", phrase: "" });

      if (content.trim().length > 10) {
        const t = addTask({ title: content.trim().slice(0, 60), priority: "normal", agentId });
        window.setTimeout(() => updateTask(t, ok ? { status: "done" } : { status: "error" }), ok ? 1000 : 300);
      }
    },
    [threads, addUserMessage, addHistory, addLog, insertAgentMessage, patchMessage, setLiveStatus, addTask, updateTask, notify, funnyStatus],
  );

  return { send };
}