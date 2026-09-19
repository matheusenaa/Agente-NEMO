import { useEffect, useRef } from "react";
import { useSquadStore } from "@/store/useSquadStore";
import type { WsMessage } from "@/types/state";

const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;
const WS_FAIL_THRESHOLD = 3;
const POLL_INTERVAL_MS = 3000;

// Em produção (backend FastAPI) o snapshot de squads vive em /api/nemo/snapshot.
// No dev (plugin Vite squadWatcher) ele fica em /api/snapshot. O polling tenta
// ambos para funcionar nos dois ambientes.
const SNAPSHOT_URLS = ["/api/nemo/snapshot", "/api/snapshot"];

export function useSquadSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const setConnected = useSquadStore((s) => s.setConnected);
  const setSnapshot = useSquadStore((s) => s.setSnapshot);
  const updateSquadState = useSquadStore((s) => s.updateSquadState);
  const setSquadInactive = useSquadStore((s) => s.setSquadInactive);

  useEffect(() => {
    let disposed = false;
    let pollingMode = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    let reconnectDelay = RECONNECT_BASE_MS;
    let wsFailCount = 0;

    function dispatch(msg: WsMessage) {
      if (disposed) return;
      switch (msg.type) {
        case "SNAPSHOT":
          setSnapshot(msg.squads, msg.activeStates);
          break;
        case "SQUAD_UPDATE":
          updateSquadState(msg.squad, msg.state);
          break;
        case "SQUAD_INACTIVE":
          setSquadInactive(msg.squad);
          break;
      }
    }

    // ── HTTP polling fallback ───────────────────────────────────────────

    function stopPolling() {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    }

    function startPolling() {
      stopPolling();

      const poll = async () => {
        if (disposed) return;
        // Tenta as URLs em ordem: produção primeiro (backend), depois dev (plugin Vite).
        for (const url of SNAPSHOT_URLS) {
          if (disposed) return;
          try {
            const res = await fetch(url, { cache: "no-store" });
            if (!res.ok) continue;
            const data = await res.json();
            if (data && Array.isArray(data.squads)) {
              const msg: WsMessage = {
                type: "SNAPSHOT",
                squads: data.squads,
                activeStates: data.activeStates && typeof data.activeStates === "object"
                  ? data.activeStates
                  : {},
              };
              dispatch(msg);
              setConnected(true);
              break;
            }
          } catch {
            // tenta a próxima URL no próximo ciclo
          }
        }
      };

      poll();
      pollTimerRef.current = setInterval(poll, POLL_INTERVAL_MS);
    }

    // ── WebSocket connection ────────────────────────────────────────────

    function connect() {
      if (disposed) return;

      if (reconnectTimer !== undefined) {
        clearTimeout(reconnectTimer);
        reconnectTimer = undefined;
      }

      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const ws = new WebSocket(
        `${protocol}//${window.location.host}/__squads_ws`,
      );
      wsRef.current = ws;

      ws.onopen = () => {
        if (disposed) { ws.close(); return; }
        setConnected(true);
        reconnectDelay = RECONNECT_BASE_MS;
        wsFailCount = 0;
        if (pollingMode) {
          pollingMode = false;
          stopPolling();
        }
      };

      ws.onmessage = (event) => {
        if (disposed) return;
        try {
          const msg: WsMessage = JSON.parse(event.data);
          dispatch(msg);
        } catch {
          // Ignore malformed messages
        }
      };

      ws.onclose = () => {
        if (disposed) return;

        setConnected(false);
        wsFailCount++;

        if (wsFailCount >= WS_FAIL_THRESHOLD) {
          // Em produção não há WS de squads — desiste do WS e usa polling HTTP.
          pollingMode = true;
          startPolling();
          return;
        }

        reconnectTimer = setTimeout(() => {
          reconnectDelay = Math.min(reconnectDelay * 2, RECONNECT_MAX_MS);
          connect();
        }, reconnectDelay);
      };

      ws.onerror = () => {
        // onerror is always followed by onclose — just let onclose handle it.
        // Don't call ws.close() here to avoid "closed before established" in StrictMode.
      };
    }

    connect();
    // Poll imediatamente: em produção não há WS de squads e este primeiro
    // poll popula o snapshot (OfficeView/sidebar) sem esperar falhas do WS.
    startPolling();

    return () => {
      disposed = true;
      if (reconnectTimer !== undefined) clearTimeout(reconnectTimer);
      stopPolling();
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [setConnected, setSnapshot, updateSquadState, setSquadInactive]);
}
