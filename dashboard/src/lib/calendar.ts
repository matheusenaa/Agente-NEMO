/** Helpers de data para o calendário NEMO (sem dependências externas). */

export function pad(n: number): string {
  return String(n).padStart(2, "0");
}

export function toISO(y: number, m: number, d: number): string {
  return `${y}-${pad(m + 1)}-${pad(d)}`;
}

export function parseISO(iso: string): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso ?? "");
  if (!m) return null;
  return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
}

export function todayISO(): string {
  const d = new Date();
  return toISO(d.getFullYear(), d.getMonth(), d.getDate());
}

/** Semana que contém `date`, começando na segunda-feira. */
export function weekStart(date: Date): Date {
  const d = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const dow = (d.getDay() + 6) % 7; // 0 = segunda
  d.setDate(d.getDate() - dow);
  return d;
}

export interface MonthGrid {
  year: number;
  month: number; // 0-based
  weeks: Date[][];
}

export function monthGrid(year: number, month: number): MonthGrid {
  const first = new Date(year, month, 1);
  const start = weekStart(first);
  const weeks: Date[][] = [];
  let cursor = start;
  for (let w = 0; w < 6; w++) {
    const week: Date[] = [];
    for (let i = 0; i < 7; i++) {
      week.push(new Date(cursor));
      cursor.setDate(cursor.getDate() + 1);
    }
    weeks.push(week);
    if (cursor.getMonth() !== month && cursor.getFullYear() === year) break;
    if (w === 5) break;
  }
  return { year, month, weeks };
}

/** Compare two ISO dates: -1, 0, 1 */
export function cmpISO(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

export function eventSortDate(e: { date: string; time: string }): string {
  return `${e.date}T${e.time || "00:00"}`;
}

export function fmtLong(iso: string): string {
  const d = parseISO(iso);
  if (!d) return iso;
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "long", year: "numeric" });
}

export function fmtShort(date: Date): string {
  return date.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}

export function isSameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

export function relativeLabel(isoDate: string, now = new Date()): string {
  const d = parseISO(isoDate);
  if (!d) return isoDate;
  const today = now;
  const diffDays = Math.round((new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime() - new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime()) / 86400000);
  if (diffDays === 0) return "Hoje";
  if (diffDays === 1) return "Amanhã";
  if (diffDays === -1) return "Ontem";
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}