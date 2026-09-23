import type { Agent } from '@/types/state';
import { getAgentRole } from './agentCast';
import {
  MALE_CHARACTERS, FEMALE_CHARACTERS,
  type CharacterName,
} from './assetKeys';

/** Elenco fixo (se houver) por agente; senão, alterna masc/fem pelo gênero. */
export function assignCharacters(agents: Agent[]): Map<string, CharacterName> {
  const assignments = new Map<string, CharacterName>();
  let maleIndex = 0;
  let femaleIndex = 0;

  for (const agent of agents) {
    const fixed = getAgentRole(agent.id).character;
    assignments.set(agent.id, fixed);
    if (fixed) continue;
    const useMale = agent.gender === 'male' || (agent.gender === undefined && maleIndex <= femaleIndex);
    if (useMale) {
      assignments.set(agent.id, MALE_CHARACTERS[maleIndex % MALE_CHARACTERS.length]);
      maleIndex++;
    } else {
      assignments.set(agent.id, FEMALE_CHARACTERS[femaleIndex % FEMALE_CHARACTERS.length]);
      femaleIndex++;
    }
  }

  return assignments;
}

/**
 * Distribui os agentes na grade da sala com o NEMO em posição de comando
 * (cabeceira central na primeira linha). Preserva desks vindos do squad.
 */
export function layoutAgents(agents: Agent[]): Agent[] {
  if (agents.length === 0) return agents;

  const allSameDesk = agents.length > 1 &&
    agents.every(a => a.desk.col === agents[0].desk.col && a.desk.row === agents[0].desk.row);
  if (!allSameDesk) return agents;

  const n = agents.length;
  const cols = Math.min(Math.max(3, Math.ceil(Math.sqrt(n * 1.6))), 5);
  const rows = Math.ceil(n / cols);

  const cells: { col: number; row: number }[] = [];
  for (let r = 1; r <= rows; r++) {
    for (let c = 1; c <= cols; c++) cells.push({ col: c, row: r });
  }

  const captainIdx = agents.findIndex(a => a.id === 'nemo');
  const nonCaptain = agents.slice();
  const captainCell = { col: Math.ceil(cols / 2), row: 1 };
  const usedCells = cells.filter(cp => !(cp.col === captainCell.col && cp.row === captainCell.row));

  const placed: Agent[] = [];
  if (captainIdx !== -1) {
    placed.push({ ...agents[captainIdx], desk: captainCell });
    nonCaptain.splice(captainIdx, 1);
  }
  for (let i = 0; i < nonCaptain.length; i++) {
    const cell = usedCells[i % usedCells.length];
    placed.push({ ...nonCaptain[i], desk: { col: cell.col, row: cell.row } });
  }
  return captainIdx !== -1 ? placed : placed.reverse();
}