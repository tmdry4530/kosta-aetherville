import type { WorldStatePayload } from '@aetherville/shared-schemas';

interface SceneImpactPanelProps {
  worldState: WorldStatePayload;
}

interface ImpactItem {
  key: string;
  label: string;
  detail: string;
  active: boolean;
}

function tagText(worldState: WorldStatePayload): string {
  return [
    ...worldState.citizens.flatMap((citizen) => citizen.display_tags),
    ...worldState.vehicles.flatMap((vehicle) => vehicle.display_tags),
    ...worldState.traffic_lights.flatMap((light) => light.display_tags)
  ].join(' ');
}

function cityAiActionLabel(action: string): string {
  const labels: Record<string, string> = {
    move_citizen: '시민 이동',
    call_taxi: '택시 배차',
    meet: '만남 조율',
    remember: '기억 추가',
    traffic_surge: '정체 유도',
    set_weather: '날씨 변경',
    no_op: '관찰',
    rain: '비 내림',
    clear: '맑음 전환',
    snow: '눈 내림',
    traffic_jam: '교통량 증가',
    taxi_call: '택시 호출',
    meeting: '만남',
    memory: '시민 기억',
    person_update: '시민 상태',
    relationship: '관계 변화'
  };
  return labels[action] ?? action.replaceAll('_', ' ');
}

function cityAiStatusLabel(worldState: WorldStatePayload): string {
  const mode = worldState.city_ai.mode === 'vllm' ? 'vLLM 판단' : worldState.city_ai.mode === 'rules' ? '규칙 판단' : '비활성';
  const status =
    worldState.city_ai.status === 'applied'
      ? '적용됨'
      : worldState.city_ai.status === 'planning'
        ? '계획 중'
        : worldState.city_ai.status === 'fallback'
          ? '폴백'
          : worldState.city_ai.status === 'error'
            ? '오류'
            : '대기';
  return `${mode}/${status}`;
}

export function buildImpactItems(worldState: WorldStatePayload): ImpactItem[] {
  const tags = tagText(worldState);
  const infrastructure = worldState.world.infrastructure_status ?? '';
  const activeEvent = worldState.world.active_event ?? '';
  const taxi = worldState.vehicles.find((vehicle) => vehicle.id === 'v01');
  const minji = worldState.citizens.find((citizen) => citizen.id === 'c01' || citizen.name === '민지');
  const minsu = worldState.citizens.find((citizen) => citizen.id === 'c02' || citizen.name === '민수');
  const cityAiActions = worldState.city_ai.actions.map((action) => cityAiActionLabel(action.type)).join(' → ');
  const scenario = worldState.scenario;

  return [
    {
      key: 'rain',
      label: 'RAIN',
      detail: '비/시야 이벤트',
      active: worldState.world.weather === 'rain' || activeEvent.includes('weather:rain') || tags.includes('rain')
    },
    {
      key: 'taxi',
      label: 'TAXI',
      detail: '민지 호출·승객 상태',
      active: Boolean(taxi?.passenger_id) || tags.includes('택시 호출') || activeEvent.includes('taxi')
    },
    {
      key: 'traffic',
      label: 'TRAFFIC',
      detail: '정체·저속·신호 제어',
      active:
        infrastructure.includes('congestion') ||
        infrastructure.includes('정체') ||
        activeEvent.includes('traffic congestion') ||
        tags.includes('정체') ||
        tags.includes('저속')
    },
    {
      key: 'meeting',
      label: 'MEETING',
      detail: '민지·민수 대화',
      active:
        minji?.talking_to === minsu?.id ||
        minsu?.talking_to === minji?.id ||
        tags.includes('대화') ||
        activeEvent.includes('relationship')
    },
    {
      key: 'scenario',
      label: 'SCENARIO',
      detail: scenario
        ? `${scenario.status} · ${scenario.steps.filter((step) => step.status === 'completed').length}/${scenario.steps.length} 단계`
        : '복합 상황 대기',
      active: scenario?.status === 'running' || scenario?.status === 'completed'
    },
    {
      key: 'city-ai',
      label: 'CITY AI',
      detail: `${cityAiStatusLabel(worldState)} · ${cityAiActions || worldState.city_ai.summary}`,
      active: worldState.city_ai.mode !== 'disabled' && worldState.city_ai.status === 'applied'
    },
    {
      key: 'gpu-policy',
      label: 'GPU POLICY',
      detail: `${worldState.traffic_ai.policy_version} · ${worldState.traffic_ai.training_backend}`,
      active: worldState.traffic_ai.mode === 'checkpoint' && worldState.traffic_ai.trained_on_gpu
    },
    {
      key: 'lstm',
      label: 'LSTM FORECAST',
      detail: `${worldState.traffic_forecast_ai.forecast_version} · MAPE ${worldState.traffic_forecast_ai.mape}%`,
      active:
        worldState.traffic_forecast_ai.mode === 'lstm_checkpoint' &&
        worldState.traffic_forecast_ai.trained_on_gpu
    }
  ];
}

export function SceneImpactPanel({ worldState }: SceneImpactPanelProps) {
  const impactItems = buildImpactItems(worldState);
  const activeCount = impactItems.filter((item) => item.active).length;
  const learning = worldState.learning;

  return (
    <article className="sidePanel impactPanel" aria-label="Live impact scene director">
      <div className="panelKicker">Scene director</div>
      <h2>Live impact board</h2>
      <p>
        God Mode 결과를 관객용 상황 카드로 고정 표시합니다. 활성 효과 {activeCount}/
        {impactItems.length}.
      </p>
      <div className="impactGrid" aria-label="God Mode visible impact cards">
        {impactItems.map((item) => (
          <span className={`impactChip${item.active ? ' impactChip-active' : ''}`} key={item.key}>
            <strong>{item.label}</strong>
            <small>{item.detail}</small>
          </span>
        ))}
      </div>
      <small className="impactLearning">
        AI 학습 루프: 누적 이벤트 {learning.experience_count} · 적응 {learning.adaptation_epoch} · 도시 AI{' '}
        {cityAiStatusLabel(worldState)}
      </small>
    </article>
  );
}
