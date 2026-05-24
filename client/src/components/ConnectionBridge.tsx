'use client';

import { useEffect } from 'react';
import { useConnectionStore } from '@/store/connection';
import { createOrchestratorSocket } from '@/ws/orchestratorSocket';

interface ConnectionBridgeProps {
  socketUrl: string;
}

export function ConnectionBridge({ socketUrl }: ConnectionBridgeProps) {
  const connectionState = useConnectionStore((state) => state.state);
  const lastTick = useConnectionStore((state) => state.lastTick);

  useEffect(() => {
    useConnectionStore.getState().setState('connecting');
    const socket = createOrchestratorSocket(socketUrl);
    return () => {
      socket.disconnect();
    };
  }, [socketUrl]);

  return (
    <aside className="connectionCard" aria-label="RunPod connection state">
      <span>connection: {connectionState}</span>
      <span>last tick: {lastTick}</span>
    </aside>
  );
}
