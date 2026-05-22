#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt

if [[ ! -f data/thane_orders.csv ]]; then
  echo "Generating Thane data (first run may take a few minutes)…"
  python data_pipeline.py
fi

if [[ ! -f models/eta_regressor.joblib ]]; then
  echo "Training models…"
  python train_model.py
fi

echo "Starting API on http://127.0.0.1:8000"
exec uvicorn main:app --host 127.0.0.1 --port 8000 --reload
