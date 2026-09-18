import type { ThemeId } from "@/types/idea";

export interface ThemeSpec {
  id: ThemeId;
  name: string;
  emoji: string;
  desc: string;
  accent: string;
}

export const THEMES: ThemeSpec[] = [
  { id: "ocean", name: "Dark Ocean", emoji: "🌊", desc: "Preto + azul profundo + detalhes aquáticos.", accent: "#00b4ff" },
  { id: "vasco", name: "Vasco", emoji: "⚓", desc: "Preto + branco + vermelho. São Januário sutil.", accent: "#c8102e" },
  { id: "cyber", name: "Cyber", emoji: "🌈", desc: "Preto + tons tecnológicos neon.", accent: "#00e5ff" },
  { id: "midnight", name: "Midnight", emoji: "🌙", desc: "Preto + roxo/azul.", accent: "#8b5cf6" },
  { id: "graphite", name: "Graphite", emoji: "🩶", desc: "Cinza escuro + branco.", accent: "#9ca3af" },
];

export function getTheme(id: ThemeId | string): ThemeSpec {
  return THEMES.find((t) => t.id === id) ?? THEMES[0];
}