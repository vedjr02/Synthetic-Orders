# Thane Surge — Q-Commerce SLA & Surge Pricing Engine

10-minute grocery delivery surge pricing and SLA prediction engine for **Thane, Mumbai, India**. Built on the FlowCast architecture pattern with 100% free infrastructure (OSM, OSMnx, CARTO basemaps — no Mapbox/Google Maps API keys).

## What is this project?

Imagine Zepto or Blinkit operating only in **Thane city**. This engine simulates that world:

1. **Dark stores** — **37 grocery hubs** across 9 Thane neighbourhoods (22 Blinkit + 15 Instamart, per [QuickCommerceMap](https://quickcommercemap.com/cities/thane)).
2. **Synthetic orders** — **~21,500 orders/day** × 14 days ≈ **300k deliveries**, routed on real OSM roads with lunch/evening demand peaks.
3. **ML models** — predict delivery ETA and the chance of missing the **10-minute SLA**.
4. **Surge pricing** — when SLA risk rises (rain, rush hour, low riders), the price multiplier goes up.
5. **Dashboard** — a live map of Thane showing order heat, surge zones, and monsoon weather simulation.

It is a portfolio demo of **Q-Commerce logistics intelligence**, not a production app.

## Folder Structure

```
Synthetic Orders/
├── config/
│   ├── thane.py              # Thane city bbox + zone definitions
│   └── thane_bounds.json     # Map fit bounds (committed)
├── data_pipeline.py          # Phase 1: OSM download + synthetic orders
├── train_model.py            # Phase 2: XGBoost training + joblib serialization
├── main.py                   # Phase 3: FastAPI backend
├── requirements.txt          # Python dependencies
├── README.md
├── data/
│   ├── thane_orders.csv      # Generated synthetic orders (10k × 14 days)
│   └── thane_network.geojson # OSMnx node network for map layer
├── models/
│   ├── eta_regressor.joblib  # XGBoost ETA model
│   ├── sla_classifier.joblib # XGBoost SLA breach classifier
│   ├── thane_graph.joblib    # Serialized drive network
│   ├── dark_stores.json      # 4 dark-store hub locations
│   └── model_meta.json       # Feature columns + metrics
├── cache/                    # OSMnx tile/cache (use_cache=True)
└── frontend/                 # Phase 4: Next.js + deck.gl dashboard
    ├── package.json
    ├── next.config.js
    ├── tsconfig.json
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx
    │   └── globals.css
    ├── components/
    │   ├── DashboardMap.tsx   # deck.gl Hexagon + Scatterplot layers
    │   ├── ControlPanel.tsx   # Monsoon weather simulator
    │   └── MetricsPanel.tsx   # Live KPI cards
    └── lib/
        └── api.ts             # Backend client
```

## 3-Step Quick Start

### Step 1 — Generate data & train models

```bash
cd "/Users/ved/MAINS/Maynooth UNI/Vs Code/Synthetic Orders"
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python data_pipeline.py            # Downloads Thane OSM graph, writes CSV (~5–10 min first run)
python train_model.py              # Trains XGBoost models → models/
```

### Step 2 — Start the backend

```bash
source .venv/bin/activate
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

API docs: http://127.0.0.1:8000/docs

### Step 3 — Launch the frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard: http://localhost:3000

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/network` | Thane OSMnx nodes as GeoJSON |
| `POST` | `/api/predict_surge` | ETA, surge multiplier, SLA risk |
| `GET` | `/api/metrics` | Live ops KPIs — active orders, fleet utilization |
| `GET` | `/api/analytics` | Full BI bundle — GMV, trends, zones, leaderboard |
| `GET` | `/api/analytics/overview` | Business KPI summary |
| `GET` | `/api/dark-stores` | Dark store hub coordinates |
| `GET` | `/api/orders` | Sample delivery points for map |

## Surge Formula

```
Surge Multiplier = Base × (1 + SLA_Breach_Risk) × Weather_Factor
```

| Weather | Factor |
|---------|--------|
| Clear | 1.00 |
| Rain | 1.15 |
| Heavy Rain | 1.35 |

## Stack (100% Free)

- **Routing**: OSMnx + NetworkX (OpenStreetMap)
- **ML**: XGBoost + scikit-learn + joblib
- **Backend**: FastAPI + Uvicorn
- **Frontend**: Next.js 14 + deck.gl + MapLibre GL + CARTO Dark Matter basemap

## macOS Note (XGBoost)

If `train_model.py` fails with a `libomp` error, install OpenMP then re-run:

```bash
brew install libomp
python train_model.py
```

Without Homebrew, the script automatically falls back to scikit-learn `HistGradientBoosting` models (same API, saved via joblib).

## License

MIT
