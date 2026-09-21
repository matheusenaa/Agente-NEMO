import { useState } from "react";
import { useIdeStore } from "@/store/useIdeStore";
import { getAgent, PRIORITY_ICON } from "@/data/agents";
import { AgentAvatar } from "@/components/AgentAvatar";
import type { TaskItem, TaskStatus } from "@/types/idea";

const STATUS_TEXT: Record<TaskStatus, string> = {
  pending: "⏳ pendente",
  running: "▶ em execução",
  done: "✓ concluída",
  error: "✗ erro",
};

export function TasksView() {
  const tasks = useIdeStore((s) => s.tasks);
  const updateTask = useIdeStore((s) => s.updateTask);
  const addTask = useIdeStore((s) => s.addTask);
  const notify = useIdeStore((s) => s.notify);
  const [newTitle, setNewTitle] = useState("");

  const open = tasks.filter((t) => t.status === "pending").length;
  const done = tasks.filter((t) => t.status === "done").length;
  const running = tasks.filter((t) => t.status === "running").length;

  const create = () => {
    const title = newTitle.trim();
    if (!title) return;
    addTask({ title, priority: "normal" });
    setNewTitle("");
    notify({ icon: "✅", text: `Tarefa criada: ${title.slice(0, 40)}`, tone: "ok" });
  };

  const nextOf = (t: TaskItem): TaskStatus =>
    t.status === "done" ? "pending" : t.status === "error" ? "pending" : "done";

  return (
    <section className="view-area">
      <div className="tasks-wrap">
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 14, flexWrap: "wrap" }}>
          <h2 style={{ margin: 0, fontSize: 18 }}>Tasks · {tasks.length}</h2>
          <span className="status-pill running">▶ {running}</span>
          <span className="status-pill">⏳ {open}</span>
          <span className="status-pill done">✓ {done}</span>
          <div style={{ flex: 1, display: "flex", gap: 6, justifyContent: "flex-end" }}>
            <input
              className="chat-input"
              style={{ width: "min(320px,100%)", minHeight: 0, padding: "8px 12px" }}
              placeholder="Nova tarefa... ex: pesquisar obras do Vasco"
              value={newTitle}
              onChange={(e) => setNewTitle(e.currentTarget.value)}
              onKeyDown={(e) => { if (e.key === "Enter") create(); }}
            />
            <button className="tool-btn primary" onClick={create}>+ Add</button>
          </div>
        </div>

        {tasks.length === 0 && (
          <div style={{ color: "var(--text3)", textAlign: "center", padding: 40 }}>
            Sem tarefas ainda. Cada pedido no chat vira uma tarefa automaticamente. ✨
          </div>
        )}

        {tasks.map((t: TaskItem) => {
          const agent = t.agentId ? getAgent(t.agentId) : undefined;
          return (
            <div key={t.id} className={`taskline ${t.status === "done" ? "done" : ""}`}>
              <button
                className="switch"
                style={{ width: 30, height: 30, borderRadius: 9, background: t.status === "done" ? "var(--success)" : "var(--bg4)" }}
                onClick={() => updateTask(t.id, { status: nextOf(t) })}
                title="Alternar conclusão"
              >
                <span style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13 }}>
                  {t.status === "done" ? "✓" : ""}
                </span>
              </button>
              {agent && <AgentAvatar id={agent.id} accent={agent.color} size={22} badge={agent.icon} />}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 600, wordBreak: "break-word" }}>{t.title}</div>
<div style={{ display: "flex", gap: 10, fontSize: 11, color: "var(--text3)", marginTop: 2 }}>
                  <span>{agent?.name ?? "nemo"}</span>
                  <span>{PRIORITY_ICON[t.priority].icon} {PRIORITY_ICON[t.priority].label}</span>
                  {t.dueDate && <span>📅 {new Date(t.dueDate).toLocaleDateString("pt-BR", { month: "2-digit", day: "2-digit" })}</span>}
                  <span>🕐 {new Date(t.createdAt).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</span>
                </div>
              </div>
              <span className={`status-pill ${t.status}`}>{STATUS_TEXT[t.status]}</span>
            </div>
          );
        })}
      </div>
    </section>
  );
}