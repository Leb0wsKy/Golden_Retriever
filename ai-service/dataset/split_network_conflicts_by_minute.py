from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from pipeline import PROCESSED_DIR, ensure_dirs


def safe_filename(minute_ts) -> str:
    return minute_ts.strftime("%Y%m%d_%H%M")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Split network_conflicts.csv into per-minute CSV files by snapshot_ts."
    )
    parser.add_argument(
        "--in",
        dest="in_path",
        default=str(PROCESSED_DIR / "network_conflicts.csv"),
        help="Input network_conflicts.csv path.",
    )
    parser.add_argument(
        "--out-dir",
        default=str(PROCESSED_DIR / "network_conflicts_by_minute"),
        help="Output directory for per-minute CSV files.",
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

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(in_path)
    if args.time_col not in df.columns:
        raise SystemExit(f"Missing timestamp column: {args.time_col}")

    timestamps = pd.to_datetime(df[args.time_col], errors="coerce", utc=True)
    df["_minute"] = timestamps.dt.floor("min")

    unknown_df = df[df["_minute"].isna()].drop(columns=["_minute"])
    if not unknown_df.empty:
        unknown_df.to_csv(out_dir / "network_conflicts_unknown_timestamp.csv", index=False)

    for minute_ts, group in df[df["_minute"].notna()].groupby("_minute"):
        minute_key = safe_filename(minute_ts.to_pydatetime())
        out_path = out_dir / f"network_conflicts_{minute_key}.csv"
        group.drop(columns=["_minute"]).to_csv(out_path, index=False)

    print(f"Wrote per-minute files in: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
