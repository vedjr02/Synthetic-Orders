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

export interface DarkStore {
  dark_store_id: number;
  node_id: number;
  lat: number;
  lon: number;
  name: string;
  zone?: string;
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
