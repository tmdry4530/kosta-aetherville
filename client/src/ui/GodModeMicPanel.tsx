'use client';

import { useState } from 'react';
import type {
  GodCommand,
  GodCommandResponse,
  WorldStatePayload
} from '@aetherville/shared-schemas';

interface GodModeMicPanelProps {
  mode: string;
  worldState: WorldStatePayload;
}

const MACROS = [
  { label: '비 내리기', text: '도시에 비를 내려줘' },
  { label: '차량 정체', text: '동쪽 도로에 정체 이벤트를 만들어줘' },
  { label: '시민 기억', text: '민준에게 오늘 카페 손님을 기억시켜줘' },
  { label: '관계 변화', text: '민준과 서연의 관계를 친구로 바꿔줘' }
];

export function GodModeMicPanel({ mode, worldState }: GodModeMicPanelProps) {
  const [text, setText] = useState('도시에 비를 내려줘');
  const [lastResult, setLastResult] = useState<string>('text fallback ready');

  async function submitCommand(rawText = text) {
    setText(rawText);
    setLastResult('sending command...');
    try {
      const baseUrl = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL ?? 'http://localhost:8080';
      const commandPayload: GodCommand = {
        kind: 'god_command',
        input_modality: 'text',
        raw_text: rawText,
        audio_blob_b64: null,
        user_id: 'presenter'
      };
      const response = await fetch(`${baseUrl}/api/v1/god/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(commandPayload)
      });
      if (!response.ok) {
        setLastResult(`command rejected: HTTP ${response.status}`);
        return;
      }
      const responsePayload = (await response.json()) as GodCommandResponse;
      setLastResult(`${responsePayload.category}: ${responsePayload.event.message}`);
    } catch {
      setLastResult('offline fallback: command queued for replay/demo');
    }
  }

  return (
    <article className="sidePanel godPanel" id="god-mode-panel">
      <div className="panelKicker">God Mode</div>
      <h2>명령 콘솔</h2>
      <p>
        현재 모드: {mode}. 날씨: {worldState.world.weather}. 이벤트:{' '}
        {worldState.world.active_event ?? '대기'}.
      </p>
      <label className="godInputLabel">
        <span>Text command</span>
        <textarea value={text} onChange={(event) => setText(event.target.value)} />
      </label>
      <div className="macroGrid" aria-label="God Mode fallback macros">
        {MACROS.map((macro) => (
          <button type="button" key={macro.label} onClick={() => void submitCommand(macro.text)}>
            {macro.label}
          </button>
        ))}
      </div>
      <button className="godPrimary" type="button" onClick={() => void submitCommand()}>
        실행
      </button>
      <button className="godVoice" type="button" disabled>
        Voice STT optional
      </button>
      <small className="godResult" aria-live="polite">
        {lastResult}
      </small>
    </article>
  );
}
