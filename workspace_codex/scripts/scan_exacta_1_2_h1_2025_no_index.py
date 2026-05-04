from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import duckdb
import numpy as np
import pandas as pd
from runtime_paths import REPO_ROOT, default_results_db_path


DEFAULT_START_DATE = "2025-01-01"
DEFAULT_END_DATE = "2025-06-30"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "reports" / "strategies" / "exacta_1_2_h1_2025_no_index_slice_scan_20260503"
STAKE_YEN = 100
TARGET_COMBO = "1-2"


def _lane_level_query(start_date: str, end_date: str) -> str:
    return f"""
WITH base AS (
  SELECT
    e.race_id,
    e.race_date,
    e.stadium_code,
    r.stadium_name,
    e.race_no,
    r.race_title,
    rm.grade,
    rm.meeting_day_no,
    rm.meeting_day_label,
    rm.is_final_day,
    e.lane,
    e.racer_class,
    e.age,
    e.weight_kg,
    e.f_count,
    e.l_count,
    e.avg_start_timing,
    e.national_win_rate,
    e.national_place_rate,
    e.national_top3_rate,
    e.local_win_rate,
    e.local_place_rate,
    e.local_top3_rate,
    e.motor_place_rate,
    e.motor_top3_rate,
    e.boat_place_rate,
    e.boat_top3_rate,
    bi.exhibition_time,
    bi.start_exhibition_st,
    COALESCE(bi.wind_speed_m, res.wind_speed_m) AS wind_speed_m,
    COALESCE(bi.wave_height_cm, res.wave_height_cm) AS wave_height_cm,
    COALESCE(bi.weather_condition, res.weather_condition) AS weather_condition,
    res.first_place_lane,
    res.second_place_lane,
    res.exacta_combo,
    CAST(res.exacta_payout AS BIGINT) AS exacta_payout
  FROM entries e
  JOIN races r USING (race_id)
  JOIN results res USING (race_id)
  LEFT JOIN race_meta rm USING (race_id)
  LEFT JOIN beforeinfo_entries bi
    ON bi.race_id = e.race_id
   AND bi.lane = e.lane
  WHERE e.race_date BETWEEN DATE '{start_date}' AND DATE '{end_date}'
),
ranked AS (
  SELECT
    *,
    DENSE_RANK() OVER (
      PARTITION BY race_id
      ORDER BY
        CASE WHEN national_win_rate IS NULL THEN 1 ELSE 0 END,
        national_win_rate DESC,
        lane ASC
    ) AS national_win_rank,
    DENSE_RANK() OVER (
      PARTITION BY race_id
      ORDER BY
        CASE WHEN national_place_rate IS NULL THEN 1 ELSE 0 END,
        national_place_rate DESC,
        lane ASC
    ) AS national_place_rank,
    DENSE_RANK() OVER (
      PARTITION BY race_id
      ORDER BY
        CASE WHEN local_win_rate IS NULL THEN 1 ELSE 0 END,
        local_win_rate DESC,
        lane ASC
    ) AS local_win_rank,
    DENSE_RANK() OVER (
      PARTITION BY race_id
      ORDER BY
        CASE WHEN local_place_rate IS NULL THEN 1 ELSE 0 END,
        local_place_rate DESC,
        lane ASC
    ) AS local_place_rank,
    DENSE_RANK() OVER (
      PARTITION BY race_id
      ORDER BY
        CASE WHEN motor_place_rate IS NULL THEN 1 ELSE 0 END,
        motor_place_rate DESC,
        lane ASC
    ) AS motor_rank,
    DENSE_RANK() OVER (
      PARTITION BY race_id
      ORDER BY
        CASE WHEN boat_place_rate IS NULL THEN 1 ELSE 0 END,
        boat_place_rate DESC,
        lane ASC
    ) AS boat_rank,
    DENSE_RANK() OVER (
      PARTITION BY race_id
      ORDER BY
        CASE WHEN avg_start_timing IS NULL THEN 1 ELSE 0 END,
        avg_start_timing ASC,
        lane ASC
    ) AS avg_start_rank,
    DENSE_RANK() OVER (
      PARTITION BY race_id
      ORDER BY
        CASE WHEN exhibition_time IS NULL THEN 1 ELSE 0 END,
        exhibition_time ASC,
        lane ASC
    ) AS exhibition_rank,
    DENSE_RANK() OVER (
      PARTITION BY race_id
      ORDER BY
        CASE WHEN start_exhibition_st IS NULL THEN 1 ELSE 0 END,
        start_exhibition_st ASC,
        lane ASC
    ) AS exhibition_st_rank,
    MIN(exhibition_time) OVER (PARTITION BY race_id) AS best_exhibition_time,
    MIN(start_exhibition_st) OVER (PARTITION BY race_id) AS best_start_exhibition_st
  FROM base
)
SELECT *
FROM ranked
WHERE exacta_combo IS NOT NULL
  AND exacta_payout IS NOT NULL
  AND first_place_lane IS NOT NULL
  AND second_place_lane IS NOT NULL
QUALIFY COUNT(*) OVER (PARTITION BY race_id) = 6
ORDER BY race_date, race_id, lane
"""


def _normalize_combo(value: object) -> str:
    return str(value or "").replace(" ", "")


def _class_group(value: object) -> str:
    text = str(value or "missing")
    if text in {"A1", "A2"}:
        return "A"
    if text in {"B1", "B2"}:
        return "B"
    return "missing"


def _bucket_rank(value: object) -> str:
    if pd.isna(value):
        return "missing"
    value_int = int(value)
    if value_int == 1:
        return "1"
    if value_int == 2:
        return "2"
    if value_int == 3:
        return "3"
    return "4+"


def _bucket_rank_with_source(rank_value: object, source_value: object) -> str:
    if pd.isna(source_value):
        return "missing"
    return _bucket_rank(rank_value)


def _bucket_count(value: object) -> str:
    if pd.isna(value):
        return "missing"
    return str(int(value))


def _bucket_numeric(value: object, cuts: list[float], labels: list[str]) -> str:
    if pd.isna(value):
        return "missing"
    number = float(value)
    for cut, label in zip(cuts, labels, strict=False):
        if number <= cut:
            return label
    return labels[-1]


def _bucket_rate(value: object) -> str:
    return _bucket_numeric(value, [4.50, 5.50, 6.50], ["<=4.50", "4.51-5.50", "5.51-6.50", "6.51+"])


def _bucket_place_rate(value: object) -> str:
    return _bucket_numeric(value, [25.0, 35.0, 45.0], ["<=25", "25.1-35", "35.1-45", "45.1+"])


def _bucket_lane12_rate_diff(value: object) -> str:
    if pd.isna(value):
        return "missing"
    number = float(value)
    if number <= -1.00:
        return "lane2_plus_1.00+"
    if number <= -0.35:
        return "lane2_plus_0.35_1.00"
    if number < 0.35:
        return "near_equal"
    if number < 1.00:
        return "lane1_plus_0.35_1.00"
    return "lane1_plus_1.00+"


def _bucket_lane12_place_diff(value: object) -> str:
    if pd.isna(value):
        return "missing"
    number = float(value)
    if number <= -10.0:
        return "lane2_plus_10+"
    if number <= -4.0:
        return "lane2_plus_4_10"
    if number < 4.0:
        return "near_equal"
    if number < 10.0:
        return "lane1_plus_4_10"
    return "lane1_plus_10+"


def _bucket_time_diff(value: object, *, tight: float, wide: float) -> str:
    if pd.isna(value):
        return "missing"
    number = float(value)
    if number <= -wide:
        return f"lane1_faster_{wide:.2f}+"
    if number <= -tight:
        return f"lane1_faster_{tight:.2f}_{wide:.2f}"
    if number < tight:
        return "near_equal"
    if number < wide:
        return f"lane2_faster_{tight:.2f}_{wide:.2f}"
    return f"lane2_faster_{wide:.2f}+"


def _load_lane_level(db_path: Path, start_date: str, end_date: str) -> pd.DataFrame:
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        return con.execute(_lane_level_query(start_date, end_date)).fetchdf()
    finally:
        con.close()


def _build_race_level(lane_level: pd.DataFrame) -> pd.DataFrame:
    lane_level = lane_level.copy()
    lane_level["race_id"] = lane_level["race_id"].astype(str)
    meta_cols = [
        "race_id",
        "race_date",
        "stadium_code",
        "stadium_name",
        "race_no",
        "race_title",
        "grade",
        "meeting_day_no",
        "meeting_day_label",
        "is_final_day",
        "wind_speed_m",
        "wave_height_cm",
        "weather_condition",
        "first_place_lane",
        "second_place_lane",
        "exacta_combo",
        "exacta_payout",
        "best_exhibition_time",
        "best_start_exhibition_st",
    ]
    lane_cols = [
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
        "exhibition_time",
        "start_exhibition_st",
        "national_win_rank",
        "national_place_rank",
        "local_win_rank",
        "local_place_rank",
        "motor_rank",
        "boat_rank",
        "avg_start_rank",
        "exhibition_rank",
        "exhibition_st_rank",
    ]
    race = lane_level[meta_cols].groupby("race_id", as_index=False, observed=True).first()
    for lane in range(1, 7):
        part = lane_level[lane_level["lane"] == lane][["race_id", *lane_cols]].copy()
        part = part.rename(columns={col: f"lane{lane}_{col}" for col in lane_cols})
        race = race.merge(part, on="race_id", how="inner")
    return race.sort_values(["race_date", "race_id"]).reset_index(drop=True)


def _add_features(frame: pd.DataFrame) -> pd.DataFrame:
    df = frame.copy()
    df["race_date"] = pd.to_datetime(df["race_date"])
    df["month"] = df["race_date"].dt.strftime("%Y-%m")
    df["exacta_combo_norm"] = df["exacta_combo"].map(_normalize_combo)
    df["hit_1_2"] = (df["exacta_combo_norm"] == TARGET_COMBO).astype(int)
    df["stake_1_2_yen"] = STAKE_YEN
    df["return_1_2_yen"] = np.where(df["hit_1_2"] == 1, df["exacta_payout"], 0).astype(int)
    df["profit_1_2_yen"] = df["return_1_2_yen"] - STAKE_YEN

    df["race_no_bucket"] = pd.cut(
        df["race_no"],
        bins=[0, 3, 6, 9, 12],
        labels=["1-3R", "4-6R", "7-9R", "10-12R"],
        include_lowest=True,
    ).astype("string").fillna("missing")
    df["grade_group"] = df["grade"].fillna("general").astype(str)
    df["meeting_phase_bucket"] = np.select(
        [
            df["is_final_day"].fillna(False).astype(bool),
            df["meeting_day_no"].between(1, 2, inclusive="both"),
            df["meeting_day_no"].between(3, 4, inclusive="both"),
            df["meeting_day_no"].ge(5),
        ],
        ["final", "day1-2", "day3-4", "day5+"],
        default="unknown",
    )
    df["wind_bucket"] = df["wind_speed_m"].map(lambda v: _bucket_numeric(v, [2, 4, 6], ["0-2", "3-4", "5-6", "7+"]))
    df["wave_bucket"] = df["wave_height_cm"].map(lambda v: _bucket_numeric(v, [4, 9], ["0-4", "5-9", "10+"]))
    df["weather_group"] = df["weather_condition"].fillna("missing").astype(str)

    for lane in range(1, 7):
        class_col = f"lane{lane}_racer_class"
        df[f"lane{lane}_class"] = df[class_col].fillna("missing").astype(str)
        df[f"lane{lane}_class_group"] = df[f"lane{lane}_class"].map(_class_group)
        rank_sources = {
            "national_win_rank": "national_win_rate",
            "national_place_rank": "national_place_rate",
            "local_win_rank": "local_win_rate",
            "local_place_rank": "local_place_rate",
            "motor_rank": "motor_place_rate",
            "boat_rank": "boat_place_rate",
            "avg_start_rank": "avg_start_timing",
            "exhibition_rank": "exhibition_time",
            "exhibition_st_rank": "start_exhibition_st",
        }
        for rank_col, source_col in rank_sources.items():
            df[f"lane{lane}_{rank_col}_bucket"] = [
                _bucket_rank_with_source(rank_value, source_value)
                for rank_value, source_value in zip(
                    df[f"lane{lane}_{rank_col}"],
                    df[f"lane{lane}_{source_col}"],
                    strict=False,
                )
            ]
        for rate_col in ["national_win_rate", "local_win_rate"]:
            df[f"lane{lane}_{rate_col}_bucket"] = df[f"lane{lane}_{rate_col}"].map(_bucket_rate)
        for place_col in ["motor_place_rate", "boat_place_rate", "national_place_rate", "local_place_rate"]:
            df[f"lane{lane}_{place_col}_bucket"] = df[f"lane{lane}_{place_col}"].map(_bucket_place_rate)
        df[f"lane{lane}_exhibition_gap"] = (df[f"lane{lane}_exhibition_time"] - df["best_exhibition_time"]).round(3)
        df[f"lane{lane}_exhibition_gap_bucket"] = df[f"lane{lane}_exhibition_gap"].map(
            lambda v: _bucket_numeric(v, [0.00, 0.05, 0.10], ["best", "<=0.05", "0.06-0.10", ">0.10"])
        )
        df[f"lane{lane}_start_exhibition_gap"] = (
            df[f"lane{lane}_start_exhibition_st"] - df["best_start_exhibition_st"]
        ).round(3)
        df[f"lane{lane}_start_exhibition_gap_bucket"] = df[f"lane{lane}_start_exhibition_gap"].map(
            lambda v: _bucket_numeric(v, [0.00, 0.03, 0.06], ["best", "<=0.03", "0.04-0.06", ">0.06"])
        )

    df["lane12_class_pair"] = df["lane1_class"] + "-" + df["lane2_class"]
    df["lane12_group_pair"] = df["lane1_class_group"] + "-" + df["lane2_class_group"]
    df["class_group_pattern_123456"] = df[[f"lane{lane}_class_group" for lane in range(1, 7)]].agg("-".join, axis=1)
    df["partner_group_pattern_3456"] = df[[f"lane{lane}_class_group" for lane in range(3, 7)]].agg("-".join, axis=1)
    df["lane3456_a_count"] = df[[f"lane{lane}_class_group" for lane in range(3, 7)]].eq("A").sum(axis=1)
    df["lane3456_b2_count"] = df[[f"lane{lane}_class" for lane in range(3, 7)]].eq("B2").sum(axis=1)
    df["lane23456_a_count"] = df[[f"lane{lane}_class_group" for lane in range(2, 7)]].eq("A").sum(axis=1)
    for col in ["lane3456_a_count", "lane3456_b2_count", "lane23456_a_count"]:
        df[f"{col}_bucket"] = df[col].map(_bucket_count)

    df["lane12_national_win_diff"] = (df["lane1_national_win_rate"] - df["lane2_national_win_rate"]).round(3)
    df["lane12_local_win_diff"] = (df["lane1_local_win_rate"] - df["lane2_local_win_rate"]).round(3)
    df["lane12_motor_place_diff"] = (df["lane1_motor_place_rate"] - df["lane2_motor_place_rate"]).round(3)
    df["lane12_boat_place_diff"] = (df["lane1_boat_place_rate"] - df["lane2_boat_place_rate"]).round(3)
    df["lane12_avg_start_diff"] = (df["lane1_avg_start_timing"] - df["lane2_avg_start_timing"]).round(3)
    df["lane12_exhibition_time_diff"] = (df["lane1_exhibition_time"] - df["lane2_exhibition_time"]).round(3)
    df["lane12_start_exhibition_st_diff"] = (
        df["lane1_start_exhibition_st"] - df["lane2_start_exhibition_st"]
    ).round(3)

    df["lane12_national_win_diff_bucket"] = df["lane12_national_win_diff"].map(_bucket_lane12_rate_diff)
    df["lane12_local_win_diff_bucket"] = df["lane12_local_win_diff"].map(_bucket_lane12_rate_diff)
    df["lane12_motor_place_diff_bucket"] = df["lane12_motor_place_diff"].map(_bucket_lane12_place_diff)
    df["lane12_boat_place_diff_bucket"] = df["lane12_boat_place_diff"].map(_bucket_lane12_place_diff)
    df["lane12_avg_start_diff_bucket"] = df["lane12_avg_start_diff"].map(
        lambda v: _bucket_time_diff(v, tight=0.02, wide=0.05)
    )
    df["lane12_exhibition_time_diff_bucket"] = df["lane12_exhibition_time_diff"].map(
        lambda v: _bucket_time_diff(v, tight=0.05, wide=0.10)
    )
    df["lane12_start_exhibition_st_diff_bucket"] = df["lane12_start_exhibition_st_diff"].map(
        lambda v: _bucket_time_diff(v, tight=0.03, wide=0.06)
    )

    for source_col, target_col in [
        ("national_win_rate", "outer_national_better_than_lane2_count"),
        ("local_win_rate", "outer_local_better_than_lane2_count"),
        ("motor_place_rate", "outer_motor_better_than_lane2_count"),
        ("boat_place_rate", "outer_boat_better_than_lane2_count"),
    ]:
        outer_cols = [f"lane{lane}_{source_col}" for lane in range(3, 7)]
        df[target_col] = df[outer_cols].gt(df[f"lane2_{source_col}"], axis=0).sum(axis=1)
        df[f"{target_col}_bucket"] = df[target_col].map(_bucket_count)

    df["outer_exhibition_faster_than_lane2_count"] = df[[f"lane{lane}_exhibition_time" for lane in range(3, 7)]].lt(
        df["lane2_exhibition_time"],
        axis=0,
    ).sum(axis=1)
    df["outer_st_faster_than_lane2_count"] = df[[f"lane{lane}_start_exhibition_st" for lane in range(3, 7)]].lt(
        df["lane2_start_exhibition_st"],
        axis=0,
    ).sum(axis=1)
    df["outer_exhibition_faster_than_lane2_count_bucket"] = df["outer_exhibition_faster_than_lane2_count"].map(_bucket_count)
    df["outer_st_faster_than_lane2_count_bucket"] = df["outer_st_faster_than_lane2_count"].map(_bucket_count)

    df["lane2_outer_pressure_bucket"] = np.select(
        [
            df["outer_national_better_than_lane2_count"].ge(2) | df["outer_exhibition_faster_than_lane2_count"].ge(2),
            df["outer_national_better_than_lane2_count"].eq(1) | df["outer_exhibition_faster_than_lane2_count"].eq(1),
        ],
        ["high_outer_pressure", "some_outer_pressure"],
        default="low_outer_pressure",
    )
    df["lane1_lane2_rank_pair"] = (
        df["lane1_national_win_rank_bucket"] + "-" + df["lane2_national_win_rank_bucket"]
    )
    df["lane1_lane2_exhibition_rank_pair"] = (
        df["lane1_exhibition_rank_bucket"] + "-" + df["lane2_exhibition_rank_bucket"]
    )
    return df


def _metric_row(frame: pd.DataFrame, *, slice_family: str, slice_value: str) -> dict[str, object]:
    sample = int(len(frame))
    hits_frame = frame[frame["hit_1_2"] == 1]
    hits = int(len(hits_frame))
    stake = sample * STAKE_YEN
    returned = int(hits_frame["exacta_payout"].sum())
    return {
        "slice_family": slice_family,
        "slice_value": slice_value,
        "sample_races": sample,
        "hits": hits,
        "hit_rate_pct": round(hits * 100.0 / sample, 2) if sample else 0.0,
        "stake_yen": stake,
        "return_yen": returned,
        "profit_yen": returned - stake,
        "roi_pct": round(returned * 100.0 / stake, 2) if stake else 0.0,
        "avg_hit_payout_yen": round(returned / hits, 2) if hits else 0.0,
    }


def _scan_singles(frame: pd.DataFrame, features: Iterable[str], *, min_sample: int) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for feature in features:
        for value, group in frame.groupby(feature, dropna=False, observed=True):
            value_text = "missing" if pd.isna(value) else str(value)
            row = _metric_row(group, slice_family=feature, slice_value=value_text)
            if int(row["sample_races"]) >= min_sample:
                rows.append(row)
    return pd.DataFrame(rows)


def _scan_pairs(frame: pd.DataFrame, pairs: Iterable[tuple[str, str]], *, min_sample: int) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for left, right in pairs:
        for values, group in frame.groupby([left, right], dropna=False, observed=True):
            left_value, right_value = values
            row = _metric_row(
                group,
                slice_family=f"{left} x {right}",
                slice_value=(
                    f"{'missing' if pd.isna(left_value) else left_value}"
                    f" | {'missing' if pd.isna(right_value) else right_value}"
                ),
            )
            if int(row["sample_races"]) >= min_sample:
                rows.append(row)
    return pd.DataFrame(rows)


def _write_readme(
    output_dir: Path,
    *,
    start_date: str,
    end_date: str,
    overall: dict[str, object],
    top_min100: pd.DataFrame,
    top_min300: pd.DataFrame,
    candidates: pd.DataFrame,
    hit_rate_min300: pd.DataFrame,
) -> None:
    def table(frame: pd.DataFrame, cols: list[str], limit: int = 12) -> str:
        view = frame[cols].head(limit).copy()
        lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
        for row in view.itertuples(index=False):
            values = [str(v).replace("|", "\\|") for v in row]
            lines.append("| " + " | ".join(values) + " |")
        return "\n".join(lines)

    readme = f"""# Exacta 1-2 H1 2025 Slice Scan, No Racer Index

## Scope

- period: `{start_date}` to `{end_date}`
- bet shape: exacta `{TARGET_COMBO}` single ticket
- stake model: 100 yen per race
- no racer-index
- settlement source: `results.exacta_combo` and `results.exacta_payout`

## Overall

| sample_races | hits | hit_rate_pct | stake_yen | return_yen | profit_yen | roi_pct | avg_hit_payout_yen |
|---:|---:|---:|---:|---:|---:|---:|---:|
| {overall['sample_races']} | {overall['hits']} | {overall['hit_rate_pct']:.2f}% | {overall['stake_yen']:,} | {overall['return_yen']:,} | {overall['profit_yen']:,} | {overall['roi_pct']:.2f}% | {overall['avg_hit_payout_yen']:.2f} |

## Candidate Conditions

{table(candidates, ['slice_family', 'slice_value', 'sample_races', 'hits', 'hit_rate_pct', 'return_yen', 'profit_yen', 'roi_pct', 'avg_hit_payout_yen'])}

## Top ROI Slices, Min 100 Races

{table(top_min100, ['slice_family', 'slice_value', 'sample_races', 'hits', 'hit_rate_pct', 'return_yen', 'profit_yen', 'roi_pct'])}

## Top ROI Slices, Min 300 Races

{table(top_min300, ['slice_family', 'slice_value', 'sample_races', 'hits', 'hit_rate_pct', 'return_yen', 'profit_yen', 'roi_pct'])}

## Top Hit Rate Slices, Min 300 Races

{table(hit_rate_min300, ['slice_family', 'slice_value', 'sample_races', 'hits', 'hit_rate_pct', 'return_yen', 'profit_yen', 'roi_pct'])}

## Files

- `overall_summary.csv`
- `all_slices_min30.csv`
- `top_roi_min100.csv`
- `top_roi_min300.csv`
- `top_hit_rate_min300.csv`
- `candidate_conditions.csv`
- `race_level_1_2.csv`
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")


def run_scan(db_path: Path, output_dir: Path, start_date: str, end_date: str) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    lane_level = _load_lane_level(db_path, start_date, end_date)
    race_level = _add_features(_build_race_level(lane_level))
    overall = _metric_row(race_level, slice_family="overall", slice_value="all")

    single_features = [
        "month",
        "stadium_code",
        "race_no",
        "race_no_bucket",
        "grade_group",
        "meeting_phase_bucket",
        "wind_bucket",
        "wave_bucket",
        "weather_group",
        "lane1_class",
        "lane2_class",
        "lane1_class_group",
        "lane2_class_group",
        "lane12_class_pair",
        "lane12_group_pair",
        "class_group_pattern_123456",
        "partner_group_pattern_3456",
        "lane3456_a_count_bucket",
        "lane3456_b2_count_bucket",
        "lane23456_a_count_bucket",
        "lane1_national_win_rank_bucket",
        "lane2_national_win_rank_bucket",
        "lane1_national_place_rank_bucket",
        "lane2_national_place_rank_bucket",
        "lane1_local_win_rank_bucket",
        "lane2_local_win_rank_bucket",
        "lane1_motor_rank_bucket",
        "lane2_motor_rank_bucket",
        "lane1_boat_rank_bucket",
        "lane2_boat_rank_bucket",
        "lane1_avg_start_rank_bucket",
        "lane2_avg_start_rank_bucket",
        "lane1_exhibition_rank_bucket",
        "lane2_exhibition_rank_bucket",
        "lane1_exhibition_st_rank_bucket",
        "lane2_exhibition_st_rank_bucket",
        "lane1_national_win_rate_bucket",
        "lane2_national_win_rate_bucket",
        "lane1_local_win_rate_bucket",
        "lane2_local_win_rate_bucket",
        "lane1_motor_place_rate_bucket",
        "lane2_motor_place_rate_bucket",
        "lane1_boat_place_rate_bucket",
        "lane2_boat_place_rate_bucket",
        "lane1_exhibition_gap_bucket",
        "lane2_exhibition_gap_bucket",
        "lane1_start_exhibition_gap_bucket",
        "lane2_start_exhibition_gap_bucket",
        "lane12_national_win_diff_bucket",
        "lane12_local_win_diff_bucket",
        "lane12_motor_place_diff_bucket",
        "lane12_boat_place_diff_bucket",
        "lane12_avg_start_diff_bucket",
        "lane12_exhibition_time_diff_bucket",
        "lane12_start_exhibition_st_diff_bucket",
        "outer_national_better_than_lane2_count_bucket",
        "outer_local_better_than_lane2_count_bucket",
        "outer_motor_better_than_lane2_count_bucket",
        "outer_boat_better_than_lane2_count_bucket",
        "outer_exhibition_faster_than_lane2_count_bucket",
        "outer_st_faster_than_lane2_count_bucket",
        "lane2_outer_pressure_bucket",
        "lane1_lane2_rank_pair",
        "lane1_lane2_exhibition_rank_pair",
    ]
    pair_features = [
        ("lane1_class", "lane2_class"),
        ("lane1_class_group", "lane2_class_group"),
        ("lane12_group_pair", "lane3456_a_count_bucket"),
        ("lane12_group_pair", "lane2_outer_pressure_bucket"),
        ("lane12_class_pair", "lane2_outer_pressure_bucket"),
        ("lane1_national_win_rank_bucket", "lane2_national_win_rank_bucket"),
        ("lane1_national_win_rank_bucket", "lane12_national_win_diff_bucket"),
        ("lane2_national_win_rank_bucket", "lane12_national_win_diff_bucket"),
        ("lane2_national_win_rank_bucket", "lane3456_a_count_bucket"),
        ("lane2_national_win_rank_bucket", "outer_national_better_than_lane2_count_bucket"),
        ("lane2_national_win_rank_bucket", "lane12_start_exhibition_st_diff_bucket"),
        ("lane2_exhibition_rank_bucket", "outer_exhibition_faster_than_lane2_count_bucket"),
        ("lane2_exhibition_st_rank_bucket", "outer_st_faster_than_lane2_count_bucket"),
        ("lane1_exhibition_rank_bucket", "lane2_exhibition_rank_bucket"),
        ("lane1_exhibition_st_rank_bucket", "lane2_exhibition_st_rank_bucket"),
        ("lane1_exhibition_gap_bucket", "lane2_exhibition_gap_bucket"),
        ("lane1_start_exhibition_gap_bucket", "lane2_start_exhibition_gap_bucket"),
        ("lane12_national_win_diff_bucket", "lane12_start_exhibition_st_diff_bucket"),
        ("lane12_exhibition_time_diff_bucket", "lane12_start_exhibition_st_diff_bucket"),
        ("lane12_motor_place_diff_bucket", "lane12_boat_place_diff_bucket"),
        ("lane2_class", "lane2_national_win_rank_bucket"),
        ("lane2_class", "lane2_exhibition_rank_bucket"),
        ("lane1_class", "lane1_national_win_rank_bucket"),
        ("race_no_bucket", "lane12_group_pair"),
        ("stadium_code", "lane12_group_pair"),
        ("meeting_phase_bucket", "lane12_group_pair"),
        ("wind_bucket", "lane12_start_exhibition_st_diff_bucket"),
        ("wave_bucket", "lane12_exhibition_time_diff_bucket"),
    ]

    slices = pd.concat(
        [
            _scan_singles(race_level, single_features, min_sample=30),
            _scan_pairs(race_level, pair_features, min_sample=30),
        ],
        ignore_index=True,
    ).sort_values(["roi_pct", "sample_races"], ascending=[False, False])

    top_min100 = (
        slices[slices["sample_races"] >= 100]
        .sort_values(["roi_pct", "sample_races"], ascending=[False, False])
        .head(100)
    )
    top_min300 = (
        slices[slices["sample_races"] >= 300]
        .sort_values(["roi_pct", "sample_races"], ascending=[False, False])
        .head(100)
    )
    hit_rate_min300 = (
        slices[slices["sample_races"] >= 300]
        .sort_values(["hit_rate_pct", "roi_pct", "sample_races"], ascending=[False, False, False])
        .head(100)
    )
    candidates = (
        slices[
            (slices["sample_races"] >= 100)
            & (slices["roi_pct"] >= 105.0)
            & (slices["hit_rate_pct"] >= overall["hit_rate_pct"])
        ]
        .sort_values(["roi_pct", "sample_races"], ascending=[False, False])
        .head(50)
    )

    pd.DataFrame([overall]).to_csv(output_dir / "overall_summary.csv", index=False, encoding="utf-8-sig")
    slices.to_csv(output_dir / "all_slices_min30.csv", index=False, encoding="utf-8-sig")
    top_min100.to_csv(output_dir / "top_roi_min100.csv", index=False, encoding="utf-8-sig")
    top_min300.to_csv(output_dir / "top_roi_min300.csv", index=False, encoding="utf-8-sig")
    hit_rate_min300.to_csv(output_dir / "top_hit_rate_min300.csv", index=False, encoding="utf-8-sig")
    candidates.to_csv(output_dir / "candidate_conditions.csv", index=False, encoding="utf-8-sig")
    race_level.to_csv(output_dir / "race_level_1_2.csv", index=False, encoding="utf-8-sig")
    _write_readme(
        output_dir,
        start_date=start_date,
        end_date=end_date,
        overall=overall,
        top_min100=top_min100,
        top_min300=top_min300,
        candidates=candidates,
        hit_rate_min300=hit_rate_min300,
    )

    return {
        "output_dir": str(output_dir),
        "sample_races": int(overall["sample_races"]),
        "hit_rate_pct": float(overall["hit_rate_pct"]),
        "roi_pct": float(overall["roi_pct"]),
        "candidate_rows": int(len(candidates)),
        "slice_rows": int(len(slices)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan exacta 1-2 slices on 2025H1 without racer-index.")
    parser.add_argument("--db-path", type=Path, default=default_results_db_path())
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--end-date", default=DEFAULT_END_DATE)
    args = parser.parse_args()
    result = run_scan(args.db_path, args.output_dir, args.start_date, args.end_date)
    for key, value in result.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
