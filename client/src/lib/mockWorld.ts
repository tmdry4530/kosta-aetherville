import type { Vec3, WorldStatePayload, YoloDetection } from '@aetherville/shared-schemas';

function vec3(x: number, y: number, z: number): Vec3 {
  return [x, y, z];
}

type Route2D = Array<readonly [number, number]>;

const citizenRoutes: Route2D[] = [
  [
    [-5.2, -2.7],
    [-2.4, -2.7],
    [-0.8, -0.9],
    [1.6, -0.9],
    [4.9, 0.8]
  ],
  [
    [2.8, -5.1],
    [2.8, -1.4],
    [1.1, 0],
    [-1.3, 0],
    [-1.3, 4.8]
  ]
];

const vehicleRoute: Route2D = [
  [-4.4, -1.7],
  [-1.2, -1.7],
  [0, 0],
  [1.4, 1.7],
  [4.4, 1.7]
];

const droneRoute: Route2D = [
  [-2.6, 2.4],
  [0.6, 3.2],
  [2.8, -1.8],
  [-1.8, -2.4]
];

function poseOnRoute(route: Route2D, progress: number) {
  const segments = route.slice(0, -1).map((start, index) => {
    const end = route[index + 1];
    const length = Math.hypot(end[0] - start[0], end[1] - start[1]);
    return { start, end, length };
  });
  const totalLength = segments.reduce((sum, segment) => sum + segment.length, 0);
  let distance = ((progress % totalLength) + totalLength) % totalLength;

  for (const segment of segments) {
    if (distance <= segment.length) {
      const local = distance / Math.max(segment.length, 0.001);
      const x = segment.start[0] + (segment.end[0] - segment.start[0]) * local;
      const z = segment.start[1] + (segment.end[1] - segment.start[1]) * local;
      const yaw = Math.atan2(segment.end[0] - segment.start[0], segment.end[1] - segment.start[1]);
      return { x, z, yaw };
    }
    distance -= segment.length;
  }

  const last = segments[segments.length - 1];
  return {
    x: last.end[0],
    z: last.end[1],
    yaw: Math.atan2(last.end[0] - last.start[0], last.end[1] - last.start[1])
  };
}

export function createFallbackWorldState(tick = 0): WorldStatePayload {
  const trafficLightState = Math.floor(tick / 30) % 2 === 0 ? 'green' : 'red';
  const citizenA = poseOnRoute(citizenRoutes[0], tick * 0.055);
  const citizenB = poseOnRoute(citizenRoutes[1], tick * 0.048 + 3.4);
  const vehicle = poseOnRoute(vehicleRoute, tick * 0.14);
  const drone = poseOnRoute(droneRoute, tick * 0.07);
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
        pos: vec3(citizenA.x, 0, citizenA.z),
        rot: vec3(0, citizenA.yaw, 0),
        anim: tick > 0 ? 'walk' : 'idle',
        current_action: tick > 0 ? 'walking toward cafe waypoint' : 'waiting for state',
        talking_to: null
      },
      {
        id: 'c02',
        name: '서연',
        pos: vec3(citizenB.x, 0, citizenB.z),
        rot: vec3(0, citizenB.yaw, 0),
        anim: 'talk',
        current_action: 'checking memory kiosk',
        talking_to: tick % 80 > 40 ? 'c01' : null
      }
    ],
    vehicles: [
      {
        id: 'v01',
        type: 'taxi',
        pos: vec3(vehicle.x, 0, vehicle.z),
        rot: vec3(0, vehicle.yaw, 0),
        speed: tick > 0 ? 3.2 : 0,
        passenger_id: null,
        destination: vec3(4.4, 0, 1.7),
        yolo_detections: detections
      }
    ],
    drones: [
      {
        id: 'd01',
        pos: vec3(drone.x, 3, drone.z),
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
