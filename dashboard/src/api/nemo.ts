import type {
  AiConfigResponse, AiConversation, AiMemory, AiProfile, AiTask, CalendarEvent, FileNode, OpenFile, SearchWebResult,
} from "@/types/idea";

const BASE = "/api/nemo";

/**
 * Token Bearer fica APENAS em memória, para clientes não-browser (shell
 * desktop / testes). No navegador a sessão é o cookie HttpOnly `nemo_session`.
 *
 * Antes o token era lido de `localStorage["nemo-auth"]`, mas o store nunca o
 * persistia (a chave `token` era removida no `partialize`): a leitura devolvia
 * sempre `""` e o cabeçalho Authorization nunca era enviado.
 */
let bearerToken = "";

export function setBearerToken(token: string): void {
  bearerToken = (token || "").trim();
}

export function getBearerToken(): string {
  return bearerToken;
}

/** Extrai uma mensagem legível do corpo de erro do backend. */
export function extractApiError(body: string, status: number): string {
  try {
    const parsed = JSON.parse(body);
    const detail = parsed?.detail;
    if (typeof detail === "string" && detail) return detail;
    if (Array.isArray(detail) && detail.length) {
      const first = detail[0];
      if (typeof first === "string") return first;
      if (first?.msg) return `${(first.loc || []).slice(1).join(".")}: ${first.msg}`;
    }
    if (parsed?.error) return String(parsed.error);
  } catch {
    /* corpo não-JSON */
  }
  return body?.trim() || `HTTP ${status}`;
}

function getToken(): string {
  return bearerToken;
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
      model_used: string;
      is_fallback?: boolean;
      offline?: boolean;
      latency_ms?: number;
      prompt_tokens?: number;
      completion_tokens?: number;
      total_tokens?: number;
      finish_reason?: string | null;
      conversation_id?: string;
      search?: { used: boolean; ok?: boolean; provider?: string; query?: string; results?: number; error?: string };
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
      conversation_id?: string;
      search?: { used: boolean; ok?: boolean; provider?: string; query?: string; results?: number; error?: string };
    };

export const nemoApi = {
  async health(): Promise<ServerHealth> {
    return request<ServerHealth>("/health");
  },
  async chat(agent: string, message: string, history: ChatHistoryMessage[] = [], model?: string, conversationId?: string): Promise<ChatResponse> {
    return request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({
        agent,
        message,
        model,
        max_tokens: 1100,
        // Sem isto o backend não sabia em qual conversa gravar: cada resposta
        // ia para a conversa mais recente do agente, e a conversa aberta na
        // tela podia ficar vazia depois do refresh (§3/§4/§11).
        ...(conversationId ? { conversation_id: conversationId } : {}),
        messages: history
          .filter((item) => item.content.trim().length > 0)
          .slice(-12)
          .map((item) => ({ role: item.role, content: item.content.slice(0, 12000) })),
      }),
    });
  },
  async createConversation(agent: string, title: string): Promise<{ ok: boolean; conversation: AiConversation }> {
    return request("/conversations", { method: "POST", body: JSON.stringify({ agent_id: agent, title }) });
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
    provider_errors?: Record<string, string>;
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
  /** Lojas que o servidor não conseguiu ler — o cursor não deve avançar. */
  unreadable_stores?: string[];
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