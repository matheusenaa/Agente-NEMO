/** Tipos centrais da NEMO IDE */

export type ThemeId = "ocean" | "vasco" | "cyber" | "midnight" | "graphite";
export type LayoutId = "ide" | "chat" | "command" | "minimal";
export type ViewId = "dashboard" | "chat" | "office" | "calendar" | "workspace" | "terminal" | "tasks" | "history" | "settings";
export type Density = "compact" | "comfortable" | "spacious";

export interface AgentCard {
  id: string;
  name: string;
  title: string;
  category: string;
  icon: string;
  color: string;
  gradient: string;
  role: string;
  defaultModel?: string;
  version?: string;
  /** Descrição curta exibida em tooltips / perfil. */
  description?: string;
  priority?: "Baixa" | "Normal" | "Alta" | "Crítica";
  fallbacks?: string[];
}

export type MsgStatus = "sending" | "typing" | "done" | "error";

export interface ChatMessage {
  id: string;
  role: "user" | "agent";
  agentId: string;
  content: string;
  time: number;
  status: MsgStatus;
  phases?: string[];
  meta?: {
    model?: string;
    latencyMs?: number;
    isFallback?: boolean;
    promptTokens?: number;
    completionTokens?: number;
  };
  error?: string;
}

export type Priority = "urgente" | "importante" | "normal" | "baixa";
export type TaskStatus = "pending" | "running" | "done" | "error";

export interface TaskItem {
  id: string;
  title: string;
  priority: Priority;
  agentId: string;
  status: TaskStatus;
  createdAt: number;
  doneAt?: number;
}

export type LogTone = "info" | "ok" | "warn" | "error" | "agent";

export interface LogEntry {
  id: string;
  time: number;
  tone: LogTone;
  text: string;
  agentId?: string;
}

export interface NotifItem {
  id: string;
  icon: string;
  text: string;
  tone: "info" | "ok" | "warn" | "error";
  time: number;
}

export interface FileNode {
  name: string;
  path: string;
  type: "dir" | "file";
  size: number;
}

export interface OpenFile {
  path: string;
  name: string;
  language: string;
  content: string;
  dirty?: boolean;
}

export interface TermLine {
  id: string;
  text: string;
  tone: "cmd" | "out" | "err" | "ok" | "info";
}

export interface HistoryItem {
  id: string;
  time: number;
  kind: "chat" | "file" | "task" | "terminal" | "config";
  title: string;
  detail: string;
  agentId?: string;
}

export interface LiveStatus {
  agentId: string;
  label: string;
  phrase: string;
  busy: boolean;
}

export type EventCategory = "trabalho" | "pessoal" | "estudos" | "reuniao" | "lembrete" | "outro";

export interface CalendarEvent {
  id: string;
  title: string;
  description: string;
  date: string; // YYYY-MM-DD
  time: string; // HH:MM (24h)
  durationMin: number;
  category: EventCategory;
  agentId: string;
  remind: number; // minutos antes
  createdAt: number;
}

export interface IdeConfig {
  theme: ThemeId;
  layout: LayoutId;
  fontSize: number;
  density: Density;
  animations: boolean;
  showTimestamps: boolean;
  funnyStatus: boolean;
  favAgents: string[];
  language: "pt-BR";
}