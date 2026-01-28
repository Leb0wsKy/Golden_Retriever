from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from pipeline import PROCESSED_DIR, ensure_dirs


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize snapshot_ts to minute resolution in a single CSV."
    )
    parser.add_argument(
        "--in",
        dest="in_path",
        default=str(PROCESSED_DIR / "network_conflicts.csv"),
        help="Input network_conflicts.csv path.",
    )
    parser.add_argument(
        "--out",
        default=str(PROCESSED_DIR / "network_conflicts_minute.csv"),
        help="Output CSV path.",
    )
    parser.add_argument(
        "--time-col",
        default="snapshot_ts",
        help="Timestamp column name (default: snapshot_ts).",
    )
    args = parser.parse_args()

    ensure_dirs()
    in_path = Path(args.in_path)
    if not in_path.exists():
        raise SystemExit(f"Missing input file: {in_path}")

    df = pd.read_csv(in_path)
    if args.time_col not in df.columns:
        raise SystemExit(f"Missing timestamp column: {args.time_col}")

    timestamps = pd.to_datetime(df[args.time_col], errors="coerce", utc=True)
    if timestamps.isna().any():
        bad_count = int(timestamps.isna().sum())
        raise SystemExit(f"Invalid timestamps detected in {bad_count} rows. Fix them before normalizing.")

    minute_ts = timestamps.dt.floor("min")
    df[args.time_col] = minute_ts.dt.strftime("%Y-%m-%dT%H:%M:00Z")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)

    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
