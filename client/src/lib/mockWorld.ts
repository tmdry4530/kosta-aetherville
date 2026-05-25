import type { Vec3, WorldStatePayload, YoloDetection } from '@aetherville/shared-schemas';

function vec3(x: number, y: number, z: number): Vec3 {
  return [x, y, z];
}

type Route2D = Array<readonly [number, number]>;

const citizenRoutes: Route2D[] = [
  [
    [-5.7, -3.72],
    [-3.72, -3.72],
    [-3.72, -0.72],
    [-0.72, -0.72],
    [-0.72, 2.28]
  ],
  [
    [-2.28, -5.7],
    [-2.28, -3.72],
    [0.72, -3.72],
    [0.72, -0.72],
    [3.72, -0.72]
  ],
  [
    [2.28, -5.7],
    [2.28, -3.72],
    [5.7, -3.72],
    [5.7, -0.72],
    [2.28, -0.72]
  ],
  [
    [-5.7, 0.72],
    [-3.72, 0.72],
    [-3.72, 3.72],
    [-0.72, 3.72],
    [-0.72, 5.7]
  ],
  [
    [0.72, 5.7],
    [0.72, 3.72],
    [3.72, 3.72],
    [3.72, 0.72],
    [5.7, 0.72]
  ],
  [
    [-5.7, 5.7],
    [-5.7, 3.72],
    [-2.28, 3.72],
    [-2.28, 0.72],
    [0.72, 0.72]
  ],
  [
    [5.7, 5.7],
    [3.72, 5.7],
    [3.72, 2.28],
    [0.72, 2.28],
    [0.72, -2.28]
  ]
];

const vehicleRoutes: Route2D[] = [
  [
    [-6, -3],
    [-3, -3],
    [0, -3],
    [3, -3],
    [6, -3]
  ],
  [
    [-6, 0],
    [-3, 0],
    [0, 0],
    [0, 3],
    [0, 6]
  ],
  [
    [3, -6],
    [3, -3],
    [3, 0],
    [6, 0],
    [6, 3]
  ]
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
  const citizenNames = ['민지', '민수', '서연', '도윤', '하린', '지호', '민준'];
  const citizens = citizenNames.map((name, index) => {
    const pose = poseOnRoute(citizenRoutes[index], tick * (0.045 + (index % 4) * 0.006) + index * 1.35);
    return {
      id: `c${String(index + 1).padStart(2, '0')}`,
      name,
      pos: vec3(pose.x + ((index % 3) - 1) * 0.14, 0, pose.z),
      rot: vec3(0, pose.yaw, 0),
      anim: tick > 0 ? 'walk' : 'idle',
      current_action: '인도 경로를 따라 이동 중',
      talking_to: null,
      display_tags: [name, '인도']
    };
  });
  const vehicles = vehicleRoutes.map((route, index) => {
    const pose = poseOnRoute(route, tick * (0.13 + index * 0.025) + index * 2.5);
    return {
      id: `v${String(index + 1).padStart(2, '0')}`,
      type: index === 0 ? 'taxi' : 'shuttle',
      pos: vec3(pose.x, 0, pose.z),
      rot: vec3(0, pose.yaw, 0),
      speed: tick > 0 ? 3.2 + index * 0.4 : 0,
      passenger_id: null,
      destination: vec3(route[route.length - 1][0], 0, route[route.length - 1][1]),
      yolo_detections: [] as YoloDetection[],
      display_tags: index === 0 ? ['TAXI', '차도', 'v01'] : ['차도', `v0${index + 1}`]
    };
  });
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
  vehicles[0].yolo_detections = detections;
  return {
    world: {
      time_of_day: '09:30',
      weather: 'replay-clear',
      temperature: 21.5
    },
    citizens,
    vehicles,
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
        id: 'tl_nw',
        pos: vec3(-3, 0, -3),
        state: trafficLightState,
        remaining_sec: Math.max(0, 30 - (tick % 30)),
        display_tags: ['신호등', trafficLightState]
      },
      {
        id: 'tl_ne',
        pos: vec3(3, 0, -3),
        state: Math.floor(tick / 30) % 2 === 0 ? 'red' : 'green',
        remaining_sec: Math.max(0, 30 - (tick % 30)),
        display_tags: ['신호등', Math.floor(tick / 30) % 2 === 0 ? 'red' : 'green']
      },
      {
        id: 'tl_sw',
        pos: vec3(-3, 0, 3),
        state: Math.floor(tick / 30) % 2 === 0 ? 'red' : 'green',
        remaining_sec: Math.max(0, 30 - (tick % 30)),
        display_tags: ['신호등', Math.floor(tick / 30) % 2 === 0 ? 'red' : 'green']
      },
      {
        id: 'tl_se',
        pos: vec3(3, 0, 3),
        state: trafficLightState,
        remaining_sec: Math.max(0, 30 - (tick % 30)),
        display_tags: ['신호등', trafficLightState]
      }
    ],
    traffic_forecast: [5, 10, 15].map((minute) => ({
      minute_offset: minute,
      expected_vehicle_count: 28 + minute * 2 + (tick % 7),
      congestion_index: Math.min(1, 0.22 + minute / 60 + (tick % 9) / 100)
    })),
    traffic_ai: {
      mode: 'fixed_cycle',
      policy_version: 'fixed-cycle-replay-v0',
      checkpoint_loaded: false,
      trained_on_gpu: false,
      training_backend: 'none',
      episodes: 0,
      improvement_pct: 0,
      avg_queue_fixed_cycle: null,
      avg_queue_candidate: null,
      last_action: null,
      detail: 'replay fallback fixed-cycle baseline'
    },
    traffic_forecast_ai: {
      mode: 'deterministic_fallback',
      forecast_version: 'deterministic-replay-v0',
      checkpoint_loaded: false,
      trained_on_gpu: false,
      training_backend: 'none',
      sequence_length: 0,
      horizon_minutes: [5, 10, 15],
      mape: null,
      training_loss: null,
      detail: 'replay fallback deterministic forecast'
    },
    learning: {
      mode: 'deterministic_online_adaptation',
      storage: 'memory',
      experience_count: Math.floor(tick / 45),
      adaptation_epoch: Math.floor(tick / 135),
      policy_version: `adaptive-demo-v${Math.floor(tick / 135)}`,
      traffic_bias: Math.min(1, Math.floor(tick / 45) * 0.04),
      taxi_success_rate: Math.min(0.92, 0.5 + Math.floor(tick / 60) * 0.03),
      citizen_memory_count: Math.floor(tick / 30),
      weather_bias: Math.min(1, Math.floor(tick / 90) * 0.08),
      last_updated_tick: tick,
      insights: ['Replay fallback에서도 학습 패널 형태를 유지합니다.']
    },
    city_ai: {
      mode: 'rules',
      status: 'applied',
      plan_id: `replay_city_${Math.floor(tick / 120)}`,
      last_planned_tick: Math.max(0, tick - (tick % 120)),
      next_plan_tick: Math.max(120, tick - (tick % 120) + 120),
      summary: 'Replay 도시 AI가 시민 이동·교통·날씨 상황을 순환 계획합니다.',
      actions: [
        {
          type: 'move_citizen',
          actor_id: 'c03',
          target_id: 'c01',
          vehicle_id: null,
          destination_actor_id: 'c01',
          destination: null,
          weather: null,
          memory: null,
          label: '민지에게 자율 이동',
          after: null,
          reason: 'replay fallback city planner'
        }
      ],
      reason: 'replay fallback city planner'
    }
  };
}
