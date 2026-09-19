import { useState } from "react";
import { SquadSelector } from "@/components/SquadSelector";
import { PhaserGame } from "@/office/PhaserGame";
import { StatusBar } from "@/components/StatusBar";
import { AgentProfileModal } from "./AgentProfileModal";
import { useSquadStore } from "@/store/useSquadStore";
import { useIdeStore } from "@/store/useIdeStore";

export function OfficeView() {
  const selectedSquad = useSquadStore((s) => s.selectedSquad);
  const isConnected = useSquadStore((s) => s.isConnected);
  const setView = useIdeStore((s) => s.setView);
  const setActiveAgent = useIdeStore((s) => s.setActiveAgent);
  const [agentModal, setAgentModal] = useState(false);

  const handleAgentClick = (agentId: string) => {
    setActiveAgent(agentId);
    setAgentModal(true);
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

      <div className="office-wrap">
        <SquadSelector />
        <div style={{ flex: 1, minWidth: 0, position: "relative", background: "var(--bg0)" }}>
          <PhaserGame onAgentClick={handleAgentClick} />
        </div>
      </div>

      <StatusBar />

      {agentModal && <AgentProfileModal onClose={() => setAgentModal(false)} />}
    </section>
  );
}