'use client';

import { useEffect } from 'react';
import { createFallbackWorldState } from '@/lib/mockWorld';
import { useConnectionStore } from '@/store/connection';

export function ReplayDriver() {
  useEffect(() => {
    let tick = 0;
    useConnectionStore.getState().applyReplayWorldState(tick, createFallbackWorldState(tick));

    const timer = window.setInterval(() => {
      tick += 1;
      useConnectionStore.getState().applyReplayWorldState(tick, createFallbackWorldState(tick));
    }, 500);

    return () => window.clearInterval(timer);
  }, []);

  return (
    <aside className="replayBadge" aria-label="Replay mode status">
      replay mode · deterministic fallback active
    </aside>
  );
}
