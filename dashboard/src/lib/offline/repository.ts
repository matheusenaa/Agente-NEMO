import { indexedDBManager, type OfflineStoreName } from "./indexedDB";
import { extractApiError, getBearerToken } from "@/api/nemo";
import type { AiConversation, AiMemory, AiTask, CalendarEvent, AiProfile } from "@/types/idea";

export interface DataRepository {
  listConversations(agentId?: string): Promise<AiConversation[]>;
  createConversation(agentId: string, title: string): Promise<AiConversation>;
  getConversation(id: string): Promise<AiConversation | null>;
  updateConversation(id: string, patch: Partial<AiConversation>): Promise<void>;
  deleteConversation(id: string): Promise<void>;
  listMessages(conversationId: string): Promise<{ role: string; content: string; created_at: number }[]>;
  appendMessage(conversationId: string, role: string, content: string, meta?: any): Promise<void>;

  listMemories(agentId?: string): Promise<AiMemory[]>;
  saveMemory(agentId: string, content: string, kind: string): Promise<AiMemory>;
  deleteMemory(id: string): Promise<void>;

  listTasks(): Promise<AiTask[]>;
  saveTask(task: AiTask): Promise<void>;
  deleteTask(id: string): Promise<void>;

  listEvents(): Promise<CalendarEvent[]>;
  saveEvent(event: CalendarEvent): Promise<void>;
  deleteEvent(id: string): Promise<void>;

  getProfile(): Promise<AiProfile>;
  saveProfile(data: Partial<AiProfile>): Promise<void>;

  listApiKeys(): Promise<{ provider: string; masked: string; model: string; verified: boolean }[]>;
  getApiKey(provider: string): Promise<string | null>;
  saveApiKey(provider: string, encrypted: string, masked: string, model: string, verified: boolean): Promise<void>;
  deleteApiKey(provider: string): Promise<void>;
  getAiSettings(): Promise<any>;
  saveAiSettings(data: any): Promise<void>;

  logActivity(data: any): Promise<void>;
  listActivity(limit?: number): Promise<any[]>;
  saveSearch(data: any): Promise<void>;

  enqueueSync(operation: "create" | "update" | "delete", store: OfflineStoreName, data: any): Promise<string>;
  getPendingSync(limit?: number): Promise<any[]>;
  markSynced(id: string): Promise<void>;
  incrementRetry(id: string): Promise<void>;
  cleanupSynced(): Promise<number>;
}

class LocalRepository implements DataRepository {
  async listConversations(agentId?: string): Promise<AiConversation[]> {
    const all = await indexedDBManager.getAll<AiConversation>("conversations");
    if (agentId) return all.filter((c) => c.agent_id === agentId);
    return all.sort((a, b) => (Number(b.updated_at) ?? 0) - (Number(a.updated_at) ?? 0));
  }

  async createConversation(agentId: string, title: string): Promise<AiConversation> {
    const conv: AiConversation = {
      id: `c_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      agent_id: agentId,
      title: title || "Nova conversa",
      created_at: Date.now(),
      updated_at: Date.now(),
      message_count: 0,
    };
    await indexedDBManager.put("conversations", conv);
    return conv;
  }

  async getConversation(id: string): Promise<AiConversation | null> {
    const result = await indexedDBManager.get<AiConversation>("conversations", id);
    return result ?? null;
  }

  async updateConversation(id: string, patch: Partial<AiConversation>): Promise<void> {
    const conv = await this.getConversation(id);
    if (conv) {
      await indexedDBManager.put("conversations", { ...conv, ...patch, updated_at: Date.now() });
    }
  }

  async deleteConversation(id: string): Promise<void> {
    await indexedDBManager.delete("conversations", id);
    await indexedDBManager.delete("messages", id);
  }

  async listMessages(conversationId: string): Promise<{ role: string; content: string; created_at: number }[]> {
    return indexedDBManager.getAllByIndex("messages", "conversation_id", conversationId);
  }

  async appendMessage(conversationId: string, role: string, content: string, meta?: any): Promise<void> {
    const msg = {
      id: `m_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      conversation_id: conversationId,
      role,
      content,
      meta: meta ?? {},
      created_at: Date.now(),
    };
    await indexedDBManager.put("messages", msg);
    await this.updateConversation(conversationId, { updated_at: Date.now() });
  }

  async listMemories(agentId?: string): Promise<AiMemory[]> {
    const all = await indexedDBManager.getAll<AiMemory>("memories");
    if (agentId) return all.filter((m) => m.agent_id === agentId);
    return all.sort((a, b) => (Number(b.created_at) ?? 0) - (Number(a.created_at) ?? 0));
  }

  async saveMemory(agentId: string, content: string, kind: string): Promise<AiMemory> {
    const mem: AiMemory = {
      id: `m_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      agent_id: agentId,
      content,
      kind,
      created_at: Date.now(),
    };
    await indexedDBManager.put("memories", mem);
    return mem;
  }

  async deleteMemory(id: string): Promise<void> {
    await indexedDBManager.delete("memories", id);
  }

  async listTasks(): Promise<AiTask[]> {
    const all = await indexedDBManager.getAll<AiTask>("tasks");
    return all.sort((a, b) => (Number(b.created_at) ?? 0) - (Number(a.created_at) ?? 0));
  }

  async saveTask(task: AiTask): Promise<void> {
    await indexedDBManager.put("tasks", task);
  }

  async deleteTask(id: string): Promise<void> {
    await indexedDBManager.delete("tasks", id);
  }

  async listEvents(): Promise<CalendarEvent[]> {
    const all = await indexedDBManager.getAll<CalendarEvent>("events");
    return all.sort((a, b) => (a.date ?? "").localeCompare(b.date ?? "") || (a.time ?? "").localeCompare(b.time ?? ""));
  }

  async saveEvent(event: CalendarEvent): Promise<void> {
    await indexedDBManager.put("events", event);
  }

  async deleteEvent(id: string): Promise<void> {
    await indexedDBManager.delete("events", id);
  }

  async getProfile(): Promise<AiProfile> {
    const result = await indexedDBManager.get<AiProfile>("profile", "current");
    return result ?? ({} as AiProfile);
  }

  async saveProfile(data: Partial<AiProfile>): Promise<void> {
    const current = await this.getProfile();
    await indexedDBManager.put("profile", { ...current, ...data, id: "current" });
  }

  async listApiKeys(): Promise<{ provider: string; masked: string; model: string; verified: boolean }[]> {
    return indexedDBManager.getAll("ai_keys");
  }

  async getApiKey(provider: string): Promise<string | null> {
    const entry = await indexedDBManager.get("ai_keys", provider);
    return (entry as any)?.encrypted_key ?? null;
  }

  async saveApiKey(provider: string, encrypted: string, masked: string, model: string, verified: boolean): Promise<void> {
    await indexedDBManager.put("ai_keys", {
      id: provider,
      provider,
      encrypted_key: encrypted,
      masked,
      model,
      verified,
      updated_at: new Date().toISOString(),
    });
  }

  async deleteApiKey(provider: string): Promise<void> {
    await indexedDBManager.delete("ai_keys", provider);
  }

  async getAiSettings(): Promise<any> {
    const result = await indexedDBManager.get("ai_settings", "current");
    return result ?? {};
  }

  async saveAiSettings(data: any): Promise<void> {
    const current = await this.getAiSettings();
    await indexedDBManager.put("ai_settings", { ...current, ...data, id: "current", updated_at: new Date().toISOString() });
  }

  async logActivity(data: any): Promise<void> {
    const entry = { ...data, id: `act_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`, created_at: new Date().toISOString() };
    await indexedDBManager.put("activity_logs", entry);
  }

  async listActivity(limit = 50): Promise<any[]> {
    const all = await indexedDBManager.getAll("activity_logs");
    return all.slice(0, limit);
  }

  async saveSearch(data: any): Promise<void> {
    const entry = { ...data, id: `search_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`, created_at: new Date().toISOString() };
    await indexedDBManager.put("web_searches", entry);
  }

  async enqueueSync(operation: "create" | "update" | "delete", store: OfflineStoreName, data: any): Promise<string> {
    return indexedDBManager.enqueueSync({ operation, store, data });
  }

  async getPendingSync(limit = 50): Promise<any[]> {
    return indexedDBManager.getPendingSync(limit);
  }

  async markSynced(id: string): Promise<void> {
    await indexedDBManager.markSynced(id);
  }

  async incrementRetry(id: string): Promise<void> {
    await indexedDBManager.incrementRetry(id);
  }

  async cleanupSynced(): Promise<number> {
    return indexedDBManager.removeSynced();
  }
}

class RemoteRepository implements DataRepository {
  private baseUrl = "/api/nemo";
  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const headers = new Headers(init?.headers);
    headers.set("Content-Type", "application/json");
    // O token vinha de `localStorage["nemo-auth"].state.token`, chave que o
    // store nunca grava: o header virava `Bearer undefined` e o servidor
    // respondia 401 mesmo com a sessão válida. No navegador a sessão é o
    // cookie HttpOnly; o Bearer só existe para clientes não-browser.
    const token = getBearerToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const res = await fetch(`${this.baseUrl}${path}`, { ...init, headers, credentials: "include" });
    if (!res.ok) {
      const body = await res.text();
      throw new Error(extractApiError(body, res.status));
    }
    return res.json();
  }

  async listConversations(agentId?: string): Promise<AiConversation[]> {
    const params = new URLSearchParams();
    if (agentId) params.set("agent", agentId);
    return this.request(`/conversations${params.toString() ? `?${params}` : ""}`);
  }

  async createConversation(agentId: string, title: string): Promise<AiConversation> {
    return this.request("/conversations", { method: "POST", body: JSON.stringify({ agent: agentId, title }) });
  }

  async getConversation(id: string): Promise<AiConversation | null> {
    try {
      return await this.request(`/conversations/${id}`);
    } catch (error) {
      // 404 é o único caso em que "não existe" é a resposta correta; nos demais
      // (401, 500, rede) devolver null fazia o chamador limpar a conversa da tela.
      if (error instanceof Error && /404/.test(error.message)) return null;
      throw error;
    }
  }

  async updateConversation(id: string, patch: Partial<AiConversation>): Promise<void> {
    await this.request(`/conversations/${id}`, { method: "PUT", body: JSON.stringify(patch) });
  }

  async deleteConversation(id: string): Promise<void> {
    await this.request(`/conversations/${id}`, { method: "DELETE" });
  }

  async listMessages(conversationId: string): Promise<{ role: string; content: string; created_at: number }[]> {
    return this.request(`/conversations/${conversationId}/messages`);
  }

  async appendMessage(_conversationId: string, _role: string, _content: string, _meta?: any): Promise<void> {
    // Messages are appended via chat endpoint, not directly
  }

  async listMemories(agentId?: string): Promise<AiMemory[]> {
    const params = new URLSearchParams();
    if (agentId) params.set("agent", agentId);
    return this.request(`/ai/memories${params.toString() ? `?${params}` : ""}`);
  }

  async saveMemory(agentId: string, content: string, kind: string): Promise<AiMemory> {
    return this.request("/ai/memories", { method: "POST", body: JSON.stringify({ agent: agentId, content, kind }) });
  }

  async deleteMemory(id: string): Promise<void> {
    await this.request(`/ai/memories/${id}`, { method: "DELETE" });
  }

  async listTasks(): Promise<AiTask[]> {
    return this.request("/tasks");
  }

  async saveTask(task: AiTask): Promise<void> {
    await this.request("/tasks", { method: "POST", body: JSON.stringify(task) });
  }

  async deleteTask(id: string): Promise<void> {
    await this.request(`/tasks/${id}`, { method: "DELETE" });
  }

  async listEvents(): Promise<CalendarEvent[]> {
    return this.request("/events");
  }

  async saveEvent(event: CalendarEvent): Promise<void> {
    await this.request("/events", { method: "POST", body: JSON.stringify(event) });
  }

  async deleteEvent(id: string): Promise<void> {
    await this.request(`/events/${id}`, { method: "DELETE" });
  }

  async getProfile(): Promise<AiProfile> {
    return this.request("/profile");
  }

  async saveProfile(data: Partial<AiProfile>): Promise<void> {
    await this.request("/profile", { method: "POST", body: JSON.stringify(data) });
  }

  async listApiKeys(): Promise<{ provider: string; masked: string; model: string; verified: boolean }[]> {
    return this.request("/ai/keys");
  }

  async getApiKey(_provider: string): Promise<string | null> {
    // Keys are never returned from server (only masked)
    return null;
  }

  async saveApiKey(provider: string, encrypted: string, _masked: string, model: string, _verified: boolean): Promise<void> {
    await this.request("/ai/keys", { method: "POST", body: JSON.stringify({ provider, api_key: encrypted, model }) });
  }

  async deleteApiKey(provider: string): Promise<void> {
    await this.request(`/ai/keys/${provider}`, { method: "DELETE" });
  }

  async getAiSettings(): Promise<any> {
    return this.request("/ai/config");
  }

  async saveAiSettings(data: any): Promise<void> {
    await this.request("/ai/config", { method: "POST", body: JSON.stringify(data) });
  }

  async logActivity(_data: any): Promise<void> {
    // Activity logging is handled server-side
  }

  async listActivity(limit = 50): Promise<any[]> {
    return this.request(`/ai/activity?limit=${limit}`);
  }

  async saveSearch(_data: any): Promise<void> {
    // Search is handled via ai/search endpoint
  }

  async enqueueSync(): Promise<string> { return ""; }
  async getPendingSync(): Promise<any[]> { return []; }
  async markSynced(): Promise<void> {}
  async incrementRetry(): Promise<void> {}
  async cleanupSynced(): Promise<number> { return 0; }
}

/** Loga a queda para o armazenamento local — degradar é correto, sumir é não. */
function warnRemoteFallback(error: unknown): void {
  console.warn(
    "[NEMO offline] servidor indisponível, usando dados locais:",
    error instanceof Error ? error.message : error,
  );
}

class SyncRepository implements DataRepository {
  constructor(
    private local: LocalRepository,
    private remote: RemoteRepository,
    private isOnline: () => boolean
  ) {}

  private async tryRemote<T>(fn: () => Promise<T>, fallback: () => Promise<T>): Promise<T> {
    if (!this.isOnline()) return fallback();
    try {
      return await fn();
    } catch (error) {
      // Degradar para o IndexedDB é o comportamento correto, mas era SILENCIOSO:
      // o usuário via os dados antigos do navegador sem nenhuma pista de que o
      // servidor estava fora do ar ou devolvendo erro (§31/§36).
      warnRemoteFallback(error);
      return fallback();
    }
  }

  /** Grava localmente e enfileira para o servidor, avisando se a fila falhar. */
  private async persistLocally(
    apply: () => Promise<void>,
    enqueue: () => Promise<unknown>,
  ): Promise<void> {
    await apply();
    try {
      await enqueue();
    } catch (error) {
      console.warn("[NEMO offline] falha ao enfileirar operação para sincronização:", error);
    }
  }

  async listConversations(agentId?: string): Promise<AiConversation[]> {
    return this.tryRemote(
      () => this.remote.listConversations(agentId),
      () => this.local.listConversations(agentId)
    );
  }

  async createConversation(agentId: string, title: string): Promise<AiConversation> {
    if (this.isOnline()) {
      try {
        return await this.remote.createConversation(agentId, title);
      } catch (error) {
        warnRemoteFallback(error);
      }
    }
    const local = await this.local.createConversation(agentId, title);
    await this.persistLocally(
      async () => {},
      () => this.local.enqueueSync("create", "conversations", local),
    );
    return local;
  }

  async getConversation(id: string): Promise<AiConversation | null> {
    return this.tryRemote(
      () => this.remote.getConversation(id),
      () => this.local.getConversation(id)
    );
  }

  async updateConversation(id: string, patch: Partial<AiConversation>): Promise<void> {
    if (this.isOnline()) {
      try {
        await this.remote.updateConversation(id, patch);
        return;
      } catch (error) {
        warnRemoteFallback(error);
      }
    }
    await this.persistLocally(
      () => this.local.updateConversation(id, patch),
      () => this.local.enqueueSync("update", "conversations", { id, ...patch }),
    );
  }

  async deleteConversation(id: string): Promise<void> {
    if (this.isOnline()) {
      try {
        await this.remote.deleteConversation(id);
        return;
      } catch (error) {
        warnRemoteFallback(error);
      }
    }
    await this.persistLocally(
      () => this.local.deleteConversation(id),
      () => this.local.enqueueSync("delete", "conversations", { id }),
    );
  }

  async listMessages(conversationId: string) {
    return this.tryRemote(
      () => this.remote.listMessages(conversationId),
      () => this.local.listMessages(conversationId)
    );
  }

  async appendMessage(conversationId: string, role: string, content: string, meta?: any): Promise<void> {
    await this.local.appendMessage(conversationId, role, content, meta);
    await this.local.enqueueSync("create", "messages", { conversationId, role, content, meta });
  }

  async listMemories(agentId?: string): Promise<AiMemory[]> {
    return this.tryRemote(
      () => this.remote.listMemories(agentId),
      () => this.local.listMemories(agentId)
    );
  }

  async saveMemory(agentId: string, content: string, kind: string): Promise<AiMemory> {
    if (this.isOnline()) {
      try {
        return await this.remote.saveMemory(agentId, content, kind);
      } catch (error) {
        warnRemoteFallback(error);
      }
    }
    const local = await this.local.saveMemory(agentId, content, kind);
    await this.persistLocally(
      async () => {},
      () => this.local.enqueueSync("create", "memories", local),
    );
    return local;
  }

  async deleteMemory(id: string): Promise<void> {
    if (this.isOnline()) {
      try {
        await this.remote.deleteMemory(id);
        return;
      } catch (error) {
        warnRemoteFallback(error);
      }
    }
    await this.persistLocally(
      () => this.local.deleteMemory(id),
      () => this.local.enqueueSync("delete", "memories", { id }),
    );
  }

  async listTasks(): Promise<AiTask[]> {
    return this.tryRemote(
      () => this.remote.listTasks(),
      () => this.local.listTasks()
    );
  }

  async saveTask(task: AiTask): Promise<void> {
    if (this.isOnline()) {
      try {
        await this.remote.saveTask(task);
        return;
      } catch (error) {
        warnRemoteFallback(error);
      }
    }
    await this.persistLocally(
      () => this.local.saveTask(task),
      () => this.local.enqueueSync("update", "tasks", task),
    );
  }

  async deleteTask(id: string): Promise<void> {
    if (this.isOnline()) {
      try {
        await this.remote.deleteTask(id);
        return;
      } catch (error) {
        warnRemoteFallback(error);
      }
    }
    await this.persistLocally(
      () => this.local.deleteTask(id),
      () => this.local.enqueueSync("delete", "tasks", { id }),
    );
  }

  async listEvents(): Promise<CalendarEvent[]> {
    return this.tryRemote(
      () => this.remote.listEvents(),
      () => this.local.listEvents()
    );
  }

  async saveEvent(event: CalendarEvent): Promise<void> {
    if (this.isOnline()) {
      try {
        await this.remote.saveEvent(event);
        return;
      } catch (error) {
        warnRemoteFallback(error);
      }
    }
    await this.persistLocally(
      () => this.local.saveEvent(event),
      () => this.local.enqueueSync("update", "events", event),
    );
  }

  async deleteEvent(id: string): Promise<void> {
    if (this.isOnline()) {
      try {
        await this.remote.deleteEvent(id);
        return;
      } catch (error) {
        warnRemoteFallback(error);
      }
    }
    await this.persistLocally(
      () => this.local.deleteEvent(id),
      () => this.local.enqueueSync("delete", "events", { id }),
    );
  }

  async getProfile(): Promise<AiProfile> {
    return this.tryRemote(
      () => this.remote.getProfile(),
      () => this.local.getProfile()
    );
  }

  async saveProfile(data: Partial<AiProfile>): Promise<void> {
    if (this.isOnline()) {
      try {
        await this.remote.saveProfile(data);
        return;
      } catch (error) {
        warnRemoteFallback(error);
      }
    }
    await this.persistLocally(
      () => this.local.saveProfile(data),
      () => this.local.enqueueSync("update", "profile", data),
    );
  }

  async listApiKeys() {
    return this.tryRemote(
      () => this.remote.listApiKeys(),
      () => this.local.listApiKeys()
    );
  }

  async getApiKey(provider: string) {
    return this.local.getApiKey(provider);
  }

  async saveApiKey(provider: string, encrypted: string, masked: string, model: string, verified: boolean): Promise<void> {
    if (this.isOnline()) {
      try {
        await this.remote.saveApiKey(provider, encrypted, masked, model, verified);
        return;
      } catch (error) {
        warnRemoteFallback(error);
      }
    }
    await this.local.saveApiKey(provider, encrypted, masked, model, verified);
  }

  async deleteApiKey(provider: string): Promise<void> {
    if (this.isOnline()) {
      try {
        await this.remote.deleteApiKey(provider);
        return;
      } catch (error) {
        warnRemoteFallback(error);
      }
    }
    await this.local.deleteApiKey(provider);
  }

  async getAiSettings() {
    return this.tryRemote(
      () => this.remote.getAiSettings(),
      () => this.local.getAiSettings()
    );
  }

  async saveAiSettings(data: any): Promise<void> {
    if (this.isOnline()) {
      try {
        await this.remote.saveAiSettings(data);
        return;
      } catch (error) {
        warnRemoteFallback(error);
      }
    }
    await this.persistLocally(
      () => this.local.saveAiSettings(data),
      () => this.local.enqueueSync("update", "ai_settings", data),
    );
  }

  async logActivity(data: any): Promise<void> {
    await this.local.logActivity(data);
    if (this.isOnline()) {
      try {
        await this.remote.logActivity(data);
      } catch (error) {
        warnRemoteFallback(error);
      }
    }
  }

  async listActivity(limit = 50) {
    return this.tryRemote(
      () => this.remote.listActivity(limit),
      () => this.local.listActivity(limit)
    );
  }

  async saveSearch(data: any): Promise<void> {
    await this.local.saveSearch(data);
    if (this.isOnline()) {
      try {
        await this.remote.saveSearch(data);
      } catch (error) {
        warnRemoteFallback(error);
      }
    }
  }

  async enqueueSync(operation: "create" | "update" | "delete", store: OfflineStoreName, data: any): Promise<string> {
    return this.local.enqueueSync(operation, store, data);
  }

  async getPendingSync(limit = 50) {
    return this.local.getPendingSync(limit);
  }

  async markSynced(id: string): Promise<void> {
    await this.local.markSynced(id);
  }

  async incrementRetry(id: string): Promise<void> {
    await this.local.incrementRetry(id);
  }

  async cleanupSynced(): Promise<number> {
    return this.local.cleanupSynced();
  }
}

let repositoryInstance: DataRepository | null = null;

export function createRepository(isOnline: () => boolean): DataRepository {
  const local = new LocalRepository();
  const remote = new RemoteRepository();
  repositoryInstance = new SyncRepository(local, remote, isOnline);
  return repositoryInstance;
}

export function getRepository(): DataRepository {
  if (!repositoryInstance) {
    throw new Error("Repository not initialized. Call createRepository() first.");
  }
  return repositoryInstance;
}