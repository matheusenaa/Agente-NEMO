import { CELL_W, CELL_H, MARGIN, WALL_H } from './palette';
import { BaseRoomScene } from './RoomSceneBase';
import { assignCharacters, layoutAgents } from './layoutAgents';
import { getAgentRole } from './agentCast';
import { AGENT_ROSTER } from '@/data/agents';
import type { Agent } from '@/types/state';

export class OfficeScene extends BaseRoomScene {
  constructor() {
    super('OfficeScene');
  }

  protected environmentLabel(): string {
    return 'Escritório NEMO';
  }

  protected defaultAgents(): Agent[] {
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

  protected roomSize(agents: Agent[]): { roomW: number; roomH: number } {
    if (agents.length === 0) return { roomW: 600, roomH: 400 };
    let maxCol = 0, maxRow = 0;
    for (const agent of agents) {
      maxCol = Math.max(maxCol, agent.desk.col);
      maxRow = Math.max(maxRow, agent.desk.row);
    }
    const cellW = CELL_W + 64;
    const cellH = CELL_H + 80;
    const roomW = Math.max(maxCol * cellW + MARGIN * 2, 580);
    const roomH = Math.max(maxRow * cellH + MARGIN * 2 + WALL_H + CELL_H * 2, 400);
    return { roomW, roomH };
  }

  protected place(agents: Agent[], _roomW: number, _roomH: number): void {
    const layout = layoutAgents(agents);
    const characterMap = assignCharacters(layout);
    const cellW = CELL_W + 64;
    const cellH = CELL_H + 80;

    for (const agent of layout) {
      const x = (agent.desk.col - 1) * cellW + MARGIN + cellW / 2;
      const y = (agent.desk.row - 1) * cellH + MARGIN + WALL_H + cellH / 2;
      const characterName = characterMap.get(agent.id) ?? getAgentRole(agent.id).character;
      const deskVariant = getAgentRole(agent.id).desk;
      this.spawn(agent, x, y, characterName, deskVariant);
    }
  }
}