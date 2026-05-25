'use client';

import type { LearningSnapshot } from '@aetherville/shared-schemas';

interface LearningPanelProps {
  learning: LearningSnapshot;
}

function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

export function LearningPanel({ learning }: LearningPanelProps) {
  const latestInsight =
    learning.insights.at(-1) ?? '아직 충분한 학습 신호가 없습니다. God Mode 명령을 실행해 보세요.';

  return (
    <article className="sidePanel learningPanel">
      <div className="panelKicker">AI learning loop</div>
      <h2>AI 학습 루프</h2>
      <p>
        {learning.policy_version} · {learning.storage === 'json_persistence' ? '영속 저장' : '메모리'}
      </p>
      <div className="learningMetrics" aria-label="AI learning metrics">
        <span>
          <strong>{learning.experience_count}</strong>
          경험
        </span>
        <span>
          <strong>{learning.adaptation_epoch}</strong>
          epoch
        </span>
        <span>
          <strong>{percent(learning.taxi_success_rate)}</strong>
          택시
        </span>
      </div>
      <div className="learningMeter" aria-label="Learned traffic pressure">
        <span style={{ width: percent(learning.traffic_bias) }} />
      </div>
      <small className="learningInsight">{latestInsight}</small>
    </article>
  );
}
