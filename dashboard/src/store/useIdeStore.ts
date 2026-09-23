import { create } from "zustand";
import { persist } from "zustand/middleware";
import type {
  CalendarEvent, ChatMessage, FileNode, HistoryItem, IdeConfig, LiveStatus, LogEntry,
  NotifItem, OpenFile, TaskItem, TaskStatus, TermLine, ViewId,
} from "@/types/idea";
import { getAgent } from "@/data/agents";
import { FUNNY_PHRASES, pickPhrase } from "@/data/statusPhrases";

const AMBIENT_INTERVAL_MS = 10 * 60 * 1000;
const INITIAL_AMBIENT_PHRASE = pickPhrase(FUNNY_PHRASES, "");

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

const NEMO_GREETING: ChatMessage = {
  id: uid("msg"),
  role: "agent",
  agentId: "nemo",
  content:
    "Bom dia! 👋 Sou o **NEMO**, coordenador da sua equipe de agentes.\n\nO que vamos resolver hoje?\n\n- `Analise meus gastos e encontre duplicados` (financeiro + dados)\n- `Monte um relatório do Vasco` (pesquisa + redação)\n- `Abra os arquivos do projeto` (área de trabalho)\n\nÉ só conversar — eu delego, executo, valido e te trago o resultado. 🐟",
  time: Date.now(),
  status: "done",
};

const INITIAL_THREADS: Record<string, ChatMessage[]> = { nemo: [NEMO_GREETING] };

export function seedThread(agentId: string): ChatMessage {
  const agent = getAgent(agentId);
  return {
    id: uid("msg"),
    role: "agent",
    agentId,
    content: `Olá! 👋 Sou **${agent.name}** — ${agent.role}. Como posso ajudar?`,
    time: Date.now(),
    status: "done",
  };
}

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

  // frase ambiente (rotaciona a cada 10 minutos)
  ambientPhrase: string;
  ambientPhraseAt: number;
  ensureAmbientPhrase: (force?: boolean) => string;

  // chat por agente (threads independentes)
  threads: Record<string, ChatMessage[]>;
  addUserMessage: (agentId: string, content: string) => string;
  insertAgentMessage: (agentId: string, m: Omit<ChatMessage, "id" | "time" | "status">) => string;
  patchMessage: (agentId: string, id: string, patch: Partial<ChatMessage>) => void;

  // calendário / eventos
  events: CalendarEvent[];
  setEvents: (events: CalendarEvent[]) => void;
  addEvent: (e: Omit<CalendarEvent, "id" | "createdAt">) => string;
  updateEvent: (id: string, patch: Partial<CalendarEvent>) => void;
  deleteEvent: (id: string) => void;

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
  addTask: (t: { title: string; priority?: TaskItem["priority"]; agentId?: string; status?: TaskStatus }) => string;
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
  deleteHistory: (id: string) => void;
  clearHistory: () => void;
}

function withThread(get: () => IdeStore, agentId: string): ChatMessage[] {
  return get().threads[agentId] ?? [];
}

export const useIdeStore = create<IdeStore>()(
  persist(
    (set, get) => ({
      config: DEFAULT_CONFIG,
      setConfig: (patch) => set((s) => ({ config: { ...s.config, ...patch } })),

      activeView: "dashboard",
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
        set((s) => ({ threads: { ...s.threads, [id]: s.threads[id] ?? [seedThread(id)] } }));
        get().addLog({ tone: "agent", agentId: id, text: `${getAgent(id).name} selecionado no chat` });
      },
      liveStatus: { agentId: "nemo", label: "🟢 Online", phrase: "", busy: false },
      setLiveStatus: (patch) => set((s) => ({ liveStatus: { ...s.liveStatus, ...patch } })),

      ambientPhrase: INITIAL_AMBIENT_PHRASE,
      ambientPhraseAt: Date.now(),
      ensureAmbientPhrase: (force) => {
        const now = Date.now();
        const s = get();
        const stale = force || !s.ambientPhrase || now - s.ambientPhraseAt >= AMBIENT_INTERVAL_MS;
        if (stale) {
          set({ ambientPhrase: pickPhrase(FUNNY_PHRASES, s.ambientPhrase), ambientPhraseAt: now });
          return get().ambientPhrase;
        }
        return s.ambientPhrase;
      },

      threads: INITIAL_THREADS,
      addUserMessage: (agentId, content) => {
        const id = uid("msg");
        set((s) => ({
          threads: {
            ...s.threads,
            [agentId]: [...withThread(get, agentId), { id, role: "user", agentId: "user", content, time: Date.now(), status: "done" }],
          },
        }));
        return id;
      },
      insertAgentMessage: (agentId, m) => {
        const id = uid("msg");
        set((s) => ({
          threads: {
            ...s.threads,
            [agentId]: [...withThread(get, agentId), { ...m, id, time: Date.now(), status: "typing", phases: [] }],
          },
        }));
        return id;
      },
      patchMessage: (agentId, id, patch) =>
        set((s) => ({
          threads: {
            ...s.threads,
            [agentId]: (s.threads[agentId] ?? []).map((m) => (m.id === id ? { ...m, ...patch } : m)),
          },
        })),

      events: [],
      setEvents: (events) => set({ events }),
      addEvent: (e) => {
        const id = uid("evt");
        const event: CalendarEvent = { ...e, id, createdAt: Date.now() };
        set((s) => ({ events: [...s.events, event] }));
        get().addLog({ tone: "ok", text: `Evento criado: ${e.title}` });
        get().addHistory({ kind: "task", title: e.title, detail: `${e.date} ${e.time} · ${getAgent(e.agentId).name}` });
        return id;
      },
      updateEvent: (id, patch) =>
        set((s) => ({ events: s.events.map((ev) => (ev.id === id ? { ...ev, ...patch } : ev)) })),
      deleteEvent: (id) => {
        set((s) => ({ events: s.events.filter((ev) => ev.id !== id) }));
        get().addLog({ tone: "warn", text: "Evento removido do calendário" });
      },

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
        { id: uid("term"), tone: "info", text: "NEMO IDE terminal — bem-vindo! Rode comandos seguros, ex: `dir` ou `python nemo_server.py`." },
      ],
      pushTerm: (line) => set((s) => ({ termLines: [...s.termLines.slice(-800), { ...line, id: uid("term") }] })),
      clearTerm: () => set({ termLines: [] }),

      tasks: [],
      addTask: (t) => {
        const id = uid("task");
        const task: TaskItem = { id, title: t.title, priority: t.priority ?? "normal", agentId: t.agentId ?? "nemo", status: t.status ?? "pending", createdAt: Date.now() };
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
      deleteHistory: (id) => {
        set((s) => ({ history: s.history.filter((h) => h.id !== id) }));
        get().addLog({ tone: "warn", text: "Registro de histórico excluído" });
      },
      clearHistory: () => {
        set({ history: [] });
        get().addLog({ tone: "warn", text: "Histórico completo excluído" });
      },
    }),
    {
      name: "nemo-ide",
      partialize: (s) => ({
        config: s.config,
activeAgentId: s.activeAgentId,
        threads: s.threads,
        events: s.events,
        tasks: s.tasks,
        notifications: s.notifications,
        history: s.history,
      }),
    },
  ),
);