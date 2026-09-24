import { useEffect, useRef } from 'react';
import Phaser from 'phaser';
import { OfficeScene } from './OfficeScene';
import { MeetingScene } from './MeetingScene';
import { RestScene } from './RestScene';
import { BaseRoomScene } from './RoomSceneBase';
import { useSquadStore } from '@/store/useSquadStore';
import { useIdeStore } from '@/store/useIdeStore';
import { AGENT_ROSTER } from '@/data/agents';

export type RoomId = 'office' | 'reuniao' | 'agentes';

const SCENE_BY_ROOM: Record<RoomId, string> = {
  office: 'OfficeScene',
  reuniao: 'MeetingScene',
  agentes: 'RestScene',
};

export interface RoomController {
  sendToRest: (agentId: string) => void;
  returnToDesk: (agentId: string) => void;
  isResting: (agentId: string) => boolean;
}

interface PhaserGameProps {
  roomId?: RoomId;
  onAgentClick?: (agentId: string) => void;
  controllerRef?: { current: RoomController | null };
}

export function PhaserGame({ roomId = 'office', onAgentClick, controllerRef }: PhaserGameProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const gameRef = useRef<Phaser.Game | null>(null);
  const clickRef = useRef(onAgentClick);
  const roomRef = useRef(roomId);
  clickRef.current = onAgentClick;
  roomRef.current = roomId;

  // Create Phaser game on mount
  useEffect(() => {
    if (!containerRef.current || gameRef.current) return;

    const container = containerRef.current;
    const w = container.clientWidth || 800;
    const h = container.clientHeight || 600;

    // Renderer 2D (Canvas): pintura previsível em qualquer placa/driver,
    // eliminando a classe de falhas de "tela preta" do WebGL.
    const game = new Phaser.Game({
      type: Phaser.CANVAS,
      parent: container,
      width: w,
      height: h,
      pixelArt: false,
      antialias: false,
      roundPixels: true,
      backgroundColor: '#1a1420',
      scale: {
        mode: Phaser.Scale.NONE,
      },
    });

    // Registra e inicia a cena correspondente à sala (o Phaser só auto-inicia
    // a primeira cena da lista; aqui quem decide é o roomId).
    game.scene.add('OfficeScene', OfficeScene);
    game.scene.add('MeetingScene', MeetingScene);
    game.scene.add('RestScene', RestScene);
    game.scene.start(SCENE_BY_ROOM[roomRef.current] ?? 'OfficeScene');

    gameRef.current = game;
    // Expor para debug/QA — útil para validar o pipeline visual
    (window as unknown as { __nemoGame?: Phaser.Game }).__nemoGame = game;

    // Redimensiona APENAS quando o layout acalmar (debounce 300ms) e só se
    // o tamanho real mudou. Cada game.scale.resize() zera o buffer do canvas 2D
    // durante a troca de frames; aplicá-lo a cada mudança transitória do layout
    // causa o quadro "tela preta" intermitente no renderer Canvas.
    let resizeTimer: number | undefined;
    let lastW = 0;
    let lastH = 0;
    const applyResize = () => {
      const rect = container.getBoundingClientRect();
      const w = Math.round(rect.width);
      const h = Math.round(rect.height);
      if (w > 0 && h > 0 && (w !== lastW || h !== lastH)) {
        lastW = w;
        lastH = h;
        game.scale.resize(w, h);
        // Recalcula zoom + câmera da sala ativa para caber o novo viewport.
        // Sem isso a sala fica cortada ou flutuando quando a janela muda.
        const activeScenes = game.scene.getScenes(true);
        for (const scene of activeScenes) {
          (scene as unknown as { fitViewport?: (x: number, y: number) => void }).fitViewport?.(w, h);
        }
      }
    };
    const ro = new ResizeObserver(() => {
      window.clearTimeout(resizeTimer);
      resizeTimer = window.setTimeout(applyResize, 300);
    });
    ro.observe(container);

    return () => {
      ro.disconnect();
      if (gameRef.current === game) game.destroy(true);
      gameRef.current = null;
    };
  }, []);

  // Bridge React state → Phaser scene (emite estado inicial + mudanças)
  useEffect(() => {
    const getScene = (): BaseRoomScene | null => {
      const game = gameRef.current;
      if (!game) return null;
      const key = SCENE_BY_ROOM[roomRef.current];
      const scene = game.scene.getScene(key) as BaseRoomScene | null;
      if (!scene || !scene.scene.isActive()) return null;
      return scene;
    };

    const emitSquad = () => {
      const scene = getScene();
      if (!scene) return;
      const state = useSquadStore.getState();
      const selectedSquad = state.selectedSquad;
      const squadState = selectedSquad
        ? state.activeStates.get(selectedSquad) ?? null
        : null;
      scene.events.emit("stateUpdate", squadState);
    };

    const emitActivity = () => {
      const scene = getScene();
      if (!scene) return;
      const state = useIdeStore.getState();
      const live = state.liveStatus;
      const busyAgents = new Set<string>();
      if (live.busy) busyAgents.add(live.agentId);
      state.tasks.forEach((t) => (t.status === "running" ? busyAgents.add(t.agentId) : undefined));
      busyAgents.forEach((agentId) => {
        scene.events.emit("activity", {
          agentId,
          busy: true,
          label: live.agentId === agentId ? live.label : "em execução",
        });
      });
      AGENT_ROSTER.forEach((a) => {
        if (!busyAgents.has(a.id)) {
          scene.events.emit("activity", { agentId: a.id, busy: false, label: "" });
        }
      });
    };

    const onAgentClick = (id: string) => clickRef.current?.(id);

    const unsubSquad = useSquadStore.subscribe(emitSquad);
    const unsubIde = useIdeStore.subscribe((state, prev) => {
      if (state.liveStatus !== prev.liveStatus) emitActivity();
      if (state.tasks !== prev.tasks) emitActivity();
    });

    // Expõe um controlador imperativo para o React (ex.: botão "sofá").
    // As cenas são criadas/recriadas por remount, então o controller apenas
    // dispara eventos na cena ativa — resolvido via scene.events.
    const attachController = (scene: BaseRoomScene) => {
      if (!controllerRef) return;
      controllerRef.current = {
        sendToRest: (id) => scene.events.emit('toRest', id),
        returnToDesk: (id) => scene.events.emit('toDesk', id),
        isResting: (id) => scene.isAgentResting(id),
      };
    };

    const reShot = setInterval(() => {
      const scene = getScene();
      if (scene) {
        scene.setAgentClickHandler(onAgentClick);
        attachController(scene);
        scene.events.off('agentClick');
        scene.events.on('agentClick', onAgentClick);
        emitSquad();
        emitActivity();
        clearInterval(reShot);
      }
    }, 300);

    return () => {
      clearInterval(reShot);
      unsubSquad();
      unsubIde();
      const scene = getScene();
      if (scene) scene.events.off('agentClick');
      if (controllerRef) controllerRef.current = null;
    };
    // Intentional: apenas na montagem — a cena é trocada por remount do React
  }, []);

  return (
    <div
      ref={containerRef}
      style={{
        flex: 1,
        overflow: 'hidden',
        imageRendering: 'auto',
        cursor: 'default',
        position: 'relative',
        minHeight: 400,
      }}
    />
  );
}