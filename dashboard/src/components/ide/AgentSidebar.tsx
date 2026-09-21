import { AGENT_ROSTER } from "@/data/agents";
import { useIdeStore } from "@/store/useIdeStore";
import { useSquadStore } from "@/store/useSquadStore";
import { AgentAvatar } from "@/components/AgentAvatar";

export function AgentSidebar() {
  const activeAgentId = useIdeStore((s) => s.activeAgentId);
  const setActiveAgent = useIdeStore((s) => s.setActiveAgent);
  const setView = useIdeStore((s) => s.setView);
  const leftOpen = useIdeStore((s) => s.leftOpen);
  const liveStatus = useIdeStore((s) => s.liveStatus);
  const activeStates = useSquadStore((s) => s.activeStates);
  const squads = useSquadStore((s) => s.squads);
  const selectSquad = useSquadStore((s) => s.selectSquad);

  if (!leftOpen) return null;

  const runningSquads = Array.from(activeStates.entries()).map(([code, st]) => ({ code, ...st, info: squads.get(code) }));

  return (
    <aside className="rail">
      <div className="rail-head">
        <span className="rail-title">Agentes</span>
        <button className="icon-btn" onClick={() => useIdeStore.getState().toggleLeft(false)} style={{ fontSize: 13, width: 28, height: 28 }}>
          ×
        </button>
      </div>

      <div className="agents-list">
        {AGENT_ROSTER.map((a) => {
          const sel = activeAgentId === a.id;
          const isLive = liveStatus.agentId === a.id && liveStatus.busy;
          return (
            <div
              key={a.id}
              className={`agent-item ${sel ? "sel" : ""}`}
              onClick={() => {
                setActiveAgent(a.id);
                setView("chat");
              }}
              title={a.description}
            >
              <div style={{ position: "relative", display: "flex" }}>
                <AgentAvatar id={a.id} accent={a.color} size={34} badge={a.icon} />
                {isLive && (
                  <span
                    style={{ position: "absolute", bottom: -1, right: -1, width: 10, height: 10, borderRadius: "50%", background: "var(--success)", border: "2px solid var(--bg1)", animation: "pulse 1.4s infinite" }}
                  />
                )}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="agent-name">{a.name}</div>
                <div className="agent-role">{a.role}</div>
              </div>
              {isLive && (
                <div className="st-live" style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <span style={{ width: 6, height: 6, borderRadius: 9, background: "var(--success)", display: "inline-block", animation: "pulse 1.4s infinite" }} />
                  <span style={{ fontSize: 11, color: "var(--accent)" }}>busy</span>
                </div>
              )}
            </div>
          );
        })}

        {runningSquads.length > 0 && (
          <>
            <div className="squad-sec">
              <div className="rail-title" style={{ marginBottom: 5, paddingLeft: 4 }}>Squads ativos</div>
            </div>
            {runningSquads.map((sq) => (
              <div
                key={sq.code}
                className="agent-item"
                onClick={() => {
                  selectSquad(sq.code);
                  setView("office");
                }}
                title={sq.info?.description ?? sq.code}
              >
                <div className="agent-ava" style={{ background: sq.status === "running" ? "var(--success)" : sq.status === "checkpoint" ? "var(--warn)" : "var(--bg4)" }}>
                  {sq.info?.icon ?? "🐟"}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="agent-name">{sq.info?.name ?? sq.code}</div>
                  <div className="agent-role">{sq.status} · passo {sq.step?.current ?? 0}/{sq.step?.total ?? "?"}</div>
                </div>
              </div>
            ))}
          </>
        )}

        {liveStatus.phrase && <div className="livephrase">"{liveStatus.phrase}"</div>}
      </div>
    </aside>
  );
}