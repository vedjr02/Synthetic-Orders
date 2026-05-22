"use client";

import type { Metrics, PredictSurgeResult, SimulationMeta } from "@/lib/api";

interface Props {
  metrics: Metrics | null;
  simulation: SimulationMeta | null;
  prediction: PredictSurgeResult | null;
  loading?: boolean;
  error?: string | null;
}

function Metric({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div>
      <div className="label">{label}</div>
      <div className="value-sm" style={{ color: accent ? "var(--accent)" : undefined, marginTop: 4 }}>
        {value}
      </div>
    </div>
  );
}

export default function MetricsPanel({ metrics, simulation, prediction, loading, error }: Props) {
  if (error) {
    return (
      <div className="glass" style={{ padding: "18px 20px", borderColor: "rgba(248,113,113,0.3)" }}>
        <div className="label" style={{ color: "var(--danger)" }}>
          API Offline
        </div>
        <p style={{ fontSize: "0.85rem", marginTop: 8, color: "var(--text-muted)" }}>{error}</p>
        <p style={{ fontSize: "0.75rem", marginTop: 8, color: "var(--text-muted)" }}>
          Run backend: uvicorn main:app --reload
        </p>
      </div>
    );
  }

  return (
    <div className="glass" style={{ padding: "18px 20px" }}>
      <div className="label" style={{ marginBottom: 14 }}>
        Live KPIs {loading ? "· syncing…" : ""}
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 16,
        }}
      >
        <Metric
          label="Active Orders"
          value={metrics ? metrics.total_active_orders.toLocaleString() : "—"}
        />
        <Metric
          label="Fleet Util."
          value={metrics ? `${(metrics.fleet_utilization * 100).toFixed(0)}%` : "—"}
        />
        <Metric
          label="Avg Surge"
          value={metrics ? `${metrics.average_surge_multiplier.toFixed(2)}×` : "—"}
          accent
        />
        <Metric
          label="SLA Breach"
          value={metrics ? `${(metrics.sla_breach_rate * 100).toFixed(1)}%` : "—"}
        />
      </div>

      {simulation && (
        <p style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: 12, lineHeight: 1.5 }}>
          {simulation.num_dark_stores} dark stores · ~
          {simulation.daily_orders_target.toLocaleString()} orders/day (Thane benchmark)
        </p>
      )}

      {prediction && (
        <div
          style={{
            marginTop: 16,
            paddingTop: 14,
            borderTop: "1px solid var(--border-glass)",
          }}
        >
          <div className="label">Sample Route Prediction</div>
          <div style={{ display: "flex", gap: 20, marginTop: 8 }}>
            <Metric label="ETA" value={`${prediction.eta_minutes.toFixed(1)} min`} accent />
            <Metric label="Surge" value={`${prediction.surge_multiplier.toFixed(2)}×`} />
            <Metric label="SLA Risk" value={`${(prediction.sla_breach_risk * 100).toFixed(0)}%`} />
          </div>
        </div>
      )}
    </div>
  );
}
