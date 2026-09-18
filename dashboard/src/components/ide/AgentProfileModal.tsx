import { useIdeStore } from "@/store/useIdeStore";
import { getAgent } from "@/data/agents";

export function AgentProfileModal() {
  const activeAgentId = useIdeStore((s) => s.activeAgentId);
  const liveStatus = useIdeStore((s) => s.liveStatus);
  const toggleRight = useIdeStore((s) => s.toggleRight);
  const toggleBottom = useIdeStore((s) => s.toggleBottom);
  const setView = useIdeStore((s) => s.setView);

  const agent = getAgent(activeAgentId);
  const isLive = liveStatus.agentId === activeAgentId && liveStatus.busy;

  return (
    <div className="modal-mask" onClick={() => useIdeStore.getState().setView("chat")}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div className="agent-ava" style={{ background: agent.color, width: 42, height: 42, fontSize: 22 }} dangerouslySetInnerHTML={{ __html: agent.icon }} />
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700, fontSize: 16 }}>{agent.name}</div>
            <div style={{ color: "var(--text2)", fontSize: 13 }}>{agent.role}</div>
          </div>
          <button className="icon-btn" onClick={() => useIdeStore.getState().setView("chat")} style={{ fontSize: 16 }}>
            ✕
          </button>
        </div>
        <div className="modal-body">
          <div className="kv">
            <strong>Status</strong>
            <span>{isLive ? "🧠 Pensando..." : "🟢 Online"}</span>
          </div>
          <div className="kv">
            <strong>Descrição</strong>
            <span>{agent.description}</span>
          </div>
          <div className="kv">
            <strong>Modelo padrão</strong>
            <span style={{ fontFamily: "Consolas, monospace", color: "var(--accentText)" }}>{agent.defaultModel}</span>
          </div>
          <div className="kv">
            <strong>Prioridade</strong>
            <span>{agent.priority}</span>
          </div>
          {agent.fallbacks && agent.fallbacks.length > 0 && (
            <div className="kv">
              <strong>Fallbacks</strong>
              <span style={{ fontFamily: "Consolas, monospace", color: "var(--accentText)" }}>{agent.fallbacks.join(" → ")}</span>
            </div>
          )}
          <div style={{ marginTop: 14, display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button className="tool-btn" onClick={() => { useIdeStore.getState().setActiveAgent(agent.id); useIdeStore.getState().setView("chat"); }}>
              💬 Abrir chat
            </button>
            <button className="tool-btn" onClick={() => { useIdeStore.getState().setActiveAgent(agent.id); toggleRight(); setView("chat"); }}>
              🗂️ Contexto
            </button>
            <button className="tool-btn" onClick={() => { useIdeStore.getState().setActiveAgent(agent.id); toggleBottom(); }}>
              🖥️ Logs
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}