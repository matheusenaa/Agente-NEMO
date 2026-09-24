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
  token: string;
}

const BASE = "/api/auth";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    throw new Error((body?.detail as string) || `HTTP ${res.status}`);
  }
  return body as T;
}

export const authApi = {
  async register(name: string, email: string, password: string): Promise<AuthResponse> {
    return request<AuthResponse>("/register", {
      method: "POST",
      body: JSON.stringify({ name, email, password }),
    });
  },
  async login(email: string, password: string): Promise<AuthResponse> {
    return request<AuthResponse>("/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },
  async logout(token: string): Promise<void> {
    await request("/logout", {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  },
  async me(token: string): Promise<{ ok: boolean; user: AuthUser }> {
    return request("/me", { headers: { Authorization: `Bearer ${token}` } });
  },
};