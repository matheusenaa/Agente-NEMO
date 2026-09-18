import { useIdeStore } from "@/store/useIdeStore";
import { THEMES } from "@/data/themes";
import { LAYOUTS } from "@/data/agents";
import type { Density, IdeConfig, LayoutId } from "@/types/idea";

function resetAll() {
  if (!window.confirm("Resetar TODAS as configurações da NEMO IDE?")) return;
  localStorage.removeItem("nemo-ide");
  localStorage.removeItem("nemo-user-name");
  window.location.reload();
}

export function SettingsView() {
  const config = useIdeStore((s) => s.config);
  const setConfig = useIdeStore((s) => s.setConfig);
  const addLog = useIdeStore((s) => s.addLog);
  const addHistory = useIdeStore((s) => s.addHistory);

  const apply = <K extends keyof IdeConfig>(key: K, value: IdeConfig[K]) => {
    setConfig({ [key]: value } as Partial<IdeConfig>);
    addLog({ tone: "ok", text: `Config alterada: ${String(key)} → ${String(value)}` });
    addHistory({ kind: "config", title: String(key), detail: String(value) });
  };

  return (
    <section className="view-area">
      <div className="settings-wrap">
        <h2 style={{ margin: "0 0 12px", fontSize: 20 }}>⚙️ Configurações</h2>

        <div className="set-card">
          <h3>🎨 Tema</h3>
          <div className="theme-grid">
            {THEMES.map((t) => (
              <button key={t.id} className={`theme-cell ${config.theme === t.id ? "on" : ""}`} onClick={() => apply("theme", t.id)}>
                <div className="swatch" style={{ background: t.accent }}>
                  <span style={{ marginRight: 4 }}>{t.emoji}</span>
                  <span>{t.name}</span>
                </div>
                <div style={{ fontSize: 11, color: "var(--text2)" }}>{t.desc}</div>
              </button>
            ))}
          </div>
        </div>

        <div className="set-card">
          <h3>🧱 Layout</h3>
          <div className="layout-grid">
            {LAYOUTS.map((l) => (
              <button key={l.id} className={`layout-cell ${config.layout === l.id ? "on" : ""}`} onClick={() => apply("layout", l.id as LayoutId)}>
                <b>{l.label}</b>
                <small>{l.desc}</small>
              </button>
            ))}
          </div>
          <div style={{ marginTop: 8, fontSize: 12, color: "var(--text3)" }}>
            Atualmente no layout <b>PRO MAX (IDE profissional)</b>. Os demais estarão disponíveis em breve.
          </div>
        </div>

        <div className="set-card">
          <h3>📐 Aparência</h3>
          <div className="set-row">
            <span>Densidade</span>
            <div className="seg">
              {(["compact", "comfortable", "spacious"] as Density[]).map((d) => (
                <button key={d} className={`seg-btn ${config.density === d ? "on" : ""}`} onClick={() => apply("density", d)}>
                  {d}
                </button>
              ))}
            </div>
          </div>
          <div className="set-row">
            <span>Tamanho da fonte ({config.fontSize}px)</span>
            <div className="seg">
              <button className="seg-btn" onClick={() => apply("fontSize", Math.max(12, config.fontSize - 1))}>A−</button>
              <button className="seg-btn" onClick={() => apply("fontSize", Math.min(20, config.fontSize + 1))}>A+</button>
            </div>
          </div>
          <div className="set-row">
            <span>Animações</span>
            <button className={`switch ${config.animations ? "on" : ""}`} onClick={() => apply("animations", !config.animations)} />
          </div>
          <div className="set-row">
            <span>Timestamps no chat</span>
            <button className={`switch ${config.showTimestamps ? "on" : ""}`} onClick={() => apply("showTimestamps", !config.showTimestamps)} />
          </div>
          <div className="set-row">
            <span>Frases divertidas de status</span>
            <button className={`switch ${config.funnyStatus ? "on" : ""}`} onClick={() => apply("funnyStatus", !config.funnyStatus)} />
          </div>
        </div>

        <div className="set-card">
          <h3>💾 Sessão</h3>
          <div className="set-row">
            <span>Configurações do tema/densidade são persistidas automaticamente.</span>
          </div>
          <div className="set-row">
            <button className="tool-btn" style={{ color: "var(--danger)", borderColor: "var(--danger)" }} onClick={resetAll}>
              Resetar tudo
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}