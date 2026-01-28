from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import joblib
import pandas as pd
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from pipeline import MODELS_DIR, PROCESSED_DIR, LABELS, ensure_dirs, train_features_from_row


def main() -> int:
    ensure_dirs()
    dataset_path = PROCESSED_DIR / "dataset.csv"
    if not dataset_path.exists():
        raise SystemExit(f"Missing dataset: {dataset_path}. Run `python3 ai-service/dataset/build_dataset.py` first.")

    df = pd.read_csv(dataset_path)
    if "label" not in df.columns:
        raise SystemExit("dataset.csv must contain a `label` column.")

    feature_dicts: List[Dict[str, Any]] = [train_features_from_row(r) for r in df.to_dict(orient="records")]
    y = df["label"].fillna("normal").astype(str).tolist()

    X_train, X_test, y_train, y_test = train_test_split(
        feature_dicts, y, test_size=0.2, random_state=42, stratify=y if len(set(y)) > 1 else None
    )

    pipeline = Pipeline(
        steps=[
            ("vec", DictVectorizer(sparse=True)),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced", n_jobs=1)),
        ]
    )

    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)

    report = classification_report(y_test, y_pred, labels=list(LABELS), output_dict=True, zero_division=0)
    cm = confusion_matrix(y_test, y_pred, labels=list(LABELS)).tolist()

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / "train_anomaly_model.joblib"
    joblib.dump({"pipeline": pipeline, "labels": list(LABELS)}, model_path)

    metrics = {
        "dataset_path": str(dataset_path),
        "model_path": str(model_path),
        "labels": list(LABELS),
        "classification_report": report,
        "confusion_matrix": {"labels": list(LABELS), "matrix": cm},
        "n_rows": int(len(df)),
    }

    metrics_path = MODELS_DIR / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote: {model_path}")
    print(f"Wrote: {metrics_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

