import { useEffect, useMemo, useState } from "react";
import { useIdeStore } from "@/store/useIdeStore";
import { nemoApi } from "@/api/nemo";
import { getAgent } from "@/data/agents";
import type { CalendarEvent } from "@/types/idea";
import { monthGrid, toISO, todayISO, eventSortDate } from "@/lib/calendar";
import { AgentAvatar } from "@/components/AgentAvatar";
import { EventModal, categoryMeta } from "./EventModal";

const WEEKDAYS = ["SEG", "TER", "QUA", "QUI", "SEX", "SAB", "DOM"];
const MONTHS = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];

export function CalendarView() {
  const events = useIdeStore((s) => s.events);
  const setEvents = useIdeStore((s) => s.setEvents);
  const notify = useIdeStore((s) => s.notify);

  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth());
  const [modal, setModal] = useState<{ event: CalendarEvent | null; date: string } | null>(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const serverEvents = await nemoApi.listEvents();
        if (!alive || serverEvents.length === 0) return;
        const merged = new Map(events.map((e) => [e.id, e]));
        serverEvents.forEach((se) => merged.set(se.id, se));
        setEvents(Array.from(merged.values()));
        notify({ icon: "📅", text: `Calendário sincronizado (${serverEvents.length} evento(s) no servidor)`, tone: "info" });
      } catch {
        /* backend offline — usa o armazenamento local persistido */
      }
    })();
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const grid = useMemo(() => monthGrid(year, month), [year, month]);
  const monthKey = (d: Date) => toISO(d.getFullYear(), d.getMonth(), d.getDate());
  const byDay = useMemo(() => {
    const map = new Map<string, CalendarEvent[]>();
    for (const e of events) {
      const list = map.get(e.date) ?? [];
      list.push(e);
      map.set(e.date, list);
    }
    for (const list of map.values()) list.sort((a, b) => eventSortDate(a).localeCompare(eventSortDate(b)));
    return map;
  }, [events]);

  const today = todayISO();
  const monthEvents = events.filter((e) => e.date.startsWith(`${year}-${String(month + 1).padStart(2, "0")}`));

  const prevMonth = () => setMonth((m) => (m === 0 ? (setYear((y) => y - 1), 11) : m - 1));
  const nextMonth = () => setMonth((m) => (m === 11 ? (setYear((y) => y + 1), 0) : m + 1));
  const goToday = () => {
    const d = new Date();
    setYear(d.getFullYear());
    setMonth(d.getMonth());
  };

  return (
    <section className="view-area">
      <div className="cal-wrap">
        <div className="cal-head">
          <div className="cal-title">
            <span style={{ fontSize: 20, fontWeight: 700 }}>
              📅 {MONTHS[month]} {year}
            </span>
            <span className="status-pill">{monthEvents.length} evento(s)</span>
          </div>
          <div className="cal-nav">
            <button className="tool-btn" onClick={goToday} title="Ir para hoje">Hoje</button>
            <button className="icon-btn" onClick={prevMonth} title="Mês anterior">◀</button>
            <span className="cal-ym">{MONTHS[month].slice(0, 3)} {year}</span>
            <button className="icon-btn" onClick={nextMonth} title="Próximo mês">▶</button>
            <button className="tool-btn primary" onClick={() => setModal({ event: null, date: today })}>+ Novo evento</button>
          </div>
        </div>

        <div className="cal-grid">
          {WEEKDAYS.map((w) => (
            <div key={w} className="cal-wd">{w}</div>
          ))}

          {grid.weeks.flat().map((d, i) => {
            const key = monthKey(d);
            const inMonth = d.getMonth() === month;
            const isToday = key === today;
            const dayEvents = byDay.get(key) ?? [];

            return (
              <div
                key={`${key}-${i}`}
                className={`cal-cell ${inMonth ? "" : "dim"} ${isToday ? "today" : ""}`}
                onClick={() => setModal({ event: null, date: key })}
              >
                <div className="cal-daynum">{inMonth ? d.getDate() : ""}</div>
                <div className="cal-events">
                  {dayEvents.slice(0, 3).map((e) => (
                    <button
                      key={e.id}
                      className="cal-chip"
                      title={`${e.title} · ${e.time} · ${getAgent(e.agentId).name}`}
                      style={{ borderLeftColor: categoryMeta(e.category).color }}
                      onClick={(ev) => {
                        ev.stopPropagation();
                        setModal({ event: e, date: key });
                      }}
                    >
                      <span className="cal-chip-time">{e.time ?? "09:00"}</span>
                      <span className="cal-chip-title">{e.title}</span>
                    </button>
                  ))}
                  {dayEvents.length > 3 && (
                    <div className="cal-more">+{dayEvents.length - 3} mais</div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {events.length > 0 && (
          <div className="cal-list">
            <div className="cal-list-title">Próximos eventos</div>
            {events
              .filter((e) => eventSortDate(e) >= today + "T00:00")
              .sort((a, b) => eventSortDate(a).localeCompare(eventSortDate(b)))
              .slice(0, 6)
              .map((e) => {
                const cat = categoryMeta(e.category);
                const agents = getAgent(e.agentId);
                return (
                  <button key={e.id} className="cal-list-item clickable" onClick={() => setModal({ event: e, date: e.date })}>
                    <span className="cal-dot" style={{ background: cat.color }} />
                    <AgentAvatar id={e.agentId} accent={agents.color} size={22} badge={agents.icon} />
                    <span className="cal-list-date">{e.date === today ? "Hoje" : new Date(e.date + "T00:00").toLocaleDateString("pt-BR", { day: "2-digit", month: "short" })}</span>
                    <span className="cal-list-time">{e.time}</span>
                    <span className="cal-list-title">
                      <b>{e.title}</b>
                      {e.description && <small>{e.description.slice(0, 60)}</small>}
                    </span>
                    <span className="cal-list-agent">{agents.name}</span>
                  </button>
                );
              })}
          </div>
        )}
      </div>

      {modal && <EventModal event={modal.event} defaultDate={modal.date} onClose={() => setModal(null)} />}
    </section>
  );
}