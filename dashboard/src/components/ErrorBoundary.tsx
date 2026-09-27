import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
  info: string;
}

/**
 * Rede de seguranca da raiz. O React 19 nao tem UI de erro padrao: qualquer
 * excecao durante o render desmonta a arvore inteira e deixa a pagina em
 * branco sem nenhuma mensagem. Este boundary mostra o erro e permite recarregar.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null, info: "" };

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[SYNOP] erro nao tratado na interface:", error, info.componentStack);
    this.setState({ error, info: info.componentStack || "" });
  }

  private reset = () => {
    this.setState({ error: null, info: "" });
  };

  render() {
    const { error, info } = this.state;
    if (!error) return this.props.children;

    return (
      <div style={styles.wrap}>
        <div style={styles.card}>
          <h1 style={styles.title}>SYNOP nao conseguiu iniciar</h1>
          <p style={styles.text}>
            Ocorreu um erro inesperado ao montar a interface. Seus dados locais continuam intactos.
          </p>
          <pre style={styles.pre}>{String(error?.message || error)}</pre>
          {info ? <pre style={styles.trace}>{info.trim().split("\n").slice(0, 8).join("\n")}</pre> : null}
          <div style={styles.actions}>
            <button style={styles.primary} onClick={() => window.location.reload()}>
              Recarregar
            </button>
            <button style={styles.secondary} onClick={this.reset}>
              Tentar novamente
            </button>
            <button
              style={styles.secondary}
              onClick={() => {
                try {
                  localStorage.clear();
                  sessionStorage.clear();
                } catch {
                  /* storage indisponivel */
                }
                if ("serviceWorker" in navigator) {
                  navigator.serviceWorker.getRegistrations?.().then((regs) => {
                    regs.forEach((r) => r.unregister());
                  });
                }
                window.location.reload();
              }}
            >
              Limpar cache e recarregar
            </button>
          </div>
        </div>
      </div>
    );
  }
}

const styles: Record<string, React.CSSProperties> = {
  wrap: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "#07080f",
    color: "#e6e9f2",
    fontFamily: "Inter, system-ui, -apple-system, sans-serif",
    padding: 24,
  },
  card: {
    maxWidth: 720,
    width: "100%",
    background: "#0e1120",
    border: "1px solid #1e2a44",
    borderRadius: 12,
    padding: 24,
  },
  title: { margin: "0 0 8px", fontSize: 20, color: "#5eead4" },
  text: { margin: "0 0 16px", fontSize: 14, lineHeight: 1.6, color: "#a7b0c7" },
  pre: {
    background: "#070810",
    border: "1px solid #1e2a44",
    borderRadius: 8,
    padding: 12,
    fontSize: 12,
    overflowX: "auto",
    color: "#fca5a5",
    margin: "0 0 12px",
  },
  trace: {
    background: "#070810",
    border: "1px solid #1e2a44",
    borderRadius: 8,
    padding: 12,
    fontSize: 11,
    overflowX: "auto",
    color: "#7dd3fc",
    margin: "0 0 16px",
    maxHeight: 160,
  },
  actions: { display: "flex", flexWrap: "wrap", gap: 10 },
  primary: {
    background: "#0066cc",
    color: "#fff",
    border: 0,
    borderRadius: 8,
    padding: "10px 18px",
    fontSize: 14,
    cursor: "pointer",
  },
  secondary: {
    background: "transparent",
    color: "#5eead4",
    border: "1px solid #1e2a44",
    borderRadius: 8,
    padding: "10px 18px",
    fontSize: 14,
    cursor: "pointer",
  },
};

export default ErrorBoundary;
