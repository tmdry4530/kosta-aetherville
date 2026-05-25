'use client';

import { useEffect } from 'react';
import type { SocketTransport } from '@/lib/config';
import { useConnectionStore } from '@/store/connection';
import { createOrchestratorSocket } from '@/ws/orchestratorSocket';

interface ConnectionBridgeProps {
  orchestratorUrl: string;
  socketUrl: string;
  transports: SocketTransport[];
}

export function ConnectionBridge({
  orchestratorUrl,
  socketUrl,
  transports
}: ConnectionBridgeProps) {
  const connectionState = useConnectionStore((state) => state.state);
  const lastTick = useConnectionStore((state) => state.lastTick);

  useEffect(() => {
    useConnectionStore.getState().setState('connecting');
    void fetch(`${orchestratorUrl}/api/v1/sim/start`, {
      method: 'POST'
    }).catch(() => {
      // Socket/replay fallback still provides the visible connection error state.
    });
    const socket = createOrchestratorSocket(socketUrl, transports);
    return () => {
      socket.disconnect();
    };
  }, [orchestratorUrl, socketUrl, transports]);

  return (
    <aside className="connectionCard" aria-label="RunPod connection state">
      <span>connection: {connectionState}</span>
      <span>last tick: {lastTick}</span>
      <span>transport: {transports.join('+')}</span>
    </aside>
  );
}
