from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from pipeline import PROCESSED_DIR, ensure_dirs


def pick_first(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for name in candidates:
        if name in df.columns:
            return name
    return None


def build_is_conflict(df: pd.DataFrame, label_col: str | None) -> pd.Series:
    if "is_network_conflict" in df.columns:
        return df["is_network_conflict"].fillna(False).astype(bool)
    if "is_conflict" in df.columns:
        return df["is_conflict"].fillna(False).astype(bool)
    if label_col and label_col in df.columns:
        return df[label_col].fillna("normal").astype(str).str.lower().ne("normal")
    return pd.Series([False] * len(df))


def plot_label_distribution(df: pd.DataFrame, label_col: str, out_dir: Path) -> None:
    counts = df[label_col].fillna("normal").astype(str).value_counts()
    plt.figure(figsize=(8, 4))
    counts.plot(kind="bar")
    plt.title("Label distribution")
    plt.ylabel("count")
    plt.tight_layout()
    plt.savefig(out_dir / "label_distribution.png")
    plt.close()


def plot_conflict_rate_over_time(df: pd.DataFrame, time_col: str, is_conflict: pd.Series, out_dir: Path) -> None:
    timestamps = pd.to_datetime(df[time_col], errors="coerce", utc=True)
    if timestamps.isna().all():
        return
    minute = timestamps.dt.floor("min")
    temp = pd.DataFrame({"minute": minute, "is_conflict": is_conflict})
    series = temp.groupby("minute")["is_conflict"].mean()
    plt.figure(figsize=(10, 4))
    series.plot()
    plt.title("Conflict rate per minute")
    plt.ylabel("conflict rate")
    plt.xlabel("minute")
    plt.tight_layout()
    plt.savefig(out_dir / "conflict_rate_per_minute.png")
    plt.close()


def plot_top_networks(df: pd.DataFrame, network_col: str, is_conflict: pd.Series, out_dir: Path) -> None:
    temp = df.copy()
    temp["is_conflict"] = is_conflict
    counts = temp.groupby(network_col)["is_conflict"].sum().sort_values(ascending=False).head(10)
    if counts.empty:
        return
    plt.figure(figsize=(8, 4))
    counts.sort_values().plot(kind="barh")
    plt.title("Top networks by conflict count")
    plt.xlabel("conflict count")
    plt.tight_layout()
    plt.savefig(out_dir / "top_networks_conflicts.png")
    plt.close()


def plot_correlation(df: pd.DataFrame, out_dir: Path) -> None:
    numeric = df.select_dtypes(include="number")
    if numeric.empty:
        return
    if numeric.shape[1] > 20:
        numeric = numeric.iloc[:, :20]
    corr = numeric.corr()
    plt.figure(figsize=(8, 6))
    plt.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
    plt.xticks(range(len(corr.columns)), corr.columns, rotation=90)
    plt.yticks(range(len(corr.index)), corr.index)
    plt.colorbar()
    plt.title("Feature correlation")
    plt.tight_layout()
    plt.savefig(out_dir / "feature_correlation.png")
    plt.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate simple plots for conflict datasets.")
    parser.add_argument(
        "--in",
        dest="in_path",
        default=str(PROCESSED_DIR / "network_conflicts_minute.csv"),
        help="Input CSV path.",
    )
    parser.add_argument(
        "--out-dir",
        default=str(PROCESSED_DIR / "plots"),
        help="Output directory for PNG plots.",
    )
    parser.add_argument(
        "--time-col",
        default=None,
        help="Timestamp column override (default auto).",
    )
    parser.add_argument(
        "--label-col",
        default=None,
        help="Label column override (default auto).",
    )
    parser.add_argument(
        "--network-col",
        default=None,
        help="Network column override (default auto).",
    )
    args = parser.parse_args()

    ensure_dirs()
    in_path = Path(args.in_path)
    if not in_path.exists():
        raise SystemExit(f"Missing input file: {in_path}")

    df = pd.read_csv(in_path)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    label_col = args.label_col or pick_first(df, ["network_conflict_label", "conflict_label", "label"])
    time_col = args.time_col or pick_first(df, ["snapshot_ts", "timestamp", "time"])
    network_col = args.network_col or pick_first(df, ["network_id", "network"])

    if label_col:
        plot_label_distribution(df, label_col, out_dir)

    is_conflict = build_is_conflict(df, label_col)

    if time_col:
        plot_conflict_rate_over_time(df, time_col, is_conflict, out_dir)

    if network_col:
        plot_top_networks(df, network_col, is_conflict, out_dir)

    plot_correlation(df, out_dir)

    print(f"Wrote plots to: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
