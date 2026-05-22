"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import DashboardMap from "@/components/DashboardMap";
import ControlPanel from "@/components/ControlPanel";
import MetricsPanel from "@/components/MetricsPanel";
import {
  fetchDarkStores,
  fetchMetrics,
  fetchOrders,
  predictSurge,
  type DarkStore,
  type Metrics,
  type OrderPoint,
  type PredictSurgeResult,
  type Weather,
} from "@/lib/api";

const THANE_CENTER = { longitude: 72.9781, latitude: 19.2183, zoom: 12.2 };

export default function HomePage() {
  const [weather, setWeather] = useState<Weather>("Clear");
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [orders, setOrders] = useState<OrderPoint[]>([]);
  const [stores, setStores] = useState<DarkStore[]>([]);
  const [prediction, setPrediction] = useState<PredictSurgeResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (w: Weather) => {
    setLoading(true);
    setError(null);
    try {
      const [m, o, s] = await Promise.all([
        fetchMetrics(w),
        fetchOrders(w),
        fetchDarkStores(),
      ]);
      setMetrics(m);
      setOrders(o);
      setStores(s);

      if (s.length >= 2) {
        const origin = s[0];
        const dest = o[0] ?? { delivery_lat: origin.lat + 0.01, delivery_lon: origin.lon + 0.01 };
        const pred = await predictSurge(
          { lat: origin.lat, lon: origin.lon },
          { lat: dest.delivery_lat, lon: dest.delivery_lon },
          w
        );
        setPrediction(pred);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to connect to API");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh(weather);
  }, [weather, refresh]);

  const surgeByPoint = useMemo(() => {
    if (!prediction) return orders;
    const factor = prediction.surge_multiplier;
    return orders.map((o) => ({
      ...o,
      surge_estimate: factor * (o.sla_breach ? 1.2 : 1.0),
    }));
  }, [orders, prediction]);

  return (
    <main
      style={{
        position: "relative",
        width: "100vw",
        height: "100vh",
        overflow: "hidden",
      }}
    >
      <DashboardMap
        initialViewState={THANE_CENTER}
        orders={surgeByPoint}
        stores={stores}
        weather={weather}
      />

      <div
        style={{
          position: "absolute",
          top: 20,
          left: 20,
          zIndex: 10,
          display: "flex",
          flexDirection: "column",
          gap: 12,
          maxWidth: 360,
        }}
      >
        <div className="glass-strong" style={{ padding: "20px 24px" }}>
          <div className="label" style={{ marginBottom: 4 }}>
            Thane Q-Commerce
          </div>
          <h1 style={{ fontSize: "1.35rem", fontWeight: 700, letterSpacing: "-0.02em" }}>
            Surge & SLA Engine
          </h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: 6 }}>
            10-min grocery delivery · Mumbai monsoon simulation
          </p>
        </div>

        <ControlPanel weather={weather} onWeatherChange={setWeather} loading={loading} />
        <MetricsPanel metrics={metrics} prediction={prediction} loading={loading} error={error} />
      </div>

      <div
        className="glass"
        style={{
          position: "absolute",
          bottom: 20,
          right: 20,
          zIndex: 10,
          padding: "12px 16px",
          fontSize: "0.75rem",
          color: "var(--text-muted)",
        }}
      >
        Basemap © CARTO · OSM contributors · No paid APIs
      </div>
    </main>
  );
}
