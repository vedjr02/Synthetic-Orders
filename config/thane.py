"""Thane city (Municipal Corporation) geographic constants — not the wider district."""

from __future__ import annotations

# WGS84 bounding box covering Thane city proper (West, East, Ghodbunder, Kalwa)
THANE_CITY_BBOX: dict[str, float] = {
    "north": 19.295,
    "south": 19.055,
    "east": 73.085,
    "west": 72.905,
}

THANE_CITY_CENTER: dict[str, float] = {
    "latitude": 19.197,
    "longitude": 72.978,
}

# Dark-store zones — one hub per quadrant for city-wide coverage
THANE_STORE_ZONES: list[dict] = [
    {"id": 1, "name": "Thane West", "pred": "nw"},
    {"id": 2, "name": "Thane East", "pred": "ne"},
    {"id": 3, "name": "Wagle / Naupada", "pred": "sw"},
    {"id": 4, "name": "Ghodbunder Road", "pred": "se"},
]


def zone_predicate(zone_key: str, lat: float, lon: float, mid_lat: float, mid_lon: float) -> bool:
    if zone_key == "nw":
        return lat >= mid_lat and lon < mid_lon
    if zone_key == "ne":
        return lat >= mid_lat and lon >= mid_lon
    if zone_key == "sw":
        return lat < mid_lat and lon < mid_lon
    return lat < mid_lat and lon >= mid_lon
