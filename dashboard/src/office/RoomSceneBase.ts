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
  private fitW = 800;
  private fitH = 600;
  protected roomW = 0;
  protected roomH = 0;
  private lastLayout: Map<string, { col: number; row: number }> = new Map();
  protected restingIds: Set<string> = new Set();

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

    // Viewport inicial = tamanho real do canvas do Phaser (não o config)
    const gameSize = this.scale.gameSize;
    if (gameSize && gameSize.width > 0) this.fitW = gameSize.width;
    if (gameSize && gameSize.height > 0) this.fitH = gameSize.height;

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
    this.events.on('toRest', (id: string) => this.sendAgentToRest(id));
    this.events.on('toDesk', (id: string) => this.returnAgentToDesk(id));

    this.renderScene(this.defaultAgents());
  }

  // ------------------------------------------------------------------
  // Interação com a sala: enviar agente para descansar no sofá / voltar à mesa
  // ------------------------------------------------------------------

  /** Posição do sofá / área de descanso da sala (override nas subclasses). */
  protected restAnchor(): { x: number; y: number } | null {
    return null;
  }

  isAgentResting(id: string): boolean {
    return this.restingIds.has(id);
  }

  sendAgentToRest(id: string): void {
    const anchor = this.restAnchor();
    const sprite = this.agentSprites.get(id);
    if (!anchor || !sprite || this.restingIds.has(id)) return;
    // Espalha os colegas pelo sofá para não empilharem
    const spread = (this.restingIds.size - Math.floor(this.restingIds.size / 2)) * 44;
    sprite.moveTo(anchor.x + spread, anchor.y, true);
    this.restingIds.add(id);
  }

  returnAgentToDesk(id: string): void {
    const sprite = this.agentSprites.get(id);
    if (!sprite || !this.restingIds.has(id)) return;
    const home = sprite.homePosition();
    sprite.moveTo(home.x, home.y, false);
    this.restingIds.delete(id);
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

    const agents = this.rosterAgents(state.agents);

    // Mesmo elenco (mesmas ids) e mesmas posições (desk)? Atualiza status
    // in-place. Evita clearScene() + rebuild completo a cada mudança do
    // squad, que reinicia as animações e faz os personagens "piscarem".
    const existing = Array.from(this.agentSprites.keys());
    const incoming = agents.map((a) => a.id);
    const sameRoster =
      existing.length === incoming.length &&
      existing.every((id, i) => {
        if (id !== incoming[i]) return false;
        const prev = this.lastLayout.get(id);
        const cur = agents[i].desk;
        return !!prev && !!cur && prev.col === cur.col && prev.row === cur.row;
      });

    if (sameRoster && existing.length > 0) {
      agents.forEach((agent) => {
        const sprite = this.agentSprites.get(agent.id);
        if (sprite) sprite.updateStatus(agent);
      });
      return;
    }

    this.renderScene(agents);
  }

  protected renderScene(rawAgents: Agent[]): void {
    this.clearScene();
    const agents = this.rosterAgents(rawAgents);
    const { roomW, roomH } = this.roomSize(agents);
    this.roomW = roomW;
    this.roomH = roomH;
    this.roomBuilder.build(roomW, roomH);
    this.roomBuilder.buildBranding(roomW);
    if (agents.length > 0) {
      this.lastLayout = new Map(agents.map((a) => [a.id, { ...a.desk }]));
      this.place(agents, roomW, roomH);
    } else {
      this.lastLayout = new Map();
    }
    this.fitCamera();
  }

  /**
   * Recalcula zoom e centraliza a câmera a partir do viewport real informado
   * pelo container (PhaserGame). Chamado a cada resize — sem isso a sala
   * aparece cortada ou flutuando quando a janela muda de tamanho.
   */
  fitViewport(width: number, height: number): void {
    this.fitW = width;
    this.fitH = height;
    this.fitCamera();
  }

  /** Aplica zoom/centralização para caber a sala inteira no viewport atual. */
  private fitCamera(): void {
    if (this.roomW <= 0 || this.roomH <= 0) return;
    const cam = this.cameras.main;
    // Zoom determinístico: a sala inteira sempre encaixa no canvas — sem corte.
    // Quanto maior o canvas, maior o zoom (personagens proporcionais e fixos).
    const zoom = Math.max(0.35, Math.min(this.fitW / (this.roomW + 32), this.fitH / (this.roomH + 32), 2));
    cam.setZoom(zoom);
    cam.centerOn(this.roomW / 2, this.roomH / 2);
  }

  protected clearScene(): void {
    for (const sprite of this.agentSprites.values()) {
      sprite.destroy();
    }
    this.agentSprites.clear();
    this.children.removeAll(true);
  }
}