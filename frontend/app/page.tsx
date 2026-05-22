"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import AnalyticsDashboard from "@/components/AnalyticsDashboard";
import DashboardMap from "@/components/DashboardMap";
import ControlPanel from "@/components/ControlPanel";
import MetricsPanel from "@/components/MetricsPanel";
import ViewTabs from "@/components/ViewTabs";
import {
  fetchAnalytics,
  fetchBounds,
  fetchDarkStores,
  fetchMetrics,
  fetchOrders,
  predictSurge,
  fetchSimulationMeta,
  type AnalyticsBundle,
  type CityBounds,
  type SimulationMeta,
  type DarkStore,
  type Metrics,
  type OrderPoint,
  type PredictSurgeResult,
  type Weather,
} from "@/lib/api";

type View = "operations" | "analytics";

export default function HomePage() {
  const [view, setView] = useState<View>("operations");
  const [weather, setWeather] = useState<Weather>("Clear");
  const [bounds, setBounds] = useState<CityBounds | null>(null);
  const [simulation, setSimulation] = useState<SimulationMeta | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsBundle | null>(null);
  const [orders, setOrders] = useState<OrderPoint[]>([]);
  const [stores, setStores] = useState<DarkStore[]>([]);
  const [prediction, setPrediction] = useState<PredictSurgeResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (w: Weather) => {
    setLoading(true);
    setError(null);
    try {
      const [m, o, s, b, sim, a] = await Promise.all([
        fetchMetrics(w),
        fetchOrders(w),
        fetchDarkStores(),
        fetchBounds(),
        fetchSimulationMeta(),
        fetchAnalytics(w),
      ]);
      setMetrics(m);
      setOrders(o);
      setStores(s);
      setBounds(b);
      setSimulation(sim);
      setAnalytics(a);

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
    <main className={view === "analytics" ? "page-analytics" : "page-operations"}>
      <header className="app-header glass-strong">
        <div>
          <div className="label">Thane Q-Commerce</div>
          <h1>Surge & SLA Engine</h1>
        </div>
        <ViewTabs active={view} onChange={setView} />
        <ControlPanel weather={weather} onWeatherChange={setWeather} loading={loading} compact />
      </header>

      {view === "operations" ? (
        <>
          <DashboardMap bounds={bounds} orders={surgeByPoint} stores={stores} weather={weather} />
          <aside className="ops-sidebar">
            <MetricsPanel
              metrics={metrics}
              simulation={simulation}
              prediction={prediction}
              loading={loading}
              error={error}
            />
          </aside>
        </>
      ) : (
        <AnalyticsDashboard data={analytics} loading={loading} />
      )}
    </main>
  );
}
