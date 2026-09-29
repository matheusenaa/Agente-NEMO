import { useCallback, useEffect, useMemo, useState } from "react";
import { useIdeStore } from "@/store/useIdeStore";
import { getAgent } from "@/data/agents";
import { AgentAvatar } from "@/components/AgentAvatar";
import { nemoApi } from "@/api/nemo";
import type { AiConversation } from "@/types/idea";
import type { ChatMessage } from "@/types/idea";

const KIND_LABEL: Record<string, string> = {
  chat: "conversa", file: "arquivo", task: "tarefa", terminal: "terminal", config: "config",
};

const KIND_ICON: Record<string, string> = {
  chat: "💬", file: "📄", task: "✅", terminal: "🖥️", config: "⚙️",
};

export function HistoryView() {
  const history = useIdeStore((s) => s.history);
  const deleteHistory = useIdeStore((s) => s.deleteHistory);
  const clearHistory = useIdeStore((s) => s.clearHistory);
  const notify = useIdeStore((s) => s.notify);
  const setView = useIdeStore((s) => s.setView);
  const setActiveAgent = useIdeStore((s) => s.setActiveAgent);
  const replaceThread = useIdeStore((s) => s.replaceThread);
  const setChatConversation = useIdeStore((s) => s.setChatConversation);
  const [q, setQ] = useState("");
  const [kind, setKind] = useState("all");
  const [confirm, setConfirm] = useState<{ kind: "one" | "all" | "server"; id?: string } | null>(null);

  // Conversas REAIS do servidor (Supabase). Antes desta tela só mostrava o
  // registro local do navegador: quem limpava o navegador perdia o histórico,
  // e trocar de dispositivo não trazia nada.
  const [serverConvs, setServerConvs] = useState<AiConversation[]>([]);
  const [serverBusy, setServerBusy] = useState(false);
  const [serverError, setServerError] = useState("");

  const loadServer = useCallback(async () => {
    setServerBusy(true);
    setServerError("");
    try {
      const res = await nemoApi.listConversations();
      setServerConvs(res.conversations ?? []);
    } catch (e) {
      setServerError(e instanceof Error ? e.message : "Falha ao carregar conversas.");
    } finally {
      setServerBusy(false);
    }
  }, []);

  useEffect(() => {
    void loadServer();
  }, [loadServer]);

  const filteredServer = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return serverConvs;
    return serverConvs.filter((c) => `${c.title ?? ""} ${c.agent_id ?? ""}`.toLowerCase().includes(needle));
  }, [serverConvs, q]);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return history.filter((h) => {
      if (kind !== "all" && h.kind !== kind) return false;
      if (!needle) return true;
      return (h.title + " " + h.detail).toLowerCase().includes(needle);
    });
  }, [history, q, kind]);

  const apply = (h: (typeof history)[number]) => {
    if (h.kind === "chat") {
      const agentId = h.agentId ?? h.title;
      setActiveAgent(agentId === "nemo" || agentId === "Nemo" ? "nemo" : agentId);
      setView("chat");
    } else if (h.kind === "file") {
      setView("workspace");
    } else if (h.kind === "task") {
      setView("tasks");
    } else {
      setView("terminal");
    }
  };

  /** Reabre uma conversa do servidor: carrega as mensagens na thread do agente. */
  const openServerConversation = async (conv: AiConversation) => {
    const agentId = conv.agent_id || "nemo";
    setServerBusy(true);
    try {
      const res = await nemoApi.conversationMessages(conv.id);
      const msgs: ChatMessage[] = (res.messages ?? []).map((m, i) => ({
        id: `${conv.id}-${i}`,
        role: m.role === "assistant" ? "agent" : "user",
        agentId,
        content: m.content,
        time: new Date(m.created_at ?? Date.now()).getTime(),
        status: "done",
      }));
      replaceThread(agentId, msgs);
      setChatConversation(agentId, conv.id);
      setActiveAgent(agentId);
      setView("chat");
      notify({ icon: "💬", text: `Conversa "${conv.title || "sem título"}" reaberta`, tone: "ok" });
    } catch (e) {
      notify({ icon: "⚠️", text: e instanceof Error ? e.message : "Não consegui abrir a conversa", tone: "error" });
    } finally {
      setServerBusy(false);
    }
  };

  const doDeleteServer = async (id: string) => {
    try {
      await nemoApi.deleteConversation(id);
      setServerConvs((prev) => prev.filter((c) => c.id !== id));
      notify({ icon: "🗑️", text: "Conversa excluída do servidor.", tone: "ok" });
    } catch (e) {
      notify({ icon: "⚠️", text: e instanceof Error ? e.message : "Falha ao excluir", tone: "error" });
    }
  };

  const doDeleteOne = () => {
    if (confirm?.kind === "one" && confirm.id) {
      deleteHistory(confirm.id);
      notify({ icon: "🗑️", text: "Registro excluído do histórico.", tone: "ok" });
    }
  };
  const doClearAll = () => {
    clearHistory();
    notify({ icon: "🗑️", text: "Histórico excluído com sucesso.", tone: "ok" });
  };
  const runConfirm = () => {
    if (confirm?.kind === "one") doDeleteOne();
    else if (confirm?.kind === "server" && confirm.id) doDeleteServer(confirm.id);
    else doClearAll();
    setConfirm(null);
  };

  return (
    <section className="view-area">
      <div className="hist-wrap">
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 12, flexWrap: "wrap" }}>
          <h2 style={{ margin: 0, fontSize: 18 }}>Histórico · {history.length}</h2>
          <div className="seg">
            {["all", "chat", "file", "task", "terminal", "config"].map((k) => (
              <button key={k} className={`seg-btn ${kind === k ? "on" : ""}`} onClick={() => setKind(k)}>
                {k === "all" ? "Todos" : KIND_ICON[k] + " " + KIND_LABEL[k]}
              </button>
            ))}
          </div>
          {history.length > 0 && (
            <button className="tool-btn" style={{ marginLeft: "auto", color: "var(--danger)" }} onClick={() => setConfirm({ kind: "all" })}>
              🗑️ Excluir histórico
            </button>
          )}
        </div>
        <input className="hist-search" placeholder="🔎 Buscar no histórico..." value={q} onChange={(e) => setQ(e.target.value)} />

        {/* ---- Conversas no servidor (fonte da verdade) ---- */}
        <div className="hist-section">
          <div className="hist-section-head">
            <strong>💾 Conversas no servidor</strong>
            <span className="hist-section-sub">
              {serverBusy ? "carregando..." : `${serverConvs.length} salvas`}
            </span>
            <button className="tool-btn icon" title="Atualizar" onClick={() => void loadServer()} disabled={serverBusy}>
              {serverBusy ? "⏳" : "🔄"}
            </button>
          </div>

          {serverError && (
            <div className="hist-note error">
              Não consegui carregar as conversas do servidor: {serverError}
            </div>
          )}

          {!serverError && serverConvs.length === 0 && !serverBusy && (
            <div className="hist-note">Nenhuma conversa salva ainda. As conversas do chat aparecem aqui automaticamente.</div>
          )}

          {filteredServer.map((c) => {
            const agent = getAgent(c.agent_id || "nemo");
            return (
              <div key={c.id} className="hist-row" onClick={() => void openServerConversation(c)} style={{ cursor: "pointer" }} title="Reabrir conversa">
                <span className="ht">{new Date(c.updated_at ?? c.created_at ?? Date.now()).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" })}</span>
                <span>💬</span>
                <AgentAvatar id={agent.id} accent={agent.color} size={22} badge={agent.icon} />
                <span style={{ fontWeight: 600 }}>{c.title || "(sem título)"}</span>
                <span style={{ color: "var(--text3)", fontSize: 11, marginLeft: "auto" }}>
                  {new Date(c.updated_at ?? c.created_at ?? Date.now()).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
                </span>
                <button
                  className="tool-btn icon"
                  title="Excluir conversa no servidor"
                  style={{ padding: "4px 6px", fontSize: 13, color: "var(--danger)" }}
                  onClick={(e) => {
                    e.stopPropagation();
                    setConfirm({ kind: "server", id: c.id });
                  }}
                >
                  🗑️
                </button>
              </div>
            );
          })}
        </div>

        <div className="hist-section">
          <div className="hist-section-head">
            <strong>🕘 Atividade neste dispositivo</strong>
            <span className="hist-section-sub">{filtered.length} registro(s)</span>
          </div>

        {filtered.length === 0 && (
          <div style={{ color: "var(--text3)", textAlign: "center", padding: 24 }}>
            Nada registrado ainda neste dispositivo — atividades suas e dos agentes aparecem aqui.
          </div>
        )}

        {filtered.map((h) => {
          const agent = h.kind === "chat" ? getAgent(h.agentId ?? h.title) : undefined;
          return (
            <div key={h.id} className="hist-row" onClick={() => apply(h)} style={{ cursor: "pointer" }} title="Reabrir">
              <span className="ht">{new Date(h.time).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" })}</span>
              <span>{KIND_ICON[h.kind]}</span>
              {agent && <AgentAvatar id={agent.id} accent={agent.color} size={22} badge={agent.icon} />}
              <span style={{ fontWeight: 600 }}>{h.title}</span>
              <span style={{ color: "var(--text2)", flex: 1, minWidth: 0, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {h.detail}
              </span>
              <span style={{ color: "var(--text3)", fontSize: 11 }}>
                {new Date(h.time).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
              </span>
              <button
                className="tool-btn icon"
                title="Excluir registro"
                style={{ padding: "4px 6px", fontSize: 13, color: "var(--danger)" }}
                onClick={(e) => {
                  e.stopPropagation();
                  setConfirm({ kind: "one", id: h.id });
                }}
              >
                🗑️
              </button>
            </div>
          );
        })}
        </div>
      </div>

      {confirm && (
        <div className="modal-mask" onClick={() => setConfirm(null)}>
          <div className="modal-card" style={{ width: "min(420px,92vw)" }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <span style={{ fontSize: 20 }}>🗑️</span>
              <strong>
                {confirm.kind === "all"
                  ? "Excluir todo o histórico?"
                  : confirm.kind === "server"
                    ? "Excluir esta conversa?"
                    : "Excluir este registro?"}
              </strong>
            </div>
            <div className="modal-body" style={{ fontSize: 13, color: "var(--text2)", lineHeight: 1.6 }}>
              {confirm.kind === "all"
                ? "Isto apaga o registro de atividades deste dispositivo. As conversas salvas no servidor não são afetadas."
                : confirm.kind === "server"
                  ? "Isto apaga a conversa e todas as mensagens dela no servidor. Esta ação não pode ser desfeita."
                  : "Tem certeza que deseja excluir este registro? Esta ação não pode ser desfeita."}
            </div>
            <div className="modal-foot">
              <button className="tool-btn" style={{ flex: 1 }} onClick={() => setConfirm(null)}>
                Cancelar
              </button>
              <button className="tool-btn primary" style={{ flex: 1, background: "var(--danger)", borderColor: "var(--danger)" }} onClick={runConfirm}>
                {confirm.kind === "all" ? "Excluir histórico" : "Excluir"}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}