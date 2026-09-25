import { create } from "zustand";
import { persist } from "zustand/middleware";
import { authApi, type AuthUser } from "@/api/auth";

interface AuthState {
  user: AuthUser | null;
  token: string;
  /** true durante a validação inicial da sessão salva */
  checking: boolean;
  error: string | null;
  login: (email: string, password: string, remember?: boolean) => Promise<boolean>;
  register: (name: string, email: string, password: string, remember?: boolean) => Promise<boolean>;
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

      login: async (email, password, remember = true) => {
        set({ error: null });
        try {
          const res = await authApi.login(email, password, remember);
          set({ user: res.user, token: "", checking: false });
          return true;
        } catch (err) {
          set({ error: (err as Error).message, checking: false });
          return false;
        }
      },

      register: async (name, email, password, remember = true) => {
        set({ error: null });
        try {
          const res = await authApi.register(name, email, password, remember);
          set({ user: res.user, token: "", checking: false });
          return true;
        } catch (err) {
          set({ error: (err as Error).message, checking: false });
          return false;
        }
      },

      logout: async () => {
        const token = get().token || undefined;
        try {
          await authApi.logout(token);
        } catch {
          set({ error: null });
        }
        try {
          localStorage.removeItem("nemo-auth");
          localStorage.removeItem("nemo-user-name");
        } catch {
          set({ error: null });
        }
        set({ user: null, token: "", checking: false, error: null });
      },

      restore: async () => {
        const legacyToken = get().token || undefined;
        try {
          const res = await authApi.me(legacyToken);
          set({ user: res.user, token: "", checking: false, error: null });
        } catch {
          set({ user: null, token: "", checking: false, error: null });
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: "nemo-auth",
      partialize: (s) => ({ user: s.user }),
    },
  ),
);