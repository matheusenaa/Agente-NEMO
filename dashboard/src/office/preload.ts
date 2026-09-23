import Phaser from 'phaser';
import {
  CHARACTER_NAMES, avatarKeys, avatarPath,
  DESK_PATHS, FURNITURE_PATHS,
} from './assetKeys';

/** Pré-carrega os assets compartilhados de todos os ambientes (personagens, mesas, mobília). */
export function loadRoomAssets(scene: Phaser.Scene): void {
  for (const [key, path] of Object.entries(DESK_PATHS)) {
    scene.load.image(key, path);
  }

  for (const name of CHARACTER_NAMES) {
    const keys = avatarKeys(name);
    scene.load.image(keys.blink, avatarPath(name, 'blink'));
    scene.load.image(keys.talk, avatarPath(name, 'talk'));
    scene.load.image(keys.wave1, avatarPath(name, 'wave1'));
    scene.load.image(keys.wave2, avatarPath(name, 'wave2'));
  }

  for (const [key, path] of Object.entries(FURNITURE_PATHS)) {
    scene.load.image(key, path);
  }

  scene.load.on('loaderror', (file: Phaser.Loader.File) => {
    console.warn('[NEMO room] falha ao carregar asset:', file.key, file.url);
  });
}