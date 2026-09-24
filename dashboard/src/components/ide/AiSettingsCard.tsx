import { useEffect, useState } from "react";
import { nemoApi } from "@/api/nemo";
import { useIdeStore } from "@/store/useIdeStore";
import type { AiConfigResponse, AiProviderInfo } from "@/types/idea";

const inputStyle: React.CSSProperties = {
  background: "var(--bg3)",
  color: "var(--text1)",
  border: "1px solid var(--border)",
  borderRadius: 7,
  padding: "6px 10px",
  fontSize: "calc(var(--fs) - 2px)",
  flex: 1,
  minWidth: 0,
};

const labelStyle: React.CSSProperties = { fontSize: "calc(var(--fs) - 3px)", color: "var(--text2)", minWidth: 110, display: "inline-block" };

/** Central de IA (missão §39/45): provedor padrão, modelo e API Keys do usuário. */
export function AiSettingsCard() {
  const addLog = useIdeStore((s) => s.addLog);
  const notify = useIdeStore((s) => s.notify);

  const [data, setData] = useState<AiConfigResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [provider, setProvider] = useState("");
  const [model, setModel] = useState("");
  const [keys, setKeys] = useState<Record<string, { key: string; model: string }>>({});
  const [testResult, setTestResult] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState("");

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function load() {
    setLoading(true);
    try {
      const cfg = await nemoApi.aiConfig();
      setData(cfg);
      setProvider(cfg.user.settings.default_provider ?? cfg.system.default_provider ?? "");
      setModel(cfg.user.settings.default_model ?? "");
    } catch {
      addLog({ tone: "error", text: "Falha ao carregar a Central de IA" });
      notify({ icon: "🤖", text: "Não foi possível carregar a Central de IA", tone: "error" });
    } finally {
      setLoading(false);
    }
  }

  async function saveDefaults() {
    setBusy("config");
    try {
      await nemoApi.saveAiConfig({ default_provider: provider || undefined, default_model: model || undefined });
      addLog({ tone: "ok", text: `IA padrão: ${provider || "sistema"} / ${model || "padrão"}` });
      notify({ icon: "🤖", text: "Configuração de IA salva", tone: "ok" });
      await load();
    } catch {
      notify({ icon: "🤖", text: "Falha ao salvar configuração", tone: "error" });
    } finally {
      setBusy("");
    }
  }

  async function saveKey(p: AiProviderInfo) {
    const entry = keys[p.id];
    if (!entry?.key?.trim()) {
      notify({ icon: "🔑", text: "Informe a chave para salvar", tone: "warn" });
      return;
    }
    setBusy(`save-${p.id}`);
    try {
      const res = await nemoApi.saveAiKey(p.id, entry.key.trim(), entry.model || undefined);
      setTestResult((prev) => ({ ...prev, [p.id]: res.test.ok ? "✓ Conexão funcionando." : res.test.message }));
      addLog({ tone: res.verified ? "ok" : "warn", text: `Chave ${p.name} ${res.verified ? "verificada" : "salva (verificação pendente)"}` });
      notify({ icon: "🔑", text: `Chave ${p.name} salva`, tone: res.verified ? "ok" : "warn" });
      await load();
    } catch {
      notify({ icon: "🔑", text: `Falha ao salvar chave do ${p.name}`, tone: "error" });
    } finally {
      setBusy("");
    }
  }

  async function testKey(p: AiProviderInfo) {
    setBusy(`test-${p.id}`);
    try {
      const entry = keys[p.id];
      const res = await nemoApi.testAiKey(p.id, entry?.key || undefined, entry?.model || undefined);
      setTestResult((prev) => ({ ...prev, [p.id]: res.message }));
      addLog({ tone: res.ok ? "ok" : "warn", text: `Conexão ${p.name}: ${res.message}` });
    } catch {
      setTestResult((prev) => ({ ...prev, [p.id]: "✕ Não foi possível testar." }));
    } finally {
      setBusy("");
    }
  }

  async function removeKey(p: AiProviderInfo) {
    if (!window.confirm(`Remover a chave do ${p.name}?`)) return;
    setBusy(`del-${p.id}`);
    try {
      await nemoApi.deleteAiKey(p.id);
      setKeys((prev) => {
        const next = { ...prev };
        delete next[p.id];
        return next;
      });
      notify({ icon: "🔑", text: `Chave ${p.name} removida`, tone: "warn" });
      await load();
    } catch {
      notify({ icon: "🔑", text: `Falha ao remover chave do ${p.name}`, tone: "error" });
    } finally {
      setBusy("");
    }
  }

  if (loading && !data) {
    return (
      <div className="set-card">
        <h3>🤖 Inteligência Artificial</h3>
        <div style={{ color: "var(--text2)", fontSize: 13 }}>Carregando Central de IA…</div>
      </div>
    );
  }

  const providers = data?.system.providers ?? [];
  const storedKeys: Record<string, string> = {};
  for (const k of data?.user.keys ?? []) storedKeys[k.provider] = k.masked;
  const backend = data?.system.store_backend ?? "local";

  return (
    <div className="set-card">
      <h3>🤖 Inteligência Artificial</h3>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginBottom: 10, fontSize: 12, color: "var(--text2)" }}>
        <span>Banco: <b style={{ color: backend === "supabase" ? "var(--ok)" : "var(--text2)" }}>{backend === "supabase" ? "🟢 Supabase" : "local (_data)"}</b></span>
        <span>Busca web: <b>{data?.system.web_search.join(", ") || "—"}</b></span>
        <span>Criptografia: <b>{data?.system.encryption ? "🟢 ativa" : "🔴 indisponível"}</b></span>
      </div>

      <div className="set-row">
        <span style={labelStyle}>Provedor padrão</span>
        <div className="seg" style={{ flex: 1 }}>
          {providers.map((p) => (
            <button key={p.id} className={`seg-btn ${provider === p.id ? "on" : ""}`} onClick={() => { setProvider(p.id); if (!model) setModel(p.models[0] ?? ""); }}>
              {p.icon} {p.name}
            </button>
          ))}
        </div>
      </div>

      <div className="set-row">
        <span style={labelStyle}>Modelo padrão</span>
        <select
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="seg-btn"
          style={inputStyle}
        >
          {(() => {
            const active = providers.find((p) => p.id === provider);
            const models = active?.models?.length ? active.models : (provider === "openrouter" ? ["deepseek/deepseek-chat"] : []);
            return (
              <>
                <option value="">Padrão da categoria</option>
                {models.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </>
            );
          })()}
        </select>
        <button className="tool-btn primary" disabled={busy === "config"} onClick={saveDefaults}>💾 Salvar padrão</button>
      </div>

      <div style={{ marginTop: 10 }}>
        <h4 style={{ fontSize: "calc(var(--fs) - 1px)", margin: "8px 0 6px", color: "var(--text2)" }}>Minhas API Keys</h4>
        {providers.map((p) => {
          const entry = keys[p.id] ?? { key: "", model: "" };
          const stored = storedKeys[p.id];
          return (
            <div key={p.id} style={{ borderTop: "1px solid var(--border)", padding: "10px 0" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                <span style={{ minWidth: 130, fontWeight: 600 }}>{p.icon} {p.name}</span>
                {p.configured && <span className="seg-btn" style={{ cursor: "default", padding: "3px 8px", color: "var(--ok)" }}>chave do sistema</span>}
                {stored ? (
                  <code style={{ fontSize: 12, color: "var(--text2)" }}>{stored}</code>
                ) : (
                  <span style={{ fontSize: 12, color: "var(--text3)" }}>sem chave própria</span>
                )}
              </div>
              <div style={{ display: "flex", gap: 8, marginTop: 6, flexWrap: "wrap", alignItems: "center" }}>
                <input
                  type="password"
                  placeholder="API Key (nunca é exibida completa)"
                  value={entry.key}
                  style={inputStyle}
                  onChange={(e) => setKeys((prev) => ({ ...prev, [p.id]: { ...entry, key: e.target.value } }))}
                />
                <input
                  type="text"
                  placeholder="Modelo (opcional)"
                  value={entry.model}
                  style={{ ...inputStyle, flex: "0 0 160px" }}
                  onChange={(e) => setKeys((prev) => ({ ...prev, [p.id]: { ...entry, model: e.target.value } }))}
                />
                <button className="tool-btn" disabled={busy === `save-${p.id}`} onClick={() => saveKey(p)}>💾 Salvar</button>
                <button className="tool-btn" disabled={busy === `test-${p.id}`} onClick={() => testKey(p)}>📡 Testar</button>
                {stored && <button className="tool-btn" style={{ color: "var(--danger)", borderColor: "var(--danger)" }} disabled={busy === `del-${p.id}`} onClick={() => removeKey(p)}>🗑️ Remover</button>}
              </div>
              {testResult[p.id] && <div style={{ fontSize: 12, marginTop: 4, color: testResult[p.id].startsWith("✓") ? "var(--ok)" : "var(--danger)" }}>{testResult[p.id]}</div>}
            </div>
          );
        })}
      </div>

      <div style={{ marginTop: 8, fontSize: 12, color: "var(--text3)" }}>
        🔒 Suas chaves são criptografadas antes de serem armazenadas e nunca aparecem nos logs, no Git ou no frontend (somente a máscara).
      </div>
    </div>
  );
}