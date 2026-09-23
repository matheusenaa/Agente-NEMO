import { useMemo, useState } from "react";
import { useIdeStore } from "@/store/useIdeStore";
import { getAgent } from "@/data/agents";
import { AgentAvatar } from "@/components/AgentAvatar";

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
  const [q, setQ] = useState("");
  const [kind, setKind] = useState("all");
  const [confirm, setConfirm] = useState<{ kind: "one" | "all"; id?: string } | null>(null);

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

        {filtered.length === 0 && (
          <div style={{ color: "var(--text3)", textAlign: "center", padding: 40 }}>
            Nada registrado ainda — atividades suas e dos agentes aparecem aqui.
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

      {confirm && (
        <div className="modal-mask" onClick={() => setConfirm(null)}>
          <div className="modal-card" style={{ width: "min(420px,92vw)" }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <span style={{ fontSize: 20 }}>🗑️</span>
              <strong>{confirm.kind === "all" ? "Excluir todo o histórico?" : "Excluir este registro?"}</strong>
            </div>
            <div className="modal-body" style={{ fontSize: 13, color: "var(--text2)", lineHeight: 1.6 }}>
              {confirm.kind === "all"
                ? "Tem certeza que deseja excluir todo o histórico? Esta ação não pode ser desfeita."
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