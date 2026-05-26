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
  status: 'pending' | 'ok' | 'fallback' | 'error';
}

interface LastResult {
  status: CommandHistoryItem['status'] | 'idle';
  title: string;
  detail: string;
  command: string;
  actions: string[];
}

const MACROS = [
  { label: '비 내리기', text: '도시에 비를 내려줘' },
  { label: '민지·민수 만남', text: '민지랑 민수가 만난다' },
  { label: '택시 호출', text: '민지가 택시를 불러줘' },
  { label: '차량 정체', text: '동쪽 도로에 정체 이벤트를 만들어줘' },
  {
    label: '연쇄 상황',
    text: '민수가 하린이를 만난 뒤 택시를 불러 민지에게 가고, 드론은 서연에게 이동한 뒤 서연은 민지와 민수를 만나러 간다'
  }
];

export function GodModeMicPanel({ mode, worldState, orchestratorUrl }: GodModeMicPanelProps) {
  const [text, setText] = useState('민지랑 민수가 만난다');
  const [lastResult, setLastResult] = useState<LastResult>({
    status: 'idle',
    title: '명령 대기',
    detail: '자연어 상황을 입력하면 vLLM 해석과 도시 반응을 여기 고정합니다.',
    command: '',
    actions: []
  });
  const [history, setHistory] = useState<CommandHistoryItem[]>([]);
  const [recorder, setRecorder] = useState<MediaRecorder | null>(null);
  const [isRecording, setIsRecording] = useState(false);

  function pushHistory(item: Omit<CommandHistoryItem, 'id'>) {
    const id = `${Date.now()}-${item.source}-${item.status}`;
    setHistory((current) => [{ id, ...item }, ...current].slice(0, 4));
  }

  async function submitCommand(rawText = text) {
    const commandText = rawText.trim() || text.trim() || '도시 상황을 바꿔줘';
    setText(commandText);
    setLastResult({
      status: 'pending',
      title: '명령 접수 중',
      detail: 'RunPod orchestrator에 명령을 보내고 있습니다.',
      command: commandText,
      actions: []
    });
    try {
      if (!orchestratorUrl) {
        setLastResult({
          status: 'fallback',
          title: '리플레이 폴백',
          detail: 'live orchestrator unavailable; replay fallback',
          command: commandText,
          actions: []
        });
        pushHistory({
          source: 'fallback',
          command: commandText,
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
        raw_text: commandText,
        audio_blob_b64: null,
        user_id: 'presenter'
      };
      const response = await fetch(`${baseUrl}/api/v1/god/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(commandPayload)
      });
      if (!response.ok) {
        const detail = `command rejected: HTTP ${response.status}`;
        setLastResult({
          status: 'error',
          title: '명령 실패',
          detail,
          command: commandText,
          actions: []
        });
        pushHistory({
          source: 'text',
          command: commandText,
          result: detail,
          actions: [],
          status: 'error'
        });
        return;
      }
      const responsePayload = (await response.json()) as GodCommandResponse;
      const aiActions = responsePayload.ai_actions ?? [];
      const actionText = formatActionList(aiActions);
      const title = responsePayload.ai_mode === 'vllm' ? 'vLLM이 상황을 적용함' : '규칙 폴백으로 상황 적용';
      const scenarioText = responsePayload.scenario
        ? ` · ${responsePayload.scenario.title} ${responsePayload.scenario.steps.length}단계`
        : '';
      const resultText = actionText
        ? `${actionText} · ${categoryLabel(responsePayload.category)}${scenarioText}`
        : responsePayload.event.message;
      setLastResult({
        status: responsePayload.ai_mode === 'vllm' ? 'ok' : 'fallback',
        title,
        detail: resultText,
        command: commandText,
        actions: aiActions
      });
      pushHistory({
        source: 'text',
        command: commandText,
        result: resultText,
        actions: aiActions,
        status: responsePayload.ai_mode === 'vllm' ? 'ok' : 'fallback'
      });
    } catch {
      const detail = 'offline fallback: command queued for replay/demo';
      setLastResult({
        status: 'fallback',
        title: '오프라인 폴백',
        detail,
        command: commandText,
        actions: []
      });
      pushHistory({
        source: 'fallback',
        command: commandText,
        result: detail,
        actions: [],
        status: 'fallback'
      });
    }
  }

  async function submitVoiceCommand(audioBlobB64: string, mimeType: string) {
    setLastResult({
      status: 'pending',
      title: '음성 인식 중',
      detail: 'STT 결과를 God Mode 명령으로 변환합니다.',
      command: text,
      actions: []
    });
    try {
      if (!orchestratorUrl) {
        setLastResult({
          status: 'fallback',
          title: '리플레이 폴백',
          detail: 'live orchestrator unavailable; replay fallback',
          command: text,
          actions: []
        });
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
        const detail = `voice command rejected: HTTP ${response.status}`;
        setLastResult({
          status: 'error',
          title: '음성 명령 실패',
          detail,
          command: text,
          actions: []
        });
        pushHistory({
          source: 'voice',
          command: text,
          result: detail,
          actions: [],
          status: 'error'
        });
        return;
      }
      const responsePayload = (await response.json()) as VoiceCommandResponse;
      setText(responsePayload.transcript);
      const aiActions = responsePayload.command.ai_actions ?? [];
      const resultText = `${formatActionList(aiActions) || '도시 명령'} · ${responsePayload.transcript}`;
      setLastResult({
        status: responsePayload.stt_status === 'ok' ? 'ok' : 'fallback',
        title: `음성 명령 적용 · ${sttLabel(responsePayload.stt_mode)}`,
        detail: resultText,
        command: responsePayload.transcript,
        actions: aiActions
      });
      pushHistory({
        source: 'voice',
        command: responsePayload.transcript,
        result: resultText,
        actions: aiActions,
        status: responsePayload.stt_status === 'ok' ? 'ok' : 'fallback'
      });
    } catch {
      const detail = 'voice offline fallback: use text command';
      setLastResult({
        status: 'fallback',
        title: '음성 폴백',
        detail,
        command: text,
        actions: []
      });
      pushHistory({
        source: 'fallback',
        command: text,
        result: detail,
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
      setLastResult({
        status: 'fallback',
        title: '음성 사용 불가',
        detail: '이 브라우저에서는 텍스트 명령을 사용하세요.',
        command: text,
        actions: []
      });
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
      setLastResult({
        status: 'pending',
        title: '녹음 중',
        detail: '다시 누르면 녹음을 멈추고 STT로 명령을 실행합니다.',
        command: text,
        actions: []
      });
    } catch {
      setLastResult({
        status: 'fallback',
        title: '마이크 권한 없음',
        detail: '텍스트 명령으로 동일한 God Mode 동작을 실행할 수 있습니다.',
        command: text,
        actions: []
      });
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
      <div className={`godResult godResult-${lastResult.status}`} aria-live="polite">
        <strong>{lastResult.title}</strong>
        {lastResult.command ? <span>“{lastResult.command}”</span> : null}
        <small>{lastResult.detail}</small>
        {lastResult.actions.length ? (
          <div className="godActionChips" aria-label="Applied God Mode actions">
            {lastResult.actions.map((action) => (
              <em key={action}>{actionLabel(action)}</em>
            ))}
          </div>
        ) : null}
      </div>
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
              <span>{sourceLabel(item.source)}</span>
              <b>{item.command}</b>
              <small>{item.actions.length ? `${formatActionList(item.actions)} · ${item.result}` : item.result}</small>
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

function actionLabel(action: string): string {
  const labels: Record<string, string> = {
    rain: '비 내림',
    clear: '맑음 전환',
    snow: '눈 내림',
    traffic_jam: '교통량 증가',
    taxi_call: '택시 호출',
    meeting: '만남 조율',
    memory: '시민 기억',
    person_update: '시민 상태',
    relationship: '관계 변화',
    scenario_directive: '상황 디렉터',
    move_actor_to_actor: '대상 이동',
    taxi_drive_to_actor: '택시 이동',
    drone_move_to_actor: '드론 이동',
    move_actor_to_group: '그룹 합류',
    move_citizen: '시민 이동',
    call_taxi: '택시 배차',
    meet: '만남',
    remember: '기억 추가',
    traffic_surge: '정체 유도',
    set_weather: '날씨 변경',
    no_op: '관찰'
  };
  return labels[action] ?? action.replaceAll('_', ' ');
}

function formatActionList(actions: string[]): string {
  return actions.map(actionLabel).join(' → ');
}

function categoryLabel(category: GodCommandResponse['category']): string {
  const labels: Record<GodCommandResponse['category'], string> = {
    environment: '환경 변화',
    event: '도시 이벤트',
    person: '시민 상태',
    infrastructure: '인프라 제어',
    relationship: '관계/만남'
  };
  return labels[category];
}

function sourceLabel(source: CommandHistoryItem['source']): string {
  if (source === 'text') {
    return 'TEXT';
  }
  if (source === 'voice') {
    return 'VOICE';
  }
  return 'FALLBACK';
}

function sttLabel(mode: VoiceCommandResponse['stt_mode']): string {
  if (mode === 'faster_whisper') {
    return 'faster-whisper';
  }
  if (mode === 'stub') {
    return 'stub';
  }
  return 'fallback';
}
