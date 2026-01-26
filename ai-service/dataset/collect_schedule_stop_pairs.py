from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv
from tqdm import tqdm

from pipeline import RAW_DIR, ensure_dirs, load_config, utc_now_iso


def load_api_key() -> Optional[str]:
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


def extract_next_url(payload: Dict[str, Any]) -> Optional[str]:
    meta = payload.get("meta") or {}
    links = payload.get("links") or {}
    return meta.get("next") or meta.get("next_url") or links.get("next")


def fetch_page(url: str, api_key: str, params: Dict[str, Any]) -> Dict[str, Any]:
    resp = requests.get(url, headers={"apikey": api_key}, params=params, timeout=60)
    resp.raise_for_status()
    payload = resp.json()
    if "timestamp" not in payload:
        payload["timestamp"] = utc_now_iso()
    return payload


def parse_stop_ids(text: Optional[str]) -> List[str]:
    if not text:
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect Transitland schedule_stop_pairs for stop IDs.")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--endpoint", default=None)
    parser.add_argument("--stop-ids", default=None, help="Comma-separated stop_onestop_id list.")
    parser.add_argument("--stops-file", default=None, help="Text file with stop_onestop_id per line.")
    parser.add_argument("--out", default=str(RAW_DIR / "schedule_stop_pairs.jsonl"))
    parser.add_argument("--follow-next", action="store_true")
    parser.add_argument("--max-pages", type=int, default=5)
    parser.add_argument("--params-json", default="{}")
    args = parser.parse_args()

    ensure_dirs()
    cfg = load_config()
    tl_cfg = cfg.get("transitland") or {}

    base_url = args.base_url or tl_cfg.get("base_url", "https://transit.land/api/v2")
    endpoint = args.endpoint or tl_cfg.get("schedule_stop_pairs_endpoint", "/rest/schedule_stop_pairs")

    api_key = load_api_key()
    if not api_key:
        raise SystemExit("Missing TRANSITLAND_API_KEY. Set env var or put it in backend/.env.")

    stop_ids = parse_stop_ids(args.stop_ids)
    if args.stops_file:
        stop_ids.extend([line.strip() for line in Path(args.stops_file).read_text().splitlines() if line.strip()])

    if not stop_ids:
        raise SystemExit("Provide stop IDs with --stop-ids or --stops-file.")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    base_url = base_url.rstrip("/")
    endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
    base_url = base_url.rstrip("/")
    endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
    base_endpoint_url = f"{base_url}{endpoint}"
    base_params = json.loads(args.params_json)

    with out_path.open("a", encoding="utf-8") as f:
        for stop_id in tqdm(stop_ids, desc="Collecting stop pairs"):
            params = dict(base_params)
            params["origin_onestop_id"] = stop_id
            page = 0
            url = base_endpoint_url
            while True:
                payload = fetch_page(url=url, api_key=api_key, params=params)
                payload["_query_stop_id"] = stop_id
                payload["_source"] = "transitland"
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
                f.flush()

                if not args.follow_next:
                    break
                next_url = extract_next_url(payload)
                if not next_url or page + 1 >= args.max_pages:
                    break
                page += 1
                if next_url.startswith("http"):
                    url = next_url
                else:
                    url = f"{base_url}{next_url}"

    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
