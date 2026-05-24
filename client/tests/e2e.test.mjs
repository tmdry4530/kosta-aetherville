import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

test('replay route is a RunPod failure fallback without socket dependency', () => {
  const replayPage = readFileSync(new URL('../src/app/replay/page.tsx', import.meta.url), 'utf8');
  const replayDriver = readFileSync(new URL('../src/components/ReplayDriver.tsx', import.meta.url), 'utf8');

  assert.match(replayPage, /ReplayDriver/);
  assert.match(replayPage, /SidePanels/);
  assert.doesNotMatch(replayPage, /ConnectionBridge/);
  assert.match(replayDriver, /applyReplayWorldState/);
  assert.match(replayDriver, /createFallbackWorldState/);
});
