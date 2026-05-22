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
  compact?: boolean;
}

export default function ControlPanel({ weather, onWeatherChange, loading, compact }: Props) {
  return (
    <div className={compact ? "weather-compact" : "glass"} style={compact ? undefined : { padding: "18px 20px" }}>
      {!compact && (
        <div className="label" style={{ marginBottom: 12 }}>
          Weather Simulation
        </div>
      )}
      <div style={{ display: "flex", gap: compact ? 6 : 8 }}>
        {WEATHER_OPTIONS.map((opt) => {
          const active = weather === opt.id;
          return (
            <button
              key={opt.id}
              onClick={() => onWeatherChange(opt.id)}
              disabled={loading}
              title={opt.label}
              style={{
                flex: compact ? "0 0 auto" : 1,
                padding: compact ? "8px 12px" : "10px 8px",
                borderRadius: 10,
                border: active ? "1px solid var(--accent)" : "1px solid var(--border-glass)",
                background: active ? "rgba(94, 234, 212, 0.12)" : "rgba(255,255,255,0.03)",
                color: active ? "var(--accent)" : "var(--text-muted)",
                cursor: loading ? "wait" : "pointer",
                fontSize: compact ? "0.95rem" : "0.8rem",
                fontWeight: 500,
                transition: "all 0.2s ease",
              }}
            >
              {!compact && (
                <span style={{ display: "block", fontSize: "1.1rem", marginBottom: 2 }}>
                  {opt.icon}
                </span>
              )}
              {compact ? opt.icon : opt.label}
            </button>
          );
        })}
      </div>
      {!compact && weather !== "Clear" && (
        <p style={{ marginTop: 12, fontSize: "0.78rem", color: "var(--accent-warm)" }}>
          Monsoon surge active — SLA risk & pricing elevated
        </p>
      )}
    </div>
  );
}
