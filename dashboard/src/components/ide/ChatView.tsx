import { useEffect, useRef, useState } from "react";
import { useIdeStore } from "@/store/useIdeStore";
import { useNemoChat } from "@/hooks/useNemoChat";
import { getAgent } from "@/data/agents";
import { MessageBubble } from "./MessageBubble";
import { AgentAvatar } from "@/components/AgentAvatar";

const SUGGESTIONS = [
  "Analise meus gastos e encontre duplicados",
  "Monte um relatório do Vasco",
  "Crie um post para o Instagram",
  "Liste os arquivos do projeto",
];

export function ChatView() {
  const activeAgentId = useIdeStore((s) => s.activeAgentId);
  const threads = useIdeStore((s) => s.threads);
  const messages = threads[activeAgentId] ?? [];
  const liveStatus = useIdeStore((s) => s.liveStatus);
  const showTimestamps = useIdeStore((s) => s.config.showTimestamps);
  const { send } = useNemoChat();

  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const agent = getAgent(activeAgentId);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, liveStatus]);

  useEffect(() => {
    if (liveStatus.busy) setBusy(true);
    else setBusy(false);
  }, [liveStatus.busy]);

  const submit = async (value?: string) => {
    const content = (value ?? text).trim();
    if (!content || busy) return;
    setText("");
    setBusy(true);
    try {
      await send(activeAgentId, content);
    } finally {
      setBusy(false);
    }
    inputRef.current?.focus();
  };

  return (
    <section className="view-area">
      <div className="chat-head">
        <AgentAvatar id={agent.id} accent={agent.color} size={34} badge={agent.icon} title={agent.name} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: 14 }}>Chat com {agent.name}</div>
          <div className="live-line">
            <span
              style={{
                width: 7, height: 7, borderRadius: 9, display: "inline-block",
                background: liveStatus.busy ? "var(--warn)" : "var(--success)",
                animation: liveStatus.busy ? "pulse 1.2s infinite" : "none",
              }}
            />
            <span>{liveStatus.label || (liveStatus.busy ? "Pensando..." : "Online")}</span>
            {liveStatus.phrase && <span style={{ opacity: 0.7 }}>— {liveStatus.phrase}</span>}
          </div>
        </div>
        <button className="tool-btn" onClick={() => useIdeStore.getState().setView("settings")}>
          ⚙️
        </button>
      </div>

      <div className="msgs">
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} showTimestamps={showTimestamps} />
        ))}
        <div ref={endRef} />
      </div>

      <div className="chat-suggestions">
        {SUGGESTIONS.map((s) => (
          <button key={s} className="suggest-btn" onClick={() => !busy && submit(s)}>
            {s}
          </button>
        ))}
      </div>

      <div className="chat-inputrow">
        <textarea
          ref={inputRef}
          className="chat-input"
          value={text}
          placeholder={`Escreva para ${agent.name}...`}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          rows={2}
        />
        <button className="send-now" onClick={() => submit()} disabled={busy || !text.trim()} title="Enviar (Enter)">
          ➤
        </button>
      </div>
    </section>
  );
}