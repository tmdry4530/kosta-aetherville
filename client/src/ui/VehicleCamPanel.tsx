'use client';

import { useEffect, useMemo, useState } from 'react';
import type { CSSProperties } from 'react';
import type { VehicleCameraFrame, VehicleState, YoloDetection } from '@aetherville/shared-schemas';

interface VehicleCamPanelProps {
  vehicle: VehicleState | undefined;
  orchestratorUrl: string | null;
}

function boxStyle(detection: YoloDetection, width: number, height: number): CSSProperties {
  const [x1, y1, x2, y2] = detection.bbox;
  return {
    left: `${(x1 / width) * 100}%`,
    top: `${(y1 / height) * 100}%`,
    width: `${((x2 - x1) / width) * 100}%`,
    height: `${((y2 - y1) / height) * 100}%`
  };
}

export function VehicleCamPanel({ vehicle, orchestratorUrl }: VehicleCamPanelProps) {
  const [cameraFrame, setCameraFrame] = useState<VehicleCameraFrame | null>(null);
  const [cameraStatus, setCameraStatus] = useState<'state' | 'loading' | 'live' | 'offline'>('state');
  const vehicleId = vehicle?.id;

  useEffect(() => {
    if (!vehicleId || !orchestratorUrl) {
      setCameraFrame(null);
      setCameraStatus('state');
      return;
    }

    let cancelled = false;
    let timer: number | undefined;
    const baseUrl = orchestratorUrl.replace(/\/$/, '');

    const fetchCameraFrame = async () => {
      setCameraStatus((current) => (current === 'live' ? 'live' : 'loading'));
      try {
        const response = await fetch(`${baseUrl}/api/v1/vehicles/${encodeURIComponent(vehicleId)}/camera`, {
          cache: 'no-store'
        });
        if (!response.ok) {
          throw new Error(`camera endpoint returned ${response.status}`);
        }
        const frame = (await response.json()) as VehicleCameraFrame;
        if (!cancelled) {
          setCameraFrame(frame);
          setCameraStatus('live');
        }
      } catch {
        if (!cancelled) {
          setCameraStatus('offline');
        }
      }

      if (!cancelled) {
        timer = window.setTimeout(fetchCameraFrame, 3500);
      }
    };

    void fetchCameraFrame();

    return () => {
      cancelled = true;
      if (timer !== undefined) {
        window.clearTimeout(timer);
      }
    };
  }, [orchestratorUrl, vehicleId]);

  const detections = cameraFrame ? cameraFrame.detections : (vehicle?.yolo_detections ?? []);
  const frameWidth = cameraFrame?.width ?? 320;
  const frameHeight = cameraFrame?.height ?? 180;
  const hazard = detections.some(
    (detection) =>
      detection.label === 'pedestrian' ||
      detection.label === 'person' ||
      detection.traffic_light_state === 'red'
  );
  const cameraBadge = useMemo(() => {
    if (cameraFrame?.mode === 'real') {
      return 'REAL YOLO · RunPod 4090';
    }
    if (cameraStatus === 'offline') {
      return 'STATE FALLBACK · 카메라 연결 대기';
    }
    if (cameraStatus === 'loading') {
      return 'CAMERA ENDPOINT · 로딩';
    }
    return 'MOCK CAMERA · endpoint synced';
  }, [cameraFrame?.mode, cameraStatus]);

  return (
    <article className="sidePanel cameraPanel">
      <div className="panelKicker">Vehicle cam</div>
      <h2>{vehicle?.id ?? 'vehicle'} 전방 카메라</h2>
      <span className={`cameraModeBadge ${cameraFrame?.mode === 'real' ? 'cameraModeBadge-real' : ''}`}>
        {cameraBadge}
      </span>
      <div className="cameraFrame" role="img" aria-label="Simulated vehicle camera feed with boxes">
        <span className="scanLine" />
        {detections.map((detection) => (
          <span
            className="cameraBox"
            key={`${detection.label}-${detection.bbox.join('-')}`}
            style={boxStyle(detection, frameWidth, frameHeight)}
          >
            {detection.label}
          </span>
        ))}
        <strong>{detections.length} detections</strong>
        <small>{hazard ? 'slowdown / attention active' : 'camera path clear'}</small>
      </div>
    </article>
  );
}
