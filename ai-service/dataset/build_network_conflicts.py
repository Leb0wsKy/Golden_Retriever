from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd

from pipeline import (
    PROCESSED_DIR,
    ensure_dirs,
    load_config,
    load_network_conflict_config,
    NETWORK_CONFLICT_PRIORITY,
)


def assign_network_label(row: dict) -> str:
    for label in NETWORK_CONFLICT_PRIORITY:
        if row.get(label):
            return label
    return "normal"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate train-level dataset into network-level conflicts by snapshot."
    )
    parser.add_argument(
        "--in",
        dest="in_path",
        default=str(PROCESSED_DIR / "dataset.csv"),
        help="Input train-level dataset CSV.",
    )
    parser.add_argument(
        "--out",
        default=str(PROCESSED_DIR / "network_conflicts.csv"),
        help="Output network-level dataset CSV.",
    )
    args = parser.parse_args()

    ensure_dirs()
    cfg = load_config()
    net_cfg = load_network_conflict_config(cfg)

    in_path = Path(args.in_path)
    if not in_path.exists():
        raise SystemExit(f"Missing dataset: {in_path}")

    df = pd.read_csv(in_path)
    if "snapshot_ts" not in df.columns or "network_id" not in df.columns:
        raise SystemExit("dataset.csv must contain snapshot_ts and network_id columns.")

    df["is_anomaly"] = df.get("is_anomaly", False).fillna(False).astype(bool)
    df["has_conflict"] = df.get("has_conflict", False).fillna(False).astype(bool)
    df["delay"] = df.get("delay", 0).fillna(0).astype(float)
    df["conflict_type"] = df.get("conflict_type", "none").fillna("none")

    group_cols = ["snapshot_ts", "network_id"]
    agg_rows = []

    for (snapshot_ts, network_id), group in df.groupby(group_cols):
        train_count = int(len(group))
        if train_count == 0:
            continue

        anomaly_count = int(group["is_anomaly"].sum())
        conflict_count = int(group["has_conflict"].sum())
        delay_high_count = int((group["delay"] >= net_cfg.delay_high_minutes).sum())
        avg_delay = float(group["delay"].mean()) if train_count else 0.0
        avg_speed = float(group.get("speed", 0).fillna(0).mean())

        conflict_counts = Counter(group["conflict_type"].fillna("none").tolist())
        conflict_counts.pop("none", None)

        proximity_conflicts = int(conflict_counts.get("proximity_conflict", 0))
        congestion_conflicts = int(conflict_counts.get("congestion_conflict", 0))

        anomaly_ratio = anomaly_count / train_count
        conflict_ratio = conflict_count / train_count

        row = {
            "snapshot_ts": snapshot_ts,
            "network_id": network_id,
            "train_count": train_count,
            "anomaly_count": anomaly_count,
            "conflict_count": conflict_count,
            "delay_high_count": delay_high_count,
            "avg_delay": avg_delay,
            "avg_speed": avg_speed,
            "anomaly_ratio": anomaly_ratio,
            "conflict_ratio": conflict_ratio,
            "proximity_conflict_count": proximity_conflicts,
            "congestion_conflict_count": congestion_conflicts,
        }

        row["network_congestion_conflict"] = congestion_conflicts >= net_cfg.min_conflict_trains
        row["network_proximity_conflict"] = (
            proximity_conflicts >= net_cfg.min_conflict_trains and not row["network_congestion_conflict"]
        )
        row["network_delay_conflict"] = delay_high_count >= net_cfg.min_conflict_trains
        row["network_anomaly_spike"] = anomaly_ratio >= net_cfg.anomaly_ratio_threshold

        if conflict_ratio >= net_cfg.conflict_ratio_threshold:
            row["network_congestion_conflict"] = True

        row["network_conflict_label"] = assign_network_label(row)
        row["is_network_conflict"] = row["network_conflict_label"] != "normal"

        agg_rows.append(row)

    out_df = pd.DataFrame(agg_rows)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out_path, index=False)

    label_counts = Counter(out_df["network_conflict_label"].fillna("normal").tolist())
    dist_path = out_path.with_suffix(".label_distribution.json")
    dist_path.write_text(json.dumps(label_counts, indent=2), encoding="utf-8")

    print(f"Wrote: {out_path}")
    print(f"Wrote: {dist_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

