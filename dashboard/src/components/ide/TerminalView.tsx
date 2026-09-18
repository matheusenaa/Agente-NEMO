import { useRef, useState } from "react";
import { useIdeStore } from "@/store/useIdeStore";
import { nemoApi } from "@/api/nemo";

export function TerminalView() {
  const termLines = useIdeStore((s) => s.termLines);
  const pushTerm = useIdeStore((s) => s.pushTerm);
  const clearTerm = useIdeStore((s) => s.clearTerm);
  const addLog = useIdeStore((s) => s.addLog);
  const [cmd, setCmd] = useState("");
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<{ command: string; result: Awaited<ReturnType<typeof nemoApi.runCommand>> } | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  async function run(force = false) {
    const command = cmd.trim();
    if (!command) return;
    setCmd("");
    setBusy(true);
    try {
      const res = await nemoApi.runCommand(command, force);
      if (res.requires_confirm && !force) {
        setPending({ command, result: res });
        return;
      }
      if (res.ok) {
        pushTerm({ tone: "ok", text: `✓ ${command}` });
        if (res.stdout) pushTerm({ tone: "ok", text: res.stdout });
        addLog({ tone: "ok", text: `Terminal: ${command} → OK` });
      } else {
        pushTerm({ tone: "err", text: `✗ ${command}` });
        if (res.stderr) pushTerm({ tone: "err", text: res.stderr });
        if (res.stdout) pushTerm({ tone: "out", text: res.stdout });
        addLog({ tone: "error", text: `Terminal: ${command} → falhou (code ${res.code ?? "?"})` });
      }
    } catch (err) {
      pushTerm({ tone: "err", text: `Falha ao executar: ${(err as Error).message}` });
    } finally {
      setBusy(false);
      setPending(null);
      requestAnimationFrame(() => endRef.current?.scrollIntoView({ behavior: "smooth" }));
    }
  }

  return (
    <section className="view-area">
      <div className="term-wrap">
        <div style={{ fontSize: 12, color: "var(--text3)", marginBottom: 4, display: "flex", gap: 6 }}>
          <span>🖥️</span>
          <span>Terminal NEMO (seguro — comandos perigosos bloqueados por padrão)</span>
          <button className="tool-btn" onClick={clearTerm} style={{ marginLeft: "auto", padding: "3px 10px" }}>Limpar</button>
        </div>
        <div style={{ flex: 1, overflowY: "auto" }}>
          {termLines.map((l) => (
            <div key={l.id} className="term-line">
              {l.tone === "ok" && <span className="ok">{l.text}</span>}
              {l.tone === "err" && <span className="err">{l.text}</span>}
              {l.tone === "info" && <span className="out" style={{ color: "var(--accentText)" }}>{l.text}</span>}
              {l.tone === "out" && <span className="out">{l.text}</span>}
            </div>
          ))}
          <div ref={endRef} />
        </div>
        {pending && (
          <div className="destructive-warn">
            <span>⚠️ {pending.result.reason}</span>
            <button className="tool-btn" onClick={() => run(true)}>Confirmar execução</button>
            <button className="tool-btn" onClick={() => setPending(null)}>Cancelar</button>
          </div>
        )}
        <div className="term-inputrow">
          <input
            className="term-in"
            value={cmd}
            placeholder="Digite um comando (ex: python nemo_server.py)..."
            onChange={(e) => setCmd(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !busy) run(); }}
            disabled={busy}
          />
          <button className="tool-btn primary" onClick={() => run()} disabled={busy || !cmd.trim()}>
            {busy ? "⏳" : "▶ Executar"}
          </button>
        </div>
      </div>
    </section>
  );
}