import { useEffect, useRef } from 'react';
import Phaser from 'phaser';
import { OfficeScene } from './OfficeScene';
import { useSquadStore } from '@/store/useSquadStore';
import { useIdeStore } from '@/store/useIdeStore';
import { AGENT_ROSTER } from '@/data/agents';

interface PhaserGameProps {
  onAgentClick?: (agentId: string) => void;
}

export function PhaserGame({ onAgentClick }: PhaserGameProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const gameRef = useRef<Phaser.Game | null>(null);
  const clickRef = useRef(onAgentClick);
  clickRef.current = onAgentClick;

  // Create Phaser game on mount
  useEffect(() => {
    if (!containerRef.current || gameRef.current) return;

    const container = containerRef.current;
    const w = container.clientWidth || 800;
    const h = container.clientHeight || 600;

    const game = new Phaser.Game({
      type: Phaser.AUTO,
      parent: container,
      width: w,
      height: h,
      pixelArt: false,          // disabled globally so text renders smooth
      antialias: false,          // keep pixel art look for sprites
      roundPixels: true,         // snap sprites to whole pixels
      backgroundColor: '#1a1420',
      scene: [OfficeScene],
      scale: {
        mode: Phaser.Scale.NONE,
      },
    });

    gameRef.current = game;

    // Resize canvas when container resizes
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        if (width > 0 && height > 0) {
          game.scale.resize(width, height);
        }
      }
    });
    ro.observe(container);

    return () => {
      ro.disconnect();
      game.destroy(true);
      gameRef.current = null;
    };
  }, []);

  // Bridge React state → Phaser scene (emite estado inicial + mudanças)
  useEffect(() => {
    const getScene = (): OfficeScene | null => {
      const game = gameRef.current;
      if (!game) return null;
      const scene = game.scene.getScene("OfficeScene") as OfficeScene | null;
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

    // Estado inicial (ex.: squad já ativo ao montar a cena)
    emitSquad();

    const unsubSquad = useSquadStore.subscribe(emitSquad);
    const unsubIde = useIdeStore.subscribe((state, prev) => {
      if (state.liveStatus !== prev.liveStatus) emitActivity();
      if (state.tasks !== prev.tasks) emitActivity();
      // cliques vêm da cena através do handler registrado abaixo
    });

    // Re-emite após a cena Phaser terminar de criar (estado inicial não chega antes)
    const reShot = setInterval(() => {
      const scene = getScene();
      if (scene) {
        scene.setAgentClickHandler(onAgentClick);
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
    };
  }, []);

  return (
    <div
      ref={containerRef}
      style={{
        flex: 1,
        overflow: 'hidden',
        imageRendering: 'auto',
        cursor: 'default',
      }}
    />
  );
}