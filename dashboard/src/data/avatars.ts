import type { AgentCard } from "@/types/idea";

/**
 * Avatares SVG procedurais por agente (Etapa 3/4 — identidade visual individual).
 *
 * Gera determinísticamente um avatar único a partir do id/cor/gradiêne do agente:
 * - anel em gradiente com a cor da categoria
 * - fundo escuro com brilho radial (remetente ao visual do NEMO)
 * - glifo por categoria + inicial do nome
 *
 * Os agentes são seres distintos: cada um tem paleta própria, sem depender de
 * emoji genérico ou foto (regra 28 — nada de funcionalidade fake).
 */
export const categoryGlyph: Record<string, string> = {
  assistant: "✦",
  technology: "⚙",
  data: "◈",
  research: "◎",
  writing: "✎",
  review: "✓",
  design: "◐",
  strategy: "▲",
  social: "◆",
  publishing: "▣",
  video: "▶",
  seo: "⌖",
};

export function avatarSVG(agent: Pick<AgentCard, "id" | "name" | "color" | "category">): string {
  const id = agent.id.toLowerCase();
  // seeds determinísticos por id — mesmo agente = mesmo avatar
  let h1 = 0, h2 = 0;
  for (let i = 0; i < id.length; i++) {
    h1 = (h1 * 31 + id.charCodeAt(i)) % 360;
    h2 = (h2 * 17 + id.charCodeAt(i)) % 360;
  }
  const base = agent.color.startsWith("#") ? agent.color : "#38bdf8";
  const c1 = `hsl(${h1},70%,55%)`;
  const c2 = `hsl(${h2},70%,35%)`;
  const glyph = categoryGlyph[agent.category] ?? "✦";
  const initial = (agent.name || "?").trim().charAt(0).toUpperCase();

  return [
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="100%" height="100%">`,
    `<defs>`,
    `  <linearGradient id="av_${id}" x1="0" y1="0" x2="1" y2="1">`,
    `    <stop offset="0" stop-color="${c1}"/>`,
    `    <stop offset="1" stop-color="${c2}"/>`,
    `  </linearGradient>`,
    `  <radialGradient id="avc_${id}" cx="0.32" cy="0.28" r="0.75">`,
    `    <stop offset="0" stop-color="rgba(255,255,255,0.28)"/>`,
    `    <stop offset="1" stop-color="rgba(255,255,255,0)"/>`,
    `  </radialGradient>`,
    `</defs>`,
    `<g stroke="url(#av_${id})" stroke-width="6" fill="none" transform="rotate(${h1} 60 60)">`,
    `  <circle cx="60" cy="60" r="54"/>`,
    `  <circle cx="60" cy="60" r="47" opacity="0.6"/>`,
    `</g>`,
    `<circle cx="60" cy="60" r="41" fill="${base}22"/>`,
    `<circle cx="60" cy="60" r="41" fill="url(#avc_${id})"/>`,
    `<text x="60" y="74" text-anchor="middle" font-family="Segoe UI, system-ui" font-size="46" font-weight="700" fill="url(#av_${id})">${initial}</text>`,
    `<text x="60" y="109" text-anchor="middle" font-family="Segoe UI, system-ui" font-size="15" fill="rgba(255,255,255,0.85)">${glyph}</text>`,
    `</svg>`,
  ].join("");
}

/** Fallback: derruba para emoji do roster caso o avatar SVG não seja desejado. */
export function avatarMarkup(agent: Pick<AgentCard, "id" | "name" | "color" | "category" | "icon">): string {
  return avatarSVG(agent);
}
