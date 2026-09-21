import { useState } from "react";
import { useIdeStore } from "@/store/useIdeStore";
import { AGENT_ROSTER } from "@/data/agents";
import { nemoApi } from "@/api/nemo";
import type { CalendarEvent, EventCategory } from "@/types/idea";

export const EVENT_CATEGORIES: { id: EventCategory; label: string; color: string }[] = [
  { id: "trabalho", label: "💼 Trabalho", color: "#38bdf8" },
  { id: "reuniao", label: "🤝 Reunião", color: "#a78bfa" },
  { id: "estudos", label: "📚 Estudos", color: "#34d399" },
  { id: "pessoal", label: "🏠 Pessoal", color: "#f472b6" },
  { id: "lembrete", label: "🔔 Lembrete", color: "#fbbf24" },
  { id: "outro", label: "📌 Outro", color: "#94a3b8" },
];

export function categoryMeta(cat: EventCategory): { label: string; color: string } {
  return EVENT_CATEGORIES.find((c) => c.id === cat) ?? EVENT_CATEGORIES[EVENT_CATEGORIES.length - 1];
}

interface EventModalProps {
  event?: CalendarEvent | null;
  defaultDate: string;
  onClose: () => void;
}

export function EventModal({ event, defaultDate, onClose }: EventModalProps) {
  const addEvent = useIdeStore((s) => s.addEvent);
  const updateEvent = useIdeStore((s) => s.updateEvent);
  const deleteEvent = useIdeStore((s) => s.deleteEvent);
  const notify = useIdeStore((s) => s.notify);

  const today = new Date();
  const [title, setTitle] = useState(event?.title ?? "");
  const [description, setDescription] = useState(event?.description ?? "");
  const [date, setDate] = useState(event?.date ?? defaultDate);
  const [time, setTime] = useState(event?.time ?? "09:00");
  const [duration, setDuration] = useState(event?.durationMin ?? 60);
  const [category, setCategory] = useState<EventCategory>(event?.category ?? "trabalho");
  const [agentId, setAgentId] = useState(event?.agentId ?? "nemo");
  const [remind, setRemind] = useState(event?.remind ?? 15);

  const save = async () => {
    if (!title.trim() || !date.trim()) {
      notify({ icon: "⚠️", text: "Preencha título e data do evento.", tone: "warn" });
      return;
    }
    const payload = { title: title.trim(), description: description.trim(), date, time, durationMin: Number(duration) || 60, category, agentId, remind: Number(remind) || 0 };
    if (event) {
      updateEvent(event.id, payload);
      nemoApi.updateEvent(event.id, payload).catch(() => undefined);
      notify({ icon: "📅", text: `Evento atualizado: ${payload.title}`, tone: "ok" });
    } else {
      const id = addEvent(payload);
      nemoApi.createEvent({ ...payload, id }).catch(() => undefined);
      notify({ icon: "📅", text: `Evento criado: ${payload.title}`, tone: "ok" });
    }
    onClose();
  };

  const remove = async () => {
    if (!event) return;
    if (!window.confirm(`Excluir o evento "${event.title}"?`)) return;
    deleteEvent(event.id);
    nemoApi.deleteEvent(event.id).catch(() => undefined);
    notify({ icon: "🗑️", text: `Evento excluído: ${event.title}`, tone: "info" });
    onClose();
  };

  return (
    <div className="modal-mask" onClick={onClose}>
      <div className="modal-card" style={{ width: "min(520px,94vw)" }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div
            className="agent-ava"
            style={{ width: 36, height: 36, borderRadius: 10, background: categoryMeta(category).color, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 17 }}
          >
            {categoryMeta(category).label.split(" ")[0]}
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700, fontSize: 16 }}>{event ? "Editar evento" : "Novo evento"}</div>
            <div style={{ color: "var(--text3)", fontSize: 12 }}>
              {new Date(date + "T00:00").toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "long" })}
            </div>
          </div>
          <button className="icon-btn" onClick={onClose} style={{ fontSize: 16 }}>✕</button>
        </div>

        <div className="modal-body">
          <div className="ev-form">
            <label>
              <span>Título *</span>
              <input className="ev-in" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Ex.: Estudar programação" autoFocus />
            </label>

            <label>
              <span>Descrição</span>
              <textarea className="ev-in" rows={2} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Detalhes do evento (opcional)" />
            </label>

            <div className="ev-grid">
              <label>
                <span>Data *</span>
                <input className="ev-in" type="date" value={date} min={`${today.getFullYear()}-01-01`} onChange={(e) => setDate(e.target.value)} />
              </label>
              <label>
                <span>Horário</span>
                <input className="ev-in" type="time" value={time} onChange={(e) => setTime(e.target.value)} />
              </label>
              <label>
                <span>Duração</span>
                <select className="ev-in" value={duration} onChange={(e) => setDuration(Number(e.target.value))}>
                  {[15, 30, 45, 60, 90, 120, 180, 240, 480].map((m) => (
                    <option key={m} value={m}>{m < 60 ? `${m} min` : m % 60 === 0 ? `${m / 60}h` : `${Math.floor(m / 60)}h ${m % 60}min`}</option>
                  ))}
                </select>
              </label>
            </div>

            <div className="ev-grid">
              <label>
                <span>Categoria</span>
                <select className="ev-in" value={category} onChange={(e) => setCategory(e.target.value as EventCategory)}>
                  {EVENT_CATEGORIES.map((c) => (
                    <option key={c.id} value={c.id}>{c.label}</option>
                  ))}
                </select>
              </label>
              <label>
                <span>Agente responsável</span>
                <select className="ev-in" value={agentId} onChange={(e) => setAgentId(e.target.value)}>
                  {AGENT_ROSTER.map((a) => (
                    <option key={a.id} value={a.id}>{a.name}</option>
                  ))}
                </select>
              </label>
              <label>
                <span>Lembrete</span>
                <select className="ev-in" value={remind} onChange={(e) => setRemind(Number(e.target.value))}>
                  <option value={0}>Sem lembrete</option>
                  <option value={10}>10 min antes</option>
                  <option value={30}>30 min antes</option>
                  <option value={60}>1 h antes</option>
                  <option value={360}>6 h antes</option>
                  <option value={1440}>1 dia antes</option>
                </select>
              </label>
            </div>
          </div>
        </div>

        <div className="modal-foot">
          {event && (
            <button className="tool-btn" style={{ color: "var(--danger)", borderColor: "var(--danger)" }} onClick={remove}>
              🗑️ Excluir
            </button>
          )}
          <div style={{ flex: 1 }} />
          <button className="tool-btn" onClick={onClose}>Cancelar</button>
          <button className="tool-btn primary" onClick={save}>💾 Salvar</button>
        </div>
      </div>
    </div>
  );
}