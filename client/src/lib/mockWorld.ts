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
      insights: ['Replay fallback에서도 학습 패널 형태를 유지합니다.'],
      trajectory_events: [
        {
          id: `replay_traj_${tick}`,
          tick,
          event_kind: 'scenario_step_started',
          entity_id: 'c02',
          action: 'taxi_drive_to_actor',
          summary: 'Replay trajectory: 민수 택시 이동과 드론 이동을 causal chain에 표시합니다.'
        }
      ],
      outcome_scores: [
        {
          id: `replay_outcome_${tick}`,
          task_id: 'replay_scenario',
          success: true,
          duration_ticks: 180,
          replan_count: 1,
          score: 0.84,
          reason: 'Replay fallback scenario completed with visible observability.'
        }
      ],
      signals: [
        {
          id: `replay_signal_${tick}`,
          tick,
          kind: 'fallback_path',
          value: 1,
          entity_id: 'v01',
          description: 'Replay fallback path keeps demo explainability when live backend is absent.'
        }
      ],
      policy_bias: {
        taxi_caution: 0.18,
        walking_bias: 0.12,
        traffic_caution: Math.min(1, Math.floor(tick / 45) * 0.04),
        rain_delay_expectation: Math.min(1, Math.floor(tick / 90) * 0.08),
        drone_caution: 0.1,
        safer_timeout_bias: 0.16
      },
      evolution: {
        version: `evolution-v${Math.floor(tick / 135)}`,
        storage: 'memory',
        persistence_path: null,
        scenario_success_count: Math.floor(tick / 180),
        scenario_failure_count: 0,
        replan_count: tick > 120 ? 1 : 0,
        fallback_path_usage: tick > 120 ? 1 : 0,
        taxi_pickup_success_rate: Math.min(0.92, 0.5 + Math.floor(tick / 60) * 0.03),
        weather_delay_impact: Math.min(1, Math.floor(tick / 90) * 0.08),
        traffic_delay_impact: Math.min(1, Math.floor(tick / 45) * 0.04),
        citizen_meeting_success_count: Math.floor(tick / 220),
        repeated_actor_memory_count: Math.floor(tick / 30),
        last_signal: 'Replay mode shows deterministic evolution sample; model weights are not self-trained.'
      },
      policy_candidates: [
        {
          id: `replay_candidate_${tick}`,
          tick,
          candidate_version: `adaptive-policy-candidate-v${Math.max(1, Math.floor(tick / 180))}`,
          source_signal: 'fallback_path',
          score_before: 0.52,
          score_after: Math.min(0.88, 0.56 + Math.floor(tick / 180) * 0.04),
          promoted: tick > 180,
          reason: 'Replay fallback shows how reward-gated policy promotion is visualized.'
        }
      ],
      promotion_gate: {
        active_policy_version: `adaptive-policy-candidate-v${Math.max(1, Math.floor(tick / 180))}`,
        evaluator: 'deterministic_reward_gate',
        candidate_count: Math.max(1, Math.floor(tick / 180)),
        promoted_count: tick > 180 ? Math.max(1, Math.floor(tick / 240)) : 0,
        rejected_count: 0,
        last_decision: tick > 180 ? 'promoted' : 'none',
        last_promoted_version: tick > 180 ? `adaptive-policy-candidate-v${Math.max(1, Math.floor(tick / 180))}` : null,
        rollback_available: tick > 180
      },
      model_training: {
        mode: tick > 180 ? 'dry_run' : 'not_configured',
        approval_required: true,
        approval_env: 'AETHERVILLE_APPROVE_MODEL_TRAINING',
        experience_log_path: '/tmp/aetherville/training/experience_log.jsonl',
        registry_path: '/tmp/aetherville/training/checkpoints/registry.json',
        dataset_count: tick > 180 ? 4 : 0,
        checkpoint_count: 0,
        promoted_count: 0,
        rollback_available: false,
        targets: ['vllm_lora', 'yolo', 'traffic_ppo', 'traffic_lstm'],
        jobs: tick > 180 ? [
          {
            id: `replay_train_${tick}`,
            target: 'vllm_lora',
            status: 'dry_run',
            dry_run: true,
            dataset: null,
            checkpoint: null,
            evaluation: null,
            started_ts: tick,
            completed_ts: tick,
            detail: 'Replay shows guarded model-weight training handoff without mutating weights.',
            command: ['python3', 'scripts/train_vllm_lora.py', '--dry-run']
          }
        ] : [],
        last_cycle_id: tick > 180 ? `replay_train_${Math.floor(tick / 180)}` : null
      }
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
    },
    scenario: tick > 90 ? {
      id: `replay_scenario_${Math.floor(tick / 180)}`,
      raw_text: 'Replay fallback 복합 상황',
      title: 'Replay 연쇄 상황',
      status: tick % 360 > 300 ? 'completed' : 'running',
      created_tick: Math.max(0, tick - (tick % 180)),
      updated_tick: tick,
      current_step_id: tick % 180 < 80 ? 'replay_drone' : 'replay_taxi',
      actors: ['c01', 'c02', 'c03'],
      summary: 'Replay fallback에서도 상황 디렉터 패널과 HUD를 유지합니다.',
      steps: [
        {
          id: 'replay_drone',
          type: 'drone_move_to_actor',
          status: tick % 180 < 80 ? 'running' : 'completed',
          actor_id: null,
          target_actor_id: 'c03',
          target_actor_ids: [],
          vehicle_id: null,
          drone_id: 'd01',
          depends_on: [],
          started_tick: Math.max(0, tick - (tick % 180)),
          completed_tick: tick % 180 < 80 ? null : tick - 20,
          visible_label: '드론 → 서연 이동',
          evidence: tick % 180 < 80 ? null : 'replay drone arrived',
          metadata: { task_node_id: 'replay_drone', timeout_ticks: 360 }
        },
        {
          id: 'replay_taxi',
          type: 'taxi_drive_to_actor',
          status: tick % 180 < 80 ? 'pending' : 'running',
          actor_id: 'c02',
          target_actor_id: 'c01',
          target_actor_ids: [],
          vehicle_id: 'v01',
          drone_id: null,
          depends_on: ['replay_drone'],
          started_tick: tick % 180 < 80 ? null : tick - 10,
          completed_tick: null,
          visible_label: '택시가 민수를 민지에게 이동',
          evidence: null,
          metadata: { task_node_id: 'replay_taxi', timeout_ticks: 360 }
        }
      ]
    } : null,
    task_graph: {
      graph_id: 'replay_graph',
      plan_id: 'replay_plan',
      status: tick % 360 > 300 ? 'completed' : 'running',
      current_node_id: tick % 180 < 80 ? 'replay_drone' : 'replay_taxi',
      nodes: [
        {
          id: 'replay_drone',
          action_type: 'drone_move_to_actor',
          status: tick % 180 < 80 ? 'running' : 'completed',
          actor_id: null,
          actor_selector: null,
          target_actor_id: 'c03',
          target_actor_ids: [],
          target_entity_id: 'd01',
          target_selector: null,
          vehicle_id: null,
          drone_id: 'd01',
          location: null,
          depends_on: [],
          success_condition: { kind: 'distance_less_than', description: '드론이 서연 근처 도착', entity_id: 'd01', target_id: 'c03', threshold: 0.55, timeout_ticks: 360, metadata: {} },
          failure_condition: { kind: 'manual_review', description: '드론 지연 시 재계획', entity_id: 'd01', target_id: 'c03', threshold: null, timeout_ticks: 360, metadata: {} },
          timeout_ticks: 360,
          retry_limit: 1,
          reason: 'Replay drone demonstrates visible autonomous delivery intent.',
          visible_label: '드론 → 서연 이동',
          metadata: {}
        },
        {
          id: 'replay_taxi',
          action_type: 'taxi_drive_to_actor',
          status: tick % 180 < 80 ? 'pending' : 'running',
          actor_id: 'c02',
          actor_selector: null,
          target_actor_id: 'c01',
          target_actor_ids: [],
          target_entity_id: 'v01',
          target_selector: null,
          vehicle_id: 'v01',
          drone_id: null,
          location: null,
          depends_on: ['replay_drone'],
          success_condition: { kind: 'distance_less_than', description: '민수가 민지 근처 도착', entity_id: 'c02', target_id: 'c01', threshold: 0.55, timeout_ticks: 360, metadata: {} },
          failure_condition: { kind: 'manual_review', description: '택시 지연 시 fallback', entity_id: 'v01', target_id: 'c01', threshold: null, timeout_ticks: 360, metadata: {} },
          timeout_ticks: 360,
          retry_limit: 1,
          reason: 'Replay taxi shows pickup/dropoff intent with fallback-safe status.',
          visible_label: '택시가 민수를 민지에게 이동',
          metadata: {}
        }
      ],
      completed_count: tick % 180 < 80 ? 0 : 1,
      total_count: 2,
      assumptions: ['Replay fallback uses deterministic causal chain.'],
      rejection_reason: null,
      updated_tick: tick
    },
    entity_brains: [
      {
        entity_id: 'c02',
        entity_type: 'citizen',
        current_goal: { id: 'replay_taxi', title: '민수가 택시로 민지에게 이동', target_id: 'c01', source: 'task_graph' },
        next_action: 'taxi_drive_to_actor',
        reason: 'TaskGraph가 민수의 이동 목표와 택시 의존성을 설명합니다.',
        source: 'task_graph',
        progress: { progress_pct: tick % 180 < 80 ? 0.18 : 0.58, current_step_id: 'replay_taxi', eta_ticks: 120 },
        constraints: [{ kind: 'dependency', description: '드론 단계 이후 실행', severity: 'info' }],
        blocker: null,
        status: tick % 180 < 80 ? 'waiting' : 'moving',
        blocked_reason: null,
        updated_tick: tick
      },
      {
        entity_id: 'v01',
        entity_type: 'taxi',
        current_goal: { id: 'replay_taxi_route', title: '택시 pickup/dropoff route', target_id: 'c02', source: 'god_mode' },
        next_action: 'follow_route_or_dispatch',
        reason: '택시는 시민 호출, 교통, YOLO hazard를 반영해 이동합니다.',
        source: 'god_mode',
        progress: { progress_pct: 0.62, current_step_id: 'replay_taxi', eta_ticks: 90 },
        constraints: [{ kind: 'traffic', description: 'replay traffic pressure visible', severity: 'info' }],
        blocker: null,
        status: 'moving',
        blocked_reason: null,
        updated_tick: tick
      },
      {
        entity_id: 'd01',
        entity_type: 'drone',
        current_goal: { id: 'replay_drone', title: '드론 → 서연 이동', target_id: 'c03', source: 'task_graph' },
        next_action: 'drone_move_to_actor',
        reason: '드론 이동과 목적지를 entity brain으로 노출합니다.',
        source: 'task_graph',
        progress: { progress_pct: 0.72, current_step_id: 'replay_drone', eta_ticks: 60 },
        constraints: [{ kind: 'battery', description: 'battery 94%', severity: 'info' }],
        blocker: null,
        status: 'moving',
        blocked_reason: null,
        updated_tick: tick
      }
    ],
    replans: tick > 120 ? [
      {
        id: `replay_replan_${tick}`,
        tick,
        task_node_id: 'replay_taxi',
        entity_id: 'v01',
        blocker_type: 'traffic_delay',
        reason: 'Replay traffic delay selected a bounded fallback route.',
        attempt: 1,
        fallback_action: 'taxi_to_walking_safe_arrival',
        status: 'recovered'
      }
    ] : []
  };
}
