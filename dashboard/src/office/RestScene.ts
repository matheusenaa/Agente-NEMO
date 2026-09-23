import { CELL_W, CELL_H, MARGIN, WALL_H, TILE } from './palette';
import { BaseRoomScene } from './RoomSceneBase';
import { assignCharacters, layoutAgents } from './layoutAgents';
import { getAgentRole } from './agentCast';
import { AGENT_ROSTER } from '@/data/agents';
import type { Agent } from '@/types/state';

const REST_LABELS = {
  idle: '☕ Descansando',
  working: '🧠 Pensando alto',
  checkpoint: '⏳ Aguardando chamada',
  done: '🎉 Livre',
  delivering: '📣 Reunindo a galera',
} as const;

/**
 * Área de descanso / copinha: agentes sem mesa, à vontade, aguardando
 * serem chamados. Mesmo ecossistema visual, porém descontraído.
 */
export class RestScene extends BaseRoomScene {
  constructor() {
    super('RestScene');
  }

  protected environmentLabel(): string {
    return 'Área de Descanso NEMO';
  }

  protected defaultAgents(): Agent[] {
    const statuses: Agent['status'][] = ['idle', 'idle', 'checkpoint', 'idle', 'idle', 'working', 'idle', 'idle', 'checkpoint', 'idle', 'idle', 'done'];
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
    if (agents.length === 0) return { roomW: 860, roomH: 760 };
    const n = agents.length;
    const cols = Math.min(Math.max(3, Math.ceil(Math.sqrt(n * 1.6))), 5);
    const rows = Math.ceil(n / cols);
    const cellW = CELL_W + 72;
    const cellH = CELL_H + 96;
    // Folga extra no rodapé para o espaço do lounge (sofa + poltronas + café)
    const roomW = Math.max(cols * cellW + MARGIN * 2, 860);
    const roomH = Math.max(rows * cellH + MARGIN * 2 + WALL_H + TILE * 3, 760);
    return { roomW, roomH };
  }

  protected place(agents: Agent[], roomW: number, _roomH: number): void {
    const layout = layoutAgents(agents);
    const characterMap = assignCharacters(layout);
    const cellW = CELL_W + 72;
    const cellH = CELL_H + 96;
    const centerX = roomW / 2;

    // Recado na parede — clima de copa
    this.add.text(centerX, WALL_H / 2 + 6, '☕ COPINHO — descanse à vontade', {
      fontFamily: '"Segoe UI", "Helvetica Neue", Arial, sans-serif',
      fontSize: '16px',
      fontStyle: 'bold',
      color: '#3a2a38',
    }).setOrigin(0.5).setDepth(2);

    // Dardo de futebol na parede (identidade Vasco dentro da copa)
    const dartX = centerX - 260;
    const dartY = WALL_H / 2 + 4;
    const g = this.add.graphics();
    g.setDepth(2);
    g.fillStyle(0xffffff, 1);
    g.fillCircle(dartX, dartY, 22);
    g.lineStyle(3, 0xc8102e, 1);
    g.strokeCircle(dartX, dartY, 22);
    g.fillStyle(0xc8102e, 1);
    g.fillCircle(dartX, dartY, 7);
    g.lineStyle(2, 0x2a2030, 0.7);
    for (let i = 0; i < 4; i++) {
      const a = (Math.PI / 2) * i + Math.PI / 4;
      g.lineBetween(
        dartX + Math.cos(a) * 8, dartY + Math.sin(a) * 8,
        dartX + Math.cos(a) * 19, dartY + Math.sin(a) * 19,
      );
    }

    for (const agent of layout) {
      const baseX = (agent.desk.col - 1) * cellW + MARGIN + cellW / 2;
      const baseY = (agent.desk.row - 1) * cellH + MARGIN + WALL_H + cellH / 2;
      // Toque orgânico: leve ondulação para não parecer fila de operação
      const x = baseX + Math.sin(agent.desk.col * 1.9) * 34;
      const y = baseY + ((agent.desk.row + agent.desk.col) % 2 === 0 ? 16 : -14);
      const characterName = characterMap.get(agent.id) ?? getAgentRole(agent.id).character;
      const deskVariant = getAgentRole(agent.id).desk;
      this.spawn(agent, x, y, characterName, deskVariant, true, REST_LABELS);
    }
  }
}