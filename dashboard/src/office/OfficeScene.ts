import Phaser from 'phaser';
import {
  CHARACTER_NAMES, MALE_CHARACTERS, FEMALE_CHARACTERS, avatarKeys, avatarPath,
  DESK_PATHS,
  FURNITURE_PATHS,
  type CharacterName,
} from './assetKeys';
import { CELL_W, CELL_H, MARGIN, WALL_H } from './palette';
import { RoomBuilder } from './RoomBuilder';
import { AgentSprite } from './AgentSprite';
import { getAgentRole, AGENT_CAST } from './agentCast';
import { AGENT_ROSTER } from '@/data/agents';
import type { SquadState, Agent } from '@/types/state';

function assignCharacters(agents: Agent[]): Map<string, CharacterName> {
  const assignments = new Map<string, CharacterName>();
  let maleIndex = 0;
  let femaleIndex = 0;

  for (const agent of agents) {
    if (AGENT_CAST[agent.id]) {
      assignments.set(agent.id, getAgentRole(agent.id).character);
      continue;
    }
    // Sem elenco fixo, alterna masculino/feminino
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

// Elenco real de demonstração — a equipe NEMO (11 agentes) quando não há squad ativo
function realRosterAgents(): Agent[] {
  const statuses: Agent['status'][] = ['idle', 'working', 'idle', 'working', 'idle', 'idle', 'working', 'idle', 'idle', 'delivering', 'working'];
  return AGENT_ROSTER.map((a, i) => ({
    id: a.id,
    name: a.name,
    icon: a.icon,
    status: statuses[i % statuses.length] ?? 'idle',
    desk: { col: 1, row: 1 },
    title: a.title,
    categoryIcon: a.icon,
    colorHex: a.color,
  }));
}

/** Ajusta e distribui os agentes na grade da sala com o NEMO em posição de comando. */
function layoutAgents(agents: Agent[]): Agent[] {
  if (agents.length === 0) return agents;

  // Se o squad fornecer desks distintos, preserva o layout original
  const allSameDesk = agents.length > 1 &&
    agents.every(a => a.desk.col === agents[0].desk.col && a.desk.row === agents[0].desk.row);
  if (!allSameDesk) return agents;

  const n = agents.length;
  const cols = Math.min(Math.max(3, Math.ceil(Math.sqrt(n * 1.6))), 5);
  const rows = Math.ceil(n / cols);

  // Células em ordem linha a linha
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
  // Garante estabilidade de ordem: NEMO primeiro, depois o restante
  return captainIdx !== -1 ? placed : placed.reverse();
}

export class OfficeScene extends Phaser.Scene {
  private agentSprites: Map<string, AgentSprite> = new Map();
  private roomBuilder!: RoomBuilder;
  private onAgentClick?: (id: string) => void;

  constructor() {
    super({ key: 'OfficeScene' });
  }

  preload(): void {
    for (const [key, path] of Object.entries(DESK_PATHS)) {
      this.load.image(key, path);
    }

    for (const name of CHARACTER_NAMES) {
      const keys = avatarKeys(name);
      this.load.image(keys.blink, avatarPath(name, 'blink'));
      this.load.image(keys.talk, avatarPath(name, 'talk'));
      this.load.image(keys.wave1, avatarPath(name, 'wave1'));
      this.load.image(keys.wave2, avatarPath(name, 'wave2'));
    }

    for (const [key, path] of Object.entries(FURNITURE_PATHS)) {
      this.load.image(key, path);
    }

    this.load.on('loaderror', (file: Phaser.Loader.File) => {
      console.error('Failed to load asset:', file.key, file.url);
    });
  }

  create(): void {
    this.textures.list && Object.values(this.textures.list).forEach((tex) => {
      if (tex.key !== '__DEFAULT' && tex.key !== '__MISSING') {
        tex.setFilter(Phaser.Textures.FilterMode.NEAREST);
      }
    });

    this.roomBuilder = new RoomBuilder(this);

    this.events.on('stateUpdate', (state: SquadState | null) => {
      this.onStateUpdate(state);
    });
    // Atividade ao vivo do chat (agente ocupado/vithinking)
    this.events.on('activity', (info: { agentId: string; busy: boolean; label?: string }) => {
      const sprite = this.agentSprites.get(info.agentId);
      if (sprite) sprite.setBusy(info.busy, info.label);
    });
    this.events.on('agentClick', (id: string) => {
      if (this.onAgentClick) this.onAgentClick(id);
    });

    this.renderScene(realRosterAgents());
  }

  setAgentClickHandler(handler: (id: string) => void): void {
    this.onAgentClick = handler;
  }

  private onStateUpdate(state: SquadState | null): void {
    if (!state || !state.agents || state.agents.length === 0) {
      this.renderScene(realRosterAgents());
      return;
    }
    // Mescla rótulos visuais do elenco real quando aplicável
    const merged = state.agents.map((a) => {
      const card = AGENT_ROSTER.find((r) => r.id === a.id);
      return {
        ...a,
        title: card?.title ?? a.title,
        categoryIcon: card?.icon ?? a.icon,
        colorHex: card?.color ?? a.colorHex ?? card?.color,
      };
    });
    this.renderScene(merged);
  }

  private renderScene(agents: Agent[]): void {
    agents = layoutAgents(agents);

    let maxCol = 0, maxRow = 0;
    for (const agent of agents) {
      maxCol = Math.max(maxCol, agent.desk.col);
      maxRow = Math.max(maxRow, agent.desk.row);
    }

    // Células largas para espaçamento confortável (mesa + adereço + rótulo)
    const cellW = CELL_W + 64;
    const cellH = CELL_H + 80;

    const roomW = Math.max(maxCol * cellW + MARGIN * 2, 580);
    const loungeSpace = CELL_H + 48;
    const roomH = maxRow * cellH + MARGIN * 2 + WALL_H + loungeSpace;

    this.clearScene();
    this.roomBuilder.build(roomW, roomH);
    this.roomBuilder.buildBranding(roomW);

    const characterMap = assignCharacters(agents);

    for (let i = 0; i < agents.length; i++) {
      const agent = agents[i];
      const x = (agent.desk.col - 1) * cellW + MARGIN + cellW / 2;
      const y = (agent.desk.row - 1) * cellH + MARGIN + WALL_H + cellH / 2;
      const characterName = characterMap.get(agent.id) ?? getAgentRole(agent.id).character;
      const role = getAgentRole(agent.id);
      const deskVariant = role.desk;
      const agentSprite = new AgentSprite(this, x, y, characterName, deskVariant, {
        ...agent,
        categoryIcon: role.icon,
        colorHex: '#' + role.color.toString(16).padStart(6, '0'),
      }, (id: string) => this.events.emit('agentClick', id));
      this.agentSprites.set(agent.id, agentSprite);
    }

    // Ajusta câmera ao tamanho da sala
    const cam = this.cameras.main;
    const scaleX = cam.width / (roomW + 32);
    const scaleY = cam.height / (roomH + 32);
    const zoom = Math.min(scaleX, scaleY, 2);
    cam.setZoom(zoom);
    cam.centerOn(roomW / 2, roomH / 2);
  }

  private clearScene(): void {
    for (const sprite of this.agentSprites.values()) {
      sprite.destroy();
    }
    this.agentSprites.clear();
    this.children.removeAll(true);
  }
}