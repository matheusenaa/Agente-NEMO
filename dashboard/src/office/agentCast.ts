import type { CharacterName } from './assetKeys';
import { AGENT_ROSTER } from '@/data/agents';

// Define por agente real: personagem 2D (sprite), variante de mesa,
// emoji da função e cor de destaque (identidade visual do projeto).
export interface AgentRole {
  character: CharacterName;
  desk: 'black' | 'white';
  icon: string;
  color: number;
  title: string;
}

// Personagens disponíveis (sprites existentes em public/assets/avatars)
const MALE: CharacterName[] = ['Male1', 'Male2', 'Male3', 'Male4'];
const FEMALE: CharacterName[] = ['Female1', 'Female2', 'Female3', 'Female4', 'Female5', 'Female6'];

function hexToNumber(hex: string, fallback = 0x38bdf8): number {
  const m = /^#?([0-9a-fA-F]{6})$/.exec(hex?.trim() ?? "");
  return m ? parseInt(m[1], 16) : fallback;
}

// Elenco fixo por agente real (estável entre renders).
// NEMO é o "capitão" — personagem e mesa próprios, em destaque.
export const AGENT_CAST: Record<string, AgentRole> = {
  nemo: { character: 'Male1', desk: 'black', icon: '🐟', color: hexToNumber('#cf1126'), title: 'Assistente Pessoal & Coordenador' },
  jarvis: { character: 'Male2', desk: 'black', icon: '🛠️', color: hexToNumber('#60a5fa'), title: 'Especialista Sênior em Engenharia de Software & TI' },
  analista: { character: 'Female2', desk: 'white', icon: '📊', color: hexToNumber('#38bdf8'), title: 'Analista de Dados' },
  pesquisador: { character: 'Female1', desk: 'black', icon: '🔍', color: hexToNumber('#22d3ee'), title: 'Pesquisadora' },
  redator: { character: 'Female3', desk: 'white', icon: '✍️', color: hexToNumber('#a78bfa'), title: 'Redatora' },
  revisor: { character: 'Female6', desk: 'black', icon: '✅', color: hexToNumber('#34d399'), title: 'Revisora de Qualidade' },
  designer: { character: 'Female4', desk: 'white', icon: '🎨', color: hexToNumber('#f472b6'), title: 'Designer' },
  'criador-video': { character: 'Male4', desk: 'black', icon: '🎬', color: hexToNumber('#c084fc'), title: 'Criador de Vídeo' },
  estrategista: { character: 'Male3', desk: 'white', icon: '🎯', color: hexToNumber('#fb923c'), title: 'Estrategista' },
  'gestor-redes': { character: 'Female5', desk: 'black', icon: '📱', color: hexToNumber('#2dd4bf'), title: 'Gestora de Redes Sociais' },
  'editor-publicador': { character: 'Female4', desk: 'white', icon: '📤', color: hexToNumber('#fbbf24'), title: 'Editora & Publicadora' },
  seo: { character: 'Male2', desk: 'white', icon: '🔎', color: hexToNumber('#a3e635'), title: 'Especialista em SEO' },
};

export function getAgentRole(id: string): AgentRole {
  // Gênero da personagem determinístico por id
  const role = AGENT_CAST[id];
  if (role) return role;

  let h = 0;
  for (const ch of id) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  const useMale = id.length % 2 === 0;
  const pool = useMale ? MALE : FEMALE;
  return {
    character: pool[h % pool.length],
    desk: h % 2 === 0 ? 'black' : 'white',
    icon: '🤖',
    color: hexToNumber((AGENT_ROSTER.find((a) => a.id === id)?.color) ?? '#38bdf8'),
    title: AGENT_ROSTER.find((a) => a.id === id)?.title ?? 'Agente',
  };
}

// Ordem de exibição padrão: NEMO primeiro, depois os demais pela rotação oficial
export const ROSTER_ORDER = AGENT_ROSTER.map((a) => a.id);