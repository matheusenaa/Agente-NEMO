import { useMemo, useState } from "react";
import { useIdeStore } from "@/store/useIdeStore";
import { getAgent } from "@/data/agents";

const KIND_ICON: Record<string, string> = {
  chat: "💬", file: "📄", task: "✅", terminal: "🖥️", config: "⚙️",
};

export function HistoryView() {
  const history = useIdeStore((s) => s.history);
  const setView = useIdeStore((s) => s.setView);
  const setActiveAgent = useIdeStore((s) => s.setActiveAgent);
  const [q, setQ] = useState("");
  const [kind, setKind] = useState("all");

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

  return (
    <section className="view-area">
      <div className="hist-wrap">
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 12, flexWrap: "wrap" }}>
          <h2 style={{ margin: 0, fontSize: 18 }}>Histórico · {history.length}</h2>
          <div className="seg">
            {["all", "chat", "file", "task", "terminal", "config"].map((k) => (
              <button key={k} className={`seg-btn ${kind === k ? "on" : ""}`} onClick={() => setKind(k)}>
                {k === "all" ? "Todos" : KIND_ICON[k] + " " + k}
              </button>
            ))}
          </div>
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
              {agent && <span dangerouslySetInnerHTML={{ __html: agent.icon }} />}
              <span style={{ fontWeight: 600 }}>{h.title}</span>
              <span style={{ color: "var(--text2)", flex: 1, minWidth: 0, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {h.detail}
              </span>
              <span style={{ color: "var(--text3)", fontSize: 11 }}>
                {new Date(h.time).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
}