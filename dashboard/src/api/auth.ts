export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: "admin" | "user";
  created_at: string;
}

export interface AuthResponse {
  ok: boolean;
  user: AuthUser;
}

const BASE = "/api/auth";

async function request<T>(path: string, init?: RequestInit, token?: string): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });
  // O catch-all do backend (SPA fallback) responde 200 com HTML para rotas
  // /api desconhecidas. Nesse caso res.json() falha e o corpo seria null —
  // devolver null fazia o chamador estourar "Cannot read properties of null".
  const body = await res.json().catch(() => null);
  const contentType = res.headers.get("Content-Type") || "";
  if (!contentType.includes("application/json")) {
    throw new Error(`Resposta inválida do servidor (HTTP ${res.status}, ${contentType || "sem content-type"})`);
  }
  if (body === null) {
    throw new Error(`Resposta JSON inválida do servidor (HTTP ${res.status})`);
  }
  if (!res.ok) {
    throw new Error((body?.detail as string) || `HTTP ${res.status}`);
  }
  return body as T;
}

export const authApi = {
  async register(name: string, email: string, password: string, remember = true): Promise<AuthResponse> {
    return request<AuthResponse>("/register", {
      method: "POST",
      body: JSON.stringify({ name, email, password, remember }),
    });
  },
  async login(email: string, password: string, remember = true): Promise<AuthResponse> {
    return request<AuthResponse>("/login", {
      method: "POST",
      body: JSON.stringify({ email, password, remember }),
    });
  },
  async logout(token?: string): Promise<void> {
    await request("/logout", { method: "POST" }, token);
  },
  async me(token?: string): Promise<{ ok: boolean; user: AuthUser }> {
    return request("/me", {}, token);
  },
};

const ADMIN_BASE = "/api/admin";

export const adminApi = {
  async users(token: string): Promise<{ ok: boolean; users: AuthUser[] }> {
    const res = await fetch(`${ADMIN_BASE}/users`, { headers: { Authorization: `Bearer ${token}` } });
    const body = await res.json().catch(() => null);
    if (!res.ok) throw new Error((body?.detail as string) || `HTTP ${res.status}`);
    return body;
  },
  async createUser(token: string, data: { name: string; email: string; password: string; role?: string }): Promise<{ ok: boolean; user: AuthUser }> {
    const res = await fetch(`${ADMIN_BASE}/users`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify(data),
    });
    const body = await res.json().catch(() => null);
    if (!res.ok) throw new Error((body?.detail as string) || `HTTP ${res.status}`);
    return body;
  },
  async setRole(token: string, userId: string, role: string): Promise<{ ok: boolean; user: AuthUser }> {
    const res = await fetch(`${ADMIN_BASE}/users/role`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ userId, role }),
    });
    const body = await res.json().catch(() => null);
    if (!res.ok) throw new Error((body?.detail as string) || `HTTP ${res.status}`);
    return body;
  },
  async resetPassword(token: string, userId: string, password: string): Promise<{ ok: boolean }> {
    const res = await fetch(`${ADMIN_BASE}/users/${encodeURIComponent(userId)}/password`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ password }),
    });
    const body = await res.json().catch(() => null);
    if (!res.ok) throw new Error((body?.detail as string) || `HTTP ${res.status}`);
    return body;
  },
};