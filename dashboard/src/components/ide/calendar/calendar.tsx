import { useMemo, useState } from "react";
import { useIdeStore } from "@/store/useIdeStore";
import { AGENT_ROSTER } from "@/data/agents";
import type { CalendarEvent } from "@/types/idea";

const MONTHS = [
  "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];

const WEEKDAYS = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

const CATEGORIES = [
  { id: "Tarefa", color: "#00b4ff" },
  { id: "Reunião", color: "#c8102e" },
  { id: "Estudo", color: "#8b5cf6" },
  { id: "Pessoal", color: "#00e676" },
];

function categoryColor(cat: string): string {
  return CATEGORIES.find((c) => c.id === cat)?.color ?? "#00b4ff";
}

const pad = (n: number) => String(n).padStart(2, "0");
const toISO = (year: number, month: number, day: number) => `${year}-${pad(month + 1)}-${pad(day)}`;

const emptyForm = (date: string) => ({
  title: "",
  description: "",
  date,
  startTime: "19:00",
  duration: 60,
  category: "Tarefa",
  agentId: "nemo",
  reminder: false,
});

type FormState = ReturnType<typeof emptyForm>;

export function CalendarView() {
  const events = useIdeStore((s) => s.calendarEvents);
  const addCalendarEvent = useIdeStore((s) => s.addCalendarEvent);
  const updateCalendarEvent = useIdeStore((s) => s.updateCalendarEvent);
  const deleteCalendarEvent = useIdeStore((s) => s.deleteCalendarEvent);
  const notify = useIdeStore((s) => s.notify);

  const [currentYear, setCurrentYear] = useState<number>(new Date().getFullYear());
  const [currentMonth, setCurrentMonth] = useState<number>(new Date().getMonth());
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm(toISO(new Date().getFullYear(), new Date().getMonth(), new Date().getDate())));

  const todayISO = toISO(new Date().getFullYear(), new Date().getMonth(), new Date().getDate());

  const padForm = (patch: Partial<FormState>) => setForm((f) => ({ ...f, ...patch }));

  const grid = useMemo(() => {
    const cells: { date: string; day: number; events: CalendarEvent[]; inMonth: boolean; selected: boolean; today: boolean }[] = [];
    const firstIndex = new Date(currentYear, currentMonth, 1).getDay();
    const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
    const daysInPrev = new Date(currentYear, currentMonth, 0).getDate();

    for (let i = firstIndex - 1; i >= 0; i--) {
      cells.push({ date: toISO(currentYear, currentMonth - 1 < 0 ? 11 : currentMonth - 1, daysInPrev - i), day: daysInPrev - i, events: [], inMonth: false, selected: false, today: false });
    }
    for (let d = 1; d <= daysInMonth; d++) {
      const date = toISO(currentYear, currentMonth, d);
      const dayEvents = events.filter((e) => e.date === date);
      cells.push({ date, day: d, events: dayEvents, inMonth: true, selected: selectedDate === date, today: date === todayISO });
    }
    while (cells.length < 42) {
      const last = cells.length - firstIndex + 1;
      const nextMonth = currentMonth + 1 > 11 ? 0 : currentMonth + 1;
      const nextYear = currentMonth + 1 > 11 ? currentYear + 1 : currentYear;
      const d = last;
      cells.push({ date: toISO(nextYear, nextMonth, d), day: d, events: [], inMonth: false, selected: false, today: false });
    }
    return cells;
  }, [currentYear, currentMonth, events, selectedDate, todayISO]);

  const dayEvents = selectedDate ? events.filter((e) => e.date === selectedDate) : [];

  const navigateMonth = (delta: number) => {
    let m = currentMonth + delta;
    let y = currentYear;
    if (m < 0) { m = 11; y -= 1; }
    if (m > 11) { m = 0; y += 1; }
    setCurrentMonth(m);
    setCurrentYear(y);
  };

  const openCreate = (date: string) => {
    setEditingId(null);
    setForm(emptyForm(date || selectedDate || todayISO));
    setModalOpen(true);
  };

  const openEdit = (ev: CalendarEvent) => {
    setEditingId(ev.id);
    setForm({
      title: ev.title,
      description: ev.description ?? "",
      date: ev.date,
      startTime: ev.startTime,
      duration: ev.duration,
      category: ev.category,
      agentId: ev.agentId,
      reminder: ev.reminder,
    });
    setModalOpen(true);
  };

  const submit = () => {
    if (!form.title.trim()) {
      notify({ icon: "⚠️", text: "Informe um título para o evento.", tone: "warn" });
      return;
    }
    if (editingId) {
      updateCalendarEvent(editingId, {
        title: form.title.trim(),
        description: form.description.trim() || undefined,
        date: form.date || toISO(currentYear, currentMonth, 1),
        startTime: form.startTime,
        duration: Number(form.duration) || 60,
        category: form.category,
        agentId: form.agentId,
        reminder: form.reminder,
      });
      notify({ icon: "📅", text: "Evento atualizado.", tone: "ok" });
    } else {
      addCalendarEvent({
        title: form.title.trim(),
        description: form.description.trim() || undefined,
        date: form.date || toISO(currentYear, currentMonth, 1),
        startTime: form.startTime,
        duration: Number(form.duration) || 60,
        category: form.category,
        agentId: form.agentId,
        reminder: form.reminder,
      });
    }
    setModalOpen(false);
    setSelectedDate(form.date);
  };

  const remove = () => {
    if (editingId) deleteCalendarEvent(editingId);
    setModalOpen(false);
  };

  const agents = AGENT_ROSTER;

  return (
    <div className="calendar-view" style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", padding: "16px 20px", overflowY: "auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap", marginBottom: 14 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <button onClick={() => openCreate(selectedDate ?? todayISO)} className="tool-btn primary" style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
            ＋ Novo evento
          </button>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button className="icon-btn" onClick={() => navigateMonth(-1)} title="Mês anterior">←</button>
          <span style={{ fontWeight: 700, fontSize: "1.05rem", minWidth: 160, textAlign: "center" }}>
            {MONTHS[currentMonth]} {currentYear}
          </span>
          <button className="icon-btn" onClick={() => navigateMonth(1)} title="Próximo mês">→</button>
        </div>
      </div>

      {selectedDate && (
        <div style={{ marginBottom: 12, fontSize: 12 }}>
          <button
            className="tool-btn"
            onClick={() => setSelectedDate(null)}
            title="Limpar seleção de data"
          >
            ✕ {new Date(selectedDate + "T12:00:00").toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" })}
          </button>
        </div>
      )}

      <div className="calendar-grid" style={{ display: "grid", gridTemplateColumns: "repeat(7, minmax(0,1fr))", gap: 6 }}>
        {WEEKDAYS.map((d) => (
          <div key={d} style={{ fontSize: 11, fontWeight: 700, color: "var(--text3)", textAlign: "center", textTransform: "uppercase", letterSpacing: 1, padding: 6, borderBottom: "1px solid var(--border)" }}>
            {d}
          </div>
        ))}
        {grid.map((cell) => (
          <button
            key={cell.date}
            title={`${cell.day} de ${MONTHS[cell.date[5] === "0" ? Number(cell.date[6]) - 1 : Number(cell.date.slice(5, 7)) - 1]}${cell.events.length ? ` · ${cell.events.length} evento(s)` : ""}`}
            onClick={() => setSelectedDate(cell.date)}
            style={{
              minHeight: 74,
              display: "flex",
              flexDirection: "column",
              alignItems: "stretch",
              gap: 3,
              padding: 6,
              borderRadius: 10,
              border: cell.selected ? "1.5px solid var(--accent)" : "1px solid var(--border)",
              background: cell.selected ? "color-mix(in srgb, var(--accent) 12%, var(--bg2))" : cell.today ? "color-mix(in srgb, var(--accent) 7%, var(--bg2))" : "var(--bg2)",
              opacity: cell.inMonth ? 1 : 0.42,
              cursor: "pointer",
              textAlign: "left",
              fontFamily: "inherit",
              color: "var(--text)",
              transition: "border-color .15s, transform .1s",
            }}
          >
            <span style={{ fontSize: 12, fontWeight: cell.today ? 800 : 600, color: cell.today ? "var(--accent)" : "var(--text2)" }}>
              {cell.day}
            </span>
            {cell.events.slice(0, 2).map((ev) => (
              <span key={ev.id} style={{ fontSize: 10, lineHeight: 1.2, padding: "2px 5px", borderRadius: 5, background: "var(--bg3)", color: "var(--text)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", borderLeft: `3px solid ${categoryColor(ev.category)}` }}>
                {ev.startTime} {ev.title}
              </span>
            ))}
            {cell.events.length > 2 && (
              <span style={{ fontSize: 10, color: "var(--text3)" }}>+{cell.events.length - 2} mais</span>
            )}
          </button>
        ))}
      </div>

      <div style={{ marginTop: 16 }}>
        <h4 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 8px", color: "var(--text2)", textTransform: "uppercase", letterSpacing: 1 }}>
          {selectedDate ? `Eventos de ${new Date(selectedDate + "T12:00:00").toLocaleDateString("pt-BR")}` : "Eventos do dia"}
        </h4>
        {!selectedDate && <p style={{ fontSize: 12, color: "var(--text3)" }}>Selecione um dia no calendário para ver os eventos.</p>}
        {selectedDate && dayEvents.length === 0 && (
          <p style={{ fontSize: 12, color: "var(--text3)" }}>
            Nenhum evento neste dia.{" "}
            <a href="#" onClick={(e) => { e.preventDefault(); openCreate(selectedDate); }} style={{ color: "var(--accent)" }}>Criar evento</a>
          </p>
        )}
        {dayEvents.map((ev) => {
          const agent = agents.find((a) => a.id === ev.agentId);
          return (
            <button
              key={ev.id}
              onClick={() => openEdit(ev)}
              title="Editar / excluir evento"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                width: "100%",
                textAlign: "left",
                background: "var(--bg2)",
                border: "1px solid var(--border)",
                borderRadius: 10,
                padding: "10px 12px",
                marginBottom: 6,
                cursor: "pointer",
                fontFamily: "inherit",
                color: "var(--text)",
                transition: "border-color .15s",
              }}
            >
              <span style={{ width: 10, height: 34, borderRadius: 5, background: categoryColor(ev.category), flexShrink: 0 }} />
              <span style={{ flex: 1, minWidth: 0 }}>
                <span style={{ display: "block", fontWeight: 600, fontSize: 13 }}>{ev.title}</span>
                <span style={{ display: "block", fontSize: 11, color: "var(--text3)" }}>
                  {ev.startTime} · {ev.duration}min{ev.reminder ? " · 🔔" : ""}
                </span>
                {ev.description && <span style={{ display: "block", fontSize: 12, color: "var(--text2)", marginTop: 2 }}>{ev.description}</span>}
              </span>
              <span style={{ fontSize: 11, color: "var(--text3)", background: "var(--bg3)", padding: "4px 8px", borderRadius: 20, whiteSpace: "nowrap" }}>
                {agent ? `${agent.icon} ${agent.name}` : ev.agentId}
              </span>
            </button>
          );
        })}
      </div>

      {modalOpen && (
        <div className="modal-mask" onClick={() => setModalOpen(false)}>
          <div className="modal-card" style={{ width: "min(480px, 94vw)" }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <span style={{ fontSize: 18 }}>{editingId ? "✏️" : "📅"}</span>
              <div>
                <div style={{ fontWeight: 700 }}>{editingId ? "Editar evento" : "Novo evento"}</div>
                <div style={{ fontSize: 11, color: "var(--text3)" }}>{editingId ? "Atualize os dados e salve." : "Preencha os dados do compromisso."}</div>
              </div>
            </div>
            <div className="modal-body">
              <label style={{ display: "block", fontSize: 11, fontWeight: 600, margin: "10px 0 4px", color: "var(--text2)" }}>Título *</label>
              <input className="chat-input" style={{ minHeight: 0, padding: "8px 10px", fontSize: 13 }} value={form.title} placeholder="Estudar programação" onChange={(e) => padForm({ title: e.target.value })} />

              <label style={{ display: "block", fontSize: 11, fontWeight: 600, margin: "10px 0 4px", color: "var(--text2)" }}>Descrição</label>
              <input className="chat-input" style={{ minHeight: 0, padding: "8px 10px", fontSize: 13 }} value={form.description} placeholder="Detalhes do evento" onChange={(e) => padForm({ description: e.target.value })} />

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div>
                  <label style={{ display: "block", fontSize: 11, fontWeight: 600, margin: "10px 0 4px", color: "var(--text2)" }}>Data *</label>
                  <input type="date" className="chat-input" style={{ minHeight: 0, padding: "8px 10px", fontSize: 13 }} value={form.date} onChange={(e) => padForm({ date: e.target.value })} />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: 11, fontWeight: 600, margin: "10px 0 4px", color: "var(--text2)" }}>Horário</label>
                  <input type="time" className="chat-input" style={{ minHeight: 0, padding: "8px 10px", fontSize: 13 }} value={form.startTime} onChange={(e) => padForm({ startTime: e.target.value })} />
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div>
                  <label style={{ display: "block", fontSize: 11, fontWeight: 600, margin: "10px 0 4px", color: "var(--text2)" }}>Duração (min)</label>
                  <input type="number" min={15} step={15} className="chat-input" style={{ minHeight: 0, padding: "8px 10px", fontSize: 13 }} value={form.duration} onChange={(e) => padForm({ duration: Number(e.target.value) })} />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: 11, fontWeight: 600, margin: "10px 0 4px", color: "var(--text2)" }}>Categoria</label>
                  <select className="chat-input" style={{ minHeight: 0, padding: "8px 10px", fontSize: 13 }} value={form.category} onChange={(e) => padForm({ category: e.target.value })}>
                    {CATEGORIES.map((c) => <option key={c.id} value={c.id}>{c.id}</option>)}
                  </select>
                </div>
              </div>

              <label style={{ display: "block", fontSize: 11, fontWeight: 600, margin: "10px 0 4px", color: "var(--text2)" }}>Agente responsável</label>
              <select className="chat-input" style={{ minHeight: 0, padding: "8px 10px", fontSize: 13 }} value={form.agentId} onChange={(e) => padForm({ agentId: e.target.value })}>
                {agents.map((a) => <option key={a.id} value={a.id}>{a.icon} {a.name}</option>)}
              </select>

              <label style={{ display: "flex", alignItems: "center", gap: 8, margin: "12px 0 4px", fontSize: 13, cursor: "pointer" }}>
                <input type="checkbox" checked={form.reminder} onChange={(e) => padForm({ reminder: e.target.checked })} style={{ width: 15, height: 15 }} />
                🔔 Lembrete para este evento
              </label>
            </div>
            <div className="modal-head" style={{ justifyContent: "flex-end", gap: 8, borderBottom: "none", borderTop: "1px solid var(--border)" }}>
              {editingId && (
                <button className="tool-btn" style={{ color: "var(--danger)", borderColor: "color-mix(in srgb, var(--danger) 40%, var(--border))" }} onClick={remove}>
                  🗑 Excluir
                </button>
              )}
              <button className="tool-btn" onClick={() => setModalOpen(false)}>Cancelar</button>
              <button className="tool-btn primary" onClick={submit}>{editingId ? "Salvar" : "Criar evento"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}