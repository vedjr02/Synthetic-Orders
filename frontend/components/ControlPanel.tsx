"use client";

import type { Weather } from "@/lib/api";

const WEATHER_OPTIONS: { id: Weather; label: string; icon: string }[] = [
  { id: "Clear", label: "Clear", icon: "☀" },
  { id: "Rain", label: "Rain", icon: "🌧" },
  { id: "Heavy Rain", label: "Monsoon", icon: "⛈" },
];

interface Props {
  weather: Weather;
  onWeatherChange: (w: Weather) => void;
  loading?: boolean;
}

export default function ControlPanel({ weather, onWeatherChange, loading }: Props) {
  return (
    <div className="glass" style={{ padding: "18px 20px" }}>
      <div className="label" style={{ marginBottom: 12 }}>
        Weather Simulation
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        {WEATHER_OPTIONS.map((opt) => {
          const active = weather === opt.id;
          return (
            <button
              key={opt.id}
              onClick={() => onWeatherChange(opt.id)}
              disabled={loading}
              style={{
                flex: 1,
                padding: "10px 8px",
                borderRadius: 12,
                border: active ? "1px solid var(--accent)" : "1px solid var(--border-glass)",
                background: active ? "rgba(94, 234, 212, 0.12)" : "rgba(255,255,255,0.03)",
                color: active ? "var(--accent)" : "var(--text-muted)",
                cursor: loading ? "wait" : "pointer",
                fontSize: "0.8rem",
                fontWeight: 500,
                transition: "all 0.2s ease",
              }}
            >
              <span style={{ display: "block", fontSize: "1.1rem", marginBottom: 2 }}>
                {opt.icon}
              </span>
              {opt.label}
            </button>
          );
        })}
      </div>
      {weather !== "Clear" && (
        <p style={{ marginTop: 12, fontSize: "0.78rem", color: "var(--accent-warm)" }}>
          Monsoon surge active — SLA risk & pricing elevated
        </p>
      )}
    </div>
  );
}
