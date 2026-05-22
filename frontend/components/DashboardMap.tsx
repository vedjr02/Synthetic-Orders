"use client";

import { useMemo } from "react";
import DeckGL from "@deck.gl/react";
import { HexagonLayer } from "@deck.gl/aggregation-layers";
import { ScatterplotLayer } from "@deck.gl/layers";
import Map from "react-map-gl/maplibre";
import type { DarkStore, OrderPoint, Weather } from "@/lib/api";

/** Free CARTO basemap — no API key required */
const MAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

type OrderWithSurge = OrderPoint & { surge_estimate?: number };

interface ViewState {
  longitude: number;
  latitude: number;
  zoom: number;
  pitch?: number;
  bearing?: number;
}

interface Props {
  initialViewState: ViewState;
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

export default function DashboardMap({ initialViewState, orders, stores, weather }: Props) {
  const viewState = useMemo(
    () => ({
      ...initialViewState,
      pitch: weather === "Heavy Rain" ? 52 : weather === "Rain" ? 42 : 35,
      bearing: -12,
    }),
    [initialViewState, weather]
  );

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
      })),
    [stores]
  );

  const layers = useMemo(
    () => [
      new HexagonLayer({
        id: "order-density",
        data: orderData,
        pickable: true,
        extruded: true,
        radius: 280,
        elevationScale: weather === "Heavy Rain" ? 45 : 30,
        coverage: 0.85,
        getPosition: (d) => d.position,
        getElevationWeight: (d) => d.surge,
        getColorWeight: (d) => d.surge,
        colorRange: [
          [129, 140, 248, 180],
          [94, 234, 212, 200],
          [251, 191, 36, 220],
          [248, 113, 113, 240],
          [220, 38, 38, 255],
        ],
        elevationRange: [0, 1200],
        material: { ambient: 0.4, diffuse: 0.6, shininess: 32 },
        updateTriggers: {
          getElevationWeight: [weather],
          elevationScale: [weather],
        },
      }),
      new ScatterplotLayer({
        id: "delivery-points",
        data: orderData,
        pickable: true,
        opacity: 0.75,
        stroked: true,
        filled: true,
        radiusScale: 40,
        radiusMinPixels: 2,
        radiusMaxPixels: 8,
        lineWidthMinPixels: 1,
        getPosition: (d) => d.position,
        getRadius: (d) => 30 + d.surge * 15,
        getFillColor: (d) => surgeColor(d.surge),
        getLineColor: [255, 255, 255, 80],
        updateTriggers: {
          getFillColor: [weather],
        },
      }),
      new ScatterplotLayer({
        id: "dark-stores",
        data: storeData,
        pickable: true,
        opacity: 1,
        stroked: true,
        filled: true,
        radiusScale: 120,
        radiusMinPixels: 10,
        radiusMaxPixels: 18,
        getPosition: (d) => d.position,
        getFillColor: [94, 234, 212, 255],
        getLineColor: [255, 255, 255, 220],
        lineWidthMinPixels: 2,
      }),
    ],
    [orderData, storeData, weather]
  );

  return (
    <DeckGL
      initialViewState={viewState}
      controller={{ touchRotate: true, dragRotate: true }}
      layers={layers}
      style={{ width: "100%", height: "100%" }}
    >
      <Map mapStyle={MAP_STYLE} attributionControl />
    </DeckGL>
  );
}
