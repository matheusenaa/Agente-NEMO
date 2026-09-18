import { useEffect } from "react";
import { useIdeStore } from "@/store/useIdeStore";
import { nemoApi } from "@/api/nemo";
import type { FileNode } from "@/types/idea";

const FILE_ICONS: Record<string, string> = {
  ts: "🟦", tsx: "🟦", js: "🟨", jsx: "🟨", mjs: "🟨",
  py: "🐍", json: "🧾", css: "🎨", scss: "🎨", html: "🌐",
  md: "📄", yml: "🗂️", yaml: "🗂️", txt: "📝", sh: "⌨️",
};

export function FileExplorer() {
  const workspacePath = useIdeStore((s) => s.workspacePath);
  const setWorkspacePath = useIdeStore((s) => s.setWorkspacePath);
  const currentDir = useIdeStore((s) => s.currentDirCache);
  const setCurrentDir = useIdeStore((s) => s.setCurrentDir);
  const openFileInEditor = useIdeStore((s) => s.openFileInEditor);
  const notify = useIdeStore((s) => s.notify);

  async function load(dir: string) {
    try {
      const res = await nemoApi.listFiles(dir);
      setWorkspacePath(res.path);
      setCurrentDir(res.entries);
      useIdeStore.getState().addLog({ tone: "info", text: `Navegando: ${res.path || "projeto"}` });
    } catch {
      notify({ icon: "⚠️", text: "Falha ao listar arquivos (servidor offline)", tone: "warn" });
      setWorkspacePath(dir);
      setCurrentDir([]);
    }
  }

  useEffect(() => {
    load("");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function open(node: FileNode) {
    if (node.type === "dir") {
      await load(node.path);
      return;
    }
    try {
      const file = await nemoApi.readFile(node.path);
      openFileInEditor(file);
    } catch {
      notify({ icon: "⚠️", text: `Não foi possível abrir ${node.name}`, tone: "warn" });
    }
  }

  const crumbs = workspacePath ? workspacePath.split(/[/\\]/).filter(Boolean) : [];
  const goCrumb = (idx: number) => load(crumbs.slice(0, idx + 1).join("\\"));

  return (
    <div className="file-tree">
      <div className="path-crumbs" style={{ borderBottom: "1px solid var(--border)" }}>
        <span className="crumb" onClick={() => load("")}>🏠 NEMO</span>
        {crumbs.map((c, i) => (
          <span key={i}>
            <span style={{ color: "var(--text3)" }}>›</span>
            <span className="crumb" onClick={() => goCrumb(i)}>{c}</span>
          </span>
        ))}
      </div>
      <div className="ft-head">
        <span className="rail-title">Explorador</span>
        <button className="icon-btn" title="Atualizar" style={{ fontSize: 13, width: 26, height: 26 }} onClick={() => load(workspacePath)}>
          ↻
        </button>
      </div>
      <div style={{ flex: 1, overflowY: "auto", padding: "4px 8px" }}>
        {currentDir.length === 0 && (
          <div style={{ padding: 10, color: "var(--text3)", fontSize: 13 }}>
            Pasta vazia ou servidor offline.
            <br />
            Inicie: <code style={{ color: "var(--accentText)" }}>python nemo_server.py</code>
          </div>
        )}
        {currentDir.map((node) => {
          const ext = (node.name.split(".").pop() ?? "").toLowerCase();
          const icon = node.type === "dir" ? "📁" : FILE_ICONS[ext] ?? "📄";
          return (
            <div key={node.path} className={`fnode ${node.type === "dir" ? "dir" : ""}`} onClick={() => open(node)} title={node.path}>
              <span>{icon}</span>
              <span>{node.name}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}