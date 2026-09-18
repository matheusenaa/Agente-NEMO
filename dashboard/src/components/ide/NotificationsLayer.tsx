import { useEffect } from "react";
import { useIdeStore } from "@/store/useIdeStore";

const AUTO_DISMISS_MS = 6000;

export function NotificationsLayer() {
  const notifications = useIdeStore((s) => s.notifications);
  const dismissNotif = useIdeStore((s) => s.dismissNotif);
  const animations = useIdeStore((s) => s.config.animations);
  const notifIds = notifications.map((n) => n.id).join("|");

  useEffect(() => {
    if (!animations) return;
    const timers = notifications.map((n) => setTimeout(() => dismissNotif(n.id), AUTO_DISMISS_MS));
    return () => timers.forEach(clearTimeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [notifIds, animations]);

  if (notifications.length === 0) return null;

  return (
    <div className="toast-layer">
      {notifications.map((n) => (
        <div key={n.id} className={`toast-x ${n.tone}`} onClick={() => dismissNotif(n.id)}>
          <span style={{ fontSize: 18 }}>{n.icon}</span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontWeight: 600 }}>{n.text}</div>
            <div style={{ fontSize: 11, color: "var(--text3)" }}>
              {new Date(n.time).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
            </div>
          </div>
          <span style={{ color: "var(--text3)", cursor: "pointer" }}>✕</span>
        </div>
      ))}
    </div>
  );
}