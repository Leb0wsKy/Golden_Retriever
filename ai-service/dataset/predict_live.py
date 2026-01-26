from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List

import joblib
import requests

from pipeline import MODELS_DIR, flatten_snapshot, load_config, train_features_from_row


def load_model() -> Dict[str, Any]:
    model_path = MODELS_DIR / "train_anomaly_model.joblib"
    if not model_path.exists():
        raise SystemExit(f"Missing model: {model_path}. Run `python3 ai-service/dataset/train_model.py` first.")
    return joblib.load(model_path)


def fetch_snapshot(backend_url: str, endpoint: str) -> Dict[str, Any]:
    url = backend_url.rstrip("/") + endpoint
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.json()


def main() -> int:
    parser = argparse.ArgumentParser(description="Predict anomalies from a live backend snapshot.")
    parser.add_argument("--backend-url", default=None)
    parser.add_argument("--endpoint", default=None)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    cfg = load_config()
    backend_url = args.backend_url or cfg.get("backend_url", "http://localhost:5000")
    endpoint = args.endpoint or cfg.get("endpoint", "/api/trains/live")

    model_obj = load_model()
    pipeline = model_obj["pipeline"]

    payload = fetch_snapshot(backend_url=backend_url, endpoint=endpoint)
    rows = list(flatten_snapshot(payload))

    features: List[Dict[str, Any]] = [train_features_from_row(r) for r in rows]
    preds = pipeline.predict(features)

    print(f"snapshot_ts={payload.get('timestamp')}")
    for row, pred in list(zip(rows, preds))[: max(0, args.limit)]:
        print(
            json.dumps(
                {
                    "train_id": row.get("train_id"),
                    "country": row.get("country"),
                    "status": row.get("status"),
                    "speed": row.get("speed"),
                    "delay": row.get("delay"),
                    "pred": str(pred),
                },
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

