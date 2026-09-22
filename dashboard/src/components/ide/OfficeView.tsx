import { useState } from "react";
import { SquadSelector } from "@/components/SquadSelector";
import { PhaserGame } from "@/office/PhaserGame";
import { StatusBar } from "@/components/StatusBar";
import { AgentProfileModal } from "./AgentProfileModal";
import { AgentAvatar } from "@/components/AgentAvatar";
import { AGENT_ROSTER } from "@/data/agents";
import { useSquadStore } from "@/store/useSquadStore";
import { useIdeStore } from "@/store/useIdeStore";

export function OfficeView() {
  const selectedSquad = useSquadStore((s) => s.selectedSquad);
  const isConnected = useSquadStore((s) => s.isConnected);
  const setView = useIdeStore((s) => s.setView);
  const setActiveAgent = useIdeStore((s) => s.setActiveAgent);
  const liveStatus = useIdeStore((s) => s.liveStatus);
  const tasks = useIdeStore((s) => s.tasks);
  const [agentModal, setAgentModal] = useState(false);

  const busyAgents = new Set<string>();
  if (liveStatus.busy) busyAgents.add(liveStatus.agentId);
  tasks.forEach((t) => (t.status === "running" ? busyAgents.add(t.agentId) : undefined));

  const handleAgentClick = (agentId: string) => {
    setActiveAgent(agentId);
    setAgentModal(true);
  };

  const openChat = (agentId: string) => {
    setActiveAgent(agentId);
    setView("chat");
  };

  return (
    <section className="view-area" style={{ overflow: "hidden" }}>
      <div className="chat-head" style={{ gap: 8 }}>
        <span style={{ fontWeight: 700 }}>🏢 Sala de reunião da equipe</span>
        <span style={{ color: "var(--text3)", fontSize: 12 }}>
          {isConnected ? "🔗 ao vivo (WebSocket)" : "⭘ demonstrativo — equipe NEMO"}
        </span>
        {selectedSquad && (
          <span style={{ color: "var(--accentText)", fontSize: 12 }}>squad: {selectedSquad}</span>
        )}
        <span style={{ color: "var(--text3)", fontSize: 12 }}>👉 clique num agente para conversar</span>
        <button className="tool-btn" style={{ marginLeft: "auto" }} onClick={() => setView("chat")}>
          Voltar ao chat →
        </button>
      </div>

      <div
        id="squad-task-summary"
        style={{
          position: "absolute",
          top: 60,
          right: 12,
          background: "var(--bg1)",
          border: "1px solid var(--border)",
          borderRadius: 8,
          padding: "8px 12px",
          fontSize: 11,
          minWidth: 180,
          boxShadow: "0 2px 6px rgba(0,0,0,0.15)",
          zIndex: 100,
          transition: "box-shadow .15s ease, transform .15s ease",
        }}
        onMouseEnter={(e) => e.currentTarget.style.transform = "translateY(-2px)"}
        onMouseLeave={(e) => e.currentTarget.style.transform = "translateY(0)"}
      >
        <div style={{ fontWeight: 600, fontSize: 11, marginBottom: 6, color: "var(--text)" }}>
          Tarefas em execução
        </div>
        {(() => {
          const running = tasks.filter((t) => t.status === "running");
          const bySquad = new Map<string, string[]>();
          running.forEach((t) => {
            const sid = t.agentId || "nemo";
            if (!bySquad.has(sid)) bySquad.set(sid, []);
            bySquad.get(sid)!.push(t.title);
          });
          if (bySquad.size === 0) return null;
          return (
            <div>
              {Array.from(bySquad.entries()).map(([agentId, titles]) => {
                const agent = AGENT_ROSTER.find((a) => a.id === agentId);
                const name = agent ? agent.name : agentId;
                return (
                  <div key={agentId} style={{ marginBottom: 4, fontSize: 10 }}>
                    <span style={{ color: "var(--accentText)", fontWeight: 600 }}>{name}:</span>
                    <span style={{ color: "var(--text2)", fontSize: 10 }}>{titles.join(", ")}</span>
                  </div>
                );
              })}
            </div>
          );
        })()}
      </div>

      <div className="office-wrap">
        <SquadSelector />
        <div style={{ flex: 1, minWidth: 0, position: "relative", background: "var(--bg0)" }}>
          <PhaserGame onAgentClick={handleAgentClick} />
          <div className="office-dock">
            {AGENT_ROSTER.map((a) => {
              const isBusy = busyAgents.has(a.id);
              return (
                <button
                  key={a.id}
                  className="dock-chip"
                  onClick={() => openChat(a.id)}
                  title={`Conversar com ${a.name}`}
                  style={{
                    transition: "transform .12s ease, box-shadow .12s ease",
                    ":hover": {
                      transform: "translateY(-2px)",
                      boxShadow: "0 4px 12px rgba(0,0,0,0.2)",
                    },
                  }}
                >
                  <span className="dock-ava">
                    <AgentAvatar id={a.id} accent={a.color} size={30} badge={a.icon} shape="round" />
                    {isBusy && (
                      <span className="dock-busy" style={{ background: "var(--warn)", animation: "pulse 1.2s infinite" }} />
                    )}
                  </span>
                  <span className="dock-name">{a.name}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <StatusBar />

      {agentModal && <AgentProfileModal onClose={() => setAgentModal(false)} />}
    </section>
  );
}