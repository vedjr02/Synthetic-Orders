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

from config.thane import THANE_CITY_BBOX, node_in_bbox
from config.thane_reality import (
    CITY_FLEET_BASE,
    DAILY_ORDERS_TARGET,
    DELIVERY_RADIUS_M,
    HOURLY_DEMAND_WEIGHT,
    NUM_DARK_STORES_TARGET,
    PLATFORM_MIX,
    RIDERS_PER_STORE_BASE,
    SIMULATION_DAYS,
    THANE_NEIGHBORHOODS,
    TOTAL_ORDERS,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
MODELS_DIR = ROOT / "models"
CACHE_DIR = ROOT / "cache"

PLACE = "Thane city, Maharashtra, India"  # label only; graph uses THANE_CITY_BBOX
NUM_DARK_STORES = NUM_DARK_STORES_TARGET
NUM_ORDERS = TOTAL_ORDERS
DAYS = SIMULATION_DAYS
AVG_SPEED_KMH = 22.0  # Mumbai urban average
RANDOM_SEED = 42

WEATHER_OPTIONS = ["Clear", "Rain", "Heavy Rain"]
WEATHER_WEIGHTS = [0.55, 0.30, 0.15]  # Monsoon-skewed Mumbai mix
WEATHER_SPEED_FACTOR = {"Clear": 1.0, "Rain": 0.82, "Heavy Rain": 0.65}
WEATHER_SEVERITY = {"Clear": 0, "Rain": 1, "Heavy Rain": 2}

ox.settings.use_cache = True
ox.settings.cache_folder = str(CACHE_DIR)


def download_graph() -> nx.MultiDiGraph:
    b = THANE_CITY_BBOX
    print(f"Downloading drive network for {PLACE} (city bbox) …")
    G = ox.graph_from_bbox(
        (b["west"], b["south"], b["east"], b["north"]),
        network_type="drive",
        simplify=True,
    )
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)
    print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


def pick_dark_stores(G: nx.MultiDiGraph, k: int = NUM_DARK_STORES) -> list[tuple[int, str, str]]:
    """Place dark stores per neighbourhood using QuickCommerceMap density (37 in Thane)."""
    degrees = dict(G.degree())
    rng = random.Random(RANDOM_SEED)
    selected: list[tuple[int, str, str]] = []
    used_nodes: set[int] = set()
    platform_cycle: list[str] = []
    for plat, frac in PLATFORM_MIX:
        platform_cycle.extend([plat] * int(round(frac * k)))

    for hood in THANE_NEIGHBORHOODS:
        candidates = [
            n
            for n in G.nodes
            if n not in used_nodes
            and node_in_bbox(
                G.nodes[n]["y"],
                G.nodes[n]["x"],
                hood["south"],
                hood["north"],
                hood["west"],
                hood["east"],
            )
        ]
        if not candidates:
            print(f"  Warning: no graph nodes in {hood['name']}")
            continue

        hood_lat = float(np.mean([G.nodes[n]["y"] for n in candidates]))
        hood_lon = float(np.mean([G.nodes[n]["x"] for n in candidates]))

        for i in range(hood["count"]):
            if len(selected) >= k:
                break

            def score(node: int) -> float:
                y, x = G.nodes[node]["y"], G.nodes[node]["x"]
                dist = ox.distance.great_circle(y, x, hood_lat, hood_lon)
                separation = min(
                    (
                        ox.distance.great_circle(y, x, G.nodes[s]["y"], G.nodes[s]["x"])
                        for s in used_nodes
                    ),
                    default=9999,
                )
                return degrees.get(node, 0) - dist / 400.0 + min(separation, 1200) / 600.0

            ranked = sorted(candidates, key=score, reverse=True)
            picked = ranked[0]
            for node in ranked:
                if all(
                    ox.distance.great_circle(
                        G.nodes[node]["y"],
                        G.nodes[node]["x"],
                        G.nodes[s]["y"],
                        G.nodes[s]["x"],
                    )
                    > 350
                    for s in used_nodes
                ):
                    picked = node
                    break

            platform = platform_cycle[len(selected) % len(platform_cycle)] if platform_cycle else "Blinkit"
            label = f"{platform} · {hood['name']}"
            selected.append((picked, label, platform))
            used_nodes.add(picked)
            candidates = [n for n in candidates if n != picked]

    while len(selected) < k:
        remaining = [n for n in G.nodes if n not in used_nodes]
        if not remaining:
            break
        fallback = max(remaining, key=lambda n: degrees.get(n, 0))
        selected.append((fallback, f"Dark Store {len(selected) + 1}", "Blinkit"))
        used_nodes.add(fallback)

    rng.shuffle(selected)
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
    """Active riders attached to one dark store (~14 baseline, peaks with demand)."""
    base = RIDERS_PER_STORE_BASE
    hour_factor = HOURLY_DEMAND_WEIGHT[hour] / np.mean(HOURLY_DEMAND_WEIGHT)
    peak = 0.80 + 0.35 * hour_factor
    weekend = 1.08 if day_of_week >= 5 else 1.0
    weather_penalty = {"Clear": 1.0, "Rain": 0.88, "Heavy Rain": 0.72}[weather]
    count = int(base * peak * weekend * weather_penalty + np.random.normal(0, 2))
    return max(6, min(28, count))


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


def export_dark_stores(G: nx.MultiDiGraph, store_entries: list[tuple[int, str, str]], path: Path) -> None:
    stores = []
    for idx, (node, name, platform) in enumerate(store_entries, start=1):
        zone = name.split(" · ", 1)[-1] if " · " in name else name
        stores.append(
            {
                "dark_store_id": idx,
                "node_id": int(node),
                "lat": float(G.nodes[node]["y"]),
                "lon": float(G.nodes[node]["x"]),
                "name": name,
                "zone": zone,
                "platform": platform,
            }
        )
    path.write_text(json.dumps(stores, indent=2))
    print(f"Saved {len(stores)} dark stores → {path}")


def export_simulation_meta(path: Path, store_count: int, order_count: int) -> None:
    meta = {
        "research_basis": "QuickCommerceMap Thane 37 stores; ~580 orders/store/day",
        "sources": [
            "https://quickcommercemap.com/cities/thane",
            "https://www.moneycontrol.com/news/business/startup/blinkit-zepto-and-swiggy-instamart-scale-to-over-4-million-daily-orders-in-march-more-than-double-yoy-13012435.html",
        ],
        "num_dark_stores": store_count,
        "daily_orders_target": DAILY_ORDERS_TARGET,
        "simulation_days": DAYS,
        "total_orders_generated": order_count,
        "city_fleet_riders_peak": CITY_FLEET_BASE,
        "platforms": {"Blinkit": 22, "Swiggy Instamart": 15},
    }
    path.write_text(json.dumps(meta, indent=2))
    print(f"Saved simulation meta → {path}")


def export_city_bounds(path: Path) -> None:
    payload = {
        "city": "Thane",
        "bbox": THANE_CITY_BBOX,
        "center": {
            "latitude": (THANE_CITY_BBOX["north"] + THANE_CITY_BBOX["south"]) / 2,
            "longitude": (THANE_CITY_BBOX["east"] + THANE_CITY_BBOX["west"]) / 2,
        },
    }
    path.write_text(json.dumps(payload, indent=2))
    print(f"Saved city bounds → {path}")


def generate_orders(G: nx.MultiDiGraph, store_entries: list[tuple[int, str, str]]) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED)
    start_date = datetime(2025, 6, 1, 0, 0, 0)

    store_nodes = {i + 1: nid for i, (nid, _, _) in enumerate(store_entries)}
    store_platforms = {i + 1: plat for i, (_, _, plat) in enumerate(store_entries)}
    store_weights = np.array([1.0] * len(store_entries)) / len(store_entries)

    delivery_pools = {
        sid: nodes_within_radius(G, nid, DELIVERY_RADIUS_M) for sid, nid in store_nodes.items()
    }

    # Realistic timestamps: hourly demand curve × 14 days
    hour_weights = np.array(HOURLY_DEMAND_WEIGHT, dtype=float)
    hour_weights /= hour_weights.sum()
    total_minutes = DAYS * 24 * 60
    minute_offsets = rng.integers(0, total_minutes, size=NUM_ORDERS)
    hours = (minute_offsets // 60) % 24
    # Resample hours to match demand curve
    target_hours = rng.choice(24, size=NUM_ORDERS, p=hour_weights)
    day_offsets = minute_offsets // (24 * 60)
    minute_in_day = rng.integers(0, 60, size=NUM_ORDERS)
    timestamps = [
        start_date + timedelta(days=int(d), hours=int(h), minutes=int(m))
        for d, h, m in zip(day_offsets, target_hours, minute_in_day)
    ]

    store_ids = rng.choice(
        list(store_nodes.keys()),
        size=NUM_ORDERS,
        p=store_weights,
    )

    rows: list[dict] = []
    for i in range(NUM_ORDERS):
        store_id = int(store_ids[i])
        pool = delivery_pools[store_id]
        delivery_node = int(rng.choice(pool))
        origin_node = store_nodes[store_id]
        ts = timestamps[i]

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
                "order_id": f"THN-{i + 1:06d}",
                "timestamp": ts.isoformat(),
                "dark_store_id": store_id,
                "platform": store_platforms[store_id],
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

        if (i + 1) % 25000 == 0:
            print(f"  Generated {i + 1:,} / {NUM_ORDERS:,} orders")

    return pd.DataFrame(rows)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    G = download_graph()
    store_entries = pick_dark_stores(G)
    print("Dark stores:")
    for node, name, platform in store_entries:
        y, x = G.nodes[node]["y"], G.nodes[node]["x"]
        print(f"  [{platform}] {name}: ({y:.4f}, {x:.4f})")

    export_network_geojson(G, DATA_DIR / "thane_network.geojson")
    export_dark_stores(G, store_entries, MODELS_DIR / "dark_stores.json")
    export_city_bounds(MODELS_DIR / "thane_bounds.json")

    # Persist graph for backend routing (pickle via joblib in pipeline)
    import joblib

    joblib.dump(G, MODELS_DIR / "thane_graph.joblib")

    df = generate_orders(G, store_entries)
    out_path = DATA_DIR / "thane_orders.csv"
    df.to_csv(out_path, index=False)
    export_simulation_meta(MODELS_DIR / "simulation_meta.json", len(store_entries), len(df))
    print(f"Saved {len(df):,} orders → {out_path}")
    print(f"  ≈ {len(df) / DAYS:,.0f} orders/day (target {DAILY_ORDERS_TARGET:,}/day)")
    print(f"SLA breach rate: {df['sla_breach'].mean():.1%}")


if __name__ == "__main__":
    main()
