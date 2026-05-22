"""
Thane Q-Commerce synthetic order generator.
Downloads OSM drive network, seeds dark stores, and writes training data.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
MODELS_DIR = ROOT / "models"
CACHE_DIR = ROOT / "cache"

PLACE = "Thane, Maharashtra, India"
NUM_DARK_STORES = 4
NUM_ORDERS = 10_000
DAYS = 14
DELIVERY_RADIUS_M = 3_000
AVG_SPEED_KMH = 22.0  # Mumbai urban average
RANDOM_SEED = 42

WEATHER_OPTIONS = ["Clear", "Rain", "Heavy Rain"]
WEATHER_WEIGHTS = [0.55, 0.30, 0.15]  # Monsoon-skewed Mumbai mix
WEATHER_SPEED_FACTOR = {"Clear": 1.0, "Rain": 0.82, "Heavy Rain": 0.65}
WEATHER_SEVERITY = {"Clear": 0, "Rain": 1, "Heavy Rain": 2}

ox.settings.use_cache = True
ox.settings.cache_folder = str(CACHE_DIR)


def download_graph() -> nx.MultiDiGraph:
    print(f"Downloading drive network for {PLACE} …")
    G = ox.graph_from_place(PLACE, network_type="drive", simplify=True)
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)
    print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


def pick_dark_stores(G: nx.MultiDiGraph, k: int = NUM_DARK_STORES) -> list[int]:
    """Select k central nodes (high degree) as dark-store hubs."""
    degrees = dict(G.degree())
    sorted_nodes = sorted(degrees, key=degrees.get, reverse=True)
    # Spread stores: pick from top quartile with minimum separation
    candidates = sorted_nodes[: max(k * 8, 50)]
    rng = random.Random(RANDOM_SEED)
    rng.shuffle(candidates)
    selected: list[int] = []
    for node in candidates:
        if len(selected) >= k:
            break
        if not selected:
            selected.append(node)
            continue
        too_close = any(
            ox.distance.great_circle(
                G.nodes[node]["y"],
                G.nodes[node]["x"],
                G.nodes[s]["y"],
                G.nodes[s]["x"],
            )
            < 800
            for s in selected
        )
        if not too_close:
            selected.append(node)
    while len(selected) < k:
        selected.append(rng.choice(sorted_nodes[:100]))
    return selected[:k]


def nodes_within_radius(G: nx.MultiDiGraph, center: int, radius_m: float) -> list[int]:
    subgraph = ox.truncate.truncate_graph_dist(G, source_node=center, dist=radius_m)
    return list(subgraph.nodes())


def shortest_path_metrics(G: nx.MultiDiGraph, origin: int, dest: int) -> tuple[float, float]:
    """Return (distance_m, travel_time_min)."""
    try:
        route = nx.shortest_path(G, origin, dest, weight="length")
        dist_m = nx.shortest_path_length(G, origin, dest, weight="length")
        time_sec = sum(
            G.edges[route[i], route[i + 1], 0].get("travel_time", dist_m / (AVG_SPEED_KMH * 1000 / 3600))
            for i in range(len(route) - 1)
        )
        return float(dist_m), float(time_sec) / 60.0
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        # Fallback: haversine + assumed speed
        oy, ox_ = G.nodes[origin]["y"], G.nodes[origin]["x"]
        dy, dx = G.nodes[dest]["y"], G.nodes[dest]["x"]
        dist_m = ox.distance.great_circle(oy, ox_, dy, dx)
        time_min = (dist_m / 1000.0) / AVG_SPEED_KMH * 60.0
        return float(dist_m), float(time_min)


def simulate_active_riders(hour: int, day_of_week: int, weather: str) -> int:
    """Synthetic fleet availability (lower during peak demand / bad weather)."""
    base = 18
    peak = 1.0 + 0.35 * np.sin((hour - 8) * np.pi / 12)  # lunch + dinner peaks
    weekend = 1.12 if day_of_week >= 5 else 1.0
    weather_penalty = {"Clear": 1.0, "Rain": 0.88, "Heavy Rain": 0.72}[weather]
    count = int(base * peak * weekend * weather_penalty + np.random.normal(0, 2))
    return max(5, min(45, count))


def simulate_actual_eta(
    base_time_min: float,
    hour: int,
    weather: str,
    distance_m: float,
    active_riders: int,
) -> float:
    """Ground-truth ETA with Mumbai traffic + monsoon effects."""
    rush = 1.0 + 0.25 * (1 if hour in (8, 9, 13, 14, 19, 20) else 0)
    weather_factor = 1.0 / WEATHER_SPEED_FACTOR[weather]
    fleet_pressure = 1.0 + max(0, (25 - active_riders)) * 0.018
    distance_noise = 1.0 + (distance_m / 3000.0) * 0.08
    noise = np.random.lognormal(mean=0.0, sigma=0.08)
    eta = base_time_min * rush * weather_factor * fleet_pressure * distance_noise * noise
    return round(float(np.clip(eta, 3.0, 35.0)), 2)


def export_network_geojson(G: nx.MultiDiGraph, path: Path) -> None:
    nodes_gdf = ox.graph_to_gdfs(G, edges=False)
    nodes_gdf = nodes_gdf.reset_index().rename(columns={"osmid": "node_id"})
    geojson = json.loads(nodes_gdf.to_json())
    path.write_text(json.dumps(geojson, indent=2))
    print(f"Saved network GeoJSON → {path}")


def export_dark_stores(G: nx.MultiDiGraph, store_ids: list[int], path: Path) -> None:
    stores = []
    for idx, node in enumerate(store_ids, start=1):
        stores.append(
            {
                "dark_store_id": idx,
                "node_id": int(node),
                "lat": float(G.nodes[node]["y"]),
                "lon": float(G.nodes[node]["x"]),
                "name": f"Dark Store {idx}",
            }
        )
    path.write_text(json.dumps(stores, indent=2))
    print(f"Saved dark stores → {path}")


def generate_orders(G: nx.MultiDiGraph, store_ids: list[int]) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED)
    start_date = datetime(2025, 6, 1, 6, 0, 0)

    store_nodes = {i + 1: nid for i, nid in enumerate(store_ids)}
    delivery_pools = {
        sid: nodes_within_radius(G, nid, DELIVERY_RADIUS_M) for sid, nid in store_nodes.items()
    }

    rows: list[dict] = []
    for i in range(NUM_ORDERS):
        order_id = f"THN-{i + 1:05d}"
        offset_minutes = int(rng.integers(0, DAYS * 24 * 60))
        ts = start_date + timedelta(minutes=int(offset_minutes))
        store_id = int(rng.integers(1, NUM_DARK_STORES + 1))
        pool = delivery_pools[store_id]
        delivery_node = int(rng.choice(pool))
        origin_node = store_nodes[store_id]

        distance_m, base_time_min = shortest_path_metrics(G, origin_node, delivery_node)
        weather = str(rng.choice(WEATHER_OPTIONS, p=WEATHER_WEIGHTS))
        order_value = float(rng.integers(150, 2501))

        hour = ts.hour
        dow = ts.weekday()
        active_riders = simulate_active_riders(hour, dow, weather)
        actual_eta = simulate_actual_eta(base_time_min, hour, weather, distance_m, active_riders)
        sla_breach = int(actual_eta > 10.0)

        rows.append(
            {
                "order_id": order_id,
                "timestamp": ts.isoformat(),
                "dark_store_id": store_id,
                "origin_node_id": origin_node,
                "delivery_node_id": delivery_node,
                "origin_lat": G.nodes[origin_node]["y"],
                "origin_lon": G.nodes[origin_node]["x"],
                "delivery_lat": G.nodes[delivery_node]["y"],
                "delivery_lon": G.nodes[delivery_node]["x"],
                "order_value_inr": round(order_value, 2),
                "weather_condition": weather,
                "weather_severity": WEATHER_SEVERITY[weather],
                "distance_m": round(distance_m, 1),
                "base_travel_time_min": round(base_time_min, 2),
                "hour_of_day": hour,
                "day_of_week": dow,
                "active_rider_count": active_riders,
                "actual_eta_min": actual_eta,
                "sla_breach": sla_breach,
            }
        )

        if (i + 1) % 2000 == 0:
            print(f"  Generated {i + 1:,} / {NUM_ORDERS:,} orders")

    return pd.DataFrame(rows)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    G = download_graph()
    store_ids = pick_dark_stores(G)
    print(f"Dark store nodes: {store_ids}")

    export_network_geojson(G, DATA_DIR / "thane_network.geojson")
    export_dark_stores(G, store_ids, MODELS_DIR / "dark_stores.json")

    # Persist graph for backend routing (pickle via joblib in pipeline)
    import joblib

    joblib.dump(G, MODELS_DIR / "thane_graph.joblib")

    df = generate_orders(G, store_ids)
    out_path = DATA_DIR / "thane_orders.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df):,} orders → {out_path}")
    print(f"SLA breach rate: {df['sla_breach'].mean():.1%}")


if __name__ == "__main__":
    main()
