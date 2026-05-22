export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export type Weather = "Clear" | "Rain" | "Heavy Rain";

export interface Metrics {
  total_active_orders: number;
  fleet_utilization: number;
  average_surge_multiplier: number;
  average_eta_minutes: number;
  sla_breach_rate: number;
  average_sla_risk: number;
  weather_filter: string;
  dark_store_count: number;
  total_orders_in_dataset: number;
}

export interface CityBounds {
  city: string;
  bbox: {
    north: number;
    south: number;
    east: number;
    west: number;
  };
  center?: {
    latitude: number;
    longitude: number;
  };
}

export interface SimulationMeta {
  num_dark_stores: number;
  daily_orders_target: number;
  total_orders_generated?: number;
  simulation_days?: number;
  research_basis?: string;
}

export interface DarkStore {
  dark_store_id: number;
  node_id: number;
  lat: number;
  lon: number;
  name: string;
  zone?: string;
  platform?: string;
}

export interface OrderPoint {
  order_id: string;
  delivery_lat: number;
  delivery_lon: number;
  origin_lat: number;
  origin_lon: number;
  actual_eta_min: number;
  sla_breach: number;
  weather_condition: string;
  order_value_inr: number;
  hour_of_day: number;
  dark_store_id?: number;
}

export interface PredictSurgeResult {
  eta_minutes: number;
  surge_multiplier: number;
  sla_breach_risk: number;
  distance_m: number;
  weather: string;
  weather_factor: number;
}

export interface AnalyticsOverview {
  total_orders: number;
  orders_per_day: number;
  gmv_inr: number;
  gmv_per_day_inr: number;
  avg_order_value_inr: number;
  avg_delivery_fee_inr: number;
  avg_surge_multiplier: number;
  sla_compliance_pct: number;
  avg_eta_minutes: number;
  p95_eta_minutes: number;
}

export interface HourlyDemandPoint {
  hour: number;
  orders: number;
  avg_eta_min: number;
  sla_breach_pct: number;
  gmv_inr: number;
}

export interface DailyTrendPoint {
  date: string;
  orders: number;
  gmv_inr: number;
  sla_breach_pct: number;
  avg_eta_min: number;
}

export interface ZonePerformance {
  zone: string;
  orders: number;
  gmv_inr: number;
  avg_eta_min: number;
  sla_breach_pct: number;
  avg_order_value_inr: number;
}

export interface PlatformSplit {
  platform: string;
  orders: number;
  share_pct: number;
  gmv_inr: number;
  sla_breach_pct: number;
}

export interface WeatherImpact {
  weather: string;
  orders: number;
  avg_eta_min: number;
  sla_breach_pct: number;
  avg_surge: number;
  gmv_inr: number;
}

export interface StoreLeaderboardRow {
  store_id: number;
  name: string;
  zone: string;
  platform: string;
  orders: number;
  gmv_inr: number;
  avg_eta_min: number;
  sla_breach_pct: number;
}

export interface EtaBucket {
  bucket: string;
  count: number;
}

export interface AnalyticsBundle {
  overview: AnalyticsOverview;
  hourly_demand: HourlyDemandPoint[];
  daily_trend: DailyTrendPoint[];
  zone_performance: ZonePerformance[];
  platform_split: PlatformSplit[];
  weather_impact: WeatherImpact[];
  store_leaderboard: StoreLeaderboardRow[];
  eta_distribution: EtaBucket[];
}

export async function fetchAnalytics(weather?: Weather): Promise<AnalyticsBundle> {
  const q = weather ? `?weather=${encodeURIComponent(weather)}` : "";
  const res = await fetch(`${API_BASE}/api/analytics${q}`);
  if (!res.ok) throw new Error("Failed to load analytics");
  return res.json();
}

export async function fetchSimulationMeta(): Promise<SimulationMeta> {
  const res = await fetch(`${API_BASE}/api/simulation-meta`);
  if (!res.ok) throw new Error("Failed to load simulation meta");
  return res.json();
}

export async function fetchBounds(): Promise<CityBounds> {
  const res = await fetch(`${API_BASE}/api/bounds`);
  if (!res.ok) throw new Error("Failed to load city bounds");
  return res.json();
}

export async function fetchMetrics(weather: Weather): Promise<Metrics> {
  const res = await fetch(`${API_BASE}/api/metrics?weather=${encodeURIComponent(weather)}`);
  if (!res.ok) throw new Error("Failed to load metrics");
  return res.json();
}

export async function fetchOrders(weather: Weather, limit = 2000): Promise<OrderPoint[]> {
  const res = await fetch(
    `${API_BASE}/api/orders?limit=${limit}&weather=${encodeURIComponent(weather)}`
  );
  if (!res.ok) throw new Error("Failed to load orders");
  const data = await res.json();
  return data.orders;
}

export async function fetchDarkStores(): Promise<DarkStore[]> {
  const res = await fetch(`${API_BASE}/api/dark-stores`);
  if (!res.ok) throw new Error("Failed to load dark stores");
  const data = await res.json();
  return data.dark_stores;
}

export async function predictSurge(
  origin: { lat: number; lon: number },
  dest: { lat: number; lon: number },
  weather: Weather
): Promise<PredictSurgeResult> {
  const res = await fetch(`${API_BASE}/api/predict_surge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      origin_lat: origin.lat,
      origin_lon: origin.lon,
      dest_lat: dest.lat,
      dest_lon: dest.lon,
      weather,
    }),
  });
  if (!res.ok) throw new Error("Prediction failed");
  return res.json();
}
