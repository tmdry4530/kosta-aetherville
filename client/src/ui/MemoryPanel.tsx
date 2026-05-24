'use client';

import type { CitizenState, MemoryRecord, WorldStatePayload } from '@aetherville/shared-schemas';

interface MemoryPanelProps {
  citizen: CitizenState | undefined;
  tick: number;
  worldState: WorldStatePayload;
}

function buildFallbackMemories(
  citizen: CitizenState | undefined,
  tick: number,
  worldState: WorldStatePayload
): MemoryRecord[] {
  const citizenId = citizen?.id ?? 'c01';
  const citizenName = citizen?.name ?? 'seed citizen';
  return [
    {
      id: `${citizenId}_ui_${tick}`,
      citizen_id: citizenId,
      text: `${citizenName} observes ${worldState.world.weather} at tick ${tick}`,
      created_tick: tick,
      importance: 0.62,
      tags: ['ui', worldState.world.weather],
      retrieval_score: 0.88
    },
    {
      id: `${citizenId}_plan`,
      citizen_id: citizenId,
      text: citizen?.current_action ?? 'awaiting citizen action',
      created_tick: Math.max(0, tick - 12),
      importance: 0.54,
      tags: ['plan'],
      retrieval_score: 0.7
    }
  ];
}

export function MemoryPanel({ citizen, tick, worldState }: MemoryPanelProps) {
  const memories = buildFallbackMemories(citizen, tick, worldState);

  return (
    <article className="sidePanel memoryPanel">
      <div className="panelKicker">Memory stream</div>
      <h2>시민 기억 패널</h2>
      <p>
        {citizen?.name ?? 'seed citizen'} · {citizen?.current_action ?? 'awaiting state'}
      </p>
      <ol className="memoryList">
        {memories.map((memory) => (
          <li key={memory.id}>
            <strong>{memory.retrieval_score?.toFixed(2)}</strong> {memory.text}
          </li>
        ))}
      </ol>
    </article>
  );
}
