import Phaser from 'phaser';
import { RoomBuilder } from './RoomBuilder';
import { AgentSprite } from './AgentSprite';
import { getAgentRole } from './agentCast';
import { AGENT_ROSTER } from '@/data/agents';
import { loadRoomAssets } from './preload';
import type { CharacterName } from './assetKeys';
import type { Agent, AgentStatus, SquadState } from '@/types/state';

/**
 * Base das salas do NEMO: wiring de eventos (síndico de squad, atividade ao
 * vivo, clique), pré-load de assets, câmera e ciclo de renderização.
 * Cada ambiente (escritório, reunião, descanso) implementa como posicionar
 * os agentes e qual o tamanho da sala.
 */
export interface AgentPlacement {
  agent: Agent;
  x: number;
  y: number;
  character: CharacterName;
  deskVariant: 'black' | 'white';
  noDesk?: boolean;
}

export abstract class BaseRoomScene extends Phaser.Scene {
  protected agentSprites: Map<string, AgentSprite> = new Map();
  protected roomBuilder!: RoomBuilder;
  private onAgentClick?: (id: string) => void;

  protected constructor(key: string) {
    super({ key });
  }

  preload(): void {
    loadRoomAssets(this);
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
    this.events.on('activity', (info: { agentId: string; busy: boolean; label?: string }) => {
      const sprite = this.agentSprites.get(info.agentId);
      if (sprite) sprite.setBusy(info.busy, info.label);
    });
    this.events.on('agentClick', (id: string) => {
      if (this.onAgentClick) this.onAgentClick(id);
    });

    this.renderScene(this.defaultAgents());
  }

  setAgentClickHandler(handler: (id: string) => void): void {
    this.onAgentClick = handler;
  }

  /** Elenco padrão da equipe quando não há squad ativo. */
  protected abstract defaultAgents(): Agent[];

  /** Tamanho da sala para o conjunto de agentes. */
  protected abstract roomSize(agents: Agent[]): { roomW: number; roomH: number };

  /** Posiciona os agentes na sala (cria os AgentSprite e registra no mapa). */
  protected abstract place(agents: Agent[], roomW: number, roomH: number): void;

  /** Tipo de ambiente exibido no console ao carregar. */
  protected abstract environmentLabel(): string;

  protected readonly DEFAULT_CELL_W = 104;
  protected readonly DEFAULT_CELL_H = 128;
  protected readonly WALL_H = 88;

  protected rosterAgents(agents: Agent[]): Agent[] {
    return agents.map((a) => {
      const card = AGENT_ROSTER.find((r) => r.id === a.id);
      const role = getAgentRole(a.id);
      return {
        ...a,
        title: card?.title ?? role.title ?? a.title,
        categoryIcon: card?.icon ?? role.icon ?? a.icon,
        colorHex: card?.color ?? a.colorHex,
      };
    });
  }

  /** Cria um AgentSprite em (x, y) e guarda. */
  protected spawn(
    agent: Agent,
    x: number,
    y: number,
    character: CharacterName,
    deskVariant: 'black' | 'white',
    noDesk?: boolean,
    labelOverrides?: Partial<Record<AgentStatus, string>>,
  ): void {
    const role = getAgentRole(agent.id);
    const sprite = new AgentSprite(this, x, y, character, deskVariant, {
      ...agent,
      categoryIcon: role.icon,
      colorHex: '#' + role.color.toString(16).padStart(6, '0'),
    }, (id: string) => this.events.emit('agentClick', id), {
      noDesk,
      labelOverrides,
    });
    this.agentSprites.set(agent.id, sprite);
  }

  private onStateUpdate(state: SquadState | null): void {
    if (!state || !state.agents || state.agents.length === 0) {
      this.renderScene(this.defaultAgents());
      return;
    }
    this.renderScene(this.rosterAgents(state.agents));
  }

  protected renderScene(rawAgents: Agent[]): void {
    this.clearScene();
    const agents = this.rosterAgents(rawAgents);
    const { roomW, roomH } = this.roomSize(agents);
    this.roomBuilder.build(roomW, roomH);
    this.roomBuilder.buildBranding(roomW);
    if (agents.length > 0) {
      this.place(agents, roomW, roomH);
    }
    const cam = this.cameras.main;
    const configWidth = (this.game.config as any).width || 800;
    const configHeight = (this.game.config as any).height || 600;
    const zoom = Math.max(0.5, Math.min(configWidth / (roomW + 32), configHeight / (roomH + 32), 2));
    cam.setZoom(zoom);
    cam.centerOn(roomW / 2, roomH / 2);
  }

  protected clearScene(): void {
    for (const sprite of this.agentSprites.values()) {
      sprite.destroy();
    }
    this.agentSprites.clear();
    this.children.removeAll(true);
  }
}