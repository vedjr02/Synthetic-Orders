"use client";

import { useEffect, useMemo, useState } from "react";
import DeckGL from "@deck.gl/react";
import { WebMercatorViewport } from "@deck.gl/core";
import { HexagonLayer } from "@deck.gl/aggregation-layers";
import { PolygonLayer, ScatterplotLayer } from "@deck.gl/layers";
import Map from "react-map-gl/maplibre";
import type { CityBounds, DarkStore, OrderPoint, Weather } from "@/lib/api";

/** Free CARTO basemap — no API key required */
const MAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

type OrderWithSurge = OrderPoint & { surge_estimate?: number };

interface Props {
  bounds: CityBounds | null;
  orders: OrderWithSurge[];
  stores: DarkStore[];
  weather: Weather;
}

function surgeColor(surge: number): [number, number, number, number] {
  if (surge >= 2.2) return [248, 113, 113, 210];
  if (surge >= 1.8) return [251, 191, 36, 200];
  if (surge >= 1.4) return [94, 234, 212, 190];
  return [129, 140, 248, 170];
}

function fitCityView(bounds: CityBounds, weather: Weather) {
  const { north, south, east, west } = bounds.bbox;
  const width = typeof window !== "undefined" ? window.innerWidth : 1200;
  const height = typeof window !== "undefined" ? window.innerHeight : 800;
  const vp = new WebMercatorViewport({ width, height });
  const fitted = vp.fitBounds(
    [
      [west, south],
      [east, north],
    ],
    { padding: { top: 48, bottom: 48, left: 400, right: 48 } }
  );
  return {
    longitude: fitted.longitude,
    latitude: fitted.latitude,
    zoom: fitted.zoom,
    pitch: weather === "Heavy Rain" ? 48 : weather === "Rain" ? 40 : 32,
    bearing: -8,
  };
}

export default function DashboardMap({ bounds, orders, stores, weather }: Props) {
  const [viewState, setViewState] = useState(() =>
    bounds
      ? fitCityView(bounds, weather)
      : { longitude: 72.978, latitude: 19.197, zoom: 11.5, pitch: 32, bearing: -8 }
  );

  useEffect(() => {
    if (bounds) {
      setViewState(fitCityView(bounds, weather));
    }
  }, [bounds, weather]);

  useEffect(() => {
    const onResize = () => {
      if (bounds) setViewState(fitCityView(bounds, weather));
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [bounds, weather]);

  const orderData = useMemo(
    () =>
      orders.map((o) => ({
        position: [o.delivery_lon, o.delivery_lat] as [number, number],
        surge: o.surge_estimate ?? (o.sla_breach ? 1.8 : 1.2),
        eta: o.actual_eta_min,
        value: o.order_value_inr,
      })),
    [orders]
  );

  const storeData = useMemo(
    () =>
      stores.map((s) => ({
        position: [s.lon, s.lat] as [number, number],
        name: s.name,
        platform: s.platform ?? "Blinkit",
      })),
    [stores]
  );

  function platformColor(platform: string): [number, number, number, number] {
    if (platform.includes("Instamart")) return [255, 140, 50, 240];
    return [94, 234, 212, 240]; // Blinkit teal
  }

  const boundaryData = useMemo(() => {
    if (!bounds) return [];
    const { north, south, east, west } = bounds.bbox;
    return [
      {
        polygon: [
          [west, south],
          [east, south],
          [east, north],
          [west, north],
          [west, south],
        ],
      },
    ];
  }, [bounds]);

  const layers = useMemo(
    () => [
      new PolygonLayer({
        id: "city-boundary",
        data: boundaryData,
        pickable: false,
        stroked: true,
        filled: true,
        getPolygon: (d) => d.polygon,
        getFillColor: [94, 234, 212, 12],
        getLineColor: [94, 234, 212, 100],
        lineWidthMinPixels: 2,
      }),
      new HexagonLayer({
        id: "order-density",
        data: orderData,
        pickable: true,
        extruded: true,
        radius: 350,
        elevationScale: weather === "Heavy Rain" ? 40 : 28,
        coverage: 0.82,
        getPosition: (d) => d.position,
        getElevationWeight: (d) => d.surge,
        getColorWeight: (d) => d.surge,
        colorRange: [
          [129, 140, 248, 160],
          [94, 234, 212, 190],
          [251, 191, 36, 210],
          [248, 113, 113, 230],
          [220, 38, 38, 250],
        ],
        elevationRange: [0, 900],
        material: { ambient: 0.45, diffuse: 0.55, shininess: 28 },
        updateTriggers: {
          getElevationWeight: [weather, orderData.length],
          elevationScale: [weather],
        },
      }),
      new ScatterplotLayer({
        id: "delivery-points",
        data: orderData,
        pickable: true,
        opacity: 0.55,
        stroked: true,
        filled: true,
        radiusScale: 35,
        radiusMinPixels: 1,
        radiusMaxPixels: 6,
        lineWidthMinPixels: 1,
        getPosition: (d) => d.position,
        getRadius: (d) => 25 + d.surge * 12,
        getFillColor: (d) => surgeColor(d.surge),
        getLineColor: [255, 255, 255, 60],
      }),
      new ScatterplotLayer({
        id: "dark-stores",
        data: storeData,
        pickable: true,
        opacity: 1,
        stroked: true,
        filled: true,
        radiusScale: 60,
        radiusMinPixels: 5,
        radiusMaxPixels: 10,
        getPosition: (d) => d.position,
        getFillColor: (d) => platformColor(d.platform),
        getLineColor: [255, 255, 255, 200],
        lineWidthMinPixels: 1,
      }),
    ],
    [orderData, storeData, boundaryData, weather]
  );

  return (
    <DeckGL
      viewState={viewState}
      onViewStateChange={({ viewState: vs }) => setViewState(vs as typeof viewState)}
      controller={{ touchRotate: true, dragRotate: true, inertia: true }}
      layers={layers}
      style={{ width: "100%", height: "100%" }}
    >
      <Map mapStyle={MAP_STYLE} attributionControl />
    </DeckGL>
  );
}
