import { useState } from "react";
import { useIdeStore } from "@/store/useIdeStore";
import { VIEWS } from "@/data/agents";
import type { ViewId } from "@/types/idea";

function getUserName(): string {
  try {
    const name = localStorage.getItem("nemo-user-name");
    if (name) return name;
  } catch {
    /* fallback */
  }
  return "Operador";
}

export function TopBar() {
  const activeView = useIdeStore((s) => s.activeView);
  const setView = useIdeStore((s) => s.setView);
  const bottomOpen = useIdeStore((s) => s.bottomOpen);
  const toggleBottom = useIdeStore((s) => s.toggleBottom);
  const toggleRight = useIdeStore((s) => s.toggleRight);
  const toggleLeft = useIdeStore((s) => s.toggleLeft);
  const rightOpen = useIdeStore((s) => s.rightOpen);
  const notifications = useIdeStore((s) => s.notifications);
  const dismissNotif = useIdeStore((s) => s.dismissNotif);
  const tasks = useIdeStore((s) => s.tasks);
  const [notifOpen, setNotifOpen] = useState(false);
  const pendingTasks = tasks.filter((t) => t.status === "pending").length;

  return (
    <header className="ide-top">
      <div className="brand" onClick={() => setView("chat")} style={{ cursor: "pointer" }}>
        <div className="logo-nemo">🐟</div>
        <div>
          <div className="brand-name">NEMO</div>
          <div className="brand-sub">IDE · AI Agents</div>
        </div>
      </div>

      <nav className="views">
        {VIEWS.map((v) => (
          <button key={v.id} className={`view-tab ${activeView === v.id ? "on" : ""}`} onClick={() => setView(v.id as ViewId)}>
            <span>{v.icon}</span>
            <span>{v.label}</span>
          </button>
        ))}
      </nav>

      <div className="top-right">
        <button className="icon-btn" title="Agentes (painel esquerdo)" onClick={() => toggleLeft()}>
          👥
        </button>
        <button className="icon-btn" title={`Contexto (painel direito ${rightOpen ? "aberto" : "fechado"})`} onClick={() => toggleRight()}>
          🗂️
        </button>
        <button className="icon-btn" title="Terminal / Logs" onClick={() => toggleBottom()} style={{ color: bottomOpen ? "var(--accentText)" : undefined }}>
          👇
        </button>
        <button className="icon-btn" title={`Notificações (${notifications.length})`} onClick={() => setNotifOpen((v) => !v)}>
          🔔
          {notifications.length > 0 && <span className="dot-badge">{notifications.length}</span>}
          {notifOpen && (
            <div className="notif-drop" onClick={(e) => e.stopPropagation()}>
              <div style={{ padding: "6px 10px", fontSize: 12, fontWeight: 700, color: "var(--text3)", textTransform: "uppercase", letterSpacing: 1 }}>
                Notificações
              </div>
              {notifications.length === 0 && <div style={{ padding: 10, color: "var(--text3)", fontSize: 13 }}>Nada por aqui ainda. 🎉</div>}
              {notifications.map((n) => (
                <div key={n.id} className="notif-item" onClick={() => dismissNotif(n.id)}>
                  <span>{n.icon}</span>
                  <span style={{ flex: 1 }}>{n.text}</span>
                  <span style={{ color: "var(--text3)", fontSize: 11 }}>{new Date(n.time).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</span>
                </div>
              ))}
            </div>
          )}
        </button>
        <button className="icon-btn" title="Tarefas pendentes" onClick={() => setView("tasks")}>
          ✅
          {pendingTasks > 0 && <span className="dot-badge">{pendingTasks}</span>}
        </button>
        <button className="icon-btn" title="Configurações" onClick={() => setView("settings")}>
          ⚙️
        </button>
        <div className="user-pill">
          <div className="ua">{getUserName().slice(0, 1).toUpperCase()}</div>
          <span>{getUserName()}</span>
        </div>
      </div>
    </header>
  );
}