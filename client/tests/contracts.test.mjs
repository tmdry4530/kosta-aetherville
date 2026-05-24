import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

test('client socket bridge listens for generated state_update envelope', () => {
  const wsSource = readFileSync(new URL('../src/ws/orchestratorSocket.ts', import.meta.url), 'utf8');
  const pageSource = readFileSync(new URL('../src/app/page.tsx', import.meta.url), 'utf8');
  const replaySource = readFileSync(new URL('../src/app/replay/page.tsx', import.meta.url), 'utf8');
  const configSource = readFileSync(new URL('../src/lib/config.ts', import.meta.url), 'utf8');
  const connectionBridgeSource = readFileSync(
    new URL('../src/components/ConnectionBridge.tsx', import.meta.url),
    'utf8'
  );
  const sidePanelSource = readFileSync(new URL('../src/components/SidePanels.tsx', import.meta.url), 'utf8');
  const memoryPanelSource = readFileSync(new URL('../src/ui/MemoryPanel.tsx', import.meta.url), 'utf8');
  const godModeSource = readFileSync(new URL('../src/ui/GodModeMicPanel.tsx', import.meta.url), 'utf8');
  const trafficPanelSource = readFileSync(new URL('../src/ui/TrafficChartPanel.tsx', import.meta.url), 'utf8');
  const vehiclePanelSource = readFileSync(new URL('../src/ui/VehicleCamPanel.tsx', import.meta.url), 'utf8');
  const typesSource = readFileSync(
    new URL('../../packages/shared-schemas/src/typescript/index.ts', import.meta.url),
    'utf8'
  );

  assert.match(wsSource, /aetherville:state_update/);
  assert.match(wsSource, /WorldStatePayload/);
  assert.match(wsSource, /transports: SocketTransport/);
  assert.match(configSource, /NEXT_PUBLIC_SOCKET_TRANSPORTS/);
  assert.match(configSource, /'polling'/);
  assert.match(connectionBridgeSource, /transport:/);
  assert.match(pageSource, /SidePanels/);
  assert.match(pageSource, /Replay fallback 열기/);
  assert.ok(pageSource.includes('href="/replay"'));
  assert.match(replaySource, /ReplayDriver/);
  assert.match(replaySource, /Live city로 돌아가기/);
  assert.match(sidePanelSource, /MemoryPanel/);
  assert.match(sidePanelSource, /VehicleCamPanel/);
  assert.match(sidePanelSource, /TrafficChartPanel/);
  assert.match(sidePanelSource, /GodModeMicPanel/);
  assert.match(memoryPanelSource, /MemoryRecord/);
  assert.match(godModeSource, /GodCommandResponse/);
  assert.match(godModeSource, /GodCommand/);
  assert.match(godModeSource, /commandPayload: GodCommand/);
  assert.match(godModeSource, /response\.ok/);
  assert.match(godModeSource, /aria-live="polite"/);
  assert.match(godModeSource, /Voice STT optional/);
  assert.match(trafficPanelSource, /TrafficForecastPoint/);
  assert.match(vehiclePanelSource, /YoloDetection/);
  assert.match(vehiclePanelSource, /cameraBox/);
  assert.match(vehiclePanelSource, /Vehicle cam/);
  assert.match(trafficPanelSource, /Traffic forecast/);
  assert.match(godModeSource, /God Mode/);
  assert.match(typesSource, /export interface SimStatusResponse/);
  assert.match(typesSource, /export interface GodCommandResponse/);
});
