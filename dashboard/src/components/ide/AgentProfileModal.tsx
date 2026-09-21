import { useIdeStore } from "@/store/useIdeStore";
import { getAgent } from "@/data/agents";
import { AgentAvatar } from "@/components/AgentAvatar";

interface AgentProfileModalProps {
  onClose?: () => void;
}

export function AgentProfileModal({ onClose }: AgentProfileModalProps = {}) {
  const activeAgentId = useIdeStore((s) => s.activeAgentId);
  const liveStatus = useIdeStore((s) => s.liveStatus);
  const toggleRight = useIdeStore((s) => s.toggleRight);
  const toggleBottom = useIdeStore((s) => s.toggleBottom);
  const setView = useIdeStore((s) => s.setView);
  const setActiveAgent = useIdeStore((s) => s.setActiveAgent);
  const threads = useIdeStore((s) => s.threads);

  const agent = getAgent(activeAgentId);
  const isLive = liveStatus.agentId === activeAgentId && liveStatus.busy;
  const msgCount = (threads[activeAgentId] ?? []).length;

  const close = () => (onClose ? onClose() : useIdeStore.getState().setView("chat"));

  const openChat = () => {
    setActiveAgent(agent.id);
    setView("chat");
  };

  return (
    <div className="modal-mask" onClick={close}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head" style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <AgentAvatar id={agent.id} accent={agent.color} size={52} badge={agent.icon} shape="round" />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontWeight: 700, fontSize: 16 }}>{agent.name}</div>
            <div style={{ color: "var(--text2)", fontSize: 13 }}>{agent.title}</div>
            <div className="live-line" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, marginTop: 2 }}>
              <span
                style={{
                  width: 7, height: 7, borderRadius: 9, display: "inline-block",
                  background: isLive ? "var(--warn)" : "var(--success)",
                  animation: isLive ? "pulse 1.2s infinite" : "none",
                }}
              />
              <span>{isLive ? "🧠 Pensando..." : "🟢 Online"}</span>
              {msgCount > 0 && <span style={{ color: "var(--text3)" }}>· {msgCount} mensagens</span>}
            </div>
          </div>
          <button className="icon-btn" onClick={close} style={{ fontSize: 16 }}>
            ✕
          </button>
        </div>
        <div className="modal-body">
          <div className="kv">
            <strong>Função</strong>
            <span>{agent.role}</span>
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
            <button className="tool-btn primary" onClick={openChat}>
              💬 Abrir chat
            </button>
            <button className="tool-btn" onClick={() => { setActiveAgent(agent.id); toggleRight(); setView("chat"); }}>
              🗂️ Contexto
            </button>
            <button className="tool-btn" onClick={() => { setActiveAgent(agent.id); toggleBottom(); }}>
              🖥️ Logs
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}