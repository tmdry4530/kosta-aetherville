import type { Vec3 } from '@aetherville/shared-schemas';

export function simToScenePosition(pos: Vec3): Vec3 {
  return [pos[0], pos[1], pos[2]];
}
