'use client';

import { Canvas } from '@react-three/fiber';
import type { TrafficLightState, WorldStatePayload } from '@aetherville/shared-schemas';
import { createFallbackWorldState } from '@/lib/mockWorld';
import { useConnectionStore } from '@/store/connection';

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
    { position: [-4.4, 0.75, -4.4] as const, height: 1.5, color: '#38bdf8' },
    { position: [4.4, 1.1, -4.4] as const, height: 2.2, color: '#818cf8' },
    { position: [-4.4, 0.95, 4.4] as const, height: 1.9, color: '#2dd4bf' },
    { position: [4.4, 0.65, 4.4] as const, height: 1.3, color: '#f59e0b' }
  ];

  return (
    <group>
      {buildings.map((building) => (
        <mesh key={building.color} position={building.position}>
          <boxGeometry args={[1.4, building.height, 1.4]} />
          <meshStandardMaterial color={building.color} emissive={building.color} emissiveIntensity={0.08} />
        </mesh>
      ))}
    </group>
  );
}

function trafficColor(light: TrafficLightState) {
  if (light.state === 'green') return '#22c55e';
  if (light.state === 'yellow') return '#eab308';
  return '#ef4444';
}

function WorldActors({ worldState }: { worldState: WorldStatePayload }) {
  return (
    <group>
      {worldState.citizens.map((citizen) => (
        <mesh key={citizen.id} position={[citizen.pos[0], citizen.pos[1] + 0.25, citizen.pos[2]]}>
          <sphereGeometry args={[0.25, 24, 24]} />
          <meshStandardMaterial color="#f472b6" emissive="#831843" emissiveIntensity={0.2} />
        </mesh>
      ))}
      {worldState.vehicles.map((vehicle) => (
        <mesh key={vehicle.id} position={[vehicle.pos[0], vehicle.pos[1] + 0.18, vehicle.pos[2]]} rotation={[vehicle.rot[0], vehicle.rot[1], vehicle.rot[2]]}>
          <boxGeometry args={[0.75, 0.35, 0.42]} />
          <meshStandardMaterial color="#65f4d8" emissive="#0f766e" emissiveIntensity={0.18} />
        </mesh>
      ))}
      {worldState.drones.map((drone) => (
        <mesh key={drone.id} position={[drone.pos[0], drone.pos[1], drone.pos[2]]}>
          <octahedronGeometry args={[0.22]} />
          <meshStandardMaterial color="#f8fafc" emissive="#60a5fa" emissiveIntensity={0.35} />
        </mesh>
      ))}
      {worldState.traffic_lights.map((light) => (
        <group key={light.id} position={[light.pos[0], light.pos[1], light.pos[2]]}>
          <mesh position={[0, 0.42, 0]}>
            <cylinderGeometry args={[0.08, 0.08, 0.8, 16]} />
            <meshStandardMaterial color="#94a3b8" />
          </mesh>
          <mesh position={[0, 0.88, 0]}>
            <sphereGeometry args={[0.14, 16, 16]} />
            <meshStandardMaterial color={trafficColor(light)} emissive={trafficColor(light)} emissiveIntensity={0.55} />
          </mesh>
        </group>
      ))}
    </group>
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
