from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict

import requests
from tqdm import tqdm

from pipeline import RAW_DIR, ensure_dirs, load_config, utc_now_iso


def fetch_snapshot(backend_url: str, endpoint: str) -> Dict[str, Any]:
    url = backend_url.rstrip("/") + endpoint
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    payload = resp.json()
    if "timestamp" not in payload:
        payload["timestamp"] = utc_now_iso()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect raw snapshots from backend /api/trains/live")
    parser.add_argument("--backend-url", default=None)
    parser.add_argument("--endpoint", default=None)
    parser.add_argument("--out", default=str(RAW_DIR / "snapshots.jsonl"))
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    args = parser.parse_args()

    ensure_dirs()
    cfg = load_config()
    backend_url = args.backend_url or cfg.get("backend_url", "http://localhost:5000")
    endpoint = args.endpoint or cfg.get("endpoint", "/api/trains/live")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("a", encoding="utf-8") as f:
        for _ in tqdm(range(args.iterations), desc="Collecting snapshots"):
            payload = fetch_snapshot(backend_url=backend_url, endpoint=endpoint)
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
            f.flush()
            time.sleep(max(0.0, args.sleep_seconds))

    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

