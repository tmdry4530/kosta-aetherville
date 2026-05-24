'use client';

import type { CSSProperties } from 'react';
import type { VehicleState, YoloDetection } from '@aetherville/shared-schemas';

interface VehicleCamPanelProps {
  vehicle: VehicleState | undefined;
}

function boxStyle(detection: YoloDetection): CSSProperties {
  const [x1, y1, x2, y2] = detection.bbox;
  return {
    left: `${(x1 / 320) * 100}%`,
    top: `${(y1 / 180) * 100}%`,
    width: `${((x2 - x1) / 320) * 100}%`,
    height: `${((y2 - y1) / 180) * 100}%`
  };
}

export function VehicleCamPanel({ vehicle }: VehicleCamPanelProps) {
  const detections = vehicle?.yolo_detections ?? [];
  const hazard = detections.some(
    (detection) => detection.label === 'pedestrian' || detection.traffic_light_state === 'red'
  );

  return (
    <article className="sidePanel cameraPanel">
      <div className="panelKicker">Vehicle cam</div>
      <h2>{vehicle?.id ?? 'vehicle'} 전방 카메라</h2>
      <div className="cameraFrame" role="img" aria-label="Simulated vehicle camera feed with boxes">
        <span className="scanLine" />
        {detections.map((detection) => (
          <span className="cameraBox" key={`${detection.label}-${detection.bbox.join('-')}`} style={boxStyle(detection)}>
            {detection.label}
          </span>
        ))}
        <strong>{detections.length} detections</strong>
        <small>{hazard ? 'slowdown demo active' : 'mock YOLO clear path'}</small>
      </div>
    </article>
  );
}
