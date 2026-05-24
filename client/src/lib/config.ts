export interface ClientConfig {
  orchestratorUrl: string;
  socketUrl: string;
}

export function getClientConfig(): ClientConfig {
  return {
    orchestratorUrl: process.env.NEXT_PUBLIC_ORCHESTRATOR_URL ?? 'http://localhost:8080',
    socketUrl: process.env.NEXT_PUBLIC_SOCKET_URL ?? 'http://localhost:8080'
  };
}
