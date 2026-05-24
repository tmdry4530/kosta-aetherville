import { io, type Socket } from 'socket.io-client';
import type { Envelope, WorldStatePayload } from '@aetherville/shared-schemas';
import type { SocketTransport } from '@/lib/config';
import { useConnectionStore } from '@/store/connection';

export const STATE_UPDATE_EVENT = 'aetherville:state_update';
export const ACK_EVENT = 'aetherville:ack';
export const SERVER_EVENT = 'aetherville:event';

export function handleServerEnvelope(envelope: Envelope<unknown>): void {
  if (envelope.type === 'state_update') {
    const payload = envelope.payload as WorldStatePayload;
    useConnectionStore.getState().applyWorldState(envelope.tick, payload);
  }
}

export function createOrchestratorSocket(
  socketUrl: string,
  transports: SocketTransport[] = ['polling']
): Socket {
  const socket = io(socketUrl, {
    path: '/socket.io',
    transports,
    reconnection: true,
    reconnectionAttempts: Infinity,
    reconnectionDelayMax: 3000,
    upgrade: transports.includes('websocket') && transports.length > 1
  });

  socket.on('connect', () => useConnectionStore.getState().setState('connected'));
  socket.on('disconnect', () => useConnectionStore.getState().setState('idle'));
  socket.on('connect_error', () => useConnectionStore.getState().setState('error'));
  socket.on(ACK_EVENT, () => useConnectionStore.getState().setState('connected'));
  socket.on(STATE_UPDATE_EVENT, (envelope: Envelope<WorldStatePayload>) => {
    handleServerEnvelope(envelope);
  });
  socket.on(SERVER_EVENT, () => useConnectionStore.getState().setState('connected'));

  return socket;
}
