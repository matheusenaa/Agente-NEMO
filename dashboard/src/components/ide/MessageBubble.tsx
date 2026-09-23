import type { ChatMessage } from "@/types/idea";
import { getAgent } from "@/data/agents";
import { renderMarkdown } from "@/lib/markdown";
import { AgentAvatar } from "@/components/AgentAvatar";

interface Props {
  message: ChatMessage;
  showTimestamps: boolean;
}

export function MessageBubble({ message, showTimestamps }: Props) {
  const agent = message.agentId ? getAgent(message.agentId) : undefined;
  const isUser = message.role === "user";
  const isDone = message.status === "done";
  const isError = message.status === "error";
  const meta = message.meta;

  return (
    <div className={`msg ${isUser ? "user" : ""}`}>
      {!isUser && agent && (
        <AgentAvatar id={agent.id} accent={agent.color} size={32} badge={agent.icon} title={agent.name} />
      )}

      <div className="body">
        <div className="meta">
          <span className="who" style={{ color: isUser ? "var(--accent)" : agent?.color ?? "var(--text)" }}>
            {isUser ? "Você" : agent?.name ?? message.agentId}
          </span>
          {showTimestamps && (
            <span className="when">
              {new Date(message.time).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
            </span>
          )}
        </div>

        <div className={`bubble ${isError ? "error" : ""}`} style={isError ? { borderColor: "var(--danger)" } : undefined}>
          {message.status === "typing" && (
            <>
              <div className="typing-dots">
                <i /><i /><i />
              </div>
              <div className="phrase-line" style={{ marginTop: 6 }}>
                {liveStatusPhrase(message.agentId)}
              </div>
            </>
          )}
          {isDone && !!message.content && <div>{renderMarkdown(message.content)}</div>}
          {isError && !message.content && <div style={{ color: "var(--danger)" }}>{message.error ?? "Erro ao gerar resposta."}</div>}
        </div>

        {isDone && meta && (
          <div className="stats">
            {meta.model && <span>🤖 {meta.model}</span>}
            {meta.latencyMs != null && <span>⏱ {meta.latencyMs}ms</span>}
            {meta.promptTokens != null && <span>📝 {meta.promptTokens} tok</span>}
            {meta.isFallback && <span style={{ color: "var(--warn)" }}>⚠️ usou modelo reserva</span>}
          </div>
        )}
      </div>
    </div>
  );
}

function liveStatusPhrase(agentId?: string): string {
  const phrases: Record<string, string[]> = {
    nemo: ["NEMO está processando...", "Investigando a melhor abordagem...", "Preparando sua resposta..."],
    pesquisador: ["Pesquisando na web...", "Analisando fontes confiáveis...", "Compilando dados..."],
    redator: ["Escrevendo seu texto...", "Revisando clareza...", "Polindo frases..."],
    analista: ["Processando dados...", "Rodando cálculos...", "Montando gráficos..."],
    default: ["Pensando...", "Processando...", "Analisando..."],
  };
  const arr = phrases[agentId ?? ""] ?? phrases.default;
  return arr[Math.floor(Date.now() / 3500) % arr.length];
}