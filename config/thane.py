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


def zone_predicate(zone_key: str, lat: float, lon: float, mid_lat: float, mid_lon: float) -> bool:
    """Legacy quadrant helper (kept for tests)."""
    if zone_key == "nw":
        return lat >= mid_lat and lon < mid_lon
    if zone_key == "ne":
        return lat >= mid_lat and lon >= mid_lon
    if zone_key == "sw":
        return lat < mid_lat and lon < mid_lon
    return lat < mid_lat and lon >= mid_lon


def node_in_bbox(
    lat: float,
    lon: float,
    south: float,
    north: float,
    west: float,
    east: float,
) -> bool:
    return south <= lat <= north and west <= lon <= east
