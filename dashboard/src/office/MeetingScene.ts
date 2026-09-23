import { COLORS, MARGIN, WALL_H } from './palette';
import { BaseRoomScene } from './RoomSceneBase';
import { getAgentRole } from './agentCast';
import { AGENT_ROSTER } from '@/data/agents';
import type { Agent } from '@/types/state';

interface MeetingSeat {
  col: number;
  row: number;
  head?: boolean;
}

/** Salão: NEMO à cabeceira (esquerda, fileira de trás); demais em duas fileiras frente a frente. */
function seatsAroundTable(agents: Agent[]): Map<string, MeetingSeat> {
  const seats = new Map<string, MeetingSeat>();
  const n = agents.length;
  const cols = Math.max(3, Math.ceil(n / 2));

  const captainIdx = agents.findIndex((a) => a.id === 'nemo');
  const others = agents.filter((_, i) => i !== captainIdx);

  if (captainIdx !== -1) seats.set(agents[captainIdx].id, { col: 0, row: 1, head: true });

  const top = others.slice(0, cols); // fileira de trás (atrás da mesa)
  const bottom = others.slice(cols); // fileira da frente (frente da mesa)
  top.forEach((a, i) => seats.set(a.id, { col: i + 1, row: 1 }));
  bottom.forEach((a, i) => seats.set(a.id, { col: i + 1, row: 2 }));
  return seats;
}

export class MeetingScene extends BaseRoomScene {
  constructor() {
    super('MeetingScene');
  }

  protected environmentLabel(): string {
    return 'Sala de Reunião NEMO';
  }

  protected defaultAgents(): Agent[] {
    const statuses: Agent['status'][] = ['idle', 'working', 'idle', 'working', 'idle', 'working', 'idle', 'idle', 'working', 'idle', 'working', 'idle'];
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
    const n = agents.length;
    const cols = Math.max(3, Math.ceil(n / 2));
    const cellW = 168;
    const roomW = Math.max(cols * cellW + MARGIN * 2 + 60, 760);
    const roomH = 560;
    return { roomW, roomH };
  }

  protected place(agents: Agent[], roomW: number, roomH: number): void {
    const seats = seatsAroundTable(agents);
    const cellW = 168;
    const usableH = roomH - WALL_H - MARGIN;
    const topY = WALL_H + usableH * 0.30;
    const bottomY = WALL_H + usableH * 0.74;
    const tableY = WALL_H + usableH * 0.52;
    const tableH = 34;
    const tableW = roomW - MARGIN * 2 - 60;

    const g = this.add.graphics();
    g.fillStyle(COLORS.floor, 1);
    g.fillRoundedRect(roomW / 2 - tableW / 2, tableY - tableH / 2, tableW, tableH, 12);
    g.lineStyle(4, 0x6a4a86, 1);
    g.strokeRoundedRect(roomW / 2 - tableW / 2, tableY - tableH / 2, tableW, tableH, 12);
    g.lineStyle(2, 0x2a2030, 0.6);
    g.strokeRoundedRect(roomW / 2 - tableW / 2 + 6, tableY - tableH / 2 + 6, tableW - 12, tableH - 12, 8);
    // Brasão no centro da mesa
    g.fillStyle(0xc8102e, 1);
    g.fillCircle(roomW / 2, tableY, 30);
    g.lineStyle(3, 0xffffff, 1);
    g.strokeCircle(roomW / 2, tableY, 30);
    this.add.text(roomW / 2, tableY, '⚓', { fontSize: '24px' }).setOrigin(0.5).setDepth(2);
    this.add.text(roomW / 2, tableY - 18, 'NEMO', {
      fontFamily: '"Segoe UI", "Helvetica Neue", Arial, sans-serif',
      fontSize: '11px',
      fontStyle: 'bold',
      color: '#ffffff',
    }).setOrigin(0.5).setDepth(2);

    const labelOverrides = {
      idle: '🤝 Em reunião',
      working: '🗣️ Falando',
      checkpoint: '🚦 Aguardando vez',
      done: '🎯 Concluído',
      delivering: '📤 Apresentando',
    };

    for (const agent of agents) {
      const seat = seats.get(agent.id) ?? { col: 1, row: 1 };
      const baseX = MARGIN + cellW / 2 + 30;
      const y = seat.row === 1 ? topY : bottomY;
      const x = baseX + seat.col * cellW;
      const role = getAgentRole(agent.id);
      this.spawn(agent, x, y, role.character, role.desk, false, labelOverrides);
    }
  }
}