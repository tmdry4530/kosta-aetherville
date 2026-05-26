'use client';

import type { LearningSnapshot } from '@aetherville/shared-schemas';

interface LearningPanelProps {
  learning: LearningSnapshot;
}

function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function precisePercent(value: number) {
  return `${(value * 100).toFixed(value > 0.995 ? 2 : 1)}%`;
}

function uniqueInsights(insights: string[]) {
  return Array.from(new Set(insights)).slice(-3);
}

export function LearningPanel({ learning }: LearningPanelProps) {
  const insights = uniqueInsights(learning.insights ?? []);
  const evolution = learning.evolution ?? {
    version: 'evolution-fallback',
    scenario_success_count: 0,
    scenario_failure_count: 0,
    replan_count: 0
  };
  const policyBias = learning.policy_bias ?? {
    taxi_caution: 0,
    walking_bias: 0,
    traffic_caution: learning.traffic_bias ?? 0,
    rain_delay_expectation: learning.weather_bias ?? 0
  };
  const promotionGate = learning.promotion_gate ?? {
    active_policy_version: learning.policy_version,
    evaluator: 'deterministic_reward_gate',
    candidate_count: 0,
    promoted_count: 0,
    rejected_count: 0,
    last_decision: 'none',
    rollback_available: false
  };
  const latestCandidate = (learning.policy_candidates ?? []).at(-1);
  const latestInsight = insights.at(-1) ?? '아직 충분한 학습 신호가 없습니다. God Mode 명령을 실행해 보세요.';

  return (
    <article className="sidePanel learningPanel">
      <div className="panelKicker">Live adaptation loop</div>
      <h2>AI 학습 루프</h2>
      <p>
        RunPod 실행 중 누적된 God Mode·택시·날씨·기억 이벤트를 다음 도시 반응에 반영합니다.
      </p>
      <div className="learningMetrics" aria-label="AI learning metrics">
        <span>
          <strong>{learning.experience_count}</strong>
          이벤트
        </span>
        <span>
          <strong>{learning.adaptation_epoch}</strong>
          적응
        </span>
        <span>
          <strong>{precisePercent(learning.taxi_success_rate)}</strong>
          택시율
        </span>
      </div>
      <div className="learningMeter" aria-label="Learned traffic pressure">
        <span style={{ width: percent(learning.traffic_bias) }} />
      </div>
      <div className="learningSignals" aria-label="Learning signal sources">
        <span>저장: {learning.storage === 'json_persistence' ? 'JSON 영속 상태' : '메모리'}</span>
        <span>정책: {learning.policy_version}</span>
        <span>최근 tick: {learning.last_updated_tick}</span>
      </div>
      <div className="evolutionState" aria-label="Evolution state">
        <strong>Evolution state</strong>
        <span>{evolution.version}</span>
        <small>성공 {evolution.scenario_success_count} · blocker {evolution.scenario_failure_count} · replan {evolution.replan_count}</small>
      </div>
      <div className="policyBiasGrid" aria-label="Policy bias">
        <span>taxi caution {percent(policyBias.taxi_caution)}</span>
        <span>walking bias {percent(policyBias.walking_bias)}</span>
        <span>traffic caution {percent(policyBias.traffic_caution)}</span>
        <span>rain delay {percent(policyBias.rain_delay_expectation)}</span>
      </div>
      <div className={`promotionGate promotionGate-${promotionGate.last_decision}`} aria-label="Policy promotion gate">
        <strong>Policy promotion gate</strong>
        <span>{promotionGate.active_policy_version}</span>
        <small>
          후보 {promotionGate.candidate_count} · 승격 {promotionGate.promoted_count} · 보류{' '}
          {promotionGate.rejected_count} · {promotionGate.evaluator}
        </small>
        {latestCandidate ? (
          <small>
            최근 {latestCandidate.candidate_version}:{' '}
            {precisePercent(latestCandidate.score_before)} → {precisePercent(latestCandidate.score_after)}
            {' · '}
            {latestCandidate.promoted ? 'live policy 승격' : '기존 정책 유지'}
          </small>
        ) : null}
      </div>
      <small className="learningInsight">
        {latestInsight} · model-weight self-training: not verified, online policy-bias adaptation and promotion-gated learning only.
      </small>
      {insights.length > 1 ? (
        <ul className="learningInsightList" aria-label="Recent learning insights">
          {insights.slice(0, -1).map((insight) => (
            <li key={insight}>{insight}</li>
          ))}
        </ul>
      ) : null}
    </article>
  );
}
