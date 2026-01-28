from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv
from tqdm import tqdm

from pipeline import RAW_DIR, ensure_dirs, load_config, utc_now_iso


def load_api_key() -> Optional[str]:
    """
    Priorité:
    1) env TRANSITLAND_API_KEY
    2) backend/.env (si présent)
    3) .env (root) (si présent)
    """
    api_key = os.getenv("TRANSITLAND_API_KEY")
    if api_key:
        return api_key

    repo_root = Path(__file__).resolve().parents[2]
    backend_env = repo_root / "backend" / ".env"
    root_env = repo_root / ".env"

    if backend_env.exists():
        load_dotenv(backend_env)
    if root_env.exists():
        load_dotenv(root_env, override=False)

    return os.getenv("TRANSITLAND_API_KEY")


def fetch_transitland(base_url: str, endpoint: str, api_key: str, params: Dict[str, Any]) -> Dict[str, Any]:
    url = base_url.rstrip("/") + endpoint
    resp = requests.get(url, headers={"apikey": api_key}, params=params, timeout=60)
    resp.raise_for_status()
    payload = resp.json()
    if "timestamp" not in payload:
        payload["timestamp"] = utc_now_iso()
    payload["_source"] = "transitland"
    payload["_url"] = url
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect raw snapshots directly from Transitland API using TRANSITLAND_API_KEY."
    )
    parser.add_argument("--base-url", default=None, help="Default from ai-service/dataset/config.json")
    parser.add_argument("--endpoint", default=None, help="Example: /rest/vehicles or /rest/routes")
    parser.add_argument("--out", default=str(RAW_DIR / "transitland_snapshots.jsonl"))
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument("--params-json", default="{}", help='Extra query params as JSON string, e.g. \'{"limit":100}\'.')
    args = parser.parse_args()

    ensure_dirs()
    cfg = load_config()
    tl_cfg = cfg.get("transitland") or {}

    base_url = args.base_url or tl_cfg.get("base_url", "https://transit.land/api/v2")
    endpoint = args.endpoint or tl_cfg.get("endpoint")
    if not endpoint:
        raise SystemExit("Missing Transitland endpoint. Set it in config.json or pass --endpoint.")

    api_key = load_api_key()
    if not api_key:
        raise SystemExit("Missing TRANSITLAND_API_KEY. Set env var or put it in backend/.env.")

    params = json.loads(args.params_json)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("a", encoding="utf-8") as f:
        for _ in tqdm(range(args.iterations), desc="Collecting Transitland snapshots"):
            payload = fetch_transitland(base_url=base_url, endpoint=endpoint, api_key=api_key, params=params)
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
            f.flush()
            time.sleep(max(0.0, args.sleep_seconds))

    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

