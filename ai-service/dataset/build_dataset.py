from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pandas as pd

from pipeline import (
    PROCESSED_DIR,
    RAW_DIR,
    ensure_dirs,
    flatten_snapshot,
    add_conflict_features,
    label_train_row,
    load_config,
    load_labeling_config,
)


def main() -> int:
    ensure_dirs()
    cfg = load_config()
    labeling_cfg = load_labeling_config(cfg)

    raw_path = RAW_DIR / "snapshots.jsonl"
    if not raw_path.exists():
        raise SystemExit(
            f"Missing raw snapshots: {raw_path}. Run `python3 ai-service/dataset/collect_raw.py` first."
        )

    rows = []
    with raw_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            snapshot_rows = list(flatten_snapshot(payload))
            snapshot_rows = add_conflict_features(snapshot_rows, labeling_cfg)
            for row in snapshot_rows:
                is_anomaly, label = label_train_row(row, labeling_cfg)
                row["is_anomaly"] = bool(is_anomaly)
                row["label"] = label
                rows.append(row)

    df = pd.DataFrame(rows)
    out_csv = PROCESSED_DIR / "dataset.csv"
    df.to_csv(out_csv, index=False)

    label_counts = Counter(df["label"].fillna("unknown").tolist())
    out_dist = PROCESSED_DIR / "label_distribution.json"
    out_dist.write_text(json.dumps(label_counts, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote: {out_csv}")
    print(f"Wrote: {out_dist}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
