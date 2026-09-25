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
  const body = await res.json().catch(() => null);
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