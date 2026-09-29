import type {
  AiConfigResponse, AiConversation, AiMemory, AiProfile, AiTask, CalendarEvent, FileNode, OpenFile, SearchWebResult,
} from "@/types/idea";

const BASE = "/api/nemo";

function getToken(): string {
  try {
    const raw = localStorage.getItem("nemo-auth");
    if (!raw) return "";
    const parsed = JSON.parse(raw);
    return parsed?.state?.token ?? parsed?.token ?? "";
  } catch {
    return "";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });
  if (!res.ok) {
    const raw = await res.text().catch(() => "");
    let detail = raw;
    try {
      const parsed = JSON.parse(raw) as { detail?: unknown; error?: unknown; message?: unknown };
      detail = String(parsed.detail ?? parsed.error ?? parsed.message ?? raw);
    } catch {
      detail = raw;
    }
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return (await res.json()) as T;
}

export interface ServerHealth {
  project: string;
  version: string;
  time: string;
  api_key_configured: boolean;
  models: number;
  agents: number;
  squads: number;
}

export interface ChatHistoryMessage {
  role: "user" | "assistant";
  content: string;
}

export type ChatResponse =
  | {
      ok: true;
      agent: string;
      content: string;
      conversation_id?: string;
      model_used: string;
      is_fallback?: boolean;
      offline?: boolean;
      rate_limited?: boolean;
      latency_ms?: number;
      prompt_tokens?: number;
      completion_tokens?: number;
      total_tokens?: number;
      finish_reason?: string | null;
      used_search?: boolean;
      search_provider?: string;
      search_results?: { title?: string; url?: string; snippet?: string; source?: string }[];
    }
  | {
      ok: false;
      agent: string;
      content?: string;
      error: string;
      error_code?: string;
      model_used?: string;
      is_fallback?: boolean;
      offline?: boolean;
      latency_ms?: number;
    };

export interface ChatStreamHandlers {
  /** Texto recém-chegado do modelo (acrescentar ao que já está na tela). */
  onDelta?: (text: string) => void;
  /** O modelo caiu e vamos tentar outro: descartar o texto parcial. */
  onReset?: (info: { model?: string }) => void;
  /** Mensagem de status (ex.: "Consultando a web..."). */
  onStatus?: (info: { stage?: string; message?: string }) => void;
  /** Fontes da busca executada pelo agente. */
  onSources?: (info: { provider?: string; results?: { title?: string; url?: string; snippet?: string }[] }) => void;
  onError?: (error: { content?: string; error_code?: string; fallback_to_sync?: boolean }) => void;
  onDone?: (info: { ok: boolean; conversation_id?: string; model_used?: string; used_search?: boolean }) => void;
}

/**
 * Chat com streaming via SSE (POST + fetch reader).
 *
 * `EventSource` não serve aqui: ele só faz GET, e o chat precisa de corpo
 * JSON com o histórico e a conversa em andamento. Por isso lemos o
 * `text/event-stream` manualmente.
 */
async function chatStream(
  body: Record<string, unknown>,
  handlers: ChatStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const token = getToken();
  const headers = new Headers({ "Content-Type": "application/json", Accept: "text/event-stream" });
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${BASE}/chat/stream`, {
    method: "POST",
    headers,
    credentials: "include",
    body: JSON.stringify(body),
    signal,
  });

  if (!res.ok || !res.body) {
    const raw = await res.text().catch(() => "");
    let detail = raw;
    try {
      const parsed = JSON.parse(raw) as { detail?: unknown };
      detail = String(parsed.detail ?? raw);
    } catch {
      detail = raw;
    }
    throw new Error(detail || `HTTP ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // Eventos SSE são separados por uma linha em branco.
    let idx = buffer.indexOf("\n\n");
    while (idx !== -1) {
      const raw = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);

      let name = "";
      const dataLines: string[] = [];
      for (const line of raw.split("\n")) {
        if (line.startsWith("event:")) name = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
      }
      if (name && dataLines.length) {
        let payload: Record<string, unknown> = {};
        try {
          payload = JSON.parse(dataLines.join("\n")) as Record<string, unknown>;
        } catch {
          payload = {};
        }
        switch (name) {
          case "delta":
            handlers.onDelta?.(String(payload.text ?? ""));
            break;
          case "reset":
            handlers.onReset?.({ model: payload.model as string | undefined });
            break;
          case "status":
            handlers.onStatus?.({ stage: payload.stage as string, message: payload.message as string });
            break;
          case "tool":
            handlers.onStatus?.({ stage: "searching", message: `Consultando: ${String(payload.query ?? "")}` });
            break;
          case "sources":
            handlers.onSources?.({
              provider: payload.provider as string,
              results: (payload.results ?? []) as { title?: string; url?: string; snippet?: string }[],
            });
            break;
  case "error":
    handlers.onError?.({
      content: payload.content as string | undefined,
      error_code: payload.error_code as string | undefined,
      fallback_to_sync: payload.fallback_to_sync as boolean | undefined,
    });
    break;
          case "done":
            handlers.onDone?.({
              ok: Boolean(payload.ok),
              conversation_id: payload.conversation_id as string | undefined,
              model_used: payload.model_used as string | undefined,
              used_search: Boolean(payload.used_search),
            });
            break;
          default:
            break;
        }
      }
      idx = buffer.indexOf("\n\n");
    }
  }
}

export const nemoApi = {
  async health(): Promise<ServerHealth> {
    return request<ServerHealth>("/health");
  },
  async chat(
    agent: string,
    message: string,
    history: ChatHistoryMessage[] = [],
    model?: string,
    conversationId?: string,
    newConversation = false,
  ): Promise<ChatResponse> {
    return request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({
        agent,
        message,
        model,
        max_tokens: 1100,
        conversation_id: conversationId ?? "",
        new_conversation: newConversation,
        messages: history
          .filter((item) => item.content.trim().length > 0)
          .slice(-12)
          .map((item) => ({ role: item.role, content: item.content.slice(0, 12000) })),
      }),
    });
  },

  /** Chat com streaming progressivo (SSE). */
  async chatStream(
    agent: string,
    message: string,
    history: ChatHistoryMessage[] = [],
    options: { model?: string; conversationId?: string; newConversation?: boolean; signal?: AbortSignal } = {},
    handlers: ChatStreamHandlers = {},
  ): Promise<void> {
    await chatStream(
      {
        agent,
        message,
        model: options.model,
        max_tokens: 1100,
        conversation_id: options.conversationId ?? "",
        new_conversation: options.newConversation ?? false,
        messages: history
          .filter((item) => item.content.trim().length > 0)
          .slice(-12)
          .map((item) => ({ role: item.role, content: item.content.slice(0, 12000) })),
      },
      handlers,
      options.signal,
    );
  },
  async listFiles(path = ""): Promise<{ path: string; entries: FileNode[] }> {
    return request(`/files?path=${encodeURIComponent(path)}`);
  },
  async readFile(path: string): Promise<OpenFile> {
    return request(`/file?path=${encodeURIComponent(path)}`);
  },
  async saveFile(path: string, content: string): Promise<{ ok: boolean; path: string }> {
    return request("/file/save", { method: "POST", body: JSON.stringify({ path, content }) });
  },
  async runCommand(command: string, force = false, timeout = 60): Promise<{
    ok: boolean;
    requires_confirm?: boolean;
    reason?: string;
    stdout?: string;
    stderr?: string;
    code?: number | null;
  }> {
    return request("/terminal", { method: "POST", body: JSON.stringify({ command, force, timeout }) });
  },
  async snapshot(): Promise<unknown> {
    return request("/snapshot");
  },
  async listEvents(): Promise<CalendarEvent[]> {
    return request("/events");
  },
  async createEvent(e: Omit<CalendarEvent, "createdAt">): Promise<CalendarEvent> {
    return request("/events", { method: "POST", body: JSON.stringify(e) });
  },
  async updateEvent(id: string, patch: Partial<CalendarEvent>): Promise<CalendarEvent> {
    return request(`/events/${encodeURIComponent(id)}`, { method: "PUT", body: JSON.stringify(patch) });
  },
  async deleteEvent(id: string): Promise<{ ok: boolean; deleted: string }> {
    return request(`/events/${encodeURIComponent(id)}`, { method: "DELETE" });
  },

  // ---- Central de IA (missão §39/45) ----
  async aiConfig(): Promise<AiConfigResponse> {
    return request("/ai/config");
  },
  async saveAiConfig(data: {
    default_provider?: string;
    default_model?: string;
    agent_overrides?: Record<string, { provider?: string; model?: string }>;
  }): Promise<{ ok: boolean }> {
    return request("/ai/config", { method: "POST", body: JSON.stringify(data) });
  },
  async saveAiKey(provider: string, apiKey: string, model?: string): Promise<{
    ok: boolean; masked: string; verified: boolean; test: { ok: boolean; message: string };
  }> {
    return request("/ai/keys", { method: "POST", body: JSON.stringify({ provider, api_key: apiKey, model }) });
  },
  async deleteAiKey(provider: string): Promise<{ ok: boolean; deleted: string }> {
    return request(`/ai/keys/${encodeURIComponent(provider)}`, { method: "DELETE" });
  },
  async testAiKey(provider: string, apiKey?: string, model?: string): Promise<{
    ok: boolean; message: string; provider: string; model?: string; detail?: string;
  }> {
    return request("/ai/test", { method: "POST", body: JSON.stringify({ provider, api_key: apiKey, model }) });
  },
  async searchWeb(query: string, limit = 6, agent = "pesquisador"): Promise<{
    ok: boolean; query: string; provider: string; results: SearchWebResult[]; error?: string;
  }> {
    return request(`/ai/search?query=${encodeURIComponent(query)}&limit=${limit}&agent=${encodeURIComponent(agent)}`);
  },

  // ---- Memória dos agentes ----
  async listMemories(agent?: string): Promise<{ ok: boolean; memories: AiMemory[] }> {
    return request(`/ai/memories${agent ? `?agent=${encodeURIComponent(agent)}` : ""}`);
  },
  async saveMemory(agent: string, content: string, kind = "obs"): Promise<{ ok: boolean; memory: AiMemory }> {
    return request("/ai/memories", { method: "POST", body: JSON.stringify({ agent, content, kind }) });
  },
  async deleteMemory(id: string): Promise<{ ok: boolean; deleted: string }> {
    return request(`/ai/memories/${encodeURIComponent(id)}`, { method: "DELETE" });
  },

  // ---- Conversas persistidas ----
  async listConversations(agent?: string, q?: string): Promise<{ ok: boolean; conversations: AiConversation[] }> {
    const p = new URLSearchParams();
    if (agent) p.set("agent", agent);
    if (q) p.set("q", q);
    return request(`/conversations${p.toString() ? `?${p}` : ""}`);
  },
  async deleteConversation(id: string): Promise<{ ok: boolean; deleted: string }> {
    return request(`/conversations/${encodeURIComponent(id)}`, { method: "DELETE" });
  },
  async conversationMessages(id: string): Promise<{ ok: boolean; messages: { role: string; content: string; created_at: number | string }[] }> {
    return request(`/conversations/${encodeURIComponent(id)}/messages`);
  },

  // ---- Perfil do usuário (missão §8) ----
  async getProfile(): Promise<{ ok: boolean; profile: AiProfile }> {
    return request("/profile");
  },
  async saveProfile(data: Partial<Pick<AiProfile, "name" | "language" | "avatar" | "default_agent" | "preferences">>): Promise<{ ok: boolean; profile: AiProfile }> {
    return request("/profile", { method: "POST", body: JSON.stringify(data) });
  },

  // ---- Tarefas persistidas (sync leve) ----
  async listTasks(): Promise<{ ok: boolean; tasks: AiTask[] }> {
    return request("/tasks");
  },
  async saveTask(task: Partial<AiTask>): Promise<{ ok: boolean; task: AiTask }> {
    return request("/tasks", { method: "POST", body: JSON.stringify(task) });
  },
  async deleteTask(id: string): Promise<{ ok: boolean }> {
    return request(`/tasks/${encodeURIComponent(id)}`, { method: "DELETE" });
  },

  // ---- Sincronização Offline-First (missão §11-15) ----
  async syncPush(operations: SyncOperation[], lastSync?: number): Promise<SyncPushResponse> {
    return request("/sync/push", { method: "POST", body: JSON.stringify({ operations, last_sync: lastSync }) });
  },
  async syncPull(since?: number, stores?: string[]): Promise<SyncPullResponse> {
    const params = new URLSearchParams();
    if (since) params.set("since", String(since));
    if (stores?.length) params.set("stores", stores.join(","));
    return request(`/sync/pull${params.toString() ? `?${params}` : ""}`);
  },
  async syncResolveConflicts(conflicts: SyncConflict[]): Promise<SyncConflictResponse> {
    return request("/sync/conflicts", { method: "POST", body: JSON.stringify({ conflicts }) });
  },
};

// Sync Types
export interface SyncOperation {
  operation: "create" | "update" | "delete";
  store: "conversations" | "messages" | "memories" | "tasks" | "events" | "ai_keys" | "ai_settings" | "profile" | "activity_logs" | "web_searches";
  data: Record<string, any>;
  client_id: string;
  timestamp: number;
}

export interface SyncPushResponse {
  ok: boolean;
  results: Array<{ client_id: string; status: "ok" | "conflict" | "error"; server_id?: string; conflict?: boolean; error?: string }>;
  conflicts: Array<{ client_id: string; store: string; server_data: any; local_data: any }>;
  server_version: number;
}

export interface SyncPullResponse {
  ok: boolean;
  changes: Record<string, any[]>;
  server_version: number;
}

export interface SyncConflict {
  client_id: string;
  store: string;
  resolution: "local-wins" | "remote-wins" | "merge";
  resolved_data?: any;
}

export interface SyncConflictResponse {
  ok: boolean;
  results: Array<{ client_id: string; status: "resolved" | "error"; error?: string }>;
}