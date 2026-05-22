"""
Thane Q-Commerce Surge Pricing & SLA Prediction API.
"""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import joblib
import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("thane-surge")

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
MODELS_DIR = ROOT / "models"
CONFIG_DIR = ROOT / "config"

WEATHER_SEVERITY = {"Clear": 0, "Rain": 1, "Heavy Rain": 2}
WEATHER_FACTOR = {"Clear": 1.0, "Rain": 1.15, "Heavy Rain": 1.35}
BASE_SURGE = 1.0
AVG_SPEED_KMH = 22.0

# ---------------------------------------------------------------------------
# Global state (loaded on startup)
# ---------------------------------------------------------------------------
class AppState:
    eta_model: Any = None
    sla_model: Any = None
    feature_cols: list = []
    graph: Optional[Any] = None
    dark_stores: list = []
    orders_df: Optional[Any] = None
    network_geojson: Optional[dict] = None
    city_bounds: Optional[dict] = None
    meta: dict = {}


state = AppState()


def _load_artifacts() -> None:
    eta_path = MODELS_DIR / "eta_regressor.joblib"
    sla_path = MODELS_DIR / "sla_classifier.joblib"
    graph_path = MODELS_DIR / "thane_graph.joblib"
    stores_path = MODELS_DIR / "dark_stores.json"
    meta_path = MODELS_DIR / "model_meta.json"
    geojson_path = DATA_DIR / "thane_network.geojson"
    orders_path = DATA_DIR / "thane_orders.csv"

    missing = [p for p in [eta_path, sla_path, graph_path, stores_path, geojson_path, orders_path] if not p.exists()]
    if missing:
        names = ", ".join(p.name for p in missing)
        raise FileNotFoundError(
            f"Missing artifacts: {names}. Run `python data_pipeline.py` then `python train_model.py`."
        )

    state.eta_model = joblib.load(eta_path)
    state.sla_model = joblib.load(sla_path)
    state.graph = joblib.load(graph_path)
    state.dark_stores = json.loads(stores_path.read_text())
    state.orders_df = pd.read_csv(orders_path)
    state.orders_df["timestamp"] = pd.to_datetime(state.orders_df["timestamp"])
    state.network_geojson = json.loads(geojson_path.read_text())

    if meta_path.exists():
        state.meta = json.loads(meta_path.read_text())
        state.feature_cols = state.meta.get("feature_columns", [])
    else:
        state.feature_cols = [
            "hour_of_day",
            "day_of_week",
            "weather_severity",
            "distance_m",
            "active_rider_count",
            "base_travel_time_min",
        ]

    bounds_path = MODELS_DIR / "thane_bounds.json"
    if not bounds_path.exists():
        bounds_path = CONFIG_DIR / "thane_bounds.json"
    if bounds_path.exists():
        state.city_bounds = json.loads(bounds_path.read_text())
    else:
        state.city_bounds = None

    logger.info("Loaded models, graph (%d nodes), %d orders", state.graph.number_of_nodes(), len(state.orders_df))


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        _load_artifacts()
    except FileNotFoundError as exc:
        logger.warning("%s — API will return 503 until artifacts exist.", exc)
    yield


app = FastAPI(
    title="Thane Q-Commerce Surge Engine",
    version="1.0.0",
    description="Surge pricing & SLA prediction for 10-minute grocery delivery in Thane, Mumbai.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class PredictSurgeRequest(BaseModel):
    origin_lat: float = Field(..., description="Dark store or pickup latitude")
    origin_lon: float = Field(..., description="Dark store or pickup longitude")
    dest_lat: float = Field(..., description="Delivery latitude")
    dest_lon: float = Field(..., description="Delivery longitude")
    weather: str = Field("Clear", description="Clear | Rain | Heavy Rain")
    hour_of_day: Optional[int] = Field(None, ge=0, le=23)
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    active_rider_count: Optional[int] = Field(None, ge=1, le=60)


class PredictSurgeResponse(BaseModel):
    eta_minutes: float
    surge_multiplier: float
    sla_breach_risk: float
    distance_m: float
    weather: str
    weather_factor: float


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _ensure_ready() -> None:
    if state.eta_model is None or state.graph is None:
        raise HTTPException(
            status_code=503,
            detail="Models not loaded. Run data_pipeline.py and train_model.py first.",
        )


def _nearest_node(lat: float, lon: float) -> int:
    return ox.distance.nearest_nodes(state.graph, lon, lat)


def _route_metrics(origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float) -> tuple[float, float]:
    o_node = _nearest_node(origin_lat, origin_lon)
    d_node = _nearest_node(dest_lat, dest_lon)
    try:
        dist_m = nx.shortest_path_length(state.graph, o_node, d_node, weight="length")
        route = nx.shortest_path(state.graph, o_node, d_node, weight="length")
        time_sec = sum(
            state.graph.edges[route[i], route[i + 1], 0].get(
                "travel_time", dist_m / (AVG_SPEED_KMH * 1000 / 3600)
            )
            for i in range(len(route) - 1)
        )
        return float(dist_m), float(time_sec) / 60.0
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        dist_m = ox.distance.great_circle(origin_lat, origin_lon, dest_lat, dest_lon)
        time_min = (dist_m / 1000.0) / AVG_SPEED_KMH * 60.0
        return float(dist_m), float(time_min)


def _estimate_active_riders(hour: int, dow: int, weather: str) -> int:
    if state.orders_df is None:
        return 20
    subset = state.orders_df[
        (state.orders_df["hour_of_day"] == hour)
        & (state.orders_df["day_of_week"] == dow)
        & (state.orders_df["weather_condition"] == weather)
    ]
    if len(subset) >= 5:
        return int(subset["active_rider_count"].median())
    return int(state.orders_df["active_rider_count"].median())


def _compute_surge(sla_risk: float, weather: str) -> float:
    wf = WEATHER_FACTOR.get(weather, 1.0)
    return round(BASE_SURGE * (1.0 + sla_risk) * wf, 3)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "models_loaded": state.eta_model is not None}


@app.get("/api/network")
def get_network():
    _ensure_ready()
    return state.network_geojson


@app.get("/api/dark-stores")
def get_dark_stores():
    _ensure_ready()
    return {"dark_stores": state.dark_stores}


@app.get("/api/bounds")
def get_bounds():
    """City bounding box for map auto-fit."""
    if state.city_bounds:
        return state.city_bounds
    fallback = CONFIG_DIR / "thane_bounds.json"
    if fallback.exists():
        return json.loads(fallback.read_text())
    raise HTTPException(status_code=503, detail="City bounds not configured")


@app.get("/api/orders")
def get_orders(limit: int = 2000, weather: Optional[str] = None):
    """Sample orders evenly across dark-store zones for map visualization."""
    _ensure_ready()
    df = state.orders_df.copy()
    if weather:
        df = df[df["weather_condition"] == weather]

    if "dark_store_id" in df.columns and df["dark_store_id"].nunique() > 1:
        per_store = max(limit // df["dark_store_id"].nunique(), 50)
        parts = [
            g.sample(n=min(per_store, len(g)), random_state=42)
            for _, g in df.groupby("dark_store_id")
        ]
        sample = pd.concat(parts).head(limit)
    else:
        sample = df.sample(n=min(limit, len(df)), random_state=42)

    records = sample[
        [
            "order_id",
            "delivery_lat",
            "delivery_lon",
            "origin_lat",
            "origin_lon",
            "actual_eta_min",
            "sla_breach",
            "weather_condition",
            "order_value_inr",
            "hour_of_day",
            "dark_store_id",
        ]
    ].to_dict(orient="records")
    return {"orders": records, "count": len(records)}


@app.post("/api/predict_surge", response_model=PredictSurgeResponse)
def predict_surge(req: PredictSurgeRequest):
    _ensure_ready()

    if req.weather not in WEATHER_SEVERITY:
        raise HTTPException(status_code=400, detail=f"weather must be one of {list(WEATHER_SEVERITY)}")

    now = datetime.now()
    hour = req.hour_of_day if req.hour_of_day is not None else now.hour
    dow = req.day_of_week if req.day_of_week is not None else now.weekday()
    riders = req.active_rider_count or _estimate_active_riders(hour, dow, req.weather)

    distance_m, base_time = _route_metrics(req.origin_lat, req.origin_lon, req.dest_lat, req.dest_lon)

    features = pd.DataFrame(
        [[hour, dow, WEATHER_SEVERITY[req.weather], distance_m, riders, base_time]],
        columns=state.feature_cols,
    )
    eta = float(state.eta_model.predict(features)[0])
    sla_risk = float(state.sla_model.predict_proba(features)[0, 1])
    surge = _compute_surge(sla_risk, req.weather)

    return PredictSurgeResponse(
        eta_minutes=round(eta, 2),
        surge_multiplier=surge,
        sla_breach_risk=round(sla_risk, 4),
        distance_m=round(distance_m, 1),
        weather=req.weather,
        weather_factor=WEATHER_FACTOR[req.weather],
    )


@app.get("/api/metrics")
def get_metrics(weather: str = "Clear"):
    """Aggregated KPIs for dashboard."""
    _ensure_ready()
    df = state.orders_df
    recent = df[df["weather_condition"] == weather] if weather in WEATHER_SEVERITY else df

    # Simulate live slice: last 2 hours of synthetic day
    active_orders = int(len(recent) * 0.08) + np.random.randint(12, 48)
    fleet_size = int(recent["active_rider_count"].median()) if len(recent) else 20
    utilization = round(min(0.98, active_orders / max(fleet_size, 1)), 3)

    sla_risks = []
    sample = recent.sample(n=min(200, len(recent)), random_state=7)
    for _, row in sample.iterrows():
        X = pd.DataFrame(
            [[
                row["hour_of_day"],
                row["day_of_week"],
                row["weather_severity"],
                row["distance_m"],
                row["active_rider_count"],
                row["base_travel_time_min"],
            ]],
            columns=state.feature_cols,
        )
        sla_risks.append(float(state.sla_model.predict_proba(X)[0, 1]))

    avg_sla_risk = float(np.mean(sla_risks)) if sla_risks else 0.0
    avg_surge = _compute_surge(avg_sla_risk, weather)
    avg_eta = float(recent["actual_eta_min"].mean()) if len(recent) else 0.0
    breach_rate = float(recent["sla_breach"].mean()) if len(recent) else 0.0

    return {
        "total_active_orders": active_orders,
        "fleet_utilization": utilization,
        "average_surge_multiplier": avg_surge,
        "average_eta_minutes": round(avg_eta, 2),
        "sla_breach_rate": round(breach_rate, 4),
        "average_sla_risk": round(avg_sla_risk, 4),
        "weather_filter": weather,
        "dark_store_count": len(state.dark_stores),
        "total_orders_in_dataset": len(df),
    }
