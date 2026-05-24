export type SocketTransport = 'polling' | 'websocket';

export interface ClientConfig {
  orchestratorUrl: string;
  socketUrl: string;
  socketTransports: SocketTransport[];
}

function getSocketTransports(): SocketTransport[] {
  const rawValue = process.env.NEXT_PUBLIC_SOCKET_TRANSPORTS ?? 'polling';
  const transports = rawValue
    .split(',')
    .map((item) => item.trim())
    .filter((item): item is SocketTransport => item === 'polling' || item === 'websocket');

  return transports.length > 0 ? transports : ['polling'];
}

export function getClientConfig(): ClientConfig {
  return {
    orchestratorUrl: process.env.NEXT_PUBLIC_ORCHESTRATOR_URL ?? 'http://localhost:8080',
    socketUrl: process.env.NEXT_PUBLIC_SOCKET_URL ?? 'http://localhost:8080',
    socketTransports: getSocketTransports()
  };
}
