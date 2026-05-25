'use client';

import { useEffect, useMemo, useState } from 'react';
import type { HealthResponse, ServiceStatus, WorldStatePayload } from '@aetherville/shared-schemas';

interface RunPodProofPanelProps {
  worldState: WorldStatePayload;
  orchestratorUrl: string | null;
}

interface ProofItem {
  key: string;
  label: string;
  status: 'ok' | 'warn' | 'off';
  detail: string;
}

function dependencyMap(health: HealthResponse | null): Map<string, ServiceStatus> {
  return new Map((health?.dependencies ?? []).map((dependency) => [dependency.name, dependency]));
}

function proofStatus(active: boolean, degraded = false): ProofItem['status'] {
  if (active) {
    return degraded ? 'warn' : 'ok';
  }
  return 'off';
}

function shortDetail(detail: string | null | undefined): string {
  if (!detail) {
    return 'no detail';
  }
  return detail.replace('http://127.0.0.1:', ':').slice(0, 56);
}

export function RunPodProofPanel({ worldState, orchestratorUrl }: RunPodProofPanelProps) {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthState, setHealthState] = useState<'loading' | 'live' | 'offline'>(
    orchestratorUrl ? 'loading' : 'offline'
  );

  useEffect(() => {
    if (!orchestratorUrl) {
      setHealth(null);
      setHealthState('offline');
      return;
    }

    let cancelled = false;
    let timer: number | undefined;
    const baseUrl = orchestratorUrl.replace(/\/$/, '');

    const fetchHealth = async () => {
      try {
        const response = await fetch(`${baseUrl}/api/v1/health`, { cache: 'no-store' });
        if (!response.ok) {
          throw new Error(`health returned ${response.status}`);
        }
        const payload = (await response.json()) as HealthResponse;
        if (!cancelled) {
          setHealth(payload);
          setHealthState('live');
        }
      } catch {
        if (!cancelled) {
          setHealthState('offline');
        }
      }

      if (!cancelled) {
        timer = window.setTimeout(fetchHealth, 8000);
      }
    };

    void fetchHealth();

    return () => {
      cancelled = true;
      if (timer !== undefined) {
        window.clearTimeout(timer);
      }
    };
  }, [orchestratorUrl]);

  const proofItems = useMemo(() => {
    const deps = dependencyMap(health);
    const vllm = deps.get('vllm');
    const vision = deps.get('vision');
    const stt = deps.get('stt');
    const learning = deps.get('learning');
    const redis = deps.get('redis');
    const cameraReal = worldState.vehicles.some((vehicle) =>
      vehicle.display_tags.some((tag) => tag.includes('YOLO') || tag.includes('REAL'))
    );
    const trafficPolicy = worldState.traffic_ai;
    const forecast = worldState.traffic_forecast_ai;

    return [
      {
        key: 'vllm',
        label: 'vLLM LLM',
        status: proofStatus(vllm?.status === 'ok'),
        detail: shortDetail(vllm?.detail ?? 'Qwen OpenAI-compatible endpoint')
      },
      {
        key: 'vision',
        label: 'YOLO vision',
        status: proofStatus(vision?.status === 'ok' || cameraReal),
        detail: shortDetail(vision?.detail ?? 'vehicle camera real-mode path')
      },
      {
        key: 'stt',
        label: 'STT voice',
        status: proofStatus(stt?.status === 'ok'),
        detail: shortDetail(stt?.detail ?? 'faster-whisper optional path')
      },
      {
        key: 'traffic-policy',
        label: '4090 policy',
        status: proofStatus(
          trafficPolicy.mode === 'checkpoint' && trafficPolicy.training_backend === 'torch_cuda'
        ),
        detail: `${trafficPolicy.improvement_pct.toFixed(1)}% queue cut · ${trafficPolicy.policy_version}`
      },
      {
        key: 'lstm',
        label: '4090 LSTM',
        status: proofStatus(
          forecast.mode === 'lstm_checkpoint' && forecast.training_backend === 'torch_cuda'
        ),
        detail: `MAPE ${forecast.mape?.toFixed(1) ?? '-'}% · ${forecast.forecast_version}`
      },
      {
        key: 'learning',
        label: 'adaptive loop',
        status: proofStatus(learning?.status === 'ok' || worldState.learning.experience_count > 0),
        detail: `${worldState.learning.policy_version} · ${worldState.learning.experience_count} events`
      },
      {
        key: 'docker',
        label: 'runtime mode',
        status: proofStatus(true, redis?.status === 'stub'),
        detail: 'direct-process · no Docker · memory Redis fallback'
      }
    ] satisfies ProofItem[];
  }, [health, worldState]);

  const okCount = proofItems.filter((item) => item.status === 'ok').length;
  const warnCount = proofItems.filter((item) => item.status === 'warn').length;

  return (
    <article className="sidePanel runpodProofPanel" aria-label="RunPod AI proof panel">
      <div className="panelKicker">RunPod AI proof</div>
      <h2>4090 실행 증거</h2>
      <p>
        direct-process 상태: {healthState}. AI proof {okCount}/{proofItems.length}
        {warnCount ? ` · warn ${warnCount}` : ''}.
      </p>
      <div className="proofGrid" aria-label="RunPod 4090 active services">
        {proofItems.map((item) => (
          <span className={`proofChip proofChip-${item.status}`} key={item.key}>
            <strong>{item.label}</strong>
            <small>{item.detail}</small>
          </span>
        ))}
      </div>
    </article>
  );
}
