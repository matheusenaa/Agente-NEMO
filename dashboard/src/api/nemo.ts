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
  const res = await fetch(`${BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
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
    }
  | { ok: false; agent: string; error: string; latency_ms?: number };

export const nemoApi = {
  async health(): Promise<ServerHealth> {
    return request<ServerHealth>("/health");
  },
  async chat(agent: string, message: string, history: string[] = [], model?: string): Promise<ChatResponse> {
    return request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({
        agent,
        message,
        model,
        max_tokens: 1100,
        messages: history.slice(-12).map((content) => ({ role: "user" as const, content })),
      }),
    });
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
};