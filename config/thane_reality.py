"""
Research-backed Q-Commerce benchmarks for Thane city simulation.

Sources (2025–2026):
- QuickCommerceMap: 37 dark stores across 9 Thane areas (Blinkit 22, Instamart 15)
  https://quickcommercemap.com/cities/thane
- Moneycontrol / industry: ~4.2M daily orders India-wide (Blinkit ~1.7M, Zepto ~1.5M, Instamart ~1.1M)
- Thane city population ~2.6M (2024 est.)
- Mature dark store throughput: ~400–700 orders/store/day (Bernstein / JM Financial estimates)

Derived Thane targets:
  37 stores × ~580 orders/store/day ≈ 21,500 orders/day
  × 14-day simulation window ≈ 301,000 orders
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Fleet & volume (mimics real life at city scale)
# ---------------------------------------------------------------------------
NUM_DARK_STORES_TARGET = 37
ORDERS_PER_STORE_PER_DAY = 580  # mid-range mature throughput
DAILY_ORDERS_TARGET = NUM_DARK_STORES_TARGET * ORDERS_PER_STORE_PER_DAY  # 21,460
SIMULATION_DAYS = 14
TOTAL_ORDERS = DAILY_ORDERS_TARGET * SIMULATION_DAYS  # 301,040

# Delivery radius — Q-commerce SLA ~10 min @ ~22 km/h urban → ~2.5–3.5 km
DELIVERY_RADIUS_M = 3_000

# Riders: ~12–18 active riders per dark store at peak across shifts
RIDERS_PER_STORE_BASE = 14
CITY_FLEET_BASE = NUM_DARK_STORES_TARGET * RIDERS_PER_STORE_BASE  # ~518

# Platform mix mapped in Thane (Zepto serves via Mumbai nodes; minimal standalone in TMC)
PLATFORM_MIX: list[tuple[str, float]] = [
    ("Blinkit", 22 / 37),
    ("Swiggy Instamart", 15 / 37),
]

# Neighbourhood store counts (QuickCommerceMap Apr 2026, clipped to Thane Municipal Corp)
# Mira Road stores redistributed to Ghodbunder / Majiwada fringe within TMC bbox
THANE_NEIGHBORHOODS: list[dict] = [
    {"name": "Thane West", "count": 18, "south": 19.175, "north": 19.275, "west": 72.915, "east": 72.985},
    {"name": "Ghodbunder Road", "count": 5, "south": 19.225, "north": 19.295, "west": 72.935, "east": 72.995},
    {"name": "Majiwada", "count": 4, "south": 19.195, "north": 19.235, "west": 72.985, "east": 73.030},
    {"name": "Thane East", "count": 4, "south": 19.165, "north": 19.215, "west": 73.020, "east": 73.085},
    {"name": "Wagle Estate", "count": 2, "south": 19.095, "north": 19.145, "west": 72.915, "east": 72.965},
    {"name": "Kalwa", "count": 2, "south": 19.135, "north": 19.175, "west": 73.030, "east": 73.075},
    {"name": "Mumbra", "count": 1, "south": 19.055, "north": 19.095, "west": 72.975, "east": 73.025},
    {"name": "Shilphata", "count": 1, "south": 19.125, "north": 19.165, "west": 72.905, "east": 72.945},
]

assert sum(n["count"] for n in THANE_NEIGHBORHOODS) == NUM_DARK_STORES_TARGET

# Hourly demand curve (normalized) — lunch + evening peaks, lower 2–6 AM
HOURLY_DEMAND_WEIGHT = [
    0.015, 0.010, 0.008, 0.007, 0.010, 0.020,  # 0-5
    0.045, 0.065, 0.070, 0.055, 0.050, 0.075,  # 6-11
    0.090, 0.060, 0.045, 0.040, 0.050, 0.065,  # 12-17
    0.085, 0.095, 0.080, 0.055, 0.035, 0.020,  # 18-23
]
