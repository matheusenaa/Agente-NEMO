import { useEffect, useState } from "react";
import { useIdeStore } from "@/store/useIdeStore";
import { THEMES } from "@/data/themes";
import { LAYOUTS } from "@/data/agents";
import { AiSettingsCard } from "./AiSettingsCard";
import { nemoApi } from "@/api/nemo";
import type { AiProfile } from "@/types/idea";
import type { Density, IdeConfig, LayoutId } from "@/types/idea";

function resetAll() {
  if (!window.confirm("Resetar TODAS as configurações da NEMO IDE?")) return;
  localStorage.removeItem("nemo-ide");
  localStorage.removeItem("nemo-user-name");
  window.location.reload();
}

const AVATARS = ["🐬", "🧠", "🎨", "🔍", "✍️", "📊", "🚀", "🛠️"];

function ProfileCard() {
  const notify = useIdeStore((s) => s.notify);
  const [profile, setProfile] = useState<AiProfile | null>(null);
  const [name, setName] = useState("");
  const [language, setLanguage] = useState("pt-BR");
  const [avatar, setAvatar] = useState("🐬");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    nemoApi
      .getProfile()
      .then((r) => {
        setProfile(r.profile);
        setName(r.profile.name ?? "");
        setLanguage(r.profile.language ?? "pt-BR");
        setAvatar(r.profile.avatar ?? "🐬");
      })
      .catch(() => undefined);
  }, []);

  const save = async () => {
    setSaving(true);
    setSaved(false);
    try {
      await nemoApi.saveProfile({ name, language, avatar });
      setProfile((p) => (p ? { ...p, name, language, avatar } : p));
      setSaved(true);
      notify({ icon: "👤", text: "Perfil salvo.", tone: "ok" });
      setTimeout(() => setSaved(false), 2500);
    } catch {
      notify({ icon: "⚠️", text: "Não foi possível salvar o perfil.", tone: "error" });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="set-card">
      <h3>👤 Perfil</h3>
      {profile && (
        <div className="set-row" style={{ alignItems: "center" }}>
          <span
            style={{
              width: 40, height: 40, borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 22, background: "var(--bg2)", border: "1px solid var(--border)",
            }}
          >
            {avatar}
          </span>
          <span style={{ color: "var(--text3)", fontSize: 12 }}>
            {profile.email || "sem e-mail"} {saved && <b style={{ color: "var(--success)" }}>· salvo ✓</b>}
          </span>
        </div>
      )}
      <div className="set-row">
        <span>Nome</span>
        <input className="hist-search" style={{ margin: 0, width: "min(280px,100%)" }} value={name} onChange={(e) => setName(e.target.value)} placeholder="Seu nome" />
      </div>
      <div className="set-row">
        <span>Idioma</span>
        <div className="seg">
          {["pt-BR", "en", "es"].map((l) => (
            <button key={l} className={`seg-btn ${language === l ? "on" : ""}`} onClick={() => setLanguage(l)}>
              {l}
            </button>
          ))}
        </div>
      </div>
      <div className="set-row">
        <span>Avatar</span>
        <div className="seg" style={{ flexWrap: "wrap" }}>
          {AVATARS.map((a) => (
            <button key={a} className={`seg-btn ${avatar === a ? "on" : ""}`} onClick={() => setAvatar(a)} style={{ fontSize: 16, padding: "4px 8px" }}>
              {a}
            </button>
          ))}
        </div>
      </div>
      <div className="set-row">
        <button className="tool-btn primary" style={{ minWidth: 120 }} onClick={save} disabled={saving}>
          {saving ? "Salvando..." : "Salvar perfil"}
        </button>
      </div>
    </div>
  );
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

        <ProfileCard />

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

        <AiSettingsCard />
      </div>
    </section>
  );
}