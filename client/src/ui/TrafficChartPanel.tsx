'use client';

import type { TrafficForecastPoint } from '@aetherville/shared-schemas';

interface TrafficChartPanelProps {
  forecast: TrafficForecastPoint[];
}

export function TrafficChartPanel({ forecast }: TrafficChartPanelProps) {
  const maxVehicles = Math.max(...forecast.map((point) => point.expected_vehicle_count), 1);

  return (
    <article className="sidePanel trafficPanel">
      <div className="panelKicker">Traffic forecast</div>
      <h2>혼잡 예측</h2>
      <div className="trafficBars" aria-label="Traffic forecast chart">
        {forecast.map((point) => (
          <div className="trafficBar" key={point.minute_offset}>
            <span
              style={{ height: `${Math.max(18, (point.expected_vehicle_count / maxVehicles) * 100)}%` }}
              data-congestion={point.congestion_index.toFixed(2)}
            />
            <small>
              +{point.minute_offset}m · {(point.congestion_index * 100).toFixed(0)}%
            </small>
          </div>
        ))}
      </div>
    </article>
  );
}
