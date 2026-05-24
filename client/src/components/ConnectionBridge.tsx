'use client';

import { useEffect } from 'react';
import type { SocketTransport } from '@/lib/config';
import { useConnectionStore } from '@/store/connection';
import { createOrchestratorSocket } from '@/ws/orchestratorSocket';

interface ConnectionBridgeProps {
  socketUrl: string;
  transports: SocketTransport[];
}

export function ConnectionBridge({ socketUrl, transports }: ConnectionBridgeProps) {
  const connectionState = useConnectionStore((state) => state.state);
  const lastTick = useConnectionStore((state) => state.lastTick);

  useEffect(() => {
    useConnectionStore.getState().setState('connecting');
    const socket = createOrchestratorSocket(socketUrl, transports);
    return () => {
      socket.disconnect();
    };
  }, [socketUrl, transports]);

  return (
    <aside className="connectionCard" aria-label="RunPod connection state">
      <span>connection: {connectionState}</span>
      <span>last tick: {lastTick}</span>
      <span>transport: {transports.join('+')}</span>
    </aside>
  );
}
