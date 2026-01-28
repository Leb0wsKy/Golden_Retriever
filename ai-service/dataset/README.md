# Dataset & Training (Train Anomalies)

Objectif: générer un dataset à partir de l’API backend (`/api/trains/live`), labelliser automatiquement chaque observation (`normal` ou un type d’anomalie), puis entraîner un modèle multi-classe.

## 1) Pré-requis

- Lancer le backend (port `5000`) et avoir `TRANSITLAND_API_KEY` configuré dans `backend/.env` (ne pas committer la clé).
- Python 3.10+ recommandé (ce repo tourne aussi en 3.12).

Installer les dépendances du pipeline dataset (séparées du service Flask):

```bash
python3 -m pip install -r ai-service/dataset/requirements.txt
```

## 2) Collecte des snapshots (raw)

Collecte N snapshots depuis le backend et écrit un JSONL (1 ligne = 1 snapshot).

```bash
python3 ai-service/dataset/collect_raw.py \
  --backend-url http://localhost:5000 \
  --iterations 200 \
  --sleep-seconds 1.0
```

Sortie:
- `ai-service/dataset/raw/snapshots.jsonl`

### Alternative (direct Transitland avec API key)

Si tu veux créer la dataset directement depuis la source (Transitland) et pas seulement depuis les “trains actifs” construits par le backend:

```bash
export TRANSITLAND_API_KEY="...ta_cle..."
python3 ai-service/dataset/collect_transitland_raw.py \
  --iterations 200 \
  --sleep-seconds 1.0 \
  --endpoint /rest/vehicles
```

Sortie:
- `ai-service/dataset/raw/transitland_snapshots.jsonl`

## 3) Construction du dataset (features + labels)

```bash
python3 ai-service/dataset/build_dataset.py
```

Sorties:
- `ai-service/dataset/processed/dataset.csv`
- `ai-service/dataset/processed/label_distribution.json`

## Dataset "Schedule Conflicts" (7 types)

Ce dataset utilise les horaires (`schedule_stop_pairs`) de Transitland pour détecter:
`platform_conflict`, `headway_conflict`, `delay_propagation_conflict`, `capacity_congestion_conflict`,
`service_gap_conflict`, `schedule_inconsistency_conflict`, `transfer_timing_conflict`.

### 1) Collecter les schedule_stop_pairs

```bash
export TRANSITLAND_API_KEY="...ta_cle..."
python3 ai-service/dataset/collect_schedule_stop_pairs.py \
  --stop-ids "s-xyz,s-abc" \
  --follow-next \
  --max-pages 3
```

Sortie:
- `ai-service/dataset/raw/schedule_stop_pairs.jsonl`

### 2) Construire la dataset conflicts

```bash
python3 ai-service/dataset/build_schedule_conflicts.py
```

Sorties:
- `ai-service/dataset/processed/schedule_conflicts.csv`
- `ai-service/dataset/processed/schedule_conflicts.label_distribution.json`

## Dataset "Network Conflicts" (aggregation par network_id)

Cette dataset agrège `dataset.csv` par `snapshot_ts` + `network_id` pour déduire un conflit au niveau réseau.

```bash
python3 ai-service/dataset/build_network_conflicts.py
```

Sorties:
- `ai-service/dataset/processed/network_conflicts.csv`
- `ai-service/dataset/processed/network_conflicts.label_distribution.json`

## Split par minute (network_conflicts.csv)

Si tu veux un CSV par minute (selon `snapshot_ts`):

```bash
python3 ai-service/dataset/split_network_conflicts_by_minute.py
```

Sortie:
- `ai-service/dataset/processed/network_conflicts_by_minute/`

## Normaliser snapshot_ts par minute (un seul CSV)

Si tu veux **un seul fichier** où `snapshot_ts` est arrondi à la minute:

```bash
python3 ai-service/dataset/normalize_network_conflicts_minute.py
```

Sortie:
- `ai-service/dataset/processed/network_conflicts_minute.csv`

## Visualisation rapide (PNG)

```bash
python3 ai-service/dataset/visualize_conflicts.py \
  --in ai-service/dataset/processed/network_conflicts_minute.csv
```

Sortie:
- `ai-service/dataset/processed/plots/`

Labels réseau possibles:
- `network_congestion_conflict`
- `network_proximity_conflict`
- `network_delay_conflict`
- `network_anomaly_spike`
- `normal`

Seuils configurables dans `ai-service/dataset/config.json` → `network_conflicts`.

## 4) Entraînement du modèle multi-classe (5 anomalies + normal)

```bash
python3 ai-service/dataset/train_model.py
```

Sorties:
- `ai-service/dataset/models/train_anomaly_model.joblib`
- `ai-service/dataset/models/metrics.json`

## 5) Prédire en live depuis le backend

```bash
python3 ai-service/dataset/predict_live.py --backend-url http://localhost:5000 --limit 20
```

## Labels

Le label final est `normal` ou une des 5 classes d’anomalies:

- `delay_high`: `delay >= 5` minutes
- `delay_mismatch`: incohérence entre `status` et `delay`
- `speed_high`: `speed >= 90`
- `speed_low`: `speed <= 10`
- `status_unknown`: `status` manquant ou inattendu

Les règles sont centralisées dans `ai-service/dataset/pipeline.py` et configurables via `ai-service/dataset/config.json`.

## Conflicts (conflits opérationnels)

En plus du label d’anomalie, on ajoute des colonnes de “conflit” calculées par snapshot:

- `nearest_train_km`: distance minimale vers un autre train du même snapshot
- `nearby_trains`: nombre de trains dans un rayon `conflict_proximity_km`
- `has_conflict`: booléen
- `conflict_type`: `none`, `proximity_conflict`, `congestion_conflict`
