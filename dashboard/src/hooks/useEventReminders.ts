import { useEffect, useRef } from "react";
import { useIdeStore } from "@/store/useIdeStore";

const CHECK_MS = 20_000;

export function useEventReminders() {
  const notified = useRef<Set<string>>(new Set());
  const notify = useIdeStore((s) => s.notify);
  const events = useIdeStore((s) => s.events);

  useEffect(() => {
    const tick = () => {
      const now = Date.now();
      const today = new Date();
      const todayKey = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;

      for (const e of events) {
        const remindMin = Number(e.remind);
        if (!remindMin || remindMin < 0 || !e.time) continue;
        const start = new Date(`${e.date}T${e.time}:00`).getTime();
        if (!isFinite(start)) continue;

        const remindAt = start - remindMin * 60_000;
        const key = `${e.id}@${start}`;
        if (now >= remindAt && now < start && !notified.current.has(key)) {
          notified.current.add(key);
          const when =
            e.date === todayKey
              ? `hoje às ${e.time}`
              : `${new Date(e.date + "T00:00").toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" })} às ${e.time}`;
          notify({ icon: "⏰", text: `Lembrete: ${e.title} — ${when}`, tone: "warn" });
        }
      }
    };

    tick();
    const timer = setInterval(tick, CHECK_MS);
    return () => clearInterval(timer);
  }, [events, notify]);
}