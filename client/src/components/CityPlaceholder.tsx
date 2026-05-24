'use client';

import { Canvas } from '@react-three/fiber';
import type { CitizenState, DroneState, TrafficLightState, VehicleState, WorldStatePayload } from '@aetherville/shared-schemas';
import { createFallbackWorldState } from '@/lib/mockWorld';
import { useConnectionStore } from '@/store/connection';

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
  building: '#1e293b'
} as const;

function RoadGrid() {
  return (
    <group>
      <mesh position={[0, -0.03, 0]} receiveShadow>
        <boxGeometry args={[13, 0.04, 2]} />
        <meshStandardMaterial color="#111827" />
      </mesh>
      <mesh position={[0, -0.02, 0]} rotation={[0, Math.PI / 2, 0]} receiveShadow>
        <boxGeometry args={[13, 0.04, 2]} />
        <meshStandardMaterial color="#172033" />
      </mesh>
      <mesh position={[0, 0.01, 0]}>
        <boxGeometry args={[13, 0.015, 0.05]} />
        <meshStandardMaterial color="#f8fafc" emissive="#334155" />
      </mesh>
      <mesh position={[0, 0.02, 0]} rotation={[0, Math.PI / 2, 0]}>
        <boxGeometry args={[13, 0.015, 0.05]} />
        <meshStandardMaterial color="#f8fafc" emissive="#334155" />
      </mesh>
    </group>
  );
}

function Buildings() {
  const buildings = [
    { position: [-4.4, 0.75, -4.4] as const, height: 1.5, color: '#155e75' },
    { position: [4.4, 1.1, -4.4] as const, height: 2.2, color: '#3730a3' },
    { position: [-4.4, 0.95, 4.4] as const, height: 1.9, color: '#0f766e' },
    { position: [4.4, 0.65, 4.4] as const, height: 1.3, color: '#92400e' }
  ];

  return (
    <group>
      {buildings.map((building) => (
        <mesh key={building.color} position={building.position}>
          <boxGeometry args={[1.4, building.height, 1.4]} />
          <meshStandardMaterial color={building.color} emissive={actorPalette.building} emissiveIntensity={0.02} />
        </mesh>
      ))}
    </group>
  );
}

function CitizenActor({ citizen, index }: { citizen: CitizenState; index: number }) {
  const bodyColor = index % 2 === 0 ? actorPalette.citizenBody : '#2dd4bf';

  return (
    <group position={[citizen.pos[0], citizen.pos[1], citizen.pos[2]]} rotation={[citizen.rot[0], citizen.rot[1], citizen.rot[2]]}>
      <mesh position={[0, 0.03, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.28, 0.025, 8, 24]} />
        <meshStandardMaterial color={actorPalette.citizenRing} emissive={actorPalette.citizenHead} emissiveIntensity={0.28} />
      </mesh>
      <mesh position={[0, 0.28, 0]} castShadow>
        <cylinderGeometry args={[0.13, 0.18, 0.42, 18]} />
        <meshStandardMaterial color={bodyColor} emissive="#0f766e" emissiveIntensity={0.22} />
      </mesh>
      <mesh position={[0, 0.58, 0]} castShadow>
        <sphereGeometry args={[0.16, 20, 20]} />
        <meshStandardMaterial color={actorPalette.citizenHead} emissive="#831843" emissiveIntensity={0.32} />
      </mesh>
    </group>
  );
}

function VehicleActor({ vehicle }: { vehicle: VehicleState }) {
  return (
    <group position={[vehicle.pos[0], vehicle.pos[1], vehicle.pos[2]]} rotation={[vehicle.rot[0], vehicle.rot[1], vehicle.rot[2]]}>
      <mesh position={[0, 0.2, 0]} castShadow>
        <boxGeometry args={[1.05, 0.32, 0.58]} />
        <meshStandardMaterial color={actorPalette.vehicleBody} emissive="#92400e" emissiveIntensity={0.2} />
      </mesh>
      <mesh position={[0.12, 0.43, 0]} castShadow>
        <boxGeometry args={[0.48, 0.26, 0.46]} />
        <meshStandardMaterial color={actorPalette.vehicleCab} emissive="#075985" emissiveIntensity={0.24} />
      </mesh>
      <mesh position={[-0.42, 0.03, -0.34]} rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.12, 0.12, 0.1, 16]} />
        <meshStandardMaterial color={actorPalette.vehicleWheel} />
      </mesh>
      <mesh position={[0.42, 0.03, -0.34]} rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.12, 0.12, 0.1, 16]} />
        <meshStandardMaterial color={actorPalette.vehicleWheel} />
      </mesh>
      <mesh position={[-0.42, 0.03, 0.34]} rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.12, 0.12, 0.1, 16]} />
        <meshStandardMaterial color={actorPalette.vehicleWheel} />
      </mesh>
      <mesh position={[0.42, 0.03, 0.34]} rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.12, 0.12, 0.1, 16]} />
        <meshStandardMaterial color={actorPalette.vehicleWheel} />
      </mesh>
      <mesh position={[0, 0.66, 0]}>
        <boxGeometry args={[0.24, 0.08, 0.24]} />
        <meshStandardMaterial color="#fde68a" emissive={actorPalette.vehicleBody} emissiveIntensity={0.65} />
      </mesh>
    </group>
  );
}

function DroneActor({ drone }: { drone: DroneState }) {
  return (
    <group position={[drone.pos[0], drone.pos[1], drone.pos[2]]}>
      <mesh>
        <octahedronGeometry args={[0.24]} />
        <meshStandardMaterial color={actorPalette.drone} emissive={actorPalette.droneBeacon} emissiveIntensity={0.3} />
      </mesh>
      <mesh rotation={[0, 0, Math.PI / 4]}>
        <boxGeometry args={[0.78, 0.035, 0.035]} />
        <meshStandardMaterial color={actorPalette.droneBeacon} emissive={actorPalette.droneBeacon} emissiveIntensity={0.35} />
      </mesh>
      <mesh rotation={[0, 0, -Math.PI / 4]}>
        <boxGeometry args={[0.78, 0.035, 0.035]} />
        <meshStandardMaterial color={actorPalette.droneBeacon} emissive={actorPalette.droneBeacon} emissiveIntensity={0.35} />
      </mesh>
    </group>
  );
}

function TrafficLightActor({ light }: { light: TrafficLightState }) {
  const states = [
    { name: 'red', color: '#ef4444', y: 1.1 },
    { name: 'yellow', color: '#eab308', y: 0.88 },
    { name: 'green', color: '#22c55e', y: 0.66 }
  ];

  return (
    <group position={[light.pos[0], light.pos[1], light.pos[2]]}>
      <mesh position={[0, 0.42, 0]}>
        <cylinderGeometry args={[0.055, 0.075, 0.82, 16]} />
        <meshStandardMaterial color={actorPalette.signalPole} emissive="#475569" emissiveIntensity={0.08} />
      </mesh>
      <mesh position={[0, 0.88, 0]}>
        <boxGeometry args={[0.28, 0.68, 0.2]} />
        <meshStandardMaterial color={actorPalette.signalHousing} emissive="#111827" emissiveIntensity={0.12} />
      </mesh>
      {states.map((state) => {
        const active = state.name === light.state;
        return (
          <mesh key={state.name} position={[0, state.y, -0.11]}>
            <sphereGeometry args={[active ? 0.09 : 0.065, 16, 16]} />
            <meshStandardMaterial color={state.color} emissive={state.color} emissiveIntensity={active ? 0.9 : 0.05} />
          </mesh>
        );
      })}
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

function SceneLegend() {
  const legendItems = [
    { key: 'citizen', label: '시민', detail: '분홍 머리 + 청록 몸' },
    { key: 'vehicle', label: '차량', detail: '노란 택시 + 바퀴' },
    { key: 'signal', label: '신호등', detail: '3색 세로등' },
    { key: 'drone', label: '드론', detail: '보라 프로펠러' },
    { key: 'building', label: '건물', detail: '어두운 블록' }
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

export function CityPlaceholder() {
  const lastTick = useConnectionStore((state) => state.lastTick);
  const liveWorldState = useConnectionStore((state) => state.lastWorldState);
  const connectionState = useConnectionStore((state) => state.state);
  const worldState = liveWorldState ?? createFallbackWorldState(lastTick);

  return (
    <section className="cityPanel" aria-label="Aetherville city scene">
      <div className="statusPill">{connectionState} · tick {lastTick} · {worldState.world.weather}</div>
      <SceneLegend />
      <div className="cityCanvas">
        <Canvas camera={{ position: [7, 6, 7], fov: 45 }} shadows>
          <color attach="background" args={["#08111f"]} />
          <ambientLight intensity={0.65} />
          <directionalLight position={[6, 8, 4]} intensity={1.25} castShadow />
          <RoadGrid />
          <Buildings />
          <WorldActors worldState={worldState} />
        </Canvas>
      </div>
    </section>
  );
}
