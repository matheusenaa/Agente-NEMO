import { useEffect, useState, type FormEvent } from "react";
import { useAuthStore } from "@/store/useAuthStore";
import { AGENT_ROSTER } from "@/data/agents";
import { AgentAvatar } from "@/components/AgentAvatar";

type Mode = "login" | "register";

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

  useEffect(() => {
    let alive = true;
    fetch("/api/nemo/health", { cache: "no-store" })
      .then((r) => r.json())
      .then((h) => alive && setServerOk(Boolean(h?.project)))
      .catch(() => alive && setServerOk(false));
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => () => clearError(), [clearError]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(name, email, password);
      }
    } finally {
      setBusy(false);
    }
  };

  const switchMode = (m: Mode) => {
    setMode(m);
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
            placeholder={mode === "register" ? "Mínimo 6 caracteres" : "Sua senha"}
            autoComplete={mode === "register" ? "new-password" : "current-password"}
            onChange={setPassword}
          />

          {error && <div className="auth-error">⚠️ {error}</div>}

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