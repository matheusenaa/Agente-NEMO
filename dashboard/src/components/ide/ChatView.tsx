import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useIdeStore } from "@/store/useIdeStore";
import { useNemoChat } from "@/hooks/useNemoChat";
import { getAgent } from "@/data/agents";
import { MessageBubble } from "./MessageBubble";
import { AgentAvatar } from "@/components/AgentAvatar";
import { nemoApi } from "@/api/nemo";
import type { AiConversation, ChatMessage } from "@/types/idea";

const SUGGESTIONS = [
  "Analise meus gastos e encontre duplicados",
  "Monte um relatório do Vasco",
  "Crie um post para o Instagram",
  "Liste os arquivos do projeto",
];

function parseTs(v: number | string | undefined): number {
  if (typeof v === "number") return v;
  if (typeof v === "string") {
    const n = Number(v);
    if (!Number.isNaN(n)) return n;
    const d = Date.parse(v);
    return Number.isNaN(d) ? Date.now() : d;
  }
  return Date.now();
}

export function ChatView() {
  const activeAgentId = useIdeStore((s) => s.activeAgentId);
  const threads = useIdeStore((s) => s.threads);
  const replaceThread = useIdeStore((s) => s.replaceThread);
  const notify = useIdeStore((s) => s.notify);
  const messages = threads[activeAgentId] ?? [];
  const liveStatus = useIdeStore((s) => s.liveStatus);
  const showTimestamps = useIdeStore((s) => s.config.showTimestamps);
  const { send } = useNemoChat();

  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [convs, setConvs] = useState<AiConversation[]>([]);
  const [openHist, setOpenHist] = useState(false);
  const [histQ, setHistQ] = useState("");
  const [confirmDel, setConfirmDel] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const agent = getAgent(activeAgentId);

  const loadConvs = useCallback(async () => {
    try {
      const r = await nemoApi.listConversations(agent.id);
      setConvs(r.conversations ?? []);
    } catch {
      setConvs([]);
    }
  }, [agent.id]);

  useEffect(() => {
    loadConvs();
  }, [loadConvs]);

  const openConversation = async (id: string) => {
    setOpenHist(false);
    try {
      const r = await nemoApi.conversationMessages(id);
      const msgs: ChatMessage[] = (r.messages ?? [])
        .map((m, i) => ({
          id: `hist-${id.slice(0, 6)}-${i}`,
          role: m.role === "assistant" ? ("agent" as const) : ("user" as const),
          agentId: m.role === "assistant" ? agent.id : "user",
          content: m.content,
          time: parseTs(m.created_at),
          status: "done" as const,
        }))
        .filter((m) => m.role === "user" || m.role === "agent");
      replaceThread(agent.id, msgs);
      notify({ icon: "📚", text: "Conversa carregada do histórico.", tone: "ok" });
    } catch {
      notify({ icon: "⚠️", text: "Não foi possível carregar a conversa.", tone: "error" });
    }
  };

  const newConversation = () => {
    replaceThread(agent.id, []);
    setOpenHist(false);
    notify({ icon: "✨", text: "Nova conversa iniciada.", tone: "ok" });
  };

  const deleteConversation = async (id: string) => {
    setConfirmDel(null);
    try {
      const r = await nemoApi.deleteConversation(id);
      setConvs((prev) => prev.filter((c) => c.id !== id));
      notify({ icon: "🗑️", text: `Conversa "${r.deleted.slice(0, 8)}" excluída.`, tone: "ok" });
    } catch {
      notify({ icon: "⚠️", text: "Não foi possível excluir a conversa.", tone: "error" });
    }
  };

  const filteredConvs = useMemo(() => {
    const needle = histQ.trim().toLowerCase();
    if (!needle) return convs;
    return convs.filter((c) => (c.title ?? "").toLowerCase().includes(needle));
  }, [convs, histQ]);

  const groups = useMemo(() => {
    const out: { dayKey: string; msgs: ChatMessage[] }[] = [];
    for (const m of messages) {
      const d = new Date(m.time);
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
      const last = out[out.length - 1];
      if (last && last.dayKey === key) last.msgs.push(m);
      else out.push({ dayKey: key, msgs: [m] });
    }
    return out;
  }, [messages]);

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
      loadConvs();
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
          <div style={{ fontWeight: 700, fontSize: 14, display: "flex", alignItems: "center", gap: 8 }}>
            Chat com {agent.name}
            <span className="muted" style={{ fontSize: 11, fontWeight: 400 }}>
              {convs.length} conversa{convs.length === 1 ? "" : "s"}
            </span>
          </div>
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
        <button className="tool-btn" title="Nova conversa" onClick={newConversation}>✨</button>
        <button className="tool-btn" title="Histórico de conversas" onClick={() => setOpenHist((v) => !v)}>
          📚
        </button>
        <button className="tool-btn" onClick={() => useIdeStore.getState().setView("settings")}>
          ⚙️
        </button>
      </div>

      {openHist && (
        <div className="hist-panel">
          <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
            <input
              className="hist-search"
              placeholder="🔎 Buscar nas conversas..."
              value={histQ}
              onChange={(e) => setHistQ(e.target.value)}
            />
            <span className="muted" style={{ fontSize: 11, whiteSpace: "nowrap" }}>{filteredConvs.length}</span>
          </div>
          {filteredConvs.length === 0 && (
            <div className="dash-empty" style={{ padding: 12 }}>
              {convs.length === 0 ? "Nenhuma conversa persistida ainda — envie uma mensagem." : "Nada encontrado."}
            </div>
          )}
          {filteredConvs.map((c) => (
            <div key={c.id} className="hist-row" style={{ cursor: "pointer" }} onClick={() => openConversation(c.id)} title="Reabrir conversa">
              <span>💬</span>
              <span style={{ fontWeight: 600, maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.title || "Nova conversa"}</span>
              <span style={{ color: "var(--text3)", fontSize: 11 }}>
                {c.message_count ?? 0} msg · {new Date(parseTs(c.updated_at ?? c.created_at)).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" })}
              </span>
              <button
                className="tool-btn icon"
                title="Excluir conversa"
                style={{ marginLeft: "auto", padding: "4px 6px", fontSize: 13, color: "var(--danger)" }}
                onClick={(e) => {
                  e.stopPropagation();
                  setConfirmDel(c.id);
                }}
              >
                🗑️
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="msgs">
        {groups.map((g) => (
          <div key={g.dayKey} className="day-group">
            <div className="day-chip">{dayLabel(g.dayKey)}</div>
            {g.msgs.map((m) => (
              <MessageBubble key={m.id} message={m} showTimestamps={showTimestamps} />
            ))}
          </div>
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

      {confirmDel && (
        <div className="modal-mask" onClick={() => setConfirmDel(null)}>
          <div className="modal-card" style={{ width: "min(420px,92vw)" }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <span style={{ fontSize: 20 }}>🗑️</span>
              <strong>Excluir esta conversa?</strong>
            </div>
            <div className="modal-body" style={{ fontSize: 13, color: "var(--text2)", lineHeight: 1.6 }}>
              As mensagens e o histórico desta conversa serão removidos permanentemente. Esta ação não pode ser desfeita.
            </div>
            <div className="modal-foot">
              <button className="tool-btn" style={{ flex: 1 }} onClick={() => setConfirmDel(null)}>
                Cancelar
              </button>
              <button className="tool-btn primary" style={{ flex: 1, background: "var(--danger)", borderColor: "var(--danger)" }} onClick={() => deleteConversation(confirmDel)}>
                Excluir
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

function dayLabel(dayKey: string): string {
  const start = new Date();
  start.setHours(0, 0, 0, 0);
  const d = new Date(dayKey + "T00:00");
  const diffDays = Math.round((start.getTime() - d.getTime()) / 86400000);
  if (diffDays === 0) return "Hoje";
  if (diffDays === 1) return "Ontem";
  return d.toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "long", year: "numeric" });
}