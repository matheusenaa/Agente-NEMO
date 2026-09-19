import Phaser from 'phaser';
import { avatarKeys, DESK_KEYS, FURNITURE_KEYS, type CharacterName } from './assetKeys';
import { COLORS, VASCO, BUBBLE } from './palette';
import { FUNNY_PHRASES, pickPhrase } from '@/data/statusPhrases';
import type { Agent, AgentStatus } from '@/types/state';

// Avatar display scale — characters should be prominent at desk
const AVATAR_SCALE = 0.8;

// Status → badge color mapping
const STATUS_COLORS: Record<AgentStatus, number> = {
  idle: COLORS.statusIdle,
  working: COLORS.statusWorking,
  done: COLORS.statusDone,
  checkpoint: COLORS.statusCheckpoint,
  delivering: COLORS.statusWorking,
};

// Status → rótulo em PT-BR com emoji
const STATUS_LABELS_PT: Record<AgentStatus, string> = {
  idle: '🟢 Online',
  working: '🧠 Trabalhando...',
  done: '🎯 Pronto',
  checkpoint: '🚦 Checkpoint',
  delivering: '📤 Entregando...',
};

interface BubbleState {
  bg: Phaser.GameObjects.Graphics;
  text: Phaser.GameObjects.Text;
  timer?: Phaser.Time.TimerEvent;
}

export class AgentSprite {
  private scene: Phaser.Scene;
  private deskTable: Phaser.GameObjects.Image;
  private deskShadow: Phaser.GameObjects.Graphics;
  private desk: Phaser.GameObjects.Image;
  private coffeeMug: Phaser.GameObjects.Image;
  private avatar: Phaser.GameObjects.Image;
  private avatarRing: Phaser.GameObjects.Graphics;
  private nameText: Phaser.GameObjects.Text;
  private badgeBg: Phaser.GameObjects.Graphics;
  private statusDot: Phaser.GameObjects.Graphics;
  private statusText: Phaser.GameObjects.Text;
  private iconChip: Phaser.GameObjects.Graphics;
  private iconText: Phaser.GameObjects.Text;
  private animTimer?: Phaser.Time.TimerEvent;
  private animTween?: Phaser.Tweens.Tween;
  private bubble: BubbleState | null = null;
  private bubblePeriod?: Phaser.Time.TimerEvent;
  private agent: Agent;
  private characterName: CharacterName;
  private deskVariant: 'black' | 'white';
  private avatarDisplayH: number = 0;
  private hoverZone: Phaser.GameObjects.Zone;
  private busy = false;

  constructor(
    scene: Phaser.Scene,
    x: number,
    y: number,
    characterName: CharacterName,
    deskVariant: 'black' | 'white',
    agent: Agent,
    onClick?: (id: string) => void,
  ) {
    this.scene = scene;
    this.agent = agent;
    this.characterName = characterName;
    this.deskVariant = deskVariant;

    // Avatar — positioned further behind the desk so head/torso is clearly visible
    const avatarKey = this.getAvatarKey(agent.status);
    this.avatar = scene.add.image(x, y - 70, avatarKey)
      .setOrigin(0.5, 0.5)
      .setScale(AVATAR_SCALE)
      .setDepth(y);  // LOWEST depth — desk and monitor render in front
    this.avatarDisplayH = this.avatar.displayHeight;

    // Hover ring — circle under the avatar, shown on hover
    this.avatarRing = scene.add.graphics();
    this.avatarRing.setDepth(y + 0.5);

    // Desk table surface — renders IN FRONT of avatar (covers lower body)
    this.deskTable = scene.add.image(x, y, FURNITURE_KEYS.deskWood)
      .setOrigin(0.5, 0.5)
      .setScale(1.3)
      .setDepth(y + 1);

    // Monitor — screen-facing (_down orientation), sits on desk surface
    const deskKey = this.getDeskKey(agent.status);
    this.desk = scene.add.image(x, y - 30, deskKey)
      .setOrigin(0.5, 0.5)
      .setScale(1.3)
      .setDepth(y + 2);  // On top of desk surface, screen visible to viewer

    // Coffee mug — right side of desk, away from monitor
    this.coffeeMug = scene.add.image(x + 42, y + 8, 'furniture_coffee_mug')
      .setOrigin(0.5, 1).setScale(1.4).setDepth(y + 3);

    // Shadow (unused graphics object kept for destroy() compatibility)
    this.deskShadow = scene.add.graphics();
    this.deskShadow.setDepth(y - 1);

    // Category icon chip — emoji da função na mesa (canto esquerdo)
    this.iconChip = scene.add.graphics();
    this.iconText = scene.add.text(x - 40, y - 30, agent.categoryIcon ?? agent.icon ?? '🤖', {
      fontFamily: '"Segoe UI", "Helvetica Neue", Arial, sans-serif',
      fontSize: '18px',
    }).setOrigin(0.5, 0.5);
    this.iconText.setDepth(y + 4);
    this.drawIconChip(x - 40, y - 30, agent.colorHex ?? '#38bdf8');

    // Name badge — above avatar head (avatar center y-70, head top ≈ y-91, badge at y-140)
    const labelY = y - 140;

    // Background pill behind name + status
    this.badgeBg = scene.add.graphics();

    // Name text — bold, clean, high contrast
    this.nameText = scene.add.text(x, labelY + 5, agent.name, {
      fontFamily: '"Segoe UI", "Helvetica Neue", Arial, sans-serif',
      fontSize: '16px',
      fontStyle: 'bold',
      color: '#ffffff',
      align: 'center',
      stroke: '#000000',
      strokeThickness: 4,
      resolution: 2,
    }).setOrigin(0.5, 0);
    this.nameText.setDepth(901);

    // Status dot
    this.statusDot = scene.add.graphics();

    // Status text — colored with outline
    const statusColor = this.getStatusHexColor(agent.status);
    this.statusText = scene.add.text(x, labelY + 24, STATUS_LABELS_PT[agent.status] ?? STATUS_LABELS_PT.idle, {
      fontFamily: '"Segoe UI", "Helvetica Neue", Arial, sans-serif',
      fontSize: '13px',
      fontStyle: 'bold',
      color: statusColor,
      align: 'center',
      stroke: '#000000',
      strokeThickness: 3,
      resolution: 2,
    }).setOrigin(0.5, 0);
    this.statusText.setDepth(901);

    // Draw background and status dot
    this.drawLabelBackground(x, labelY);
    this.drawStatusDot(x, labelY + 22, agent.status);

    // Interactive hover + click
    this.hoverZone = scene.add.zone(x, y - 70, 90, 110).setInteractive({ useHandCursor: true });
    this.hoverZone.on('pointerover', () => this.setHover(true));
    this.hoverZone.on('pointerout', () => this.setHover(false));
    this.hoverZone.on('pointerdown', () => {
      if (onClick) onClick(agent.id);
    });

    this.startAnimation(agent.status);
  }

  // ------------------------------------------------------------------
  // Highlight / hover
  // ------------------------------------------------------------------
  private setHover(hover: boolean): void {
    if (hover) {
      this.avatarRing.clear();
      this.avatarRing.fillStyle(0xffffff, 0.35);
      this.avatarRing.fillEllipse(this.avatar.x, this.avatar.y + 26, 46, 15);
      this.setAvatarFrame(avatarKeys(this.characterName).talk);
    } else {
      this.avatarRing.clear();
    }
  }

  private drawIconChip(x: number, y: number, colorHex: string): void {
    const color = parseInt(colorHex.replace('#', ''), 16) || 0x38bdf8;
    this.iconChip.fillStyle(0x101018, 0.9);
    this.iconChip.fillRoundedRect(x - 16, y - 16, 32, 32, 9);
    this.iconChip.lineStyle(2, color, 1);
    this.iconChip.strokeRoundedRect(x - 16, y - 16, 32, 32, 9);
    this.iconChip.setDepth(y + 3);
  }

  // ------------------------------------------------------------------
  // Sprites / status helpers
  // ------------------------------------------------------------------
  private getStatusHexColor(status: AgentStatus): string {
    const num = STATUS_COLORS[status] ?? COLORS.statusIdle;
    return '#' + num.toString(16).padStart(6, '0');
  }

  private getDeskKey(_status: AgentStatus): string {
    // NEMO (capitão) sempre usa a mesa de comando preta em destaque
    return this.deskVariant === 'black' ? DESK_KEYS.blackCoding : DESK_KEYS.whiteCoding;
  }

  private getAvatarKey(_status: AgentStatus): string {
    return avatarKeys(this.characterName).talk;
  }

  private drawLabelBackground(x: number, labelY: number): void {
    const nameW = Math.max(this.nameText.width, this.statusText.width + 18);
    const bgW = nameW + 20;
    const bgH = 44;
    // Borda Vasco (vermelho) para o NEMO, neutra para os demais
    const isCaptain = this.agent.id === 'nemo';
    this.badgeBg.fillStyle(isCaptain ? 0x16090c : 0x1a1225, 0.95);
    this.badgeBg.fillRoundedRect(x - bgW / 2, labelY, bgW, bgH, 5);
    this.badgeBg.lineStyle(2, isCaptain ? VASCO.red : 0x6a5a80, isCaptain ? 1 : 0.4);
    this.badgeBg.strokeRoundedRect(x - bgW / 2, labelY, bgW, bgH, 4);
    this.badgeBg.setDepth(900);
  }

  private drawStatusDot(x: number, _statusY: number, status: AgentStatus): void {
    const dotColor = STATUS_COLORS[status] ?? COLORS.statusIdle;
    const textW = Math.max(this.statusText.width, 24);
    this.statusDot.fillStyle(dotColor, 1);
    this.statusDot.fillCircle(x - textW / 2 - 5, this.statusText.y + this.statusText.height / 2, 3);
    this.statusDot.setDepth(901);
  }

  private setAvatarFrame(key: string): void {
    this.avatar.setTexture(key);
    this.avatar.setScale(this.avatarDisplayH / this.avatar.height);
  }

  // ------------------------------------------------------------------
  // Animações por status
  // ------------------------------------------------------------------
  private startAnimation(status: AgentStatus): void {
    this.animTimer?.destroy();
    this.animTween?.stop();
    this.animTween = undefined;

    const keys = avatarKeys(this.characterName);
    let frame = 0;

    if (status === 'done') {
      // Comemoração: aceno (wave1/wave2) por ~2.6s e depois volta ao idle
      this.animTween = this.scene.tweens.add({
        targets: this.avatar,
        y: this.avatar.y - 6,
        duration: 180,
        yoyo: true,
        repeat: 5,
        ease: 'Sine.easeInOut',
      });
      this.animTimer = this.scene.time.addEvent({
        delay: 380,
        loop: true,
        callback: () => {
          frame = (frame + 1) % 2;
          this.setAvatarFrame(frame === 0 ? keys.wave1 : keys.wave2);
        },
      });
      this.scene.time.delayedCall(2600, () => {
        if (this.busy) return;
        this.animTimer?.destroy();
        this.animTimer = this.scene.time.addEvent({
          delay: 700,
          loop: true,
          callback: () => {
            frame = (frame + 1) % 2;
            this.setAvatarFrame(frame === 0 ? keys.talk : keys.blink);
          },
        });
      });
      return;
    }

    if (status === 'working' || status === 'delivering') {
      // Trabalho intenso: fala/digitação rápida
      this.animTimer = this.scene.time.addEvent({
        delay: 320,
        loop: true,
        callback: () => {
          frame = (frame + 1) % 2;
          this.setAvatarFrame(frame === 0 ? keys.talk : keys.blink);
        },
      });
      return;
    }

    // idle / checkpoint — respiração calma
    const delay = status === 'checkpoint' ? 900 : 650;
    this.animTimer = this.scene.time.addEvent({
      delay,
      loop: true,
      callback: () => {
        frame = (frame + 1) % 2;
        this.setAvatarFrame(frame === 0 ? keys.talk : keys.blink);
      },
    });
  }

  // ------------------------------------------------------------------
  // Balão de fala
  // ------------------------------------------------------------------
  private showBubble(text: string): void {
    this.hideBubble();
    const width = Math.min(170, text.length * 7.2 + 22);
    const x = this.avatar.x;
    const y = this.avatar.y - 64;

    const bg = this.scene.add.graphics();
    bg.fillStyle(BUBBLE.bg, 0.96);
    bg.fillRoundedRect(x - width / 2, y - 18, width, 30, 9);
    bg.lineStyle(2, BUBBLE.border, 1);
    bg.strokeRoundedRect(x - width / 2, y - 18, width, 30, 9);
    // Rabinho do balão
    bg.fillTriangle(
      x - 8, y + 12,
      x + 8, y + 12,
      x, y + 24,
    );
    bg.setDepth(902);

    const label = this.scene.add.text(x, y - 4, text, {
      fontFamily: '"Segoe UI", "Helvetica Neue", Arial, sans-serif',
      fontSize: '12px',
      fontStyle: 'bold',
      color: BUBBLE.text.toString(16).padStart(6, '0'),
      align: 'center',
      wordWrap: { width: width - 16 },
    }).setOrigin(0.5, 0.5);
    label.setDepth(903);

    this.bubble = { bg, text: label };
    this.bubble.timer = this.scene.time.delayedCall(3400, () => this.hideBubble());
  }

  private hideBubble(): void {
    if (this.bubble) {
      this.bubble.timer?.destroy();
      this.bubble.bg.destroy();
      this.bubble.text.destroy();
      this.bubble = null;
    }
  }

  private sayPhrase(): void {
    if (this.busy) {
      this.showBubble(pickPhrase(FUNNY_PHRASES));
    }
  }

  /** Atividade ao vivo vinda do chat (useIdeStore.liveStatus). */
  setBusy(busy: boolean, label?: string): void {
    // Atualiza o agente interno para refletir a animação certa
    this.agent = { ...this.agent, status: busy ? 'working' : this.agent.status === 'working' ? 'idle' : this.agent.status };

    this.bubblePeriod?.destroy();
    this.bubblePeriod = undefined;

    if (this.busy === busy) {
      if (label) this.statusText.setText(label);
      return;
    }
    this.busy = busy;

    if (label) {
      this.statusText.setText(label);
      this.statusText.setColor('#ffffff');
    } else if (this.agent) {
      this.statusText.setText(STATUS_LABELS_PT[this.agent.status] ?? STATUS_LABELS_PT.idle);
      this.statusText.setColor(this.getStatusHexColor(this.agent.status));
    }

    this.animTimer?.destroy();
    this.startAnimation(this.agent.status);

    if (busy) {
      this.sayPhrase();
      this.bubblePeriod = this.scene.time.addEvent({
        delay: 4200,
        loop: true,
        callback: () => this.sayPhrase(),
      });
    } else {
      this.hideBubble();
    }
  }

  updateStatus(agent: Agent): void {
    if (this.agent.status === agent.status && this.agent.name === agent.name) return;
    this.agent = agent;

    this.desk.setTexture(this.getDeskKey(agent.status));
    this.setAvatarFrame(this.getAvatarKey(agent.status));

    this.animTimer?.destroy();
    this.startAnimation(agent.status);

    // Update status text and dot
    if (!this.busy) {
      this.statusText.setText(STATUS_LABELS_PT[agent.status] ?? STATUS_LABELS_PT.idle);
      this.statusText.setColor(this.getStatusHexColor(agent.status));
    }

    this.statusDot.clear();
    const dotColor = STATUS_COLORS[agent.status] ?? COLORS.statusIdle;
    this.statusDot.fillStyle(dotColor, 1);
    const textW = Math.max(this.statusText.width, 24);
    this.statusDot.fillCircle(
      this.statusText.x - textW / 2 - 5,
      this.statusText.y + this.statusText.height / 2,
      3,
    );

    // Frase curta quando conclui
    if (agent.status === 'done') {
      this.showBubble('🎯 Concluído!');
    }
  }

  destroy(): void {
    this.animTimer?.destroy();
    this.animTween?.stop();
    this.bubblePeriod?.destroy();
    this.hideBubble();
    this.deskTable.destroy();
    this.deskShadow.destroy();
    this.desk.destroy();
    this.coffeeMug.destroy();
    this.avatar.destroy();
    this.avatarRing.destroy();
    this.nameText.destroy();
    this.badgeBg.destroy();
    this.statusDot.destroy();
    this.statusText.destroy();
    this.iconChip.destroy();
    this.iconText.destroy();
    this.hoverZone.destroy();
  }
}