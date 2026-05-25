'use client';

import type { ReactNode } from 'react';
import { useEffect, useMemo, useRef } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import type { CitizenState, DroneState, TrafficLightState, Vec3, VehicleState, WorldStatePayload } from '@aetherville/shared-schemas';
import { CanvasTexture, LinearFilter, Vector3 } from 'three';
import type { Group, Mesh } from 'three';
import { createFallbackWorldState } from '@/lib/mockWorld';
import { useConnectionStore } from '@/store/connection';

const CITY_STAGE_SCALE = 1.08;
const CITY_CAMERA_POSITION = [7.6, 7.15, 7.6] as [number, number, number];
const CITY_CAMERA_FOV = 38;
const ACTOR_SMOOTHING = 15.5;
const ROTATION_SMOOTHING = 15.5;
const ACTOR_SCALE = {
  citizen: 1.16,
  vehicle: 1.12,
  trafficLight: 1.1,
  drone: 1.08
} as const;
const ROAD_LINES = [-6, -3, 0, 3, 6] as const;
const BLOCK_CENTERS = [-4.5, -1.5, 1.5, 4.5] as const;
const ROAD_DASHES = [-6.2, -4.8, -3.4, -2.0, -0.6, 0.8, 2.2, 3.6, 5.0, 6.4] as const;
const STREET_LIGHTS = [
  [-3.6, -3.6],
  [3.6, -3.6],
  [-3.6, 3.6],
  [3.6, 3.6],
  [0.6, -3.6],
  [-0.6, 3.6]
] as const;
const JAM_VEHICLES = [
  [-1.55, 0, -3.0, 0],
  [-0.75, 0, -3.0, 0],
  [0.25, 0, -3.0, 0],
  [1.2, 0, -3.0, 0],
  [3.0, 0, -1.25, Math.PI / 2],
  [3.0, 0, -0.35, Math.PI / 2],
  [3.0, 0, 0.55, Math.PI / 2],
  [3.0, 0, 1.45, Math.PI / 2]
] as const;
const CITY_BLOCKS = BLOCK_CENTERS.flatMap((x, xi) =>
  BLOCK_CENTERS.map((z, zi) => ({
    position: [x, 0.045, z] as [number, number, number],
    height: 0.09 + ((xi + zi) % 2) * 0.035,
    color: (xi + zi) % 2 === 0 ? '#0b1b2d' : '#10243a'
  }))
);

const actorPalette = {
  citizenHead: '#ff5ca8',
  citizenBody: '#65f4d8',
  citizenRing: '#ff8dc7',
  vehicleBody: '#f7b955',
  vehicleCab: '#38bdf8',
  vehicleWheel: '#020617',
  drone: '#e5eefb',
  droneBeacon: '#a78bfa',
  signalHousing: '#020617',
  signalPole: '#cbd5e1',
  building: '#1e293b',
  laneDash: '#fde68a'
} as const;

function useTagTexture(lines: string[], accent: string) {
  return useMemo(() => {
    if (typeof document === 'undefined') {
      return null;
    }
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 144;
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      return null;
    }

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = 'rgba(3, 7, 18, 0.86)';
    ctx.strokeStyle = accent;
    ctx.lineWidth = 6;
    const radius = 30;
    ctx.beginPath();
    ctx.moveTo(radius, 8);
    ctx.lineTo(canvas.width - radius, 8);
    ctx.quadraticCurveTo(canvas.width - 8, 8, canvas.width - 8, radius);
    ctx.lineTo(canvas.width - 8, canvas.height - radius);
    ctx.quadraticCurveTo(canvas.width - 8, canvas.height - 8, canvas.width - radius, canvas.height - 8);
    ctx.lineTo(radius, canvas.height - 8);
    ctx.quadraticCurveTo(8, canvas.height - 8, 8, canvas.height - radius);
    ctx.lineTo(8, radius);
    ctx.quadraticCurveTo(8, 8, radius, 8);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = '#e5eefb';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.font = '700 46px sans-serif';
    ctx.fillText(lines[0] ?? '', canvas.width / 2, lines.length > 1 ? 54 : 72);
    if (lines[1]) {
      ctx.fillStyle = accent;
      ctx.font = '700 30px sans-serif';
      ctx.fillText(lines[1], canvas.width / 2, 104);
    }

    const texture = new CanvasTexture(canvas);
    texture.minFilter = LinearFilter;
    texture.magFilter = LinearFilter;
    texture.needsUpdate = true;
    return texture;
  }, [accent, lines]);
}

function BillboardTag({
  lines,
  position,
  accent = actorPalette.citizenHead,
  scale = 1
}: {
  lines: string[];
  position: [number, number, number];
  accent?: string;
  scale?: number;
}) {
  const stableLines = useMemo(() => lines.filter(Boolean).slice(0, 2), [lines]);
  const texture = useTagTexture(stableLines, accent);

  useEffect(() => () => texture?.dispose(), [texture]);

  if (!texture || stableLines.length === 0) {
    return null;
  }

  return (
    <sprite position={position} scale={[1.35 * scale, 0.38 * scale, 1]}>
      <spriteMaterial map={texture} depthTest={false} depthWrite={false} transparent />
    </sprite>
  );
}

function dampAlpha(delta: number, speed: number) {
  return 1 - Math.exp(-speed * delta);
}

function shortestAngleDistance(current: number, target: number) {
  return Math.atan2(Math.sin(target - current), Math.cos(target - current));
}

function tagIncludes(tags: string[], needle: string) {
  return tags.some((tag) => tag.includes(needle));
}

function isTrafficSurgeActive(worldState: WorldStatePayload) {
  const infrastructure = worldState.world.infrastructure_status ?? '';
  const activeEvent = worldState.world.active_event ?? '';
  return infrastructure.includes('congestion') || infrastructure.includes('정체') || activeEvent.includes('traffic congestion');
}

function isRainActive(worldState: WorldStatePayload) {
  return worldState.world.weather === 'rain' || worldState.world.active_event === 'weather:rain';
}

function cityAiFocus(worldState: WorldStatePayload): Vec3 | null {
  if (worldState.city_ai.mode === 'disabled' || worldState.city_ai.status !== 'applied') {
    return null;
  }

  const action = worldState.city_ai.actions.find(
    (candidate) => candidate.actor_id || candidate.vehicle_id || candidate.target_id
  );
  if (!action) {
    return null;
  }

  const citizen = worldState.citizens.find(
    (candidate) => candidate.id === action.actor_id || candidate.id === action.target_id
  );
  if (citizen) {
    return [citizen.pos[0], 0, citizen.pos[2]];
  }

  const vehicle = worldState.vehicles.find(
    (candidate) => candidate.id === action.vehicle_id || candidate.id === action.actor_id
  );
  return vehicle ? [vehicle.pos[0], 0, vehicle.pos[2]] : null;
}

function sceneFocusForWorld(worldState: WorldStatePayload): Vec3 {
  const taxi = worldState.vehicles.find((vehicle) => vehicle.id === 'v01');
  const minji = worldState.citizens.find((citizen) => citizen.name === '민지' || citizen.id === 'c01');
  const minsu = worldState.citizens.find((citizen) => citizen.name === '민수' || citizen.id === 'c02');
  const aiFocus = cityAiFocus(worldState);

  if (taxi && tagIncludes(taxi.display_tags, '택시 호출')) {
    if (minji && tagIncludes(taxi.display_tags, '민지에게')) {
      return [(taxi.pos[0] + minji.pos[0]) / 2, 0, (taxi.pos[2] + minji.pos[2]) / 2];
    }
    return [taxi.pos[0], 0, taxi.pos[2]];
  }

  if (minji && minsu && (minji.talking_to === minsu.id || minsu.talking_to === minji.id || tagIncludes(minji.display_tags, '대화'))) {
    return [(minji.pos[0] + minsu.pos[0]) / 2, 0, (minji.pos[2] + minsu.pos[2]) / 2];
  }

  if (isTrafficSurgeActive(worldState)) {
    return [1.6, 0, -1.6];
  }

  if (aiFocus) {
    return aiFocus;
  }

  return [0, 0, 0];
}

function GameCamera({ worldState }: { worldState: WorldStatePayload }) {
  const { camera } = useThree();
  const targetRef = useRef(new Vector3(0, 0.55, 0));
  const desiredRef = useRef(new Vector3(...CITY_CAMERA_POSITION));

  useFrame((_state, delta) => {
    const focus = sceneFocusForWorld(worldState);
    const target = targetRef.current;
    const desired = desiredRef.current;
    const scaledX = focus[0] * CITY_STAGE_SCALE;
    const scaledZ = focus[2] * CITY_STAGE_SCALE;
    const cameraDistance = isTrafficSurgeActive(worldState) ? 6.65 : 7.25;
    const cameraHeight = tagIncludes(worldState.vehicles[0]?.display_tags ?? [], '택시 호출') ? 6.2 : 7.15;

    target.set(scaledX, 0.55, scaledZ);
    desired.set(scaledX + cameraDistance, cameraHeight, scaledZ + cameraDistance);
    camera.position.lerp(desired, dampAlpha(delta, 2.05));
    camera.lookAt(target);
    camera.updateProjectionMatrix();
  });

  return null;
}

function AnimatedActorGroup({
  children,
  pos,
  rot = [0, 0, 0],
  scale = 1
}: {
  children: ReactNode;
  pos: Vec3;
  rot?: Vec3;
  scale?: number;
}) {
  const groupRef = useRef<Group>(null);

  useFrame((_state, delta) => {
    const group = groupRef.current;
    if (!group) {
      return;
    }

    const positionAlpha = dampAlpha(delta, ACTOR_SMOOTHING);
    group.position.x += (pos[0] - group.position.x) * positionAlpha;
    group.position.y += (pos[1] - group.position.y) * positionAlpha;
    group.position.z += (pos[2] - group.position.z) * positionAlpha;

    const rotationAlpha = dampAlpha(delta, ROTATION_SMOOTHING);
    group.rotation.x += shortestAngleDistance(group.rotation.x, rot[0]) * rotationAlpha;
    group.rotation.y += shortestAngleDistance(group.rotation.y, rot[1]) * rotationAlpha;
    group.rotation.z += shortestAngleDistance(group.rotation.z, rot[2]) * rotationAlpha;
  });

  return (
    <group ref={groupRef} position={[pos[0], pos[1], pos[2]]} rotation={[rot[0], rot[1], rot[2]]} scale={scale}>
      {children}
    </group>
  );
}

function RoadGrid() {
  return (
    <group>
      <mesh position={[0, -0.08, 0]} receiveShadow>
        <boxGeometry args={[15.5, 0.03, 15.5]} />
        <meshStandardMaterial color="#07101e" />
      </mesh>
      {CITY_BLOCKS.map((block) => (
        <mesh key={`${block.position[0]}:${block.position[2]}`} position={block.position} receiveShadow>
          <boxGeometry args={[2.05, block.height, 2.05]} />
          <meshStandardMaterial color={block.color} emissive="#0f172a" emissiveIntensity={0.08} />
        </mesh>
      ))}
      {ROAD_LINES.map((line) => (
        <group key={`road-x-${line}`}>
          <mesh position={[line, -0.03, 0]} receiveShadow>
            <boxGeometry args={[0.82, 0.045, 15]} />
            <meshStandardMaterial color="#070b13" />
          </mesh>
          <mesh position={[line - 0.56, 0.015, 0]}>
            <boxGeometry args={[0.06, 0.018, 15]} />
            <meshStandardMaterial color="#334155" emissive="#94a3b8" emissiveIntensity={0.1} />
          </mesh>
          <mesh position={[line + 0.56, 0.015, 0]}>
            <boxGeometry args={[0.06, 0.018, 15]} />
            <meshStandardMaterial color="#334155" emissive="#94a3b8" emissiveIntensity={0.1} />
          </mesh>
          {ROAD_DASHES.map((dash) => (
            <mesh key={`dash-x-${line}-${dash}`} position={[line, 0.036, dash]}>
              <boxGeometry args={[0.075, 0.02, 0.52]} />
              <meshStandardMaterial color={actorPalette.laneDash} emissive={actorPalette.laneDash} emissiveIntensity={0.2} />
            </mesh>
          ))}
        </group>
      ))}
      {ROAD_LINES.map((line) => (
        <group key={`road-z-${line}`}>
          <mesh position={[0, -0.02, line]} receiveShadow>
            <boxGeometry args={[15, 0.045, 0.82]} />
            <meshStandardMaterial color="#0b1220" />
          </mesh>
          <mesh position={[0, 0.02, line - 0.56]}>
            <boxGeometry args={[15, 0.018, 0.06]} />
            <meshStandardMaterial color="#334155" emissive="#94a3b8" emissiveIntensity={0.1} />
          </mesh>
          <mesh position={[0, 0.02, line + 0.56]}>
            <boxGeometry args={[15, 0.018, 0.06]} />
            <meshStandardMaterial color="#334155" emissive="#94a3b8" emissiveIntensity={0.1} />
          </mesh>
          {ROAD_DASHES.map((dash) => (
            <mesh key={`dash-z-${line}-${dash}`} position={[dash, 0.041, line]}>
              <boxGeometry args={[0.52, 0.02, 0.075]} />
              <meshStandardMaterial color={actorPalette.laneDash} emissive={actorPalette.laneDash} emissiveIntensity={0.2} />
            </mesh>
          ))}
        </group>
      ))}
      {ROAD_LINES.flatMap((x) =>
        ROAD_LINES.map((z) => (
          <group key={`crosswalk-${x}-${z}`}>
            {[-0.24, 0, 0.24].map((offset) => (
              <mesh key={`xbar-${offset}`} position={[x + offset, 0.049, z - 0.47]}>
                <boxGeometry args={[0.1, 0.018, 0.35]} />
                <meshStandardMaterial color="#f8fafc" emissive="#64748b" emissiveIntensity={0.08} />
              </mesh>
            ))}
            {[-0.24, 0, 0.24].map((offset) => (
              <mesh key={`zbar-${offset}`} position={[x - 0.47, 0.05, z + offset]}>
                <boxGeometry args={[0.35, 0.018, 0.1]} />
                <meshStandardMaterial color="#f8fafc" emissive="#64748b" emissiveIntensity={0.08} />
              </mesh>
            ))}
          </group>
        ))
      )}
    </group>
  );
}

function Buildings() {
  const buildings = BLOCK_CENTERS.flatMap((x, xi) =>
    BLOCK_CENTERS.map((z, zi) => ({
      position: [x + ((zi % 2) - 0.5) * 0.35, 0.45 + ((xi + zi) % 3) * 0.18, z] as [number, number, number],
      height: 0.9 + ((xi * 2 + zi) % 4) * 0.22,
      color: ['#155e75', '#3730a3', '#0f766e', '#92400e'][(xi + zi) % 4],
      windowColor: ['#67e8f9', '#a78bfa', '#f9a8d4', '#fde68a'][(xi * 3 + zi) % 4]
    }))
  );

  return (
    <group>
      {buildings.map((building, index) => (
        <group key={`${building.position[0]}:${building.position[2]}`} position={building.position}>
          <mesh>
            <boxGeometry args={[0.74, building.height, 0.74]} />
            <meshStandardMaterial color={building.color} emissive={actorPalette.building} emissiveIntensity={0.035} />
          </mesh>
          <mesh position={[0, building.height * 0.2, -0.382]}>
            <boxGeometry args={[0.48, building.height * 0.48, 0.018]} />
            <meshStandardMaterial color={building.windowColor} emissive={building.windowColor} emissiveIntensity={0.18 + (index % 3) * 0.04} />
          </mesh>
          <mesh position={[0, building.height * 0.54, 0]}>
            <boxGeometry args={[0.42, 0.035, 0.42]} />
            <meshStandardMaterial color="#dbeafe" emissive={building.windowColor} emissiveIntensity={0.35} />
          </mesh>
        </group>
      ))}
    </group>
  );
}

function StreetProps() {
  return (
    <group>
      {STREET_LIGHTS.map(([x, z], index) => (
        <group key={`street-light-${x}-${z}`} position={[x, 0, z]}>
          <mesh position={[0, 0.6, 0]}>
            <cylinderGeometry args={[0.035, 0.05, 1.2, 12]} />
            <meshStandardMaterial color="#94a3b8" emissive="#475569" emissiveIntensity={0.15} />
          </mesh>
          <mesh position={[0.18, 1.24, 0]} rotation={[0, 0, Math.PI / 2.8]}>
            <cylinderGeometry args={[0.025, 0.025, 0.42, 12]} />
            <meshStandardMaterial color="#94a3b8" />
          </mesh>
          <mesh position={[0.38, 1.2, 0]}>
            <sphereGeometry args={[0.1, 16, 16]} />
            <meshStandardMaterial color="#fef3c7" emissive="#fde68a" emissiveIntensity={0.95} />
          </mesh>
          {index < 4 ? <pointLight position={[0.38, 1.18, 0]} intensity={0.34} distance={3.2} color="#fde68a" /> : null}
        </group>
      ))}
    </group>
  );
}

function PedestrianRig({ citizen, index, bodyColor }: { citizen: CitizenState; index: number; bodyColor: string }) {
  const rigRef = useRef<Group>(null);
  const torsoRef = useRef<Mesh>(null);
  const leftLegRef = useRef<Mesh>(null);
  const rightLegRef = useRef<Mesh>(null);
  const leftArmRef = useRef<Mesh>(null);
  const rightArmRef = useRef<Mesh>(null);
  const headRef = useRef<Mesh>(null);
  const moving = citizen.anim !== 'idle';

  useFrame(({ clock }) => {
    const t = clock.elapsedTime * (moving ? 8.4 : 2.4) + index * 0.85;
    const gait = moving ? 1 : 0.18;
    const swing = Math.sin(t) * 0.45 * gait;
    const bounce = Math.abs(Math.sin(t)) * 0.035 * gait;

    if (rigRef.current) {
      rigRef.current.position.y = bounce;
    }
    if (torsoRef.current) {
      torsoRef.current.rotation.z = Math.sin(t * 0.5) * 0.035 * gait;
    }
    if (headRef.current) {
      headRef.current.position.y = 0.66 + bounce * 0.45;
    }
    if (leftLegRef.current) {
      leftLegRef.current.rotation.x = swing;
    }
    if (rightLegRef.current) {
      rightLegRef.current.rotation.x = -swing;
    }
    if (leftArmRef.current) {
      leftArmRef.current.rotation.x = -swing * 0.82;
    }
    if (rightArmRef.current) {
      rightArmRef.current.rotation.x = swing * 0.82;
    }
  });

  return (
    <group ref={rigRef}>
      <mesh position={[0, 0.025, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.32, 0.03, 8, 24]} />
        <meshStandardMaterial color={actorPalette.citizenRing} emissive={actorPalette.citizenHead} emissiveIntensity={0.28} />
      </mesh>
      <mesh ref={leftLegRef} position={[-0.09, 0.16, 0]}>
        <cylinderGeometry args={[0.045, 0.055, 0.34, 10]} />
        <meshStandardMaterial color="#0f766e" emissive="#0f766e" emissiveIntensity={0.12} />
      </mesh>
      <mesh ref={rightLegRef} position={[0.09, 0.16, 0]}>
        <cylinderGeometry args={[0.045, 0.055, 0.34, 10]} />
        <meshStandardMaterial color="#0f766e" emissive="#0f766e" emissiveIntensity={0.12} />
      </mesh>
      <mesh ref={torsoRef} position={[0, 0.42, 0]} castShadow>
        <cylinderGeometry args={[0.15, 0.22, 0.48, 18]} />
        <meshStandardMaterial color={bodyColor} emissive="#0f766e" emissiveIntensity={0.22} />
      </mesh>
      <mesh ref={leftArmRef} position={[-0.22, 0.43, 0]} rotation={[0.08, 0, -0.14]}>
        <cylinderGeometry args={[0.035, 0.04, 0.38, 10]} />
        <meshStandardMaterial color={actorPalette.citizenBody} emissive="#0f766e" emissiveIntensity={0.16} />
      </mesh>
      <mesh ref={rightArmRef} position={[0.22, 0.43, 0]} rotation={[-0.08, 0, 0.14]}>
        <cylinderGeometry args={[0.035, 0.04, 0.38, 10]} />
        <meshStandardMaterial color={actorPalette.citizenBody} emissive="#0f766e" emissiveIntensity={0.16} />
      </mesh>
      <mesh ref={headRef} position={[0, 0.66, 0]} castShadow>
        <sphereGeometry args={[0.2, 20, 20]} />
        <meshStandardMaterial color={actorPalette.citizenHead} emissive="#831843" emissiveIntensity={0.32} />
      </mesh>
    </group>
  );
}

function CitizenActor({ citizen, index }: { citizen: CitizenState; index: number }) {
  const bodyColor = index % 2 === 0 ? actorPalette.citizenBody : '#2dd4bf';
  const tagDetail = citizen.display_tags.filter((tag) => tag !== citizen.name).join(' · ') || '인도';

  return (
    <AnimatedActorGroup pos={citizen.pos} rot={citizen.rot} scale={ACTOR_SCALE.citizen}>
      <BillboardTag lines={[citizen.name, tagDetail]} position={[0, 1.18, 0]} accent={actorPalette.citizenHead} scale={0.92} />
      <PedestrianRig citizen={citizen} index={index} bodyColor={bodyColor} />
    </AnimatedActorGroup>
  );
}

function VehicleWheel({ position, speed, phase = 0 }: { position: [number, number, number]; speed: number; phase?: number }) {
  const wheelRef = useRef<Mesh>(null);

  useFrame((_state, delta) => {
    if (!wheelRef.current) {
      return;
    }
    wheelRef.current.rotation.x += delta * Math.max(1.6, speed * 1.9) + phase * 0.0001;
  });

  return (
    <mesh ref={wheelRef} position={position} rotation={[0, 0, Math.PI / 2]}>
      <cylinderGeometry args={[0.15, 0.15, 0.12, 18]} />
      <meshStandardMaterial color={actorPalette.vehicleWheel} roughness={0.62} />
    </mesh>
  );
}

function PulsingDispatchRing({ active, color }: { active: boolean; color: string }) {
  const ringRef = useRef<Group>(null);

  useFrame(({ clock }) => {
    if (!ringRef.current) {
      return;
    }
    const pulse = active ? 1 + Math.sin(clock.elapsedTime * 5.4) * 0.07 : 1;
    ringRef.current.scale.set(pulse, pulse, pulse);
  });

  if (!active) {
    return null;
  }

  return (
    <group ref={ringRef}>
      <mesh position={[0, 0.08, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.72, 0.035, 10, 40]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.7} transparent opacity={0.78} />
      </mesh>
      <mesh position={[0, 0.1, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.92, 0.018, 10, 48]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.45} transparent opacity={0.44} />
      </mesh>
    </group>
  );
}

function VehicleActor({ vehicle }: { vehicle: VehicleState }) {
  const primaryTag = vehicle.display_tags[0] ?? vehicle.type.toUpperCase();
  const tagDetail = vehicle.display_tags.slice(1).join(' · ') || vehicle.id;
  const taxiActive = tagIncludes(vehicle.display_tags, '택시 호출');
  const congested = tagIncludes(vehicle.display_tags, '정체') || tagIncludes(vehicle.display_tags, '저속');
  const roofColor = vehicle.type === 'taxi' ? '#fef08a' : '#bfdbfe';

  return (
    <AnimatedActorGroup pos={vehicle.pos} rot={vehicle.rot} scale={ACTOR_SCALE.vehicle}>
      <BillboardTag lines={[primaryTag, tagDetail]} position={[0, 1.28, 0]} accent={taxiActive ? actorPalette.citizenHead : actorPalette.vehicleBody} scale={1.02} />
      <PulsingDispatchRing active={taxiActive || congested} color={taxiActive ? actorPalette.citizenHead : '#ef4444'} />
      <mesh position={[0, 0.2, 0]} castShadow>
        <boxGeometry args={[0.7, 0.38, 1.28]} />
        <meshStandardMaterial color={actorPalette.vehicleBody} emissive="#92400e" emissiveIntensity={0.22} roughness={0.5} />
      </mesh>
      <mesh position={[0, 0.5, 0.12]} castShadow>
        <boxGeometry args={[0.54, 0.32, 0.58]} />
        <meshStandardMaterial color={actorPalette.vehicleCab} emissive="#075985" emissiveIntensity={0.28} roughness={0.38} />
      </mesh>
      <VehicleWheel position={[-0.43, 0.04, -0.48]} speed={vehicle.speed} />
      <VehicleWheel position={[0.43, 0.04, -0.48]} speed={vehicle.speed} phase={1} />
      <VehicleWheel position={[-0.43, 0.04, 0.48]} speed={vehicle.speed} phase={2} />
      <VehicleWheel position={[0.43, 0.04, 0.48]} speed={vehicle.speed} phase={3} />
      <mesh position={[0, 0.76, 0.06]}>
        <boxGeometry args={[0.34, 0.1, 0.32]} />
        <meshStandardMaterial color={roofColor} emissive={actorPalette.vehicleBody} emissiveIntensity={taxiActive ? 0.95 : 0.65} />
      </mesh>
      <mesh position={[-0.22, 0.24, 0.69]}>
        <boxGeometry args={[0.18, 0.08, 0.035]} />
        <meshStandardMaterial color="#fef3c7" emissive="#fde68a" emissiveIntensity={1.2} />
      </mesh>
      <mesh position={[0.22, 0.24, 0.69]}>
        <boxGeometry args={[0.18, 0.08, 0.035]} />
        <meshStandardMaterial color="#fef3c7" emissive="#fde68a" emissiveIntensity={1.2} />
      </mesh>
      <mesh position={[-0.23, 0.23, -0.69]}>
        <boxGeometry args={[0.16, 0.06, 0.035]} />
        <meshStandardMaterial color={congested ? '#ef4444' : '#fb7185'} emissive="#ef4444" emissiveIntensity={congested ? 1.05 : 0.45} />
      </mesh>
      <mesh position={[0.23, 0.23, -0.69]}>
        <boxGeometry args={[0.16, 0.06, 0.035]} />
        <meshStandardMaterial color={congested ? '#ef4444' : '#fb7185'} emissive="#ef4444" emissiveIntensity={congested ? 1.05 : 0.45} />
      </mesh>
    </AnimatedActorGroup>
  );
}

function DroneRotor({ position, phase }: { position: [number, number, number]; phase: number }) {
  const rotorRef = useRef<Mesh>(null);

  useFrame((_state, delta) => {
    if (rotorRef.current) {
      rotorRef.current.rotation.y += delta * 18 + phase * 0.0001;
    }
  });

  return (
    <mesh ref={rotorRef} position={position}>
      <boxGeometry args={[0.42, 0.024, 0.06]} />
      <meshStandardMaterial color={actorPalette.droneBeacon} emissive={actorPalette.droneBeacon} emissiveIntensity={0.65} transparent opacity={0.82} />
    </mesh>
  );
}

function DroneActor({ drone }: { drone: DroneState }) {
  return (
    <AnimatedActorGroup pos={drone.pos} scale={ACTOR_SCALE.drone}>
      <BillboardTag lines={['드론', drone.id]} position={[0, 0.68, 0]} accent={actorPalette.droneBeacon} scale={0.82} />
      <mesh>
        <octahedronGeometry args={[0.3]} />
        <meshStandardMaterial color={actorPalette.drone} emissive={actorPalette.droneBeacon} emissiveIntensity={0.3} />
      </mesh>
      <mesh>
        <boxGeometry args={[0.96, 0.04, 0.04]} />
        <meshStandardMaterial color={actorPalette.droneBeacon} emissive={actorPalette.droneBeacon} emissiveIntensity={0.35} />
      </mesh>
      <mesh>
        <boxGeometry args={[0.04, 0.04, 0.96]} />
        <meshStandardMaterial color={actorPalette.droneBeacon} emissive={actorPalette.droneBeacon} emissiveIntensity={0.35} />
      </mesh>
      <DroneRotor position={[-0.48, 0.02, 0]} phase={0} />
      <DroneRotor position={[0.48, 0.02, 0]} phase={1} />
      <DroneRotor position={[0, 0.02, -0.48]} phase={2} />
      <DroneRotor position={[0, 0.02, 0.48]} phase={3} />
    </AnimatedActorGroup>
  );
}

function TrafficLightActor({ light }: { light: TrafficLightState }) {
  const states = [
    { name: 'red', color: '#ef4444', y: 1.1 },
    { name: 'yellow', color: '#eab308', y: 0.88 },
    { name: 'green', color: '#22c55e', y: 0.66 }
  ];

  return (
    <AnimatedActorGroup pos={light.pos} scale={ACTOR_SCALE.trafficLight}>
      <BillboardTag lines={['신호등', light.state]} position={[0, 1.55, 0]} accent={activeSignalColor(light.state)} scale={0.8} />
      <mesh position={[0, 0.42, 0]}>
        <cylinderGeometry args={[0.07, 0.09, 0.92, 16]} />
        <meshStandardMaterial color={actorPalette.signalPole} emissive="#475569" emissiveIntensity={0.08} />
      </mesh>
      <mesh position={[0, 0.94, 0]}>
        <boxGeometry args={[0.36, 0.78, 0.24]} />
        <meshStandardMaterial color={actorPalette.signalHousing} emissive="#111827" emissiveIntensity={0.12} />
      </mesh>
      {states.map((state) => {
        const active = state.name === light.state;
        return (
          <mesh key={state.name} position={[0, state.y, -0.13]}>
            <sphereGeometry args={[active ? 0.115 : 0.078, 16, 16]} />
            <meshStandardMaterial color={state.color} emissive={state.color} emissiveIntensity={active ? 0.9 : 0.05} />
          </mesh>
        );
      })}
    </AnimatedActorGroup>
  );
}

function activeSignalColor(state: TrafficLightState['state']) {
  if (state === 'green') {
    return '#22c55e';
  }
  if (state === 'yellow') {
    return '#eab308';
  }
  return '#ef4444';
}

function RainStreaks({ active }: { active: boolean }) {
  const groupRef = useRef<Group>(null);
  const drops = useMemo(
    () =>
      Array.from({ length: 68 }, (_item, index) => ({
        key: `rain-${index}`,
        position: [((index * 37) % 150) / 10 - 7.5, ((index * 19) % 46) / 10 + 1.3, ((index * 53) % 150) / 10 - 7.5] as [number, number, number],
        length: 0.42 + (index % 4) * 0.08
      })),
    []
  );

  useFrame(({ clock }) => {
    if (groupRef.current) {
      groupRef.current.position.y = -((clock.elapsedTime * 3.2) % 1.2);
    }
  });

  if (!active) {
    return null;
  }

  return (
    <group ref={groupRef}>
      {drops.map((drop) => (
        <mesh key={drop.key} position={drop.position} rotation={[0.42, 0.1, -0.32]}>
          <boxGeometry args={[0.018, drop.length, 0.018]} />
          <meshBasicMaterial color="#7dd3fc" transparent opacity={0.46} />
        </mesh>
      ))}
    </group>
  );
}

function TrafficSurgeVehicles({ active }: { active: boolean }) {
  const groupRef = useRef<Group>(null);

  useFrame(({ clock }) => {
    if (!groupRef.current) {
      return;
    }
    const pulse = 0.92 + Math.sin(clock.elapsedTime * 5.8) * 0.08;
    groupRef.current.scale.set(pulse, 1, pulse);
  });

  if (!active) {
    return null;
  }

  return (
    <group ref={groupRef}>
      {JAM_VEHICLES.map(([x, y, z, yaw], index) => (
        <group key={`jam-car-${x}-${z}-${index}`} position={[x, y, z]} rotation={[0, yaw, 0]}>
          <mesh position={[0, 0.15, 0]} castShadow>
            <boxGeometry args={[0.46, 0.28, 0.78]} />
            <meshStandardMaterial color={index % 2 === 0 ? '#f97316' : '#ef4444'} emissive="#ef4444" emissiveIntensity={0.22} />
          </mesh>
          <mesh position={[0, 0.35, 0.08]}>
            <boxGeometry args={[0.34, 0.2, 0.34]} />
            <meshStandardMaterial color="#fb7185" emissive="#f43f5e" emissiveIntensity={0.35} />
          </mesh>
          <mesh position={[-0.14, 0.12, -0.43]}>
            <boxGeometry args={[0.11, 0.05, 0.025]} />
            <meshStandardMaterial color="#ef4444" emissive="#ef4444" emissiveIntensity={1.15} />
          </mesh>
          <mesh position={[0.14, 0.12, -0.43]}>
            <boxGeometry args={[0.11, 0.05, 0.025]} />
            <meshStandardMaterial color="#ef4444" emissive="#ef4444" emissiveIntensity={1.15} />
          </mesh>
        </group>
      ))}
      <mesh position={[0.45, 0.07, -2.55]} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[1.95, 0.035, 10, 72]} />
        <meshStandardMaterial color="#ef4444" emissive="#ef4444" emissiveIntensity={0.75} transparent opacity={0.42} />
      </mesh>
    </group>
  );
}

function WorldEffects({ worldState }: { worldState: WorldStatePayload }) {
  return (
    <group>
      <RainStreaks active={isRainActive(worldState)} />
      <TrafficSurgeVehicles active={isTrafficSurgeActive(worldState)} />
    </group>
  );
}

function WorldActors({ worldState }: { worldState: WorldStatePayload }) {
  return (
    <group>
      {worldState.citizens.map((citizen, index) => (
        <CitizenActor citizen={citizen} index={index} key={citizen.id} />
      ))}
      {worldState.vehicles.map((vehicle) => (
        <VehicleActor key={vehicle.id} vehicle={vehicle} />
      ))}
      {worldState.drones.map((drone) => (
        <DroneActor drone={drone} key={drone.id} />
      ))}
      {worldState.traffic_lights.map((light) => (
        <TrafficLightActor key={light.id} light={light} />
      ))}
    </group>
  );
}


function impactLabelsForWorld(worldState: WorldStatePayload) {
  const tags = [
    ...worldState.citizens.flatMap((citizen) => citizen.display_tags),
    ...worldState.vehicles.flatMap((vehicle) => vehicle.display_tags),
    ...worldState.traffic_lights.flatMap((light) => light.display_tags)
  ].join(' ');
  const minji = worldState.citizens.find((citizen) => citizen.id === 'c01' || citizen.name === '민지');
  const minsu = worldState.citizens.find((citizen) => citizen.id === 'c02' || citizen.name === '민수');
  const taxi = worldState.vehicles.find((vehicle) => vehicle.id === 'v01');
  const labels = [
    isRainActive(worldState) ? 'RAIN' : null,
    isTrafficSurgeActive(worldState) || tags.includes('정체') || tags.includes('저속') ? 'TRAFFIC SURGE' : null,
    taxi?.passenger_id || tags.includes('택시 호출') ? 'TAXI DISPATCH' : null,
    minji?.talking_to === minsu?.id || minsu?.talking_to === minji?.id || tags.includes('대화') ? 'MEETING' : null,
    worldState.city_ai.mode !== 'disabled' && worldState.city_ai.status === 'applied' ? 'CITY AI PLAN' : null,
    worldState.traffic_ai.mode === 'checkpoint' ? 'GPU POLICY' : null,
    worldState.traffic_forecast_ai.mode === 'lstm_checkpoint' ? 'LSTM FORECAST' : null
  ].filter((label): label is string => Boolean(label));

  return labels.length > 0 ? labels : ['BASELINE CITY'];
}

function SceneDirectorHud({ worldState }: { worldState: WorldStatePayload }) {
  const labels = impactLabelsForWorld(worldState);

  return (
    <div className="directorHud" aria-label="Scene director live impact HUD">
      <span className="directorHudTitle">SCENE DIRECTOR · LIVE IMPACT</span>
      <div>
        {labels.map((label) => (
          <strong key={label}>{label}</strong>
        ))}
      </div>
    </div>
  );
}

function EventOverlays({ worldState }: { worldState: WorldStatePayload }) {
  const isRaining = isRainActive(worldState);
  const isTrafficSurge = isTrafficSurgeActive(worldState);

  return (
    <>
      {isRaining ? (
        <>
          <div className="weatherOverlay weatherOverlay-rain" aria-hidden="true" />
          <div className="eventBadge eventBadge-rain">RAIN ACTIVE · 비 내리는 중</div>
        </>
      ) : null}
      {isTrafficSurge ? (
        <>
          <div className="trafficSurgeOverlay" aria-hidden="true" />
          <div className="eventBadge eventBadge-traffic">TRAFFIC SURGE · 차량 저속/정체</div>
        </>
      ) : null}
    </>
  );
}

function SceneLegend() {
  const legendItems = [
    { key: 'citizen', label: '시민', detail: '보행 애니메이션' },
    { key: 'vehicle', label: '차량', detail: '택시·바퀴·헤드라이트' },
    { key: 'signal', label: '신호등', detail: '3색 세로등' },
    { key: 'drone', label: '드론', detail: '회전 프로펠러' },
    { key: 'building', label: '건물', detail: '네온 창문' }
  ];

  return (
    <div className="sceneLegend" aria-label="3D scene legend">
      {legendItems.map((item) => (
        <div className="sceneLegendItem" key={item.key}>
          <span className={`sceneLegendSwatch sceneLegendSwatch-${item.key}`} aria-hidden="true" />
          <span>
            <strong>{item.label}</strong>
            <small>{item.detail}</small>
          </span>
        </div>
      ))}
    </div>
  );
}

export function CityPlaceholder({ initialWorldState = null }: { initialWorldState?: WorldStatePayload | null }) {
  const lastTick = useConnectionStore((state) => state.lastTick);
  const liveWorldState = useConnectionStore((state) => state.lastWorldState);
  const connectionState = useConnectionStore((state) => state.state);
  const worldState = liveWorldState ?? initialWorldState ?? createFallbackWorldState(lastTick);
  const isTrafficSurge = isTrafficSurgeActive(worldState);

  useEffect(() => {
    if (initialWorldState && !liveWorldState) {
      useConnectionStore.getState().applyWorldState(lastTick, initialWorldState);
    }
  }, [initialWorldState, lastTick, liveWorldState]);

  return (
    <section className={`cityPanel${isTrafficSurge ? ' cityPanel-trafficSurge' : ''}`} aria-label="Aetherville city scene">
      <div className="statusPill">{connectionState} · tick {lastTick} · {worldState.world.weather} · city AI {worldState.city_ai.mode}</div>
      <EventOverlays worldState={worldState} />
      <SceneDirectorHud worldState={worldState} />
      <SceneLegend />
      <div className="cityCanvas">
        <Canvas camera={{ position: CITY_CAMERA_POSITION, fov: CITY_CAMERA_FOV }} shadows>
          <color attach="background" args={["#08111f"]} />
          <fog attach="fog" args={["#08111f", 10, 24]} />
          <GameCamera worldState={worldState} />
          <ambientLight intensity={0.5} />
          <hemisphereLight args={["#93c5fd", "#020617", 0.42]} />
          <directionalLight position={[6, 8, 4]} intensity={1.22} castShadow />
          <group scale={CITY_STAGE_SCALE}>
            <RoadGrid />
            <Buildings />
            <StreetProps />
            <WorldEffects worldState={worldState} />
            <WorldActors worldState={worldState} />
          </group>
        </Canvas>
      </div>
    </section>
  );
}
