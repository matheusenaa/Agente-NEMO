import { useEffect, useState, useCallback } from "react";

export type NetworkStatus = "online" | "offline" | "reconnecting" | "syncing";

interface NetworkState {
  status: NetworkStatus;
  lastOnline: number | null;
  lastOffline: number | null;
}

export function useNetworkStatus(): NetworkState & {
  checkConnection: () => Promise<boolean>;
} {
  const [state, setState] = useState<NetworkState>({
    status: typeof navigator !== "undefined" ? (navigator.onLine ? "online" : "offline") : "online",
    lastOnline: typeof navigator !== "undefined" && navigator.onLine ? Date.now() : null,
    lastOffline: typeof navigator !== "undefined" && !navigator.onLine ? Date.now() : null,
  });

  const checkConnection = useCallback(async (): Promise<boolean> => {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 5000);
      await fetch("/api/nemo/health", {
        method: "HEAD",
        cache: "no-cache",
        signal: controller.signal,
      });
      clearTimeout(timeout);
      return true;
    } catch {
      return false;
    }
  }, []);

  useEffect(() => {
    const handleOnline = () => {
      setState((prev) => ({ ...prev, status: "reconnecting", lastOnline: Date.now() }));
      checkConnection().then((ok) => {
        setState((prev) => ({ ...prev, status: ok ? "online" : "offline" }));
      });
    };

    const handleOffline = () => {
      setState((prev) => ({ ...prev, status: "offline", lastOffline: Date.now() }));
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [checkConnection]);

  return { ...state, checkConnection };
}

export function usePeriodicSync(
  onSync: () => Promise<void>,
  intervalMs = 30000,
  enabled = true
) {
  useEffect(() => {
    if (!enabled) return;

    let mounted = true;
    let timer: ReturnType<typeof setInterval>;

    const runSync = async () => {
      if (!mounted) return;
      try {
        await onSync();
      } catch {
        // Silently fail - sync will retry on next interval
      }
    };

    timer = setInterval(runSync, intervalMs);

    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, [onSync, intervalMs, enabled]);
}