/**
 * Especificação determinística de "rosto" por agente.
 *
 * Cada agente da NEMO ganha uma identidade visual própria (tom de pele, corte
 * e cor de cabelo, óculos, acessórios, barba) derivada de um elenco curado e,
 * para ids desconhecidos, de um gerador determinístico. O mesmo id produz
 * sempre o mesmo avatar — sem estado, sem assets externos.
 */

export type HairStyle = "short" | "buzz" | "long" | "bob" | "pixie" | "bun" | "ponytail" | "curly" | "bald";
export type Glasses = "none" | "round" | "square";
export type Accessory = "none" | "headset" | "beret" | "cap" | "bow";

export interface AvatarSpec {
  skin: string;
  hair: string;
  hairStyle: HairStyle;
  gender: "m" | "f";
  glasses: Glasses;
  beard: "none" | "stubble" | "full";
  accessory: Accessory;
  accent: string;
}

const SKIN_TONES = ["#f2c9a0", "#e6b48c", "#dda37b", "#c98a5f", "#b5714a", "#a05e3b", "#8a4f34", "#f7d7b3"];
const HAIR_COLORS = ["#161616", "#2b221a", "#5b3a24", "#7a4b26", "#3d3d3d", "#1f3a5f", "#9d2f2f", "#2f5a47", "#c9a86a", "#d94f4f"];
const HAIR_STYLES: HairStyle[] = ["short", "buzz", "long", "bob", "pixie", "bun", "ponytail", "curly", "bald"];

function hashCode(str: string): number {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0;
  return h;
}

function mulberry32(seed: number): () => number {
  let a = seed;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function pick<T>(rnd: () => number, arr: readonly T[]): T {
  return arr[Math.floor(rnd() * arr.length)];
}

/** Elenco curado: cada agente real do projeto com rosto próprio. */
const ELENCO: Record<string, AvatarSpec> = {
  nemo: { skin: "#dda37b", hair: "#141414", hairStyle: "short", gender: "m", glasses: "none", beard: "stubble", accessory: "headset", accent: "#cf1126" },
  jarvis: { skin: "#e6b48c", hair: "#161616", hairStyle: "short", gender: "m", glasses: "square", beard: "full", accessory: "headset", accent: "#60a5fa" },
  analista: { skin: "#f2c9a0", hair: "#7a4b26", hairStyle: "bun", gender: "f", glasses: "round", beard: "none", accessory: "none", accent: "#38bdf8" },
  pesquisador: { skin: "#e6b48c", hair: "#1f3a5f", hairStyle: "long", gender: "f", glasses: "round", beard: "none", accessory: "none", accent: "#22d3ee" },
  redator: { skin: "#f7d7b3", hair: "#9d2f2f", hairStyle: "curly", gender: "f", glasses: "none", beard: "none", accessory: "none", accent: "#a78bfa" },
  revisor: { skin: "#dda37b", hair: "#2b221a", hairStyle: "bob", gender: "f", glasses: "square", beard: "none", accessory: "none", accent: "#34d399" },
  designer: { skin: "#f2c9a0", hair: "#2f5a47", hairStyle: "pixie", gender: "f", glasses: "none", beard: "none", accessory: "beret", accent: "#f472b6" },
  "criador-video": { skin: "#c98a5f", hair: "#5b3a24", hairStyle: "curly", gender: "m", glasses: "none", beard: "stubble", accessory: "cap", accent: "#c084fc" },
  estrategista: { skin: "#b5714a", hair: "#161616", hairStyle: "buzz", gender: "m", glasses: "round", beard: "none", accessory: "none", accent: "#fb923c" },
  "gestor-redes": { skin: "#f7d7b3", hair: "#d94f4f", hairStyle: "ponytail", gender: "f", glasses: "none", beard: "none", accessory: "bow", accent: "#2dd4bf" },
  "editor-publicador": { skin: "#e6b48c", hair: "#7a4b26", hairStyle: "bob", gender: "f", glasses: "square", beard: "none", accessory: "none", accent: "#fbbf24" },
  seo: { skin: "#dda37b", hair: "#3d3d3d", hairStyle: "curly", gender: "m", glasses: "square", beard: "stubble", accessory: "headset", accent: "#a3e635" },
};

/** Gera um rosto determinístico para um id (fallback genérico). */
function randomSpec(id: string, accent: string): AvatarSpec {
  const rnd = mulberry32(hashCode(id));
  return {
    skin: pick(rnd, SKIN_TONES),
    hair: pick(rnd, HAIR_COLORS),
    hairStyle: pick(rnd, HAIR_STYLES),
    gender: rnd() > 0.5 ? "f" : "m",
    glasses: pick(rnd, ["none", "none", "round", "square"]),
    beard: "none",
    accessory: pick(rnd, ["none", "none", "headset", "beret", "cap"]),
    accent,
  };
}

export function getAvatarSpec(id: string, accent = "#38bdf8"): AvatarSpec {
  return ELENCO[id] ?? randomSpec(id, accent);
}