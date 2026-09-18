import { FileExplorer } from "./FileExplorer";
import { CodeEditor } from "./CodeEditor";

export function WorkspaceView() {
  return (
    <section className="view-area">
      <div className="workspace" style={{ flex: 1 }}>
        <FileExplorer />
        <CodeEditor />
      </div>
    </section>
  );
}