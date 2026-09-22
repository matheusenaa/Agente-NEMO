import { useMemo } from "react";
import { useIdeStore } from "@/store/useIdeStore";
import { AGENT_ROSTER, getAgent } from "@/data/agents";

const CAT_COLORS: Record<string, string> = {
  Tarefa: "#00b4ff",
  "Reunião": "#c8102e",
  Estudo: "#8b5cf6",
  Pessoal: "#00e676",
};

export function DashboardView() {
  const setView = useIdeStore((s) => s.setView);
  const setActiveAgent = useIdeStore((s) => s.setActiveAgent);
  const liveStatus = useIdeStore((s) => s.liveStatus);
  const tasks = useIdeStore((s) => s.tasks);
  const events = useIdeStore((s) => s.calendarEvents);
  const notifications = useIdeStore((s) => s.notifications);
  const history = useIdeStore((s) => s.history);

  const activeCount = liveStatus.busy ? 1 : 0;
  const pendingCount = tasks.filter((t) => t.status === "pending" || t.status === "running").length;
  const doneCount = tasks.filter((t) => t.status === "done").length;

  const now = Date.now();
  const nextEvents = useMemo(
    () =>
      events
        .map((e) => {
          const dt = new Date(`${e.date}T${e.startTime || "12:00"}:00`).getTime();
          return { e, dt };
        })
        .filter((x) => x.dt >= now - 3600_000)
        .sort((a, b) => a.dt - b.dt)
        .slice(0, 5),
    [events, now],
  );

  const recentNotifs = notifications.slice(0, 4);
  const recentActivity = history.slice(0, 6);

  const openConversa = (agentId: string) => {
    setActiveAgent(agentId);
    setView("conversas");
  };

  const todayLabel = new Date().toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" });

  return (
    <div style={{ flex: 1, minHeight: 0, overflowY: "auto", padding: "18px 22px" }}>
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 12, flexWrap: "wrap", marginBottom: 16 }}>
        <div>
          <div style={{ fontSize: 22, fontWeight: 800, letterSpacing: -0.5 }}>Central de Operações NEMO</div>
          <div style={{ fontSize: 13, color: "var(--text3)", textTransform: "capitalize" }}>{todayLabel}</div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="tool-btn primary" onClick={() => setView("office")}>🏢 Abrir escritório</button>
          <button className="tool-btn" onClick={() => setView("calendario")}>📅 Calendário</button>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 18 }}>
        {[
          { icon: "🤖", label: "Agentes", value: String(AGENT_ROSTER.length), sub: "na frota", color: "var(--accent)", view: "agentes" as const },
          { icon: "🟢", label: "Ativos agora", value: String(activeCount), sub: liveStatus.busy ? getAgent(liveStatus.agentId).name : "aguardando", color: "var(--success)", view: "agentes" as const },
          { icon: "📋", label: "Tarefas", value: String(pendingCount), sub: `${doneCount} concluídas`, color: "var(--warn)", view: "tasks" as const },
          { icon: "📅", label: "Eventos", value: String(events.length), sub: `${nextEvents.length} próximos`, color: "#8b5cf6", view: "calendario" as const },
        ].map((c) => (
          <button
            key={c.label}
            onClick={() => setView(c.view)}
            title={`Ir para ${c.label}`}
            style={{
              background: "var(--bg2)",
              border: "1px solid var(--border)",
              borderRadius: 14,
              padding: "14px 16px",
              textAlign: "left",
              cursor: "pointer",
              fontFamily: "inherit",
              color: "var(--text)",
              display: "flex",
              flexDirection: "column",
              gap: 8,
              transition: "border-color .15s, transform .12s",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span style={{ fontSize: 22 }}>{c.icon}</span>
              <span style={{ fontSize: 28, fontWeight: 800, color: c.color }}>{c.value}</span>
            </div>
            <span style={{ fontWeight: 700, fontSize: 13 }}>{c.label}</span>
            <span style={{ fontSize: 11, color: "var(--text3)" }}>{c.sub}</span>
          </button>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: 14 }}>
        <div style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 14, padding: 14 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
            <span style={{ fontWeight: 800, fontSize: 13, textTransform: "uppercase", letterSpacing: 1, color: "var(--text2)" }}>📅 Próximos eventos</span>
            <button className="tool-btn" onClick={() => setView("calendario")}>Ver todos</button>
          </div>
          {nextEvents.length === 0 && <p style={{ fontSize: 13, color: "var(--text3)" }}>Nenhum evento agendado.</p>}
          {nextEvents.map(({ e }) => (
            <button
              key={e.id}
              onClick={() => setView("calendario")}
              style={{ display: "flex", alignItems: "center", gap: 10, width: "100%", background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 10, padding: "9px 11px", marginBottom: 6, cursor: "pointer", fontFamily: "inherit", color: "var(--text)", textAlign: "left" }}
            >
              <span style={{ width: 8, height: 36, borderRadius: 4, background: CAT_COLORS[e.category] ?? "#00b4ff", flexShrink: 0 }} />
              <span style={{ flex: 1, minWidth: 0 }}>
                <span style={{ display: "block", fontSize: 13, fontWeight: 600 }}>{e.title}</span>
                <span style={{ display: "block", fontSize: 11, color: "var(--text3)" }}>
                  {new Date(e.date + "T12:00:00").toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" })} · {e.startTime || "--:--"}
                </span>
              </span>
              <span style={{ fontSize: 11, color: "var(--text3)" }}>{getAgent(e.agentId).icon}</span>
            </button>
          ))}
        </div>

        <div style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 14, padding: 14 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
            <span style={{ fontWeight: 800, fontSize: 13, textTransform: "uppercase", letterSpacing: 1, color: "var(--text2)" }}>🐟 Frota de agentes</span>
            <button className="tool-btn" onClick={() => setView("agentes")}>Ver escritório</button>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            {AGENT_ROSTER.map((a) => {
              const isBusy = liveStatus.busy && liveStatus.agentId === a.id;
              return (
                <button
                  key={a.id}
                  onClick={() => openConversa(a.id)}
                  title={`Conversar com ${a.name}`}
                  style={{ display: "flex", alignItems: "center", gap: 8, background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 10, padding: "8px 10px", cursor: "pointer", fontFamily: "inherit", color: "var(--text)", textAlign: "left", transition: "border-color .15s" }}
                >
                  <span style={{ width: 26, height: 26, borderRadius: 9, background: a.color, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, flexShrink: 0, color: "#fff" }}>{a.icon}</span>
                  <span style={{ flex: 1, minWidth: 0 }}>
                    <span style={{ display: "block", fontSize: 12, fontWeight: 700 }}>{a.name}</span>
                    <span style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 10, color: isBusy ? "var(--success)" : "var(--text3)" }}>
                      <span style={{ width: 5, height: 5, borderRadius: 9, background: isBusy ? "var(--success)" : "var(--text3)", display: "inline-block", animation: isBusy ? "pulse 1.4s infinite" : "none" }} />
                      {isBusy ? "trabalhando" : "pronto"}
                    </span>
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: 14, marginTop: 14 }}>
        <div style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 14, padding: 14 }}>
          <span style={{ fontWeight: 800, fontSize: 13, textTransform: "uppercase", letterSpacing: 1, color: "var(--text2)" }}>🔔 Notificações</span>
          {recentNotifs.length === 0 && <p style={{ fontSize: 13, color: "var(--text3)", marginTop: 8 }}>Sem notificações recentes.</p>}
          {recentNotifs.map((n) => (
            <div key={n.id} style={{ display: "flex", gap: 9, padding: "7px 2px", borderBottom: "1px dashed var(--border)", fontSize: 13 }}>
              <span>{n.icon}</span>
              <span style={{ flex: 1 }}>{n.text}</span>
              <span style={{ color: "var(--text3)", fontSize: 11, whiteSpace: "nowrap" }}>{new Date(n.time).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</span>
            </div>
          ))}
        </div>

        <div style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 14, padding: 14 }}>
          <span style={{ fontWeight: 800, fontSize: 13, textTransform: "uppercase", letterSpacing: 1, color: "var(--text2)" }}>🕘 Atividade recente</span>
          {recentActivity.length === 0 && <p style={{ fontSize: 13, color: "var(--text3)", marginTop: 8 }}>Sem atividade registrada ainda.</p>}
          {recentActivity.map((h) => (
            <div key={h.id} style={{ display: "flex", gap: 9, padding: "6px 2px", fontSize: 13 }}>
              <span>{h.kind === "chat" ? "💬" : h.kind === "file" ? "📄" : h.kind === "task" ? "✅" : h.kind === "terminal" ? "⌨️" : "⚙️"}</span>
              <span style={{ flex: 1, minWidth: 0 }}>
                <span style={{ display: "block", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{h.title}</span>
                <span style={{ display: "block", fontSize: 11, color: "var(--text3)" }}>{h.detail}</span>
              </span>
            </div>
          ))}
        </div>
      </div>

      {pendingCount > 0 && (
        <div style={{ marginTop: 14, padding: "12px 16px", borderRadius: 12, border: "1px solid var(--border)", background: "color-mix(in srgb, var(--warn) 12%, var(--bg2))", display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <span style={{ fontSize: 16 }}>📋</span>
          <span style={{ flex: 1, fontSize: 13 }}>
            <b>{pendingCount} tarefa(s) em aberto.</b> Acompanhe o progresso ou conclua o que estiver pronto.
          </span>
          <button className="tool-btn primary" onClick={() => setView("tasks")}>Ver tarefas</button>
        </div>
      )}
    </div>
  );
}