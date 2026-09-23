import { create } from "zustand";
import { persist } from "zustand/middleware";
import { authApi, type AuthUser } from "@/api/auth";

interface AuthState {
  user: AuthUser | null;
  token: string;
  /** true durante a validação inicial da sessão salva */
  checking: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<boolean>;
  register: (name: string, email: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  restore: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: "",
      checking: true,
      error: null,

      login: async (email, password) => {
        set({ error: null });
        try {
          const res = await authApi.login(email, password);
          set({ user: res.user, token: res.token, checking: false });
          return true;
        } catch (err) {
          set({ error: (err as Error).message, checking: false });
          return false;
        }
      },

      register: async (name, email, password) => {
        set({ error: null });
        try {
          const res = await authApi.register(name, email, password);
          set({ user: res.user, token: res.token, checking: false });
          return true;
        } catch (err) {
          set({ error: (err as Error).message, checking: false });
          return false;
        }
      },

      logout: async () => {
        const token = get().token;
        try {
          if (token) await authApi.logout(token);
        } catch {
          // sessão já inválida — limpa local mesmo assim
        }
        set({ user: null, token: "", checking: false, error: null });
      },

      restore: async () => {
        const { token } = get();
        if (!token) {
          set({ checking: false });
          return;
        }
        try {
          const res = await authApi.me(token);
          set({ user: res.user, checking: false });
        } catch {
          // token expirado/inválido — desloga localmente
          set({ user: null, token: "", checking: false, error: null });
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: "nemo-auth",
      partialize: (s) => ({ user: s.user, token: s.token }),
    },
  ),
);