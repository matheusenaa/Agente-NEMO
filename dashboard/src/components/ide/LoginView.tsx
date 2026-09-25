import { useEffect, useState, type FormEvent } from "react";
import { useAuthStore } from "@/store/useAuthStore";
import { AGENT_ROSTER } from "@/data/agents";
import { AgentAvatar } from "@/components/AgentAvatar";

type Mode = "login" | "register";

interface OAuthProviderInfo {
  name: string;
  label: string;
  icon: string;
}

const OAUTH_ICONS: Record<string, string> = {
  google: "▶",
  microsoft: "▣",
  apple: "",
};

function Field(props: {
  label: string;
  type?: string;
  value: string;
  placeholder?: string;
  autoComplete?: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="auth-field">
      <span className="auth-label">{props.label}</span>
      <input
        className="auth-input"
        type={props.type ?? "text"}
        value={props.value}
        placeholder={props.placeholder ?? ""}
        autoComplete={props.autoComplete}
        onChange={(e) => props.onChange(e.target.value)}
      />
    </label>
  );
}

export function LoginView() {
  const checking = useAuthStore((s) => s.checking);
  const error = useAuthStore((s) => s.error);
  const login = useAuthStore((s) => s.login);
  const register = useAuthStore((s) => s.register);
  const clearError = useAuthStore((s) => s.clearError);

  const [mode, setMode] = useState<Mode>("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [serverOk, setServerOk] = useState(false);
  const [oauthProviders, setOauthProviders] = useState<OAuthProviderInfo[]>([]);
  const [oauthError, setOauthError] = useState("");
  const [remember, setRemember] = useState(true);
  const [confirmPassword, setConfirmPassword] = useState("");
  const [formError, setFormError] = useState("");

  useEffect(() => {
    let alive = true;
    fetch("/api/nemo/health", { cache: "no-store", credentials: "include" })
      .then((r) => r.json())
      .then((h) => alive && setServerOk(Boolean(h?.project)))
      .catch(() => alive && setServerOk(false));
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    let alive = true;
    fetch("/api/auth/oauth/status", { cache: "no-store", credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (alive && data?.providers?.length) {
          setOauthProviders(
            data.providers.map((p: { name: string; label: string }) => ({
              name: p.name,
              label: p.label ?? p.name,
              icon: OAUTH_ICONS[p.name] ?? "",
            })),
          );
        }
      })
      .catch(() => {
        /* sem OAuth não configurado — whitelist vazia */
      });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (window.location.hash === "#oauth=success") {
      void useAuthStore.getState().restore();
      setOauthError("");
      window.history.replaceState(null, "", "/");
    }
  }, []);

  const startOAuth = async (provider: string) => {
    setOauthError("");
    try {
      const res = await fetch(`/api/auth/oauth/${provider}/start`, { cache: "no-store", credentials: "include" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data?.url) window.location.assign(data.url);
      else throw new Error("URL de autorização ausente.");
    } catch (err) {
      setOauthError(`Não foi possível iniciar o login ${provider}.`);
    }
  };

  useEffect(() => () => clearError(), [clearError]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (busy) return;
    setFormError("");
    if (mode === "register" && password.length < 8) {
      setFormError("A senha deve ter pelo menos 8 caracteres.");
      return;
    }
    if (mode === "register" && password !== confirmPassword) {
      setFormError("As senhas não conferem.");
      return;
    }
    setBusy(true);
    try {
      if (mode === "login") {
        await login(email, password, remember);
      } else {
        await register(name, email, password, remember);
      }
    } finally {
      setBusy(false);
    }
  };

  const switchMode = (m: Mode) => {
    setMode(m);
    setFormError("");
    setConfirmPassword("");
    clearError();
  };

  return (
    <div className="auth-wrap">
      <div className="auth-bg" aria-hidden />

      <div className="auth-card">
        <div className="auth-brand">
          <div className="auth-logo">🐟</div>
          <div className="auth-brandname">NEMO</div>
          <div className="auth-brandsub">IDE · Agentes de IA · Ambiente privado</div>
        </div>

        <div className="auth-agent-strip">
          {AGENT_ROSTER.slice(0, 8).map((a) => (
            <div className="auth-agent" key={a.id} title={a.name}>
              <AgentAvatar id={a.id} accent={a.color} size={30} badge={a.icon} shape="round" />
            </div>
          ))}
        </div>

        <div className="auth-sep" />

        <form className="auth-form" onSubmit={submit}>
          {mode === "register" && (
            <Field
              label="Nome"
              value={name}
              placeholder="Como devemos te chamar?"
              autoComplete="name"
              onChange={setName}
            />
          )}
          <Field
            label="E-mail"
            type="email"
            value={email}
            placeholder="voce@exemplo.com"
            autoComplete="email"
            onChange={setEmail}
          />
          <Field
            label="Senha"
            type="password"
            value={password}
            placeholder={mode === "register" ? "Mínimo 8 caracteres" : "Sua senha"}
            autoComplete={mode === "register" ? "new-password" : "current-password"}
            onChange={setPassword}
          />
          {mode === "register" && (
            <Field
              label="Confirmar senha"
              type="password"
              value={confirmPassword}
              placeholder="Repita sua senha"
              autoComplete="new-password"
              onChange={setConfirmPassword}
            />
          )}

          <label className="auth-remember">
            <input type="checkbox" checked={remember} onChange={(event) => setRemember(event.target.checked)} />
            <span>Lembrar de mim</span>
          </label>

          {(formError || error) && <div className="auth-error">⚠️ {formError || error}</div>}

          <button className="auth-submit" type="submit" disabled={busy || checking}>
            {busy
              ? "Aguarde..."
              : checking
                ? "Verificando sessão..."
                : mode === "login"
                  ? "Entrar no NEMO"
                  : "Criar conta"}
          </button>
        </form>

        {oauthProviders.length > 0 && (
          <div className="oauth-block">
            <div className="oauth-sep">
              <span>ou entre com</span>
            </div>
            <div className="oauth-buttons">
              {oauthProviders.map((p) => (
                <button
                  key={p.name}
                  className="oauth-btn"
                  type="button"
                  disabled={busy}
                  onClick={() => startOAuth(p.name)}
                  title={`Entrar com ${p.label}`}
                >
                  <span className={`oauth-logo oauth-${p.name}`}>{p.icon}</span>
                  <span>{p.label}</span>
                </button>
              ))}
            </div>
            {oauthError && <div className="auth-error">⚠️ {oauthError}</div>}
          </div>
        )}

        <div className="auth-switch">
          {mode === "login" ? (
            <span>
              Ainda não tem conta?{" "}
              <button className="auth-link" onClick={() => switchMode("register")}>
                Criar conta
              </button>
            </span>
          ) : (
            <span>
              Já tem conta?{" "}
              <button className="auth-link" onClick={() => switchMode("login")}>
                Fazer login
              </button>
            </span>
          )}
        </div>

        <div className="auth-foot">
          {serverOk ? (
            <span className="auth-server ok">● servidor conectado</span>
          ) : (
            <span className="auth-server">● aguardando servidor…</span>
          )}
          <span className="auth-server">sessão protegida</span>
        </div>
      </div>
    </div>
  );
}