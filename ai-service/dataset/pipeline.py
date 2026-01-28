from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


DATASET_DIR = Path(__file__).resolve().parent
RAW_DIR = DATASET_DIR / "raw"
PROCESSED_DIR = DATASET_DIR / "processed"
MODELS_DIR = DATASET_DIR / "models"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_config() -> dict:
    cfg_path = DATASET_DIR / "config.json"
    with cfg_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        if isinstance(value, bool):
            return float(value)
        if isinstance(value, (int, float)):
            if math.isnan(float(value)) or math.isinf(float(value)):
                return None
            return float(value)
        return float(str(value))
    except Exception:
        return None


def safe_int(value: Any) -> Optional[int]:
    number = safe_float(value)
    if number is None:
        return None
    return int(round(number))


def flatten_snapshot(payload: dict) -> Iterable[dict]:
    """
    Backend `/api/trains/live` renvoie:
      { networks: [ { id, country, trains: [...], routes: [...] }, ...], timestamp }
    On aplatit en 1 ligne par train.
    """
    snapshot_ts = payload.get("timestamp") or utc_now_iso()
    networks = payload.get("networks") or []

    for network in networks:
        network_id = network.get("id")
        country = network.get("country")
        trains = network.get("trains") or []
        for train in trains:
            position = train.get("position") or [None, None]
            lat = position[0] if isinstance(position, list) and len(position) > 0 else None
            lng = position[1] if isinstance(position, list) and len(position) > 1 else None
            yield {
                "snapshot_ts": snapshot_ts,
                "network_id": network_id,
                "country": country,
                "train_id": train.get("id"),
                "route": train.get("route"),
                "status": train.get("status"),
                "speed": safe_float(train.get("speed")),
                "delay": safe_float(train.get("delay")),
                "lat": safe_float(lat),
                "lng": safe_float(lng),
            }


@dataclass(frozen=True)
class LabelingConfig:
    delay_high_minutes: float = 5.0
    speed_high_kmh: float = 90.0
    speed_low_kmh: float = 10.0
    conflict_proximity_km: float = 1.0
    conflict_congestion_count: int = 3


LABELS: Tuple[str, ...] = (
    "normal",
    "delay_high",
    "delay_mismatch",
    "speed_high",
    "speed_low",
    "status_unknown",
)


def label_train_row(row: dict, cfg: LabelingConfig) -> Tuple[bool, str]:
    status = (row.get("status") or "").strip().lower()
    delay = safe_float(row.get("delay"))
    speed = safe_float(row.get("speed"))

    known_status = status in {"on-time", "delayed"}
    if not known_status:
        return True, "status_unknown"

    if delay is not None and delay >= cfg.delay_high_minutes:
        return True, "delay_high"

    if delay is not None:
        if status == "on-time" and delay > 0:
            return True, "delay_mismatch"
        if status == "delayed" and delay == 0:
            return True, "delay_mismatch"

    if speed is not None and speed >= cfg.speed_high_kmh:
        return True, "speed_high"

    if speed is not None and speed <= cfg.speed_low_kmh:
        return True, "speed_low"

    return False, "normal"


def load_labeling_config(cfg: dict) -> LabelingConfig:
    labeling = cfg.get("labeling") or {}
    return LabelingConfig(
        delay_high_minutes=float(labeling.get("delay_high_minutes", 5)),
        speed_high_kmh=float(labeling.get("speed_high_kmh", 90)),
        speed_low_kmh=float(labeling.get("speed_low_kmh", 10)),
        conflict_proximity_km=float(labeling.get("conflict_proximity_km", 1.0)),
        conflict_congestion_count=int(labeling.get("conflict_congestion_count", 3)),
    )


def train_features_from_row(row: dict) -> Dict[str, Any]:
    """
    Features minimales, stables et compatibles sklearn DictVectorizer.
    """
    return {
        "speed": safe_float(row.get("speed")) or 0.0,
        "delay": safe_float(row.get("delay")) or 0.0,
        "status": (row.get("status") or "unknown").strip().lower(),
        "country": (row.get("country") or "unknown").strip(),
        "nearest_train_km": safe_float(row.get("nearest_train_km")) or 0.0,
        "nearby_trains": safe_int(row.get("nearby_trains")) or 0,
        "has_conflict": 1 if row.get("has_conflict") else 0,
        "conflict_type": (row.get("conflict_type") or "none").strip().lower(),
    }


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Distance en km entre deux points (lat/lon en degrés).
    """
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def add_conflict_features(rows: List[dict], cfg: LabelingConfig) -> List[dict]:
    """
    Calcule des features de conflit à l'échelle d'un snapshot:
    - nearest_train_km: distance min à un autre train (même snapshot)
    - nearby_trains: nb de trains dans un rayon conflict_proximity_km
    - has_conflict/conflict_type: dérivés des seuils
    """
    enriched = [dict(r) for r in rows]

    positions: List[Tuple[int, float, float]] = []
    for idx, row in enumerate(enriched):
        lat = safe_float(row.get("lat"))
        lng = safe_float(row.get("lng"))
        if lat is None or lng is None:
            continue
        positions.append((idx, lat, lng))

    for idx, lat, lng in positions:
        min_km: Optional[float] = None
        nearby = 0
        for jdx, lat2, lng2 in positions:
            if jdx == idx:
                continue
            d = haversine_km(lat, lng, lat2, lng2)
            if min_km is None or d < min_km:
                min_km = d
            if d <= cfg.conflict_proximity_km:
                nearby += 1

        enriched[idx]["nearest_train_km"] = min_km
        enriched[idx]["nearby_trains"] = nearby

        if min_km is not None and min_km <= cfg.conflict_proximity_km:
            enriched[idx]["has_conflict"] = True
            if nearby + 1 >= cfg.conflict_congestion_count:
                enriched[idx]["conflict_type"] = "congestion_conflict"
            else:
                enriched[idx]["conflict_type"] = "proximity_conflict"
        else:
            enriched[idx]["has_conflict"] = False
            enriched[idx]["conflict_type"] = "none"

    return enriched


@dataclass(frozen=True)
class ScheduleConflictConfig:
    platform_window_minutes: float = 5.0
    headway_min_minutes: float = 3.0
    service_gap_minutes: float = 20.0
    capacity_window_minutes: float = 10.0
    capacity_threshold_trips: int = 5
    delay_propagation_minutes: float = 5.0
    transfer_min_minutes: float = 3.0
    transfer_max_minutes: float = 15.0
    schedule_coverage_ratio_min: float = 0.7


SCHEDULE_CONFLICT_LABELS: Tuple[str, ...] = (
    "normal",
    "platform_conflict",
    "headway_conflict",
    "delay_propagation_conflict",
    "capacity_congestion_conflict",
    "service_gap_conflict",
    "schedule_inconsistency_conflict",
    "transfer_timing_conflict",
)


SCHEDULE_CONFLICT_PRIORITY: Tuple[str, ...] = (
    "platform_conflict",
    "headway_conflict",
    "delay_propagation_conflict",
    "capacity_congestion_conflict",
    "service_gap_conflict",
    "schedule_inconsistency_conflict",
    "transfer_timing_conflict",
)


@dataclass(frozen=True)
class NetworkConflictConfig:
    min_conflict_trains: int = 2
    delay_high_minutes: float = 5.0
    anomaly_ratio_threshold: float = 0.3
    conflict_ratio_threshold: float = 0.2


NETWORK_CONFLICT_LABELS: Tuple[str, ...] = (
    "normal",
    "network_congestion_conflict",
    "network_proximity_conflict",
    "network_delay_conflict",
    "network_anomaly_spike",
)


NETWORK_CONFLICT_PRIORITY: Tuple[str, ...] = (
    "network_congestion_conflict",
    "network_proximity_conflict",
    "network_delay_conflict",
    "network_anomaly_spike",
)


def load_schedule_conflict_config(cfg: dict) -> ScheduleConflictConfig:
    sc = cfg.get("schedule_conflicts") or {}
    return ScheduleConflictConfig(
        platform_window_minutes=float(sc.get("platform_window_minutes", 5)),
        headway_min_minutes=float(sc.get("headway_min_minutes", 3)),
        service_gap_minutes=float(sc.get("service_gap_minutes", 20)),
        capacity_window_minutes=float(sc.get("capacity_window_minutes", 10)),
        capacity_threshold_trips=int(sc.get("capacity_threshold_trips", 5)),
        delay_propagation_minutes=float(sc.get("delay_propagation_minutes", 5)),
        transfer_min_minutes=float(sc.get("transfer_min_minutes", 3)),
        transfer_max_minutes=float(sc.get("transfer_max_minutes", 15)),
        schedule_coverage_ratio_min=float(sc.get("schedule_coverage_ratio_min", 0.7)),
    )


def load_network_conflict_config(cfg: dict) -> NetworkConflictConfig:
    nc = cfg.get("network_conflicts") or {}
    return NetworkConflictConfig(
        min_conflict_trains=int(nc.get("min_conflict_trains", 2)),
        delay_high_minutes=float(nc.get("delay_high_minutes", 5)),
        anomaly_ratio_threshold=float(nc.get("anomaly_ratio_threshold", 0.3)),
        conflict_ratio_threshold=float(nc.get("conflict_ratio_threshold", 0.2)),
    )


def parse_time_to_minutes(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return safe_int(value)
    text = str(value).strip()
    if not text:
        return None
    if "T" in text and ":" in text:
        text = text.split("T")[-1]
    if "Z" in text:
        text = text.replace("Z", "")
    if "+" in text:
        text = text.split("+")[0]
    parts = text.split(":")
    if len(parts) == 1:
        return safe_int(parts[0])
    try:
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        second = int(parts[2]) if len(parts) > 2 else 0
    except ValueError:
        return None
    return int(hour * 60 + minute + round(second / 60))


def _first_value(record: dict, keys: Iterable[str]) -> Optional[Any]:
    for key in keys:
        if key in record and record[key] not in (None, ""):
            return record[key]
    return None


def _nested_onestop_id(record: dict, key: str) -> Optional[str]:
    value = record.get(key)
    if isinstance(value, dict):
        return value.get("onestop_id") or value.get("stop_onestop_id")
    return None


def extract_schedule_stop_pairs(payload: Any) -> List[dict]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("schedule_stop_pairs", "schedule_stop_pair", "items", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            for sub_key in ("schedule_stop_pairs", "items", "data"):
                sub_value = value.get(sub_key)
                if isinstance(sub_value, list):
                    return sub_value
    return []


def normalize_schedule_record(record: dict) -> dict:
    origin_id = _first_value(record, ["origin_onestop_id", "origin_stop_onestop_id", "stop_onestop_id"])
    origin_id = origin_id or _nested_onestop_id(record, "origin_stop")
    destination_id = _first_value(record, ["destination_onestop_id", "destination_stop_onestop_id"])
    destination_id = destination_id or _nested_onestop_id(record, "destination_stop")

    route_id = _first_value(record, ["route_onestop_id", "route_id", "route_onestopid"])
    trip_id = _first_value(record, ["trip_onestop_id", "trip_id"])
    direction_id = _first_value(record, ["direction_id", "trip_direction_id", "route_direction_id"])
    service_date = _first_value(record, ["service_date", "date", "service_day"])

    departure_time = _first_value(
        record,
        ["origin_departure_time", "departure_time", "depart_time", "scheduled_departure_time"],
    )
    arrival_time = _first_value(
        record,
        ["destination_arrival_time", "arrival_time", "arrive_time", "scheduled_arrival_time"],
    )

    return {
        "service_date": service_date,
        "origin_onestop_id": origin_id,
        "destination_onestop_id": destination_id,
        "route_onestop_id": route_id,
        "trip_onestop_id": trip_id,
        "direction_id": direction_id,
        "departure_time": departure_time,
        "arrival_time": arrival_time,
        "departure_minutes": parse_time_to_minutes(departure_time),
        "arrival_minutes": parse_time_to_minutes(arrival_time),
        "platform_code": _first_value(record, ["platform_code", "platform_id", "platform"]),
        "raw_record": record,
    }


def extract_delay_minutes(record: dict) -> Optional[float]:
    delay = _first_value(
        record,
        [
            "delay_minutes",
            "delay",
            "departure_delay",
            "arrival_delay",
            "origin_departure_delay",
            "destination_arrival_delay",
        ],
    )
    if delay is not None:
        return safe_float(delay)

    scheduled = _first_value(record, ["scheduled_departure_time", "scheduled_arrival_time"])
    realtime = _first_value(record, ["realtime_departure_time", "realtime_arrival_time"])
    if scheduled and realtime:
        sched_min = parse_time_to_minutes(scheduled)
        real_min = parse_time_to_minutes(realtime)
        if sched_min is not None and real_min is not None:
            return float(real_min - sched_min)
    return None


def add_schedule_features(rows: List[dict]) -> List[dict]:
    """
    Compute headway features for route/direction groups.
    """
    enriched = [dict(r) for r in rows]
    group_map: Dict[Tuple[Optional[str], Optional[str]], List[Tuple[int, int]]] = {}

    for idx, row in enumerate(enriched):
        route_id = row.get("route_onestop_id")
        direction_id = row.get("direction_id")
        dep_min = row.get("departure_minutes")
        if dep_min is None:
            continue
        key = (route_id, direction_id)
        group_map.setdefault(key, []).append((idx, dep_min))

    for entries in group_map.values():
        entries.sort(key=lambda x: x[1])
        for pos, (idx, dep_min) in enumerate(entries):
            prev_min = entries[pos - 1][1] if pos > 0 else None
            next_min = entries[pos + 1][1] if pos + 1 < len(entries) else None
            enriched[idx]["headway_prev_minutes"] = None if prev_min is None else dep_min - prev_min
            enriched[idx]["headway_next_minutes"] = None if next_min is None else next_min - dep_min

    return enriched


def _ensure_conflict_flags(row: dict) -> None:
    if "conflict_flags" not in row or row["conflict_flags"] is None:
        row["conflict_flags"] = set()
    elif not isinstance(row["conflict_flags"], set):
        row["conflict_flags"] = set(row["conflict_flags"])


def detect_platform_conflicts(rows: List[dict], cfg: ScheduleConflictConfig) -> None:
    events_by_stop: Dict[str, List[Tuple[int, int]]] = {}
    for idx, row in enumerate(rows):
        origin_id = row.get("origin_onestop_id")
        dep_min = row.get("departure_minutes")
        if origin_id and dep_min is not None:
            events_by_stop.setdefault(origin_id, []).append((idx, dep_min))
        dest_id = row.get("destination_onestop_id")
        arr_min = row.get("arrival_minutes")
        if dest_id and arr_min is not None:
            events_by_stop.setdefault(dest_id, []).append((idx, arr_min))

    for events in events_by_stop.values():
        events.sort(key=lambda x: x[1])
        for i in range(1, len(events)):
            prev_idx, prev_time = events[i - 1]
            curr_idx, curr_time = events[i]
            if curr_time - prev_time <= cfg.platform_window_minutes:
                _ensure_conflict_flags(rows[prev_idx])
                _ensure_conflict_flags(rows[curr_idx])
                rows[prev_idx]["conflict_flags"].add("platform_conflict")
                rows[curr_idx]["conflict_flags"].add("platform_conflict")


def detect_headway_conflicts(rows: List[dict], cfg: ScheduleConflictConfig) -> None:
    group_map: Dict[Tuple[Optional[str], Optional[str]], List[Tuple[int, int]]] = {}
    for idx, row in enumerate(rows):
        dep_min = row.get("departure_minutes")
        if dep_min is None:
            continue
        key = (row.get("route_onestop_id"), row.get("direction_id"))
        group_map.setdefault(key, []).append((idx, dep_min))

    for entries in group_map.values():
        entries.sort(key=lambda x: x[1])
        for i in range(1, len(entries)):
            prev_idx, prev_time = entries[i - 1]
            curr_idx, curr_time = entries[i]
            if curr_time - prev_time <= cfg.headway_min_minutes:
                _ensure_conflict_flags(rows[prev_idx])
                _ensure_conflict_flags(rows[curr_idx])
                rows[prev_idx]["conflict_flags"].add("headway_conflict")
                rows[curr_idx]["conflict_flags"].add("headway_conflict")


def detect_service_gap_conflicts(rows: List[dict], cfg: ScheduleConflictConfig) -> None:
    group_map: Dict[Tuple[Optional[str], Optional[str]], List[Tuple[int, int]]] = {}
    for idx, row in enumerate(rows):
        dep_min = row.get("departure_minutes")
        if dep_min is None:
            continue
        key = (row.get("route_onestop_id"), row.get("direction_id"))
        group_map.setdefault(key, []).append((idx, dep_min))

    for entries in group_map.values():
        entries.sort(key=lambda x: x[1])
        for i in range(1, len(entries)):
            prev_idx, prev_time = entries[i - 1]
            curr_idx, curr_time = entries[i]
            if curr_time - prev_time >= cfg.service_gap_minutes:
                _ensure_conflict_flags(rows[curr_idx])
                rows[curr_idx]["conflict_flags"].add("service_gap_conflict")


def detect_capacity_congestion(rows: List[dict], cfg: ScheduleConflictConfig) -> None:
    segment_map: Dict[Tuple[Optional[str], Optional[str], Optional[str]], List[Tuple[int, int]]] = {}
    for idx, row in enumerate(rows):
        dep_min = row.get("departure_minutes")
        if dep_min is None:
            continue
        key = (row.get("route_onestop_id"), row.get("origin_onestop_id"), row.get("destination_onestop_id"))
        segment_map.setdefault(key, []).append((idx, dep_min))

    for entries in segment_map.values():
        entries.sort(key=lambda x: x[1])
        start = 0
        for end in range(len(entries)):
            while entries[end][1] - entries[start][1] > cfg.capacity_window_minutes:
                start += 1
            window_size = end - start + 1
            if window_size >= cfg.capacity_threshold_trips:
                for pos in range(start, end + 1):
                    idx = entries[pos][0]
                    _ensure_conflict_flags(rows[idx])
                    rows[idx]["conflict_flags"].add("capacity_congestion_conflict")
                    rows[idx]["capacity_window_count"] = window_size


def detect_delay_propagation(rows: List[dict], cfg: ScheduleConflictConfig) -> None:
    for row in rows:
        delay_min = row.get("delay_minutes")
        if delay_min is None:
            record = row.get("raw_record") or {}
            delay_min = extract_delay_minutes(record)
            row["delay_minutes"] = delay_min
        if delay_min is not None and delay_min >= cfg.delay_propagation_minutes:
            _ensure_conflict_flags(row)
            row["conflict_flags"].add("delay_propagation_conflict")


def detect_schedule_inconsistency(rows: List[dict], cfg: ScheduleConflictConfig) -> None:
    route_trip_stops: Dict[Tuple[Optional[str], Optional[str]], set] = {}
    route_max_stops: Dict[Optional[str], int] = {}

    for row in rows:
        route_id = row.get("route_onestop_id")
        trip_id = row.get("trip_onestop_id")
        if not route_id or not trip_id:
            continue
        key = (route_id, trip_id)
        stops = route_trip_stops.setdefault(key, set())
        if row.get("origin_onestop_id"):
            stops.add(row["origin_onestop_id"])
        if row.get("destination_onestop_id"):
            stops.add(row["destination_onestop_id"])

    for (route_id, _trip_id), stops in route_trip_stops.items():
        count = len(stops)
        route_max_stops[route_id] = max(route_max_stops.get(route_id, 0), count)

    for row in rows:
        route_id = row.get("route_onestop_id")
        trip_id = row.get("trip_onestop_id")
        if not route_id or not trip_id:
            continue
        stops = route_trip_stops.get((route_id, trip_id))
        max_stops = route_max_stops.get(route_id)
        if not stops or not max_stops:
            continue
        coverage = len(stops) / max_stops if max_stops > 0 else 1.0
        row["schedule_coverage_ratio"] = coverage
        if coverage < cfg.schedule_coverage_ratio_min:
            _ensure_conflict_flags(row)
            row["conflict_flags"].add("schedule_inconsistency_conflict")


def detect_transfer_timing(rows: List[dict], cfg: ScheduleConflictConfig) -> None:
    arrivals_by_stop: Dict[str, List[Tuple[int, int, Optional[str]]]] = {}
    departures_by_stop: Dict[str, List[Tuple[int, int, Optional[str]]]] = {}

    for idx, row in enumerate(rows):
        dest_id = row.get("destination_onestop_id")
        arr_min = row.get("arrival_minutes")
        if dest_id and arr_min is not None:
            arrivals_by_stop.setdefault(dest_id, []).append((idx, arr_min, row.get("route_onestop_id")))

        origin_id = row.get("origin_onestop_id")
        dep_min = row.get("departure_minutes")
        if origin_id and dep_min is not None:
            departures_by_stop.setdefault(origin_id, []).append((idx, dep_min, row.get("route_onestop_id")))

    for stop_id, arrivals in arrivals_by_stop.items():
        departures = departures_by_stop.get(stop_id, [])
        if not departures:
            for idx, _arr_min, _route_id in arrivals:
                _ensure_conflict_flags(rows[idx])
                rows[idx]["conflict_flags"].add("transfer_timing_conflict")
            continue

        departures.sort(key=lambda x: x[1])
        for idx, arr_min, route_id in arrivals:
            best_delta = None
            for _d_idx, dep_min, dep_route_id in departures:
                if dep_min < arr_min:
                    continue
                if dep_route_id == route_id:
                    continue
                delta = dep_min - arr_min
                best_delta = delta
                break
            if best_delta is None:
                _ensure_conflict_flags(rows[idx])
                rows[idx]["conflict_flags"].add("transfer_timing_conflict")
                continue
            if best_delta < cfg.transfer_min_minutes or best_delta > cfg.transfer_max_minutes:
                _ensure_conflict_flags(rows[idx])
                rows[idx]["conflict_flags"].add("transfer_timing_conflict")


def apply_schedule_conflict_detection(rows: List[dict], cfg: ScheduleConflictConfig) -> List[dict]:
    detect_platform_conflicts(rows, cfg)
    detect_headway_conflicts(rows, cfg)
    detect_delay_propagation(rows, cfg)
    detect_capacity_congestion(rows, cfg)
    detect_service_gap_conflicts(rows, cfg)
    detect_schedule_inconsistency(rows, cfg)
    detect_transfer_timing(rows, cfg)
    return rows


def assign_conflict_label(row: dict) -> str:
    flags = row.get("conflict_flags") or set()
    if not isinstance(flags, set):
        flags = set(flags)
    for label in SCHEDULE_CONFLICT_PRIORITY:
        if label in flags:
            return label
    return "normal"
