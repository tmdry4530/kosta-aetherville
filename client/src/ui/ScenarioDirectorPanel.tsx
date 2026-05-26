import type { WorldStatePayload } from '@aetherville/shared-schemas';

interface ScenarioDirectorPanelProps {
  worldState: WorldStatePayload;
}

const STATUS_LABELS: Record<string, string> = {
  idle: '대기',
  running: '진행 중',
  completed: '완료',
  failed: '실패',
  pending: '대기',
  skipped: '건너뜀',
  accepted: '수락',
  clarification_needed: '가정 포함',
  rejected: '거절'
};

const STEP_TYPE_LABELS: Record<string, string> = {
  move_actor_to_actor: '시민 이동',
  move_actor_to_location: '위치 이동',
  meet: '만남',
  call_taxi: '택시 호출',
  taxi_pickup: '택시 픽업',
  taxi_drive_to_actor: '택시 이동',
  drone_move_to_actor: '드론 이동',
  drone_deliver: '드론 전달',
  move_actor_to_group: '합류 이동',
  group_rendezvous: '그룹 합류',
  remember: '기억',
  set_weather: '날씨',
  traffic_surge: '교통',
  wait: '대기',
  no_op: '상태 유지'
};

export function ScenarioDirectorPanel({ worldState }: ScenarioDirectorPanelProps) {
  const scenario = worldState.scenario;
  const taskGraph = worldState.task_graph;
  const runningStep = scenario?.steps.find((step) => step.id === scenario.current_step_id);
  const completed = scenario?.steps.filter((step) => step.status === 'completed').length ?? 0;
  const total = scenario?.steps.length ?? 0;
  const currentNode = taskGraph?.nodes.find((node) => node.id === taskGraph.current_node_id);
  const graphCompleted = taskGraph?.completed_count ?? 0;
  const graphTotal = taskGraph?.total_count ?? 0;

  return (
    <article className="sidePanel scenarioPanel" aria-label="Scenario Director step execution">
      <div className="panelKicker">Scenario Director</div>
      <h2>상황 실행 타임라인</h2>
      {taskGraph ? (
        <section className="scenarioNow" aria-label="TaskGraph execution snapshot">
          <strong>TaskGraph</strong>
          <span>
            {STATUS_LABELS[taskGraph.status] ?? taskGraph.status} · {graphCompleted}/{graphTotal}
            노드 완료
          </span>
          <small>
            현재 노드: {currentNode?.visible_label ?? taskGraph.current_node_id ?? '대기'}
            {taskGraph.rejection_reason ? ` · 거절 사유: ${taskGraph.rejection_reason}` : ''}
          </small>
          {taskGraph.assumptions.length > 0 ? (
            <small>가정: {taskGraph.assumptions.join(' / ')}</small>
          ) : null}
        </section>
      ) : null}
      {scenario ? (
        <>
          <p>
            {scenario.title} · {STATUS_LABELS[scenario.status] ?? scenario.status} · {completed}/{total}
            단계 완료
          </p>
          <div className="scenarioNow">
            <strong>현재 단계</strong>
            <span>{runningStep?.visible_label ?? (scenario.status === 'completed' ? '모든 단계 완료' : '다음 단계 대기')}</span>
          </div>
          <ol className="scenarioSteps">
            {scenario.steps.map((step, index) => (
              <li className={`scenarioStep scenarioStep-${step.status}`} key={step.id}>
                <span>{String(index + 1).padStart(2, '0')}</span>
                <div>
                  <strong>{step.visible_label}</strong>
                  <small>
                    {STEP_TYPE_LABELS[step.type] ?? step.type} · {STATUS_LABELS[step.status] ?? step.status}
                    {step.evidence ? ` · ${step.evidence}` : ''}
                  </small>
                </div>
              </li>
            ))}
          </ol>
        </>
      ) : (
        <p>
          복합 상황 명령을 입력하면 TaskGraph와 시민·택시·드론 단계가 여기 표시됩니다. 예:
          “민수가 하린을 만난 뒤 택시로 민지에게 가고, 드론은 서연에게 이동”.
        </p>
      )}
    </article>
  );
}
