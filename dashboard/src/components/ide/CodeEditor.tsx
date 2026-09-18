import { useEffect, useRef } from "react";
import { useIdeStore } from "@/store/useIdeStore";
import { nemoApi } from "@/api/nemo";
import type { OpenFile } from "@/types/idea";
import { highlight } from "@/lib/syntax";

function languageOf(path: string): string {
  const ext = (path.split(".").pop() ?? "").toLowerCase();
  return ext;
}

export function CodeEditor() {
  const openFiles = useIdeStore((s) => s.openFiles);
  const activeFile = useIdeStore((s) => s.activeFile);
  const closeFile = useIdeStore((s) => s.closeFile);
  const setActiveFile = useIdeStore((s) => s.setActiveFile);
  const updateFileContent = useIdeStore((s) => s.updateFileContent);
  const notify = useIdeStore((s) => s.notify);
  const pushTerm = useIdeStore((s) => s.pushTerm);
  const taRef = useRef<HTMLTextAreaElement>(null);
  const preRef = useRef<HTMLPreElement>(null);

  const current: OpenFile | undefined = openFiles.find((f) => f.path === activeFile) ?? openFiles[0];

  function syncScroll() {
    const ta = taRef.current;
    const pre = preRef.current;
    if (!ta || !pre) return;
    pre.scrollTop = ta.scrollTop;
    pre.scrollLeft = ta.scrollLeft;
  }

  useEffect(() => {
    syncScroll();
  }, [activeFile]);

  async function save(f: OpenFile) {
    if (!f.dirty) return;
    try {
      await nemoApi.saveFile(f.path, f.content);
      useIdeStore.setState((s) => ({
        openFiles: s.openFiles.map((x) => (x.path === f.path ? { ...x, dirty: false } : x)),
      }));
      pushTerm({ tone: "ok", text: `✓ Salvo [${f.path}]` });
      notify({ icon: "💾", text: `Salvo: ${baseName(f.path)}`, tone: "ok" });
      useIdeStore.getState().addLog({ tone: "ok", text: `Arquivo salvo: ${f.path}` });
      useIdeStore.getState().addHistory({ kind: "file", title: f.path, detail: "Arquivo salvo" });
    } catch {
      notify({ icon: "⚠️", text: `Falha ao salvar ${f.path}`, tone: "error" });
      pushTerm({ tone: "err", text: `✗ Erro ao salvar [${f.path}]` });
    }
  }

  function runBackup(f: OpenFile) {
    useIdeStore.getState().updateFileContent(f.path, f.content);
    useIdeStore.getState().addLog({ tone: "info", text: `Backup momentâneo de ${f.path} gerado no estado` });
    pushTerm({ tone: "info", text: `Backup de ${f.path} criado (snapshot em memória)` });
  }

  return (
    <div className="editor-stage">
      {openFiles.length === 0 ? (
        <div className="editor-empty">
          <div style={{ fontSize: 40, opacity: 0.5 }}>📄</div>
          <div>Nenhum arquivo aberto</div>
          <div style={{ fontSize: 13 }}>Use o explorador à esquerda para abrir arquivos do projeto.</div>
        </div>
      ) : (
        <>
          <div className="editor-tabs">
            {openFiles.map((f) => (
              <div key={f.path} className={`editor-tab ${current?.path === f.path ? "on" : ""}`} onClick={() => setActiveFile(f.path)}>
                <span>{iconOf(f.path)}</span>
                <span>{baseName(f.path)}</span>
                {f.dirty && <span style={{ color: "var(--warn)" }}>●</span>}
                <button
                  className="close"
                  onClick={(e) => {
                    e.stopPropagation();
                    closeFile(f.path);
                  }}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>

          <div className="editor-toolbar">
            <span style={{ color: "var(--text3)", fontSize: 12, marginRight: "auto" }}>{current.path}</span>
            <button className="tool-btn" onClick={() => save(current)} disabled={!current.dirty}>💾 Salvar</button>
            <button className="tool-btn" onClick={() => runBackup(current)}>🗃️ Backup</button>
            <button className="tool-btn" onClick={() => taRef.current?.focus()}>✏️ Editar</button>
          </div>

          <div className="editor-body" key={current.path}>
            <div className="gut">
              {Array.from({ length: countLines(current.content) }, (_, i) => i + 1).join("\n")}
            </div>
            <pre
              ref={preRef}
              className="code-pre"
              dangerouslySetInnerHTML={{ __html: highlight(current.content, languageOf(current.path)) }}
            />
            <textarea
              ref={taRef}
              className="code-ta"
              spellCheck={false}
              autoCapitalize="off"
              autoComplete="off"
              value={current.content}
              onChange={(e) => updateFileContent(current.path, e.target.value)}
              onScroll={() => syncScroll()}
              onKeyDown={(e) => {
                if (e.key === "Tab") {
                  e.preventDefault();
                  const el = e.currentTarget;
                  const { selectionStart, selectionEnd, value } = el;
                  const next = value.slice(0, selectionStart) + "  " + value.slice(selectionEnd);
                  updateFileContent(current.path, next);
                  requestAnimationFrame(() => {
                    el.selectionStart = el.selectionEnd = selectionStart + 2;
                  });
                }
              }}
            />
          </div>
        </>
      )}
    </div>
  );
}

function baseName(p: string): string {
  return p.split(/[/\\]/).pop() ?? p;
}

function iconOf(p: string): string {
  const ext = (p.split(".").pop() ?? "").toLowerCase();
  const map: Record<string, string> = {
    ts: "🟦", tsx: "🟦", js: "🟨", py: "🐍", json: "🧾", css: "🎨", html: "🌐", md: "📄", yaml: "🗂️", yml: "🗂️", txt: "📝",
  };
  return map[ext] ?? "📄";
}

function countLines(content: string): number {
  return Math.max(1, content.split("\n").length);
}