"""Pandas aggregations for business & operations analytics."""

from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd

WEATHER_FACTOR = {"Clear": 1.0, "Rain": 1.15, "Heavy Rain": 1.35}
BASE_SURGE = 1.0
DELIVERY_FEE_BASE = 25.0  # INR base delivery fee before surge


def _attach_surge_gmv(df: pd.DataFrame, sla_risk_col: str = "sla_breach") -> pd.DataFrame:
    """Estimate surge multiplier and GMV from SLA breach proxy when risk unavailable."""
    out = df.copy()
    if "surge_multiplier" not in out.columns:
        risk = out[sla_risk_col].astype(float) if sla_risk_col in out.columns else 0.1
        wf = out["weather_condition"].map(WEATHER_FACTOR).fillna(1.0)
        out["surge_multiplier"] = BASE_SURGE * (1.0 + risk * 0.35) * wf
    out["delivery_revenue"] = DELIVERY_FEE_BASE * out["surge_multiplier"]
    out["gmv"] = out["order_value_inr"] + out["delivery_revenue"]
    return out


def overview(df: pd.DataFrame, weather: Optional[str] = None) -> dict[str, Any]:
    data = df if not weather else df[df["weather_condition"] == weather]
    data = _attach_surge_gmv(data)
    days = max(data["timestamp"].dt.date.nunique(), 1)
    return {
        "total_orders": int(len(data)),
        "orders_per_day": round(len(data) / days, 1),
        "gmv_inr": round(float(data["gmv"].sum()), 2),
        "gmv_per_day_inr": round(float(data["gmv"].sum()) / days, 2),
        "avg_order_value_inr": round(float(data["order_value_inr"].mean()), 2),
        "avg_delivery_fee_inr": round(float(data["delivery_revenue"].mean()), 2),
        "avg_surge_multiplier": round(float(data["surge_multiplier"].mean()), 3),
        "sla_compliance_pct": round(float((1 - data["sla_breach"].mean()) * 100), 2),
        "avg_eta_minutes": round(float(data["actual_eta_min"].mean()), 2),
        "p95_eta_minutes": round(float(data["actual_eta_min"].quantile(0.95)), 2),
        "weather_filter": weather,
    }


def hourly_demand(df: pd.DataFrame, weather: Optional[str] = None) -> list[dict]:
    data = df if not weather else df[df["weather_condition"] == weather]
    grp = data.groupby("hour_of_day").agg(
        orders=("order_id", "count"),
        avg_eta=("actual_eta_min", "mean"),
        sla_breach_rate=("sla_breach", "mean"),
        gmv=("order_value_inr", "sum"),
    ).reset_index()
    return [
        {
            "hour": int(r.hour_of_day),
            "orders": int(r.orders),
            "avg_eta_min": round(float(r.avg_eta), 2),
            "sla_breach_pct": round(float(r.sla_breach_rate) * 100, 2),
            "gmv_inr": round(float(r.gmv), 2),
        }
        for r in grp.itertuples()
    ]


def daily_trend(df: pd.DataFrame) -> list[dict]:
    data = _attach_surge_gmv(df)
    data["date"] = data["timestamp"].dt.date.astype(str)
    grp = data.groupby("date").agg(
        orders=("order_id", "count"),
        gmv=("gmv", "sum"),
        sla_breach_rate=("sla_breach", "mean"),
        avg_eta=("actual_eta_min", "mean"),
    ).reset_index()
    return [
        {
            "date": r.date,
            "orders": int(r.orders),
            "gmv_inr": round(float(r.gmv), 2),
            "sla_breach_pct": round(float(r.sla_breach_rate) * 100, 2),
            "avg_eta_min": round(float(r.avg_eta), 2),
        }
        for r in grp.itertuples()
    ]


def zone_performance(df: pd.DataFrame, stores: list[dict]) -> list[dict]:
    store_zone = {s["dark_store_id"]: s.get("zone", s.get("name", "Unknown")) for s in stores}
    data = df.copy()
    data["zone"] = data["dark_store_id"].map(store_zone).fillna("Unknown")
    data = _attach_surge_gmv(data)
    grp = data.groupby("zone").agg(
        orders=("order_id", "count"),
        gmv=("gmv", "sum"),
        avg_eta=("actual_eta_min", "mean"),
        sla_breach_rate=("sla_breach", "mean"),
        avg_order_value=("order_value_inr", "mean"),
    ).reset_index()
    grp = grp.sort_values("orders", ascending=False)
    return [
        {
            "zone": r.zone,
            "orders": int(r.orders),
            "gmv_inr": round(float(r.gmv), 2),
            "avg_eta_min": round(float(r.avg_eta), 2),
            "sla_breach_pct": round(float(r.sla_breach_rate) * 100, 2),
            "avg_order_value_inr": round(float(r.avg_order_value), 2),
        }
        for r in grp.itertuples()
    ]


def platform_split(df: pd.DataFrame) -> list[dict]:
    if "platform" not in df.columns:
        return []
    data = _attach_surge_gmv(df)
    grp = data.groupby("platform").agg(
        orders=("order_id", "count"),
        gmv=("gmv", "sum"),
        sla_breach_rate=("sla_breach", "mean"),
    ).reset_index()
    total = grp["orders"].sum()
    return [
        {
            "platform": r.platform,
            "orders": int(r.orders),
            "share_pct": round(float(r.orders / total * 100), 1),
            "gmv_inr": round(float(r.gmv), 2),
            "sla_breach_pct": round(float(r.sla_breach_rate) * 100, 2),
        }
        for r in grp.itertuples()
    ]


def weather_impact(df: pd.DataFrame) -> list[dict]:
    data = _attach_surge_gmv(df)
    grp = data.groupby("weather_condition").agg(
        orders=("order_id", "count"),
        avg_eta=("actual_eta_min", "mean"),
        sla_breach_rate=("sla_breach", "mean"),
        avg_surge=("surge_multiplier", "mean"),
        gmv=("gmv", "sum"),
    ).reset_index()
    return [
        {
            "weather": r.weather_condition,
            "orders": int(r.orders),
            "avg_eta_min": round(float(r.avg_eta), 2),
            "sla_breach_pct": round(float(r.sla_breach_rate) * 100, 2),
            "avg_surge": round(float(r.avg_surge), 3),
            "gmv_inr": round(float(r.gmv), 2),
        }
        for r in grp.itertuples()
    ]


def store_leaderboard(df: pd.DataFrame, stores: list[dict], limit: int = 15) -> list[dict]:
    store_meta = {s["dark_store_id"]: s for s in stores}
    data = _attach_surge_gmv(df)
    grp = data.groupby("dark_store_id").agg(
        orders=("order_id", "count"),
        gmv=("gmv", "sum"),
        avg_eta=("actual_eta_min", "mean"),
        sla_breach_rate=("sla_breach", "mean"),
    ).reset_index()
    grp = grp.sort_values("orders", ascending=False).head(limit)
    rows = []
    for r in grp.itertuples():
        meta = store_meta.get(int(r.dark_store_id), {})
        rows.append(
            {
                "store_id": int(r.dark_store_id),
                "name": meta.get("name", f"Store {r.dark_store_id}"),
                "zone": meta.get("zone", "—"),
                "platform": meta.get("platform", "—"),
                "orders": int(r.orders),
                "gmv_inr": round(float(r.gmv), 2),
                "avg_eta_min": round(float(r.avg_eta), 2),
                "sla_breach_pct": round(float(r.sla_breach_rate) * 100, 2),
            }
        )
    return rows


def eta_distribution(df: pd.DataFrame, bins: int = 12) -> list[dict]:
    counts, edges = np.histogram(df["actual_eta_min"], bins=bins, range=(0, 30))
    return [
        {
            "bucket": f"{edges[i]:.0f}–{edges[i + 1]:.0f}m",
            "count": int(counts[i]),
        }
        for i in range(len(counts))
    ]
