import { create } from "zustand";
import { persist } from "zustand/middleware";
import type {
  ChatMessage, FileNode, HistoryItem, IdeConfig, LiveStatus, LogEntry,
  NotifItem, OpenFile, TaskItem, TermLine, ViewId,
} from "@/types/idea";
import { getAgent } from "@/data/agents";

let counter = 0;
const uid = (prefix = "id") => `${prefix}-${Date.now().toString(36)}-${++counter}`;

export const DEFAULT_CONFIG: IdeConfig = {
  theme: "ocean",
  layout: "ide",
  fontSize: 14,
  density: "comfortable",
  animations: true,
  showTimestamps: true,
  funnyStatus: true,
  favAgents: ["nemo"],
  language: "pt-BR",
};

interface IdeStore {
  // config
  config: IdeConfig;
  setConfig: (patch: Partial<IdeConfig>) => void;

  // navegação
  activeView: ViewId;
  setView: (v: ViewId) => void;

  // painéis
  rightOpen: boolean;
  bottomOpen: boolean;
  leftOpen: boolean;
  toggleRight: (open?: boolean) => void;
  toggleBottom: (open?: boolean) => void;
  toggleLeft: (open?: boolean) => void;

  // agentes
  activeAgentId: string;
  setActiveAgent: (id: string) => void;
  liveStatus: LiveStatus;
  setLiveStatus: (patch: Partial<LiveStatus>) => void;

  // chat
  messages: ChatMessage[];
  addUserMessage: (content: string) => string;
  insertAgentMessage: (m: Omit<ChatMessage, "id" | "time" | "status">) => string;
  patchMessage: (id: string, patch: Partial<ChatMessage>) => void;

  // workspace
  workspacePath: string;
  setWorkspacePath: (p: string) => void;
  openFiles: OpenFile[];
  activeFile: string | null;
  openFileInEditor: (f: OpenFile) => void;
  closeFile: (path: string) => void;
  setActiveFile: (path: string | null) => void;
  updateFileContent: (path: string, content: string) => void;
  currentDirCache: FileNode[];
  setCurrentDir: (nodes: FileNode[]) => void;

  // terminal
  termLines: TermLine[];
  pushTerm: (line: Omit<TermLine, "id">) => void;
  clearTerm: () => void;

  // tasks
  tasks: TaskItem[];
  addTask: (t: { title: string; priority?: TaskItem["priority"]; agentId?: string }) => string;
  updateTask: (id: string, patch: Partial<TaskItem>) => void;

  // logs
  logs: LogEntry[];
  addLog: (t: Omit<LogEntry, "id" | "time">) => void;

  // notifications
  notifications: NotifItem[];
  notify: (n: { icon?: string; text: string; tone?: NotifItem["tone"] }) => void;
  dismissNotif: (id: string) => void;

  // history
  history: HistoryItem[];
  addHistory: (h: Omit<HistoryItem, "id" | "time">) => void;
}

export const useIdeStore = create<IdeStore>()(
  persist(
    (set, get) => ({
      config: DEFAULT_CONFIG,
      setConfig: (patch) => set((s) => ({ config: { ...s.config, ...patch } })),

      activeView: "chat",
      setView: (v) => set({ activeView: v }),

      rightOpen: true,
      bottomOpen: false,
      leftOpen: true,
      toggleRight: (open) => set((s) => ({ rightOpen: open ?? !s.rightOpen })),
      toggleBottom: (open) => set((s) => ({ bottomOpen: open ?? !s.bottomOpen })),
      toggleLeft: (open) => set((s) => ({ leftOpen: open ?? !s.leftOpen })),

      activeAgentId: "nemo",
      setActiveAgent: (id) => {
        set({ activeAgentId: id });
        get().addLog({ tone: "agent", agentId: id, text: `${getAgent(id).name} selecionado no chat` });
      },
      liveStatus: { agentId: "nemo", label: "🟢 Online", phrase: "", busy: false },
      setLiveStatus: (patch) => set((s) => ({ liveStatus: { ...s.liveStatus, ...patch } })),

      messages: [
        {
          id: uid("msg"),
          role: "agent",
          agentId: "nemo",
          content:
            "Bom dia! 👋 Sou o **NEMO**, coordenador da sua equipe de agentes.\n\nO que vamos resolver hoje?\n\n- `Analise meus gastos e encontre duplicados` (financeiro + dados)\n- `Monte um relatório do Vasco` (pesquisa + redação)\n- `Abra os arquivos do projeto` (workspace)\n\nÉ só conversar — eu delego, executo, valido e te trago o resultado. 🐟",
          time: Date.now(),
          status: "done",
        },
      ],
      addUserMessage: (content) => {
        const id = uid("msg");
        set((s) => ({
          messages: [...s.messages, { id, role: "user", agentId: "user", content, time: Date.now(), status: "done" }],
        }));
        return id;
      },
      insertAgentMessage: (m) => {
        const id = uid("msg");
        set((s) => ({
          messages: [...s.messages, { ...m, id, time: Date.now(), status: "typing", phases: [] }],
        }));
        return id;
      },
      patchMessage: (id, patch) =>
        set((s) => ({ messages: s.messages.map((m) => (m.id === id ? { ...m, ...patch } : m)) })),

      workspacePath: "",
      setWorkspacePath: (p) => set({ workspacePath: p }),
      openFiles: [],
      activeFile: null,
      openFileInEditor: (f) => {
        set((s) => {
          const exists = s.openFiles.some((x) => x.path === f.path);
          return {
            openFiles: exists ? s.openFiles.map((x) => (x.path === f.path ? { ...x, content: f.content } : x)) : [...s.openFiles, f],
            activeFile: f.path,
          };
        });
        get().addLog({ tone: "ok", text: `Aberto: ${f.path}` });
        get().addHistory({ kind: "file", title: f.path, detail: "Arquivo aberto no editor" });
      },
      closeFile: (path) =>
        set((s) => {
          const remaining = s.openFiles.filter((f) => f.path !== path);
          return {
            openFiles: remaining,
            activeFile: s.activeFile === path ? (remaining.length ? remaining[remaining.length - 1].path : null) : s.activeFile,
          };
        }),
      setActiveFile: (path) => set({ activeFile: path }),
      updateFileContent: (path, content) =>
        set((s) => ({ openFiles: s.openFiles.map((f) => (f.path === path ? { ...f, content, dirty: true } : f)) })),
      currentDirCache: [],
      setCurrentDir: (nodes) => set({ currentDirCache: nodes }),

      termLines: [
        { id: uid("term"), tone: "info", text: "NEMO IDE terminal — bem-vindo! Rode comando seguros, ex: `dir` ou `python nemo_server.py`." },
      ],
      pushTerm: (line) => set((s) => ({ termLines: [...s.termLines.slice(-800), { ...line, id: uid("term") }] })),
      clearTerm: () => set({ termLines: [] }),

      tasks: [],
      addTask: (t) => {
        const id = uid("task");
        const task: TaskItem = { id, title: t.title, priority: t.priority ?? "normal", agentId: t.agentId ?? "nemo", status: "pending", createdAt: Date.now() };
        set((s) => ({ tasks: [task, ...s.tasks] }));
        get().addLog({ tone: "info", text: `Nova tarefa: ${t.title}` });
        return id;
      },
      updateTask: (id, patch) =>
        set((s) => ({ tasks: s.tasks.map((t) => (t.id === id ? { ...t, ...patch, doneAt: patch.status === "done" ? Date.now() : t.doneAt } : t)) })),

      logs: [],
      addLog: (t) =>
        set((s) => ({ logs: [...s.logs.slice(-600), { ...t, id: uid("log"), time: Date.now() }] })),

      notifications: [],
      notify: (n) => {
        const item: NotifItem = { id: uid("notif"), icon: n.icon ?? "🐟", text: n.text, tone: n.tone ?? "info", time: Date.now() };
        set((s) => ({ notifications: [...s.notifications.slice(-20), item] }));
      },
      dismissNotif: (id) => set((s) => ({ notifications: s.notifications.filter((n) => n.id !== id) })),

      history: [],
      addHistory: (h) => set((s) => ({ history: [{ ...h, id: uid("hist"), time: Date.now() }, ...s.history].slice(0, 300) })),
    }),
    {
      name: "nemo-ide",
      partialize: (s) => ({
        config: s.config,
        activeAgentId: s.activeAgentId,
      }),
    },
  ),
);