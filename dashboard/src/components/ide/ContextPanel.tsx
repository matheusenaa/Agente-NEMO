import { useIdeStore } from "@/store/useIdeStore";
import { useSquadStore } from "@/store/useSquadStore";
import { getAgent } from "@/data/agents";
import { FUNNY_PHRASES, pickPhrase } from "@/data/statusPhrases";

export function ContextPanel() {
  const rightOpen = useIdeStore((s) => s.rightOpen);
  const liveStatus = useIdeStore((s) => s.liveStatus);
  const logs = useIdeStore((s) => s.logs);
  const tasks = useIdeStore((s) => s.tasks);
  const openFiles = useIdeStore((s) => s.openFiles);
  const updateTask = useIdeStore((s) => s.updateTask);
  const notify = useIdeStore((s) => s.notify);
  const addLog = useIdeStore((s) => s.addLog);
  const isConnected = useSquadStore((s) => s.isConnected);
  const squads = useSquadStore((s) => s.squads);

  if (!rightOpen) return null;

  const open = tasks.filter((t) => t.status !== "done" && t.status !== "error").length;
  const lastLogs = logs.slice(-6).reverse();

  return (
    <aside className="ctx-panel">
      <div className="ctx-body">
        <div className="ctx-card">
          <div className="t">⭕ Status</div>
          <div className="kv">
            <strong>Agente</strong>
            <span>{getAgent(liveStatus.agentId ?? "nemo").name}</span>
          </div>
          <div className="kv">
            <strong>Fase</strong>
            <span>{liveStatus.label || "Online"}</span>
          </div>
          <div className="kv">
            <strong>Squad</strong>
            <span>{isConnected ? "🔗 conectado (WS)" : "⭘ offline (answering local)"}</span>
          </div>
          <div className="kv">
            <strong>Squads</strong>
            <span>{squads.size} descobertos</span>
          </div>
          <div className="kv">
            <strong>Frases</strong>
            <span style={{ fontStyle: "italic", color: "var(--text3)" }}>"{pickPhrase(FUNNY_PHRASES, "")}"</span>
          </div>
        </div>

        <div className="ctx-card">
          <div className="t">📌 Tarefas ({open} abertas)</div>
          {tasks.slice(0, 5).map((t) => (
            <div key={t.id} className="task-row">
              <button
                className="switch" style={{ width: 22, height: 22 }}
                onClick={() => {
                  updateTask(t.id, { status: t.status === "done" ? "pending" : "done" });
                  notify({ icon: t.status === "done" ? "↩️" : "✅", text: `Task ${t.status === "done" ? "reaberta" : "concluída"}: ${t.title.slice(0, 30)}`, tone: "ok" });
                }}
              />
              <div style={{ flex: 1, minWidth: 0, fontSize: 12 }}>
                <div style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{t.title}</div>
                {t.status === "running" && <div className="bar"><i style={{ width: "46%" }} /></div>}
              </div>
              <span style={{ fontSize: 10, color: "var(--text3)" }}>{t.status}</span>
            </div>
          ))}
        </div>

        <div className="ctx-card">
          <div className="t">🗂️ Arquivos abertos</div>
          {openFiles.length === 0 && <div style={{ fontSize: 12, color: "var(--text3)" }}>Nenhum arquivo aberto.</div>}
          {openFiles.map((f) => (
            <div key={f.path} className="file-row" onClick={() => useIdeStore.getState().setView("workspace")}>
              <span style={{ color: f.dirty ? "var(--warn)" : undefined }}>{f.dirty ? "●" : "📄"}</span>
              <span>{f.name}</span>
            </div>
          ))}
        </div>

        <div className="ctx-card">
          <div className="t">🪵 Logs recentes</div>
          {lastLogs.map((l) => (
            <div key={l.id} className="log-row">
              <span className="ts">{new Date(l.time).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</span>
              <span style={{ color: toneColor(l.tone) }}>{l.text}</span>
            </div>
          ))}
          {lastLogs.length === 0 && <div style={{ fontSize: 12, color: "var(--text3)" }}>Sem logs ainda.</div>}
        </div>

        <div className="ctx-card">
          <div className="t">💡 Dica</div>
          <div style={{ fontSize: 12, lineHeight: 1.6, color: "var(--text2)" }}>
            Use <code>AddLog</code>/<code>notify</code> no fluxo de trabalho para manter este painel vivo.
            <button className="tool-btn" style={{ marginTop: 8, display: "block" }} onClick={() => { addLog({ tone: "info", text: "Dica exibida (auto)" }); notify({ icon: "💡", text: "Contexto atualizado", tone: "info" }); }}>
              Atualizar contexto
            </button>
          </div>
        </div>
      </div>
    </aside>
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