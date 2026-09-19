import type { FileNode, OpenFile } from "@/types/idea";

const BASE = "/api/nemo";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
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
};