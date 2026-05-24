import type { Vec3, WorldStatePayload, YoloDetection } from '@aetherville/shared-schemas';

function vec3(x: number, y: number, z: number): Vec3 {
  return [x, y, z];
}

export function createFallbackWorldState(tick = 0): WorldStatePayload {
  const angle = tick * 0.08;
  const trafficLightState = Math.floor(tick / 30) % 2 === 0 ? 'green' : 'red';
  const detections: YoloDetection[] = [
    {
      label: 'traffic_light',
      confidence: 0.91,
      bbox: [236, 28, 262, 82],
      traffic_light_state: trafficLightState,
      distance_m: 18.5
    }
  ];
  if (tick % 40 >= 8 && tick % 40 <= 18) {
    detections.push({
      label: 'pedestrian',
      confidence: 0.87,
      bbox: [118, 66, 164, 170],
      traffic_light_state: null,
      distance_m: 9.5
    });
  }
  return {
    world: {
      time_of_day: '09:30',
      weather: 'replay-clear',
      temperature: 21.5
    },
    citizens: [
      {
        id: 'c01',
        name: '민준',
        pos: vec3(Math.sin(angle / 2), 0, 0),
        rot: vec3(0, 0, 0),
        anim: tick > 0 ? 'walk' : 'idle',
        current_action: tick > 0 ? 'replay walk cycle' : 'waiting for state',
        talking_to: null
      },
      {
        id: 'c02',
        name: '서연',
        pos: vec3(-1.6, 0, Math.cos(angle / 3) * 1.8),
        rot: vec3(0, Math.PI / 4, 0),
        anim: 'talk',
        current_action: 'checking memory kiosk',
        talking_to: tick % 80 > 40 ? 'c01' : null
      }
    ],
    vehicles: [
      {
        id: 'v01',
        type: 'taxi',
        pos: vec3(Math.sin(angle) * 4, 0, Math.cos(angle) * 4),
        rot: vec3(0, angle % (Math.PI * 2), 0),
        speed: tick > 0 ? 3.2 : 0,
        passenger_id: null,
        destination: vec3(8, 0, 8),
        yolo_detections: detections
      }
    ],
    drones: [
      {
        id: 'd01',
        pos: vec3(-2, 3, 2),
        destination: vec3(2, 3, -2),
        cargo: 'medical-kit',
        battery: 0.94
      }
    ],
    traffic_lights: [
      {
        id: 'tl_01',
        pos: vec3(2, 0, 2),
        state: trafficLightState,
        remaining_sec: Math.max(0, 30 - (tick % 30))
      },
      {
        id: 'tl_02',
        pos: vec3(-2, 0, -2),
        state: Math.floor(tick / 30) % 2 === 0 ? 'red' : 'green',
        remaining_sec: Math.max(0, 30 - (tick % 30))
      }
    ],
    traffic_forecast: [5, 10, 15].map((minute) => ({
      minute_offset: minute,
      expected_vehicle_count: 28 + minute * 2 + (tick % 7),
      congestion_index: Math.min(1, 0.22 + minute / 60 + (tick % 9) / 100)
    }))
  };
}
