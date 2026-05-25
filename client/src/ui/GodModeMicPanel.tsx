'use client';

import { useState } from 'react';
import type {
  GodCommand,
  GodCommandResponse,
  VoiceCommandRequest,
  VoiceCommandResponse,
  WorldStatePayload
} from '@aetherville/shared-schemas';

interface GodModeMicPanelProps {
  mode: string;
  worldState: WorldStatePayload;
  orchestratorUrl: string | null;
}

interface CommandHistoryItem {
  id: string;
  source: 'text' | 'voice' | 'fallback';
  command: string;
  result: string;
  actions: string[];
  status: 'ok' | 'fallback' | 'error';
}

const MACROS = [
  { label: '비 내리기', text: '도시에 비를 내려줘' },
  { label: '민지·민수 만남', text: '민지랑 민수가 만난다' },
  { label: '택시 호출', text: '민지가 택시를 불러줘' },
  { label: '차량 정체', text: '동쪽 도로에 정체 이벤트를 만들어줘' }
];

export function GodModeMicPanel({ mode, worldState, orchestratorUrl }: GodModeMicPanelProps) {
  const [text, setText] = useState('민지랑 민수가 만난다');
  const [lastResult, setLastResult] = useState<string>('text fallback ready');
  const [history, setHistory] = useState<CommandHistoryItem[]>([]);
  const [recorder, setRecorder] = useState<MediaRecorder | null>(null);
  const [isRecording, setIsRecording] = useState(false);

  function pushHistory(item: Omit<CommandHistoryItem, 'id'>) {
    const id = `${Date.now()}-${item.source}-${item.status}`;
    setHistory((current) => [{ id, ...item }, ...current].slice(0, 4));
  }

  async function submitCommand(rawText = text) {
    setText(rawText);
    setLastResult('sending command...');
    try {
      if (!orchestratorUrl) {
        setLastResult('live orchestrator unavailable; use replay fallback');
        pushHistory({
          source: 'fallback',
          command: rawText,
          result: 'live orchestrator unavailable; replay fallback',
          actions: [],
          status: 'fallback'
        });
        return;
      }
      const baseUrl = orchestratorUrl;
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
        pushHistory({
          source: 'text',
          command: rawText,
          result: `command rejected: HTTP ${response.status}`,
          actions: [],
          status: 'error'
        });
        return;
      }
      const responsePayload = (await response.json()) as GodCommandResponse;
      const aiBadge =
        responsePayload.ai_mode === 'vllm'
          ? `vLLM ${Math.round((responsePayload.ai_confidence ?? 0) * 100)}%`
          : 'rules fallback';
      const aiReason = responsePayload.ai_reason ? ` · ${responsePayload.ai_reason}` : '';
      const aiActions = responsePayload.ai_actions ?? [];
      const actionBadge = aiActions.length ? ` · actions: ${aiActions.join(' + ')}` : '';
      const resultText = `${aiBadge}${actionBadge} · ${responsePayload.category}: ${responsePayload.event.message}${aiReason}`;
      setLastResult(resultText);
      pushHistory({
        source: 'text',
        command: rawText,
        result: resultText,
        actions: aiActions,
        status: responsePayload.ai_mode === 'vllm' ? 'ok' : 'fallback'
      });
    } catch {
      setLastResult('offline fallback: command queued for replay/demo');
      pushHistory({
        source: 'fallback',
        command: rawText,
        result: 'offline fallback: command queued for replay/demo',
        actions: [],
        status: 'fallback'
      });
    }
  }

  async function submitVoiceCommand(audioBlobB64: string, mimeType: string) {
    setLastResult('transcribing voice command...');
    try {
      if (!orchestratorUrl) {
        setLastResult('live orchestrator unavailable; use replay fallback');
        pushHistory({
          source: 'fallback',
          command: text,
          result: 'live orchestrator unavailable; replay fallback',
          actions: [],
          status: 'fallback'
        });
        return;
      }
      const baseUrl = orchestratorUrl;
      const voicePayload: VoiceCommandRequest = {
        kind: 'voice_command',
        audio_blob_b64: audioBlobB64,
        mime_type: mimeType || 'audio/webm',
        user_id: 'presenter',
        fallback_transcript: text,
        language: 'ko'
      };
      const response = await fetch(`${baseUrl}/api/v1/god/voice`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(voicePayload)
      });
      if (!response.ok) {
        setLastResult(`voice command rejected: HTTP ${response.status}`);
        pushHistory({
          source: 'voice',
          command: text,
          result: `voice command rejected: HTTP ${response.status}`,
          actions: [],
          status: 'error'
        });
        return;
      }
      const responsePayload = (await response.json()) as VoiceCommandResponse;
      setText(responsePayload.transcript);
      const aiActions = responsePayload.command.ai_actions ?? [];
      const actionBadge = aiActions.length ? ` · actions: ${aiActions.join(' + ')}` : '';
      const resultText = `voice ${responsePayload.stt_status}/${responsePayload.stt_mode}${actionBadge} · ${responsePayload.transcript}`;
      setLastResult(resultText);
      pushHistory({
        source: 'voice',
        command: responsePayload.transcript,
        result: resultText,
        actions: aiActions,
        status: responsePayload.stt_status === 'ok' ? 'ok' : 'fallback'
      });
    } catch {
      setLastResult('voice offline fallback: use text command');
      pushHistory({
        source: 'fallback',
        command: text,
        result: 'voice offline fallback: use text command',
        actions: [],
        status: 'fallback'
      });
    }
  }

  async function toggleVoiceRecording() {
    if (recorder && recorder.state === 'recording') {
      recorder.stop();
      setIsRecording(false);
      return;
    }
    if (!navigator.mediaDevices || typeof MediaRecorder === 'undefined') {
      setLastResult('voice unavailable in this browser; use text command');
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const chunks: BlobPart[] = [];
      const nextRecorder = new MediaRecorder(stream);
      nextRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data);
        }
      };
      nextRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: nextRecorder.mimeType || 'audio/webm' });
        stream.getTracks().forEach((track) => track.stop());
        setRecorder(null);
        setIsRecording(false);
        void blobToBase64(blob).then((payload) => submitVoiceCommand(payload, blob.type));
      };
      nextRecorder.start();
      setRecorder(nextRecorder);
      setIsRecording(true);
      setLastResult('recording voice... click again to stop');
    } catch {
      setLastResult('microphone permission denied; use text command');
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
        <textarea suppressHydrationWarning value={text} onChange={(event) => setText(event.target.value)} />
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
      <button className="godVoice" type="button" onClick={() => void toggleVoiceRecording()}>
        {isRecording ? 'Stop voice command' : 'Voice STT'}
      </button>
      <small className="godResult" aria-live="polite">
        {lastResult}
      </small>
      <div className="godHistory" aria-label="God Mode command history">
        <strong>Command history</strong>
        <ol>
          {(history.length ? history : [
            {
              id: 'empty-history',
              source: 'fallback' as const,
              command: '대기 중',
              result: '명령 실행 후 vLLM actions와 visible effect가 여기에 고정됩니다.',
              actions: [],
              status: 'fallback' as const
            }
          ]).map((item) => (
            <li className={`godHistoryItem godHistoryItem-${item.status}`} key={item.id}>
              <span>{item.source}</span>
              <b>{item.command}</b>
              <small>{item.actions.length ? item.actions.join(' + ') : item.result}</small>
            </li>
          ))}
        </ol>
      </div>
    </article>
  );
}

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const result = reader.result;
      if (typeof result !== 'string') {
        reject(new Error('failed to read audio blob'));
        return;
      }
      resolve(result.split(',')[1] ?? '');
    };
    reader.onerror = () => reject(reader.error ?? new Error('failed to read audio blob'));
    reader.readAsDataURL(blob);
  });
}
