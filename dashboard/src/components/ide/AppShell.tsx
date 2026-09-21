import { useEffect, useState, type ReactNode } from "react";
import { useIdeStore } from "@/store/useIdeStore";
import { useSquadSocket } from "@/hooks/useSquadSocket";
import { getTheme } from "@/data/themes";
import { TopBar } from "./TopBar";
import { AgentSidebar } from "./AgentSidebar";
import { DashboardView } from "./DashboardView";
import { ChatView } from "./ChatView";
import { WorkspaceView } from "./WorkspaceView";
import { OfficeView } from "./OfficeView";
import { CalendarView } from "./CalendarView";
import { TerminalView } from "./TerminalView";
import { TasksView } from "./TasksView";
import { HistoryView } from "./HistoryView";
import { SettingsView } from "./SettingsView";
import { ContextPanel } from "./ContextPanel";
import { NotificationsLayer } from "./NotificationsLayer";

function LogsView() {
  const logs = useIdeStore((s) => s.logs);
  const logList = [...logs].reverse();
  return (
    <div style={{ flex: 1, overflowY: "auto", padding: "10px 14px" }}>
      {logList.length === 0 && <div style={{ color: "var(--text3)", fontSize: 12 }}>Sem logs ainda.</div>}
      {logList.map((l) => (
        <div key={l.id} className="log-row" style={{ marginBottom: 3 }}>
          <span className="ts">{new Date(l.time).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</span>
          {l.agentId && <span style={{ width: 18, height: 18, borderRadius: 6, display: "inline-flex", alignItems: "center", justifyContent: "center", background: "var(--chip-bg)", fontSize: 10 }}>{"🐟"}</span>}
          <span style={{ color: tone(l.tone) }}>{l.text}</span>
        </div>
      ))}
    </div>
  );
}

function tone(t: string): string {
  switch (t) {
    case "error": return "var(--danger)";
    case "warn": return "var(--warn)";
    case "ok": return "var(--success)";
    case "agent": return "var(--accent)";
    default: return "var(--text2)";
  }
}

function bottomClear() {
  useIdeStore.setState({ logs: [] });
}

export function AppShell() {
  useSquadSocket();
  const activeView = useIdeStore((s) => s.activeView);
  const bottomOpen = useIdeStore((s) => s.bottomOpen);
  const config = useIdeStore((s) => s.config);
  const [bottomTab, setBottomTab] = useState<"terminal" | "logs" | "running">("terminal");

  useEffect(() => {
    const theme = getTheme(config.theme);
    document.body.dataset.theme = config.theme;
    document.body.dataset.density = config.density;
    document.body.classList.toggle("no-anim", !config.animations);
    document.documentElement.style.setProperty("--fs", `${config.fontSize}px`);
    document.title = `NEMO IDE · ${theme.name}`;
    const fav = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
    if (fav) fav.href = `data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🐟</text></svg>`;
  }, [config.theme, config.density, config.animations, config.fontSize]);

  const viewMap: Record<string, ReactNode> = {
    dashboard: <DashboardView />,
    chat: <ChatView />,
    workspace: <WorkspaceView />,
    office: <OfficeView />,
    calendar: <CalendarView />,
    terminal: <TerminalView />,
    tasks: <TasksView />,
    history: <HistoryView />,
    settings: <SettingsView />,
  };

  return (
    <div className="ide-shell">
      <TopBar />
      <div className="ide-main">
        <AgentSidebar />
        <main className="center">
          {viewMap[activeView] ?? <ChatView />}

          {bottomOpen && (
            <div className="bottom">
              <div className="bottom-tabs">
                {(["terminal", "logs", "running"] as const).map((t) => (
                  <button key={t} className={`bottom-tab ${bottomTab === t ? "on" : ""}`} onClick={() => setBottomTab(t)}>
                    {t === "terminal" ? "⌨️ Terminal" : t === "logs" ? "🪵 Logs" : "▶ Exec"}
                  </button>
                ))}
                <button className="bottom-tab" style={{ marginLeft: "auto", color: "var(--danger)" }} onClick={() => { if (bottomTab === "logs") bottomClear(); useIdeStore.getState().toggleBottom(false); }}>
                  ✕ &nbsp;Sair
                </button>
              </div>
              <div className="bottom-body">
                {bottomTab === "terminal" && <TerminalView />}
                {bottomTab === "logs" && <LogsView />}
                {bottomTab === "running" && <RunningView />}
              </div>
            </div>
          )}
        </main>
        <ContextPanel />
      </div>
      <NotificationsLayer />
    </div>
  );
}

function RunningView() {
  const tasks = useIdeStore((s) => s.tasks);
  const running = tasks.filter((t) => t.status === "running");
  const widthFor = (id: string) => {
    // Largura estável por tarefa (hash simples -> 35..85%)
    let h = 0;
    for (const ch of id) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
    return 35 + (h % 51) + "%";
  };
  return (
    <div>
      {running.length === 0 && <div style={{ color: "var(--text3)", fontSize: 12 }}>Nenhuma tarefa em execução agora.</div>}
      {running.map((t) => (
        <div key={t.id} style={{ marginBottom: 8 }}>
          <div style={{ fontSize: 12 }}>{t.title}</div>
          <div className="bar"><i style={{ width: widthFor(t.id), animation: "pulse 2s infinite" }} /></div>
        </div>
      ))}
    </div>
  );
}