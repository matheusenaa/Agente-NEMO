import { useState } from "react";
import { useIdeStore } from "@/store/useIdeStore";
import { useSquadStore } from "@/store/useSquadStore";
import { AGENT_ROSTER, getAgent } from "@/data/agents";
import type { ViewId } from "@/types/idea";
import { eventSortDate } from "@/lib/calendar";
import { AgentAvatar } from "@/components/AgentAvatar";
import { categoryMeta } from "./EventModal";
import { pickPhrase } from "@/data/statusPhrases";

export function DashboardView() {
  const [emptyEventPhrase] = useState(() => pickPhrase(["Que tal agendar algo?", "Agende o próximo passo."], ""));
  const setView = useIdeStore((s) => s.setView);
  const setActiveAgent = useIdeStore((s) => s.setActiveAgent);
  const liveStatus = useIdeStore((s) => s.liveStatus);
  const tasks = useIdeStore((s) => s.tasks);
  const events = useIdeStore((s) => s.events);
  const threads = useIdeStore((s) => s.threads);
  const logs = useIdeStore((s) => s.logs);
  const notifications = useIdeStore((s) => s.notifications);
  const history = useIdeStore((s) => s.history);
  const squads = useSquadStore((s) => s.squads);

  const openTasks = tasks.filter((t) => t.status === "pending").length;
  const runningTasks = tasks.filter((t) => t.status === "running").length;
  const runningTaskItems = tasks.filter((t) => t.status === "running");
  const busyAgents = new Set<string>();
  if (liveStatus.busy) busyAgents.add(liveStatus.agentId);
  tasks.forEach((t) => (t.status === "running" ? busyAgents.add(t.agentId) : undefined));
  const day = new Date().toISOString().slice(0, 10);
  const todayEvents = events.filter((e) => e.date === day);
  const upcoming = events
    .filter((e) => eventSortDate(e) >= day + "T00:00")
    .sort((a, b) => eventSortDate(a).localeCompare(eventSortDate(b)))
    .slice(0, 5);

  const recentChats = Object.entries(threads)
    .map(([agentId, msgs]) => ({
      agentId,
      last: msgs[msgs.length - 1]?.time ?? 0,
      lastText: msgs[msgs.length - 1]?.content ?? "",
    }))
    .sort((a, b) => b.last - a.last)
    .slice(0, 5);

  const recentLogs = [...logs].reverse().slice(0, 6);

  const recentMissions = history
    .filter((h) => h.kind === "task")
    .map((h) => {
      const t = tasks.find((x) => x.title === h.title);
      return { ...h, agentId: t?.agentId ?? h.agentId ?? "nemo" };
    })
    .slice(0, 5);

  const go = (view: ViewId) => setView(view);
  const chatWith = (id: string) => {
    setActiveAgent(id);
    setView("chat");
  };

  return (
    <section className="view-area dash-wrap">
      <div className="dash-hero">
        <div className="dash-hero-text">
          <div className="dash-eyebrow">CENTRAL DE OPERAÇÕES</div>
          <h1>Bem-vindo à NEMO IDE</h1>
          <p>
            Sua equipe de agentes está pronta. Converse, agende, trabalhe — tudo num ambiente único.
            {liveStatus.busy && <span className="dash-live"> {getAgent(liveStatus.agentId).name} está {liveStatus.label}</span>}
          </p>
          <div className="dash-actions">
            <button className="tool-btn primary" onClick={() => chatWith("nemo")}>💬 Conversar com NEMO</button>
            <button className="tool-btn" onClick={() => go("office")}>🏢 Abrir escritório</button>
            <button className="tool-btn" onClick={() => go("calendar")}>📅 Novo evento</button>
          </div>
        </div>
        <div className="dash-hero-agent">
          <AgentAvatar id={liveStatus.agentId ?? "nemo"} accent={getAgent(liveStatus.agentId).color} size={92} badge={getAgent(liveStatus.agentId).icon} shape="round" />
          <div className="dash-agent-name">{getAgent(liveStatus.agentId).name}</div>
          <div className="dash-agent-title">{getAgent(liveStatus.agentId).title}</div>
          <div className="dash-agent-status">
            <span
              style={{
                width: 8, height: 8, borderRadius: 9, display: "inline-block",
                background: liveStatus.busy ? "var(--warn)" : "var(--success)",
                animation: liveStatus.busy ? "pulse 1.2s infinite" : "none",
              }}
            />
            {liveStatus.busy ? liveStatus.label : "🟢 Online"}
          </div>
        </div>
      </div>

      <div className="dash-stats">
        <div className="stat-card" onClick={() => go("chat")}>
          <div className="stat-ico">👤</div>
          <div className="stat-num">{AGENT_ROSTER.length}</div>
          <div className="stat-label">Agentes na equipe</div>
        </div>
        <div className="stat-card accent" onClick={() => go("office")}>
          <div className="stat-ico">⚡</div>
          <div className="stat-num">{busyAgents.size}</div>
          <div className="stat-label">Em atividade</div>
        </div>
        <div className="stat-card" onClick={() => go("tasks")}>
          <div className="stat-ico">✅</div>
          <div className="stat-num">{openTasks + runningTasks}</div>
          <div className="stat-label">Tarefas abertas</div>
        </div>
        <div className="stat-card" onClick={() => go("calendar")}>
          <div className="stat-ico">📅</div>
          <div className="stat-num">{todayEvents.length}</div>
          <div className="stat-label">Eventos hoje</div>
        </div>
        <div className="stat-card" onClick={() => go("history")}>
          <div className="stat-ico">🔔</div>
          <div className="stat-num">{notifications.length}</div>
          <div className="stat-label">Notificações</div>
        </div>
      </div>

      <div className="dash-cols">
        <div className="dash-col">
          <div className="card-tt">📅 Próximos eventos</div>
          <div className="dash-list">
            {upcoming.length === 0 && <div className="dash-empty">Nenhum evento futuro. {emptyEventPhrase}</div>}
            {upcoming.map((e) => {
              const cat = categoryMeta(e.category);
              const agent = getAgent(e.agentId);
              const when = e.date === day ? "Hoje" : new Date(e.date + "T00:00").toLocaleDateString("pt-BR", { weekday: "short", day: "2-digit", month: "short" });
              return (
                <button key={e.id} className="dash-row clickable" onClick={() => go("calendar")}>
                  <span className="dash-dot" style={{ background: cat.color }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="dash-row-title">{e.title}</div>
                    <div className="dash-row-sub">{when} · {e.time} · {agent.name}</div>
                  </div>
                </button>
              );
            })}
          </div>

          <div className="card-tt">🗨️ Conversas recentes</div>
          <div className="dash-list">
            {recentChats.map((c) => {
              const agent = getAgent(c.agentId);
              return (
                <button key={c.agentId} className="dash-row clickable" onClick={() => chatWith(c.agentId)}>
                  <AgentAvatar id={c.agentId} accent={agent.color} size={26} badge={agent.icon} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="dash-row-title">{agent.name} <span className="muted">· {new Date(c.last).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</span></div>
                    <div className="dash-row-sub" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.lastText.replace(/[#*`]/g, "")}</div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        <div className="dash-col">
          <div className="card-tt">🤖 Sala dos Agentes</div>
          <div className="dash-agents">
{AGENT_ROSTER.map((a) => {
              const isBusy = busyAgents.has(a.id);
              return (
                <button
                  key={a.id}
                  className="agent-rest-item clickable"
                  onClick={() => {
                    setActiveAgent(a.id);
                    setView("office");
                  }}
                  title={`Mudar ${a.name} para modo trabalho`}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    width: "100%",
                    padding: "10px 12px",
                    border: "1px solid var(--border)",
                    borderRadius: 10,
                    background: isBusy ? "var(--bg3)" : "var(--bg2)",
                    color: isBusy ? "var(--text-primary)" : "var(--text-secondary)",
                    cursor: "pointer",
                    textAlign: "left",
                    fontSize: 13,
                    fontFamily: "inherit",
                    transition: "all 0.15s ease",
                    marginBottom: 6,
                  }}
                >
                  <AgentAvatar
                    id={a.id}
                    accent={a.color}
                    size={34}
                    badge={a.icon}
                    shape="round"
                    style={{ 
                      width: 34, height: 34,
                      flexShrink: 0,
                      boxShadow: "inset 0 1px 0 rgba(255,255,255,0.12)",
                    }}
                  />
                  <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {a.name}
                  </span>
                  <span style={{ fontSize: 11, color: "var(--text3)" }}>
                    {isBusy ? "em execução" : "descansando"}
                  </span>
                </button>
              );
            })}
            {busyAgents.size === 0 && (
              <div style={{ padding: "16px 12px", color: "var(--text3)", fontSize: 12 }}>
                Todos os agentes descansando
              </div>
            )}
          </div>

          <div className="card-tt">🎬 Missões recentes</div>
          <div className="dash-list">
            {recentMissions.length === 0 && <div className="dash-empty">Nenhuma missão delegada ainda. Peça uma tarefa em 💬 Tarefas.</div>}
            {recentMissions.map((m) => {
              const agent = getAgent(m.agentId);
              return (
                <button key={m.id} className="dash-row clickable" onClick={() => go("tasks")}>
                  <AgentAvatar id={m.agentId} accent={agent.color} size={26} badge={agent.icon} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="dash-row-title">{m.title}</div>
                    <div className="dash-row-sub">{agent.name} · {new Date(m.time).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}</div>
                  </div>
                  <span style={{ color: "var(--text3)", fontSize: 11 }}>{m.detail}</span>
                </button>
              );
})}
          </div>

          <div className="card-tt">▶ Em execução</div>
          <div className="dash-list">
            {runningTaskItems.length === 0 && <div className="dash-empty">Nenhuma tarefa em execução agora.</div>}
            {runningTaskItems.map((t) => {
              const agent = getAgent(t.agentId);
              return (
                <button key={t.id} className="dash-row clickable" onClick={() => go("tasks")}>
                  <AgentAvatar id={t.agentId} accent={agent.color} size={26} badge={agent.icon} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="dash-row-title">{t.title}</div>
                    <div className="dash-row-sub">{agent.name} · em execução</div>
                  </div>
                  <span className="status-pill running">▶</span>
                </button>
              );
            })}
          </div>

          <div className="card-tt">🪵 Atividade recente</div>
          <div className="dash-logs">
            {recentLogs.length === 0 && <div className="dash-empty">Sem atividade ainda.</div>}
            {recentLogs.map((l) => (
              <div key={l.id} className="dash-log">
                <span className="ts">{new Date(l.time).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</span>
                <span style={{ color: toneColor(l.tone) }}>{l.text}</span>
              </div>
            ))}
          </div>

          {squads.size > 0 && (
            <div className="cb" style={{ marginTop: 14 }}>
              <div className="card-tt">📋 Squads ({squads.size})</div>
              <div style={{ fontSize: 12, color: "var(--text3)" }}>
                {Array.from(squads.values()).slice(0, 4).map((s) => s.name).join(" · ")}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function toneColor(t: string): string {
  switch (t) {
    case "error": return "var(--danger)";
    case "warn": return "var(--warn)";
    case "ok": return "var(--success)";
    case "agent": return "var(--accent)";
    default: return "var(--text2)";
  }
}