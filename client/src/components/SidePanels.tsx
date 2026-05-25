'use client';

import { useMemo } from 'react';
import type { WorldStatePayload } from '@aetherville/shared-schemas';
import { createFallbackWorldState } from '@/lib/mockWorld';
import { useConnectionStore } from '@/store/connection';
import { GodModeMicPanel } from '@/ui/GodModeMicPanel';
import { LearningPanel } from '@/ui/LearningPanel';
import { MemoryPanel } from '@/ui/MemoryPanel';
import { TrafficChartPanel } from '@/ui/TrafficChartPanel';
import { VehicleCamPanel } from '@/ui/VehicleCamPanel';

function usePanelWorldState(): { tick: number; worldState: WorldStatePayload; mode: string } {
  const tick = useConnectionStore((state) => state.lastTick);
  const liveWorldState = useConnectionStore((state) => state.lastWorldState);
  const mode = useConnectionStore((state) => state.state);

  return useMemo(
    () => ({
      tick,
      worldState: liveWorldState ?? createFallbackWorldState(tick),
      mode
    }),
    [liveWorldState, mode, tick]
  );
}

export function SidePanels() {
  const { tick, worldState, mode } = usePanelWorldState();
  const primaryCitizen = worldState.citizens[0];
  const primaryVehicle = worldState.vehicles[0];

  return (
    <section className="panelDeck" aria-label="Aetherville side panels">
      <MemoryPanel citizen={primaryCitizen} tick={tick} worldState={worldState} />
      <VehicleCamPanel vehicle={primaryVehicle} />
      <TrafficChartPanel
        forecast={worldState.traffic_forecast}
        trafficAi={worldState.traffic_ai}
        forecastAi={worldState.traffic_forecast_ai}
      />
      <LearningPanel learning={worldState.learning} />
      <GodModeMicPanel mode={mode} worldState={worldState} />
    </section>
  );
}
