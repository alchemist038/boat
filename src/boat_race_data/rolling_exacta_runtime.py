from __future__ import annotations

import csv
import math
from datetime import date
from pathlib import Path
from typing import Any

A_CLASSES = {"A1", "A2"}
STAKE_YEN = 100


def maybe_float(value: Any) -> float | None:
    if value in {"", None}:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(parsed):
        return None
    return parsed


def maybe_int(value: Any) -> int | None:
    if value in {"", None}:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(parsed):
        return None
    return int(parsed)


def normalize_combo(value: Any) -> str:
    return str(value or "").replace(" ", "")


def class_group(value: Any) -> str:
    text = str(value or "missing")
    if text in A_CLASSES:
        return "A"
    if text in {"B1", "B2"}:
        return "B"
    return "missing"


def bucket_rank(value: Any) -> str:
    parsed = maybe_int(value)
    if parsed is None:
        return "missing"
    if parsed == 1:
        return "1"
    if parsed == 2:
        return "2"
    if parsed == 3:
        return "3"
    return "4+"


def bucket_rank_with_source(rank_value: Any, source_value: Any) -> str:
    if maybe_float(source_value) is None:
        return "missing"
    return bucket_rank(rank_value)


def bucket_count(value: Any) -> str:
    parsed = maybe_int(value)
    if parsed is None:
        return "missing"
    return str(parsed)


def bucket_numeric(value: Any, cuts: list[float], labels: list[str]) -> str:
    number = maybe_float(value)
    if number is None:
        return "missing"
    for cut, label in zip(cuts, labels, strict=False):
        if number <= cut:
            return label
    return labels[-1]


def bucket_rate(value: Any) -> str:
    return bucket_numeric(value, [4.50, 5.50, 6.50], ["<=4.50", "4.51-5.50", "5.51-6.50", "6.51+"])


def bucket_place_rate(value: Any) -> str:
    return bucket_numeric(value, [25.0, 35.0, 45.0], ["<=25", "25.1-35", "35.1-45", "45.1+"])


def bucket_rate_diff(value: Any) -> str:
    number = maybe_float(value)
    if number is None:
        return "missing"
    if number <= -1.00:
        return "target_plus_1.00+"
    if number <= -0.35:
        return "target_plus_0.35_1.00"
    if number < 0.35:
        return "near_equal"
    if number < 1.00:
        return "lane1_plus_0.35_1.00"
    return "lane1_plus_1.00+"


def bucket_place_diff(value: Any) -> str:
    number = maybe_float(value)
    if number is None:
        return "missing"
    if number <= -10.0:
        return "target_plus_10+"
    if number <= -4.0:
        return "target_plus_4_10"
    if number < 4.0:
        return "near_equal"
    if number < 10.0:
        return "lane1_plus_4_10"
    return "lane1_plus_10+"


def bucket_time_diff(value: Any, *, tight: float, wide: float) -> str:
    number = maybe_float(value)
    if number is None:
        return "missing"
    if number <= -wide:
        return f"lane1_faster_{wide:.2f}+"
    if number <= -tight:
        return f"lane1_faster_{tight:.2f}_{wide:.2f}"
    if number < tight:
        return "near_equal"
    if number < wide:
        return f"target_faster_{tight:.2f}_{wide:.2f}"
    return f"target_faster_{wide:.2f}+"


def lane_zone(lane: int) -> str:
    if lane in {2, 3}:
        return "inner_partner"
    if lane in {4, 5}:
        return "center_outer"
    return "outermost"


def infer_grade_group(meeting_title: Any) -> str:
    text = str(meeting_title or "")
    upper = text.upper()
    if "SG" in upper or "ＳＧ" in text:
        return "SG"
    if "G1" in upper or "Ｇ１" in text or "GⅠ" in upper or "ＧⅠ" in text:
        return "G1"
    if "G2" in upper or "Ｇ２" in text or "GⅡ" in upper or "ＧⅡ" in text:
        return "G2"
    if "G3" in upper or "Ｇ３" in text or "GⅢ" in upper or "ＧⅢ" in text:
        return "G3"
    return "一般"


def _entry_by_lane(rows: list[dict[str, object]], lane: int) -> dict[str, object] | None:
    for row in rows:
        if int(row.get("lane", 0) or 0) == lane:
            return row
    return None


def _rank_lanes(values: dict[int, float | None], *, ascending: bool) -> dict[int, int | None]:
    present = [(lane, value) for lane, value in values.items() if value is not None]
    present.sort(key=lambda item: (item[1], item[0]), reverse=not ascending)
    if not ascending:
        # Reverse=True also reverses lane order; keep lane ASC as the SQL tie-breaker.
        present.sort(key=lambda item: (-float(item[1]), item[0]))
    ranks: dict[int, int | None] = {lane: None for lane in values}
    for index, (lane, _) in enumerate(present, start=1):
        ranks[lane] = index
    return ranks


def _subtract(left: Any, right: Any) -> float | None:
    left_float = maybe_float(left)
    right_float = maybe_float(right)
    if left_float is None or right_float is None:
        return None
    return round(left_float - right_float, 3)


def _gt_count(values: list[Any], threshold: Any) -> int:
    threshold_float = maybe_float(threshold)
    if threshold_float is None:
        return 0
    return sum(1 for value in values if maybe_float(value) is not None and float(value) > threshold_float)


def _lt_count(values: list[Any], threshold: Any) -> int:
    threshold_float = maybe_float(threshold)
    if threshold_float is None:
        return 0
    return sum(1 for value in values if maybe_float(value) is not None and float(value) < threshold_float)


def _meeting_phase_bucket(row: dict[str, object]) -> str:
    if int(row.get("is_final_day", 0) or 0) == 1:
        return "final"
    day_no = maybe_int(row.get("meeting_day_no"))
    if day_no is None:
        return "unknown"
    if 1 <= day_no <= 2:
        return "day1-2"
    if 3 <= day_no <= 4:
        return "day3-4"
    if day_no >= 5:
        return "day5+"
    return "unknown"


def build_watchlist_row(
    race_row: dict[str, object],
    entry_rows: list[dict[str, object]],
    profile_data: dict[str, Any],
) -> dict[str, object] | None:
    if len(entry_rows) < 6:
        return None
    deadline_time = str(race_row.get("deadline_time", "") or "")
    if not deadline_time:
        return None

    watch_minutes = int(profile_data.get("watch_minutes_before_deadline", 25))
    race_date = str(race_row.get("race_date", ""))
    row: dict[str, object] = {
        "box_id": str(profile_data.get("box_id", "rolling_1x")),
        "profile_id": str(profile_data.get("profile_id", "rolling_1x_12_13_train3m_v1")),
        "strategy_id": str(profile_data.get("strategy_id", "rolling_exacta_1x")),
        "race_id": str(race_row.get("race_id", "")),
        "race_date": race_date,
        "stadium_code": str(race_row.get("stadium_code", "")),
        "stadium_name": str(race_row.get("stadium_name", "")),
        "race_no": int(race_row.get("race_no", 0) or 0),
        "meeting_title": str(race_row.get("meeting_title", "")),
        "race_title": str(race_row.get("race_title", "")),
        "grade": str(race_row.get("grade") or infer_grade_group(race_row.get("meeting_title", ""))),
        "meeting_day_no": "" if race_row.get("meeting_day_no") is None else int(race_row.get("meeting_day_no") or 0),
        "meeting_day_label": str(race_row.get("meeting_day_label", "")),
        "is_final_day": int(race_row.get("is_final_day", 0) or 0),
        "deadline_time": deadline_time,
        "watch_start_time": _compute_watch_start_time(race_date, deadline_time, watch_minutes),
        "status": "waiting_beforeinfo",
        "pre_reason": "rolling exacta 1-2/1-3 candidate watch",
        "final_reason": "",
        "selected_combos": [],
        "rolling_selected_combos": [],
        "rolling_matched_logic_ids": [],
        "real_allowed_from": str(profile_data.get("real_allowed_from", "") or ""),
    }
    entry_map = {int(entry.get("lane", 0) or 0): entry for entry in entry_rows}
    for lane in range(1, 7):
        entry = entry_map.get(lane, {})
        for key in (
            "racer_id",
            "racer_name",
            "racer_class",
            "age",
            "weight_kg",
            "f_count",
            "l_count",
            "avg_start_timing",
            "national_win_rate",
            "national_place_rate",
            "national_top3_rate",
            "local_win_rate",
            "local_place_rate",
            "local_top3_rate",
            "motor_place_rate",
            "motor_top3_rate",
            "boat_place_rate",
            "boat_top3_rate",
        ):
            row[f"lane{lane}_{key}"] = entry.get(key, "")
    return row


def _compute_watch_start_time(race_date: str, deadline_time: str, minutes_before: int) -> str:
    from datetime import datetime, timedelta

    try:
        deadline = datetime.strptime(f"{race_date} {deadline_time}", "%Y-%m-%d %H:%M")
    except ValueError:
        try:
            deadline = datetime.strptime(f"{race_date} {deadline_time}", "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return ""
    return (deadline - timedelta(minutes=minutes_before)).strftime("%Y-%m-%d %H:%M:%S")


def resolve_candidate_path(profile_data: dict[str, Any], repo_root: Path, race_date: str) -> Path | None:
    race_day = date.fromisoformat(str(race_date))
    for window in profile_data.get("candidate_windows", []) or []:
        try:
            valid_from = date.fromisoformat(str(window.get("valid_from")))
            valid_to = date.fromisoformat(str(window.get("valid_to")))
        except (TypeError, ValueError):
            continue
        if valid_from <= race_day <= valid_to:
            raw_path = str(window.get("path", "") or "")
            return _resolve_path(raw_path, repo_root)
    raw_path = str(profile_data.get("candidate_path", "") or "")
    return _resolve_path(raw_path, repo_root) if raw_path else None


def _resolve_path(raw_path: str, repo_root: Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return repo_root / path


def load_candidates(path: Path, allowed_combos: set[str]) -> list[dict[str, str]]:
    if not path.exists():
        return []
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            combo = normalize_combo(row.get("combo"))
            if allowed_combos and combo not in allowed_combos:
                continue
            slice_family = str(row.get("slice_family", "") or "")
            slice_value = str(row.get("slice_value", "") or "")
            if not combo or not slice_family:
                continue
            rows.append(
                {
                    "combo": combo,
                    "slice_family": slice_family,
                    "slice_value": slice_value,
                    "logic_id": str(row.get("logic_id", "") or ""),
                    "train_sample_races": str(row.get("sample_races", "") or ""),
                    "train_roi_pct": str(row.get("roi_pct", "") or ""),
                }
            )
    return rows


def _base_features(row: dict[str, object], beforeinfo_rows: list[dict[str, object]]) -> dict[str, object] | None:
    beforeinfo_by_lane = {int(item.get("lane", 0) or 0): item for item in beforeinfo_rows}
    if not beforeinfo_by_lane:
        return None

    features: dict[str, object] = {
        "month": str(row.get("race_date", ""))[:7],
        "stadium_code": str(row.get("stadium_code", "")),
        "race_no": str(row.get("race_no", "")),
        "grade_group": str(row.get("grade") or infer_grade_group(row.get("meeting_title", ""))),
        "meeting_phase_bucket": _meeting_phase_bucket(row),
    }
    race_no = maybe_int(row.get("race_no"))
    if race_no is None:
        features["race_no_bucket"] = "missing"
    elif race_no <= 3:
        features["race_no_bucket"] = "1-3R"
    elif race_no <= 6:
        features["race_no_bucket"] = "4-6R"
    elif race_no <= 9:
        features["race_no_bucket"] = "7-9R"
    else:
        features["race_no_bucket"] = "10-12R"

    weather_source = beforeinfo_by_lane.get(1, next(iter(beforeinfo_by_lane.values())))
    features["weather_group"] = str(weather_source.get("weather_condition", "") or "missing")
    wind_speed = maybe_float(weather_source.get("wind_speed_m"))
    wave_height = maybe_float(weather_source.get("wave_height_cm"))
    features["wind_bucket"] = bucket_numeric(wind_speed, [2, 4, 6], ["0-2", "3-4", "5-6", "7+"])
    features["wave_bucket"] = bucket_numeric(wave_height, [4, 9], ["0-4", "5-9", "10+"])

    numeric_sources = {
        "national_win_rank": ("national_win_rate", False),
        "national_place_rank": ("national_place_rate", False),
        "local_win_rank": ("local_win_rate", False),
        "local_place_rank": ("local_place_rate", False),
        "motor_rank": ("motor_place_rate", False),
        "boat_rank": ("boat_place_rate", False),
        "avg_start_rank": ("avg_start_timing", True),
        "exhibition_rank": ("exhibition_time", True),
        "exhibition_st_rank": ("start_exhibition_st", True),
    }
    source_values: dict[str, dict[int, float | None]] = {}
    for source, _ in numeric_sources.values():
        source_values[source] = {}
    for lane in range(1, 7):
        for source in (
            "national_win_rate",
            "national_place_rate",
            "local_win_rate",
            "local_place_rate",
            "motor_place_rate",
            "boat_place_rate",
            "avg_start_timing",
        ):
            source_values[source][lane] = maybe_float(row.get(f"lane{lane}_{source}"))
        beforeinfo = beforeinfo_by_lane.get(lane, {})
        source_values["exhibition_time"][lane] = maybe_float(beforeinfo.get("exhibition_time"))
        source_values["start_exhibition_st"][lane] = maybe_float(beforeinfo.get("start_exhibition_st"))

    ranks = {
        rank_name: _rank_lanes(source_values[source_name], ascending=ascending)
        for rank_name, (source_name, ascending) in numeric_sources.items()
    }
    exhibition_values = [value for value in source_values["exhibition_time"].values() if value is not None]
    start_values = [value for value in source_values["start_exhibition_st"].values() if value is not None]
    if not exhibition_values or not start_values:
        return None
    best_exhibition_time = min(exhibition_values)
    best_start_st = min(start_values)

    for lane in range(1, 7):
        racer_class = str(row.get(f"lane{lane}_racer_class", "") or "missing")
        features[f"lane{lane}_class"] = racer_class
        features[f"lane{lane}_class_group"] = class_group(racer_class)
        for rank_name, (source_name, _) in numeric_sources.items():
            features[f"lane{lane}_{rank_name}"] = ranks[rank_name][lane]
            features[f"lane{lane}_{rank_name}_bucket"] = bucket_rank_with_source(
                ranks[rank_name][lane],
                source_values[source_name][lane],
            )
        for rate_col in ("national_win_rate", "local_win_rate"):
            value = maybe_float(row.get(f"lane{lane}_{rate_col}"))
            features[f"lane{lane}_{rate_col}"] = value
            features[f"lane{lane}_{rate_col}_bucket"] = bucket_rate(value)
        for place_col in ("motor_place_rate", "boat_place_rate", "national_place_rate", "local_place_rate"):
            value = maybe_float(row.get(f"lane{lane}_{place_col}"))
            features[f"lane{lane}_{place_col}"] = value
            features[f"lane{lane}_{place_col}_bucket"] = bucket_place_rate(value)
        exhibition_time = source_values["exhibition_time"][lane]
        start_st = source_values["start_exhibition_st"][lane]
        features[f"lane{lane}_exhibition_time"] = exhibition_time
        features[f"lane{lane}_start_exhibition_st"] = start_st
        exhibition_gap = None if exhibition_time is None else round(float(exhibition_time) - best_exhibition_time, 3)
        start_gap = None if start_st is None else round(float(start_st) - best_start_st, 3)
        features[f"lane{lane}_exhibition_gap"] = exhibition_gap
        features[f"lane{lane}_exhibition_gap_bucket"] = bucket_numeric(
            exhibition_gap,
            [0.00, 0.05, 0.10],
            ["best", "<=0.05", "0.06-0.10", ">0.10"],
        )
        features[f"lane{lane}_start_exhibition_gap"] = start_gap
        features[f"lane{lane}_start_exhibition_gap_bucket"] = bucket_numeric(
            start_gap,
            [0.00, 0.03, 0.06],
            ["best", "<=0.03", "0.04-0.06", ">0.06"],
        )
    return features


def _target_features(base: dict[str, object], target_lane: int) -> dict[str, str]:
    features = dict(base)
    combo = f"1-{target_lane}"
    other_lanes = [lane for lane in range(2, 7) if lane != target_lane]
    features["combo"] = combo
    features["target_lane"] = str(target_lane)
    features["target_lane_zone"] = lane_zone(target_lane)

    for suffix in (
        "class",
        "class_group",
        "national_win_rank_bucket",
        "national_place_rank_bucket",
        "local_win_rank_bucket",
        "local_place_rank_bucket",
        "motor_rank_bucket",
        "boat_rank_bucket",
        "avg_start_rank_bucket",
        "exhibition_rank_bucket",
        "exhibition_st_rank_bucket",
        "national_win_rate_bucket",
        "local_win_rate_bucket",
        "motor_place_rate_bucket",
        "boat_place_rate_bucket",
        "national_place_rate_bucket",
        "local_place_rate_bucket",
        "exhibition_gap_bucket",
        "start_exhibition_gap_bucket",
    ):
        features[f"target_{suffix}"] = str(features.get(f"lane{target_lane}_{suffix}", "missing"))

    features["lane1_target_class_pair"] = f"{features.get('lane1_class')}-{features['target_class']}"
    features["lane1_target_group_pair"] = f"{features.get('lane1_class_group')}-{features['target_class_group']}"
    features["lane1_target_national_rank_pair"] = (
        f"{features.get('lane1_national_win_rank_bucket')}-{features['target_national_win_rank_bucket']}"
    )
    features["lane1_target_exhibition_st_rank_pair"] = (
        f"{features.get('lane1_exhibition_st_rank_bucket')}-{features['target_exhibition_st_rank_bucket']}"
    )
    features["lane1_target_start_gap_pair"] = (
        f"{features.get('lane1_start_exhibition_gap_bucket')}-{features['target_start_exhibition_gap_bucket']}"
    )

    diff_specs = {
        "national_win": ("national_win_rate", bucket_rate_diff),
        "local_win": ("local_win_rate", bucket_rate_diff),
        "motor_place": ("motor_place_rate", bucket_place_diff),
        "boat_place": ("boat_place_rate", bucket_place_diff),
        "exhibition_time": ("exhibition_time", lambda value: bucket_time_diff(value, tight=0.05, wide=0.10)),
        "start_exhibition_st": ("start_exhibition_st", lambda value: bucket_time_diff(value, tight=0.03, wide=0.06)),
    }
    for prefix, (source, bucket_func) in diff_specs.items():
        diff = _subtract(features.get(f"lane1_{source}"), features.get(f"lane{target_lane}_{source}"))
        features[f"lane1_target_{prefix}_diff"] = diff
        features[f"lane1_target_{prefix}_diff_bucket"] = bucket_func(diff)

    features["other_a_count"] = sum(1 for lane in other_lanes if features.get(f"lane{lane}_class_group") == "A")
    features["other_b2_count"] = sum(1 for lane in other_lanes if features.get(f"lane{lane}_class") == "B2")
    features["other_a_count_bucket"] = bucket_count(features["other_a_count"])
    features["other_b2_count_bucket"] = bucket_count(features["other_b2_count"])
    features["other_group_pattern"] = "-".join(str(features.get(f"lane{lane}_class_group", "missing")) for lane in other_lanes)

    for source_col, target_col in (
        ("national_win_rate", "other_national_better_than_target_count"),
        ("local_win_rate", "other_local_better_than_target_count"),
        ("motor_place_rate", "other_motor_better_than_target_count"),
        ("boat_place_rate", "other_boat_better_than_target_count"),
    ):
        values = [features.get(f"lane{lane}_{source_col}") for lane in other_lanes]
        count = _gt_count(values, features.get(f"lane{target_lane}_{source_col}"))
        features[target_col] = count
        features[f"{target_col}_bucket"] = bucket_count(count)

    exhibition_count = _lt_count(
        [features.get(f"lane{lane}_exhibition_time") for lane in other_lanes],
        features.get(f"lane{target_lane}_exhibition_time"),
    )
    st_count = _lt_count(
        [features.get(f"lane{lane}_start_exhibition_st") for lane in other_lanes],
        features.get(f"lane{target_lane}_start_exhibition_st"),
    )
    features["other_exhibition_faster_than_target_count"] = exhibition_count
    features["other_st_faster_than_target_count"] = st_count
    features["other_exhibition_faster_than_target_count_bucket"] = bucket_count(exhibition_count)
    features["other_st_faster_than_target_count_bucket"] = bucket_count(st_count)

    national_pressure = int(features["other_national_better_than_target_count"])
    exhibition_pressure = int(features["other_exhibition_faster_than_target_count"])
    if national_pressure >= 2 or exhibition_pressure >= 2:
        features["target_outer_pressure_bucket"] = "high_other_pressure"
    elif national_pressure == 1 or exhibition_pressure == 1:
        features["target_outer_pressure_bucket"] = "some_other_pressure"
    else:
        features["target_outer_pressure_bucket"] = "low_other_pressure"
    return {key: str(value) for key, value in features.items()}


def _candidate_matches(features: dict[str, str], candidate: dict[str, str]) -> bool:
    family = str(candidate["slice_family"])
    value = str(candidate["slice_value"])
    if " x " not in family:
        return features.get(family) == value
    if " | " not in value:
        return False
    left, right = family.split(" x ", 1)
    left_value, right_value = value.split(" | ", 1)
    return features.get(left) == left_value and features.get(right) == right_value


def evaluate_row(
    row: dict[str, object],
    beforeinfo_rows: list[dict[str, object]],
    candidates: list[dict[str, str]],
    *,
    allowed_combos: set[str],
    candidate_path: Path | None,
) -> dict[str, Any]:
    if not candidates:
        row["status"] = "waiting_candidates"
        row["final_reason"] = f"candidate pack missing or empty: {candidate_path or '-'}"
        row["selected_combos"] = []
        row["rolling_selected_combos"] = []
        row["rolling_matched_logic_ids"] = []
        return {"changed": True, "ready": False}

    base = _base_features(row, beforeinfo_rows)
    if base is None:
        row["status"] = "waiting_beforeinfo"
        row["final_reason"] = "beforeinfo not ready"
        row["selected_combos"] = []
        row["rolling_selected_combos"] = []
        row["rolling_matched_logic_ids"] = []
        return {"changed": True, "ready": False}

    by_lane = {lane: _target_features(base, lane) for lane in range(2, 7)}
    selected_combos: list[str] = []
    matched_logic_ids: list[str] = []
    matched_descriptions: list[str] = []
    for index, candidate in enumerate(candidates, start=1):
        combo = normalize_combo(candidate.get("combo"))
        if allowed_combos and combo not in allowed_combos:
            continue
        try:
            target_lane = int(combo.split("-")[1])
        except (IndexError, ValueError):
            continue
        features = by_lane.get(target_lane)
        if features is None:
            continue
        if not _candidate_matches(features, candidate):
            continue
        if combo not in selected_combos:
            selected_combos.append(combo)
        logic_id = candidate.get("logic_id") or f"L{index:02d}"
        matched_logic_ids.append(logic_id)
        matched_descriptions.append(f"{logic_id}:{combo}:{candidate['slice_family']}={candidate['slice_value']}")

    row["selected_combos"] = selected_combos
    row["rolling_selected_combos"] = selected_combos
    row["rolling_matched_logic_ids"] = matched_logic_ids
    row["rolling_match_count"] = len(matched_logic_ids)
    row["rolling_candidate_path"] = "" if candidate_path is None else str(candidate_path)

    if selected_combos:
        row["status"] = "trigger_ready"
        row["final_reason"] = "rolling exacta matched " + ", ".join(matched_descriptions[:6])
        return {"changed": True, "ready": True}

    row["status"] = "filtered_out"
    row["final_reason"] = "rolling exacta no candidate match"
    return {"changed": True, "ready": False}
