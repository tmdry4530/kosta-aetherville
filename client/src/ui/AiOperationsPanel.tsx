'use client';

import type { EntityBrainState, ReplanRecord, WorldStatePayload } from '@aetherville/shared-schemas';

interface AiOperationsPanelProps {
  worldState: WorldStatePayload;
}

function statusLabel(brain: EntityBrainState) {
  const source = brain.source === 'task_graph' ? 'TaskGraph' : brain.source;
  return `${source} · ${brain.status}`;
}

function compactBrainReason(brain: EntityBrainState) {
  if (brain.blocked_reason) {
    return brain.blocked_reason;
  }
  return brain.reason.length > 86 ? `${brain.reason.slice(0, 83)}…` : brain.reason;
}

function replanCopy(record: ReplanRecord) {
  return `${record.blocker_type} → ${record.fallback_action} · ${record.status} #${record.attempt}`;
}

export function AiOperationsPanel({ worldState }: AiOperationsPanelProps) {
  const brains = (worldState.entity_brains ?? []).slice(0, 8);
  const replans = (worldState.replans ?? []).slice(-5).reverse();
  const graph = worldState.task_graph;
  const currentNode = graph?.nodes.find((node) => node.id === graph.current_node_id) ?? graph?.nodes[0];
  const latestTrajectory = (worldState.learning.trajectory_events ?? []).at(-1);
  const latestSignal = (worldState.learning.signals ?? []).at(-1);

  return (
    <article className="sidePanel aiOperationsPanel">
      <div className="panelKicker">AI operations</div>
      <h2>Entity intent · Replan feed</h2>
      <p>
        명령 → TaskGraph → entity brain → replan → learning으로 이어지는 인과 체인을 화면에서 검증합니다.
      </p>

      <div className="opsGrid" aria-label="Causal event chain">
        <span>
          <strong>TaskGraph</strong>
          {graph ? `${graph.status} ${graph.completed_count}/${graph.total_count}` : 'replay-safe fallback'}
        </span>
        <span>
          <strong>Current</strong>
          {currentNode?.visible_label ?? 'routine city loop'}
        </span>
        <span>
          <strong>Learning</strong>
          {latestSignal?.kind ?? worldState.learning.evolution?.version ?? 'evolution-fallback'}
        </span>
      </div>

      <section className="entityIntentList" aria-label="Entity intent inspector">
        <h3>Entity intent</h3>
        {brains.map((brain) => (
          <div className={`entityIntent entityIntent-${brain.status}`} key={brain.entity_id}>
            <div>
              <strong>{brain.entity_id}</strong>
              <span>{statusLabel(brain)}</span>
            </div>
            <p>{brain.current_goal.title}</p>
            <small>{compactBrainReason(brain)}</small>
          </div>
        ))}
      </section>

      <section className="replanFeed" aria-label="Replan feed">
        <h3>Replan feed</h3>
        {replans.length ? (
          replans.map((record) => (
            <div className={`replanRecord replanRecord-${record.status}`} key={record.id}>
              <strong>{replanCopy(record)}</strong>
              <span>{record.reason}</span>
            </div>
          ))
        ) : (
          <p className="emptyPanelNote">현재 blocker 없음 · bounded replanner 대기 중</p>
        )}
      </section>

      <section className="causalChain" aria-label="Causal chain details">
        <h3>Causal event chain</h3>
        <ol>
          <li>God Mode command interpreted as bounded graph/action vocabulary.</li>
          <li>{currentNode?.reason ?? 'Routine planner keeps baseline motion alive.'}</li>
          <li>{latestTrajectory?.summary ?? 'No live trajectory yet; replay fallback is deterministic.'}</li>
          <li>{worldState.learning.evolution?.last_signal ?? 'Evolution state waits for live signals.'}</li>
        </ol>
      </section>
    </article>
  );
}
