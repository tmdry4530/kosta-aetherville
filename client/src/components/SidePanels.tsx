'use client';

import { useMemo } from 'react';
import type { WorldStatePayload } from '@aetherville/shared-schemas';
import { createFallbackWorldState } from '@/lib/mockWorld';
import { useConnectionStore } from '@/store/connection';
import { AiOperationsPanel } from '@/ui/AiOperationsPanel';
import { GodModeMicPanel } from '@/ui/GodModeMicPanel';
import { LearningPanel } from '@/ui/LearningPanel';
import { MemoryPanel } from '@/ui/MemoryPanel';
import { RunPodProofPanel } from '@/ui/RunPodProofPanel';
import { SceneImpactPanel } from '@/ui/SceneImpactPanel';
import { ScenarioDirectorPanel } from '@/ui/ScenarioDirectorPanel';
import { TrafficChartPanel } from '@/ui/TrafficChartPanel';
import { VehicleCamPanel } from '@/ui/VehicleCamPanel';

function usePanelWorldState(
  initialWorldState: WorldStatePayload | null
): { tick: number; worldState: WorldStatePayload; mode: string } {
  const tick = useConnectionStore((state) => state.lastTick);
  const liveWorldState = useConnectionStore((state) => state.lastWorldState);
  const mode = useConnectionStore((state) => state.state);

  return useMemo(
    () => ({
      tick,
      worldState: liveWorldState ?? initialWorldState ?? createFallbackWorldState(tick),
      mode
    }),
    [initialWorldState, liveWorldState, mode, tick]
  );
}

export function SidePanels({
  orchestratorUrl,
  initialWorldState = null
}: {
  orchestratorUrl: string | null;
  initialWorldState?: WorldStatePayload | null;
}) {
  const { tick, worldState, mode } = usePanelWorldState(initialWorldState);
  const primaryCitizen = worldState.citizens[0];
  const primaryVehicle = worldState.vehicles[0];

  return (
    <section className="panelDeck" aria-label="Aetherville side panels">
      <SceneImpactPanel worldState={worldState} />
      <ScenarioDirectorPanel worldState={worldState} />
      <AiOperationsPanel worldState={worldState} />
      <RunPodProofPanel worldState={worldState} orchestratorUrl={orchestratorUrl} />
      <MemoryPanel citizen={primaryCitizen} tick={tick} worldState={worldState} />
      <VehicleCamPanel vehicle={primaryVehicle} orchestratorUrl={orchestratorUrl} />
      <TrafficChartPanel
        forecast={worldState.traffic_forecast}
        trafficAi={worldState.traffic_ai}
        forecastAi={worldState.traffic_forecast_ai}
      />
      <LearningPanel learning={worldState.learning} />
      <GodModeMicPanel mode={mode} worldState={worldState} orchestratorUrl={orchestratorUrl} />
    </section>
  );
}
