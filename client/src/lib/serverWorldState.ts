import type { WorldStatePayload } from '@aetherville/shared-schemas';

export async function fetchInitialWorldState(
  orchestratorUrl: string,
  timeoutMs = 2500
): Promise<WorldStatePayload | null> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${orchestratorUrl.replace(/\/$/, '')}/api/v1/sim/state`, {
      cache: 'no-store',
      signal: controller.signal
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as WorldStatePayload;
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}
