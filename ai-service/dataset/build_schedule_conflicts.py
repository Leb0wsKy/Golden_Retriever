from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd

from pipeline import (
    PROCESSED_DIR,
    RAW_DIR,
    add_schedule_features,
    apply_schedule_conflict_detection,
    assign_conflict_label,
    ensure_dirs,
    extract_delay_minutes,
    extract_schedule_stop_pairs,
    load_config,
    load_schedule_conflict_config,
    normalize_schedule_record,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build dataset for schedule-based conflicts.")
    parser.add_argument(
        "--raw",
        default=str(RAW_DIR / "schedule_stop_pairs.jsonl"),
        help="Path to raw schedule_stop_pairs JSONL.",
    )
    parser.add_argument(
        "--out",
        default=str(PROCESSED_DIR / "schedule_conflicts.csv"),
        help="Output CSV path.",
    )
    args = parser.parse_args()

    ensure_dirs()
    cfg = load_config()
    conflict_cfg = load_schedule_conflict_config(cfg)

    raw_path = Path(args.raw)
    if not raw_path.exists():
        raise SystemExit(f"Missing raw schedule_stop_pairs: {raw_path}")

    rows = []
    with raw_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            for record in extract_schedule_stop_pairs(payload):
                row = normalize_schedule_record(record)
                row["delay_minutes"] = extract_delay_minutes(record)
                rows.append(row)

    rows = add_schedule_features(rows)
    rows = apply_schedule_conflict_detection(rows, conflict_cfg)

    for row in rows:
        label = assign_conflict_label(row)
        row["conflict_label"] = label
        row["is_conflict"] = label != "normal"
        flags = row.get("conflict_flags") or set()
        if not isinstance(flags, set):
            flags = set(flags)
        row["conflict_flags"] = ",".join(sorted(flags)) if flags else ""
        row.pop("raw_record", None)

    df = pd.DataFrame(rows)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)

    label_counts = Counter(df["conflict_label"].fillna("normal").tolist())
    dist_path = out_path.with_suffix(".label_distribution.json")
    dist_path.write_text(json.dumps(label_counts, indent=2), encoding="utf-8")

    print(f"Wrote: {out_path}")
    print(f"Wrote: {dist_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

