import { AgentAvatar } from "@/components/AgentAvatar";
import { AGENT_ROSTER, getAgent } from "@/data/agents";

interface RoomFallbackProps {
  title: string;
  subtitle: string;
}

/**
 * Painel estático exibido quando o modo visual (Phaser/WebGL) não está
 * disponível. NUNCA mostramos tela preta: os agentes aparecem como cartões
 * estilizados, mantendo a identidade da equipe mesmo sem renderização 3D.
 */
export function RoomFallback({ title, subtitle }: RoomFallbackProps) {
  return (
    <div
      className="room-fallback"
      role="status"
      aria-label="Modo visual alternativo ativado"
    >
      <div className="room-fallback-head">
        <span className="room-fallback-icon">🐟</span>
        <div>
          <div className="room-fallback-title">{title}</div>
          <div className="room-fallback-subtitle">{subtitle}</div>
        </div>
      </div>

      <div className="room-fallback-note">
        O modo visual alternativo foi ativado — a equipe segura a sala por aqui.
      </div>

      <div className="room-fallback-grid">
        {AGENT_ROSTER.map((a) => {
          const nemo = a.id === "nemo";
          return (
            <div key={a.id} className={`room-fallback-card ${nemo ? "nemo" : ""}`}>
              <span className="room-fallback-ava">
                <AgentAvatar id={a.id} accent={a.color} size={nemo ? 54 : 42} badge={a.icon} shape="round" />
              </span>
              <span className="room-fallback-name">{a.name}</span>
              <span className="room-fallback-role">{a.title}</span>
            </div>
          );
        })}
      </div>

      <div className="room-fallback-foot">
        <span className="room-fallback-badge">⭘ modo demonstrativo — equipe {getAgent("nemo").name}</span>
        <span className="room-fallback-badge">👉 clique num agente para conversar</span>
      </div>
    </div>
  );
}