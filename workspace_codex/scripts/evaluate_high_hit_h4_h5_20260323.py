from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd


DB_PATH = Path("d:/boat/data/silver/boat_race.duckdb")
OUTPUT_DIR = Path("d:/boat/reports/strategies/high_hit_h4_h5_followup_20260323")

DISCOVERY_START = "2023-03-11"
DISCOVERY_END = "2023-09-10"

PERIODS = [
    ("discovery_6m", "2023-03-11", "2023-09-10"),
    ("y2023_extended", "2023-03-11", "2023-12-31"),
    ("y2024_forward", "2024-01-01", "2024-12-31"),
]

H4_GROUP_KEYS = [
    "grade_group",
    "wind_bucket",
    "lane1_class",
    "lane1_exgap_bucket",
    "lane1_st_bucket",
    "lane23_pressure_group",
]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def build_feature_query(start_date: str, end_date: str) -> str:
    return f"""
WITH base AS (
  SELECT
    e.race_id,
    e.race_date,
    e.stadium_code,
    r.stadium_name,
    e.race_no,
    rm.meeting_title,
    r.race_title,
    rm.grade,
    rm.meeting_day_no,
    rm.meeting_day_label,
    rm.is_final_day,
    e.lane,
    e.racer_id,
    e.racer_name,
    e.racer_class,
    e.branch,
    e.hometown,
    e.age,
    e.weight_kg,
    bi.weight_kg_before,
    bi.adjust_weight_kg,
    e.f_count,
    e.l_count,
    e.avg_start_timing,
    e.national_win_rate,
    e.national_place_rate,
    e.national_top3_rate,
    e.local_win_rate,
    e.local_place_rate,
    e.local_top3_rate,
    e.motor_no,
    e.motor_place_rate,
    e.motor_top3_rate,
    e.boat_no,
    e.boat_place_rate,
    e.boat_top3_rate,
    bi.exhibition_time,
    bi.tilt,
    bi.course_entry,
    bi.start_exhibition_st,
    bi.start_exhibition_status,
    COALESCE(bi.weather_condition, res.weather_condition) AS weather_condition,
    COALESCE(bi.weather_temp_c, res.weather_temp_c) AS weather_temp_c,
    COALESCE(bi.wind_speed_m, res.wind_speed_m) AS wind_speed_m,
    COALESCE(bi.wind_direction_code, res.wind_direction_code) AS wind_direction_code,
    COALESCE(bi.water_temp_c, res.water_temp_c) AS water_temp_c,
    COALESCE(bi.wave_height_cm, res.wave_height_cm) AS wave_height_cm,
    res.first_place_lane,
    res.second_place_lane,
    res.third_place_lane,
    res.exacta_combo,
    res.exacta_payout,
    res.trifecta_combo,
    res.trifecta_payout,
    res.winning_technique,
    CASE WHEN res.first_place_lane = e.lane THEN 1 ELSE 0 END AS is_winner,
    CASE WHEN e.lane IN (res.first_place_lane, res.second_place_lane) THEN 1 ELSE 0 END AS is_top2,
    CASE WHEN e.lane IN (res.first_place_lane, res.second_place_lane, res.third_place_lane) THEN 1 ELSE 0 END AS is_top3
  FROM entries e
  JOIN races r USING (race_id)
  LEFT JOIN race_meta rm USING (race_id)
  LEFT JOIN beforeinfo_entries bi ON bi.race_id = e.race_id AND bi.lane = e.lane
  LEFT JOIN results res USING (race_id)
  WHERE e.race_date BETWEEN DATE '{start_date}' AND DATE '{end_date}'
),
enriched AS (
  SELECT
    *,
    DENSE_RANK() OVER (
      PARTITION BY race_id
      ORDER BY
        CASE WHEN exhibition_time IS NULL THEN 1 ELSE 0 END,
        exhibition_time ASC,
        lane ASC
    ) AS exhibition_time_rank,
    ROUND(
      exhibition_time - MIN(exhibition_time) OVER (PARTITION BY race_id),
      3
    ) AS exhibition_time_diff_from_top,
    DENSE_RANK() OVER (
      PARTITION BY race_id
      ORDER BY
        CASE WHEN national_win_rate IS NULL THEN 1 ELSE 0 END,
        national_win_rate DESC,
        lane ASC
    ) AS win_rate_rank,
    DENSE_RANK() OVER (
      PARTITION BY race_id
      ORDER BY
        CASE WHEN start_exhibition_st IS NULL THEN 1 ELSE 0 END,
        start_exhibition_st ASC,
        lane ASC
    ) AS exhibition_st_rank
  FROM base
)
SELECT *
FROM enriched
"""


def build_race_context_query(feature_query: str) -> str:
    return f"""
WITH feature_base AS ({feature_query}),
race_base AS (
  SELECT
    race_id,
    MIN(race_date) AS race_date,
    MIN(stadium_code) AS stadium_code,
    MIN(stadium_name) AS stadium_name,
    MIN(race_no) AS race_no,
    MIN(meeting_title) AS meeting_title,
    MIN(race_title) AS race_title,
    MAX(grade) AS grade,
    MAX(meeting_day_no) AS meeting_day_no,
    MIN(meeting_day_label) AS meeting_day_label,
    MAX(is_final_day) AS is_final_day,
    MIN(weather_condition) AS weather_condition,
    MAX(wind_speed_m) AS wind_speed_m,
    MAX(wave_height_cm) AS wave_height_cm,
    MAX(first_place_lane) AS first_place_lane,
    MAX(second_place_lane) AS second_place_lane,
    MAX(third_place_lane) AS third_place_lane,
    MAX(exacta_combo) AS exacta_combo,
    MAX(exacta_payout) AS exacta_payout,
    MAX(trifecta_combo) AS trifecta_combo,
    MAX(trifecta_payout) AS trifecta_payout,
    MAX(winning_technique) AS winning_technique,
    SUM(CASE WHEN racer_class = 'A1' THEN 1 ELSE 0 END) AS a1_count,
    SUM(CASE WHEN racer_class = 'A2' THEN 1 ELSE 0 END) AS a2_count,
    SUM(CASE WHEN racer_class = 'B1' THEN 1 ELSE 0 END) AS b1_count,
    SUM(CASE WHEN racer_class = 'B2' THEN 1 ELSE 0 END) AS b2_count,
    MAX(CASE WHEN lane = 1 THEN racer_class END) AS lane1_class,
    MAX(CASE WHEN lane = 2 THEN racer_class END) AS lane2_class,
    MAX(CASE WHEN lane = 3 THEN racer_class END) AS lane3_class,
    ROUND(MAX(CASE WHEN lane = 1 THEN national_win_rate END), 3) AS lane1_national_win_rate,
    ROUND(MAX(CASE WHEN lane = 2 THEN national_win_rate END), 3) AS lane2_national_win_rate,
    ROUND(MAX(CASE WHEN lane = 3 THEN national_win_rate END), 3) AS lane3_national_win_rate,
    ROUND(MAX(CASE WHEN lane = 1 THEN motor_place_rate END), 3) AS lane1_motor_place_rate,
    ROUND(MAX(CASE WHEN lane = 2 THEN motor_place_rate END), 3) AS lane2_motor_place_rate,
    ROUND(MAX(CASE WHEN lane = 3 THEN motor_place_rate END), 3) AS lane3_motor_place_rate,
    ROUND(MAX(CASE WHEN lane = 1 THEN exhibition_time END), 3) AS lane1_exhibition_time,
    ROUND(MAX(CASE WHEN lane = 2 THEN exhibition_time END), 3) AS lane2_exhibition_time,
    ROUND(MAX(CASE WHEN lane = 3 THEN exhibition_time END), 3) AS lane3_exhibition_time,
    MAX(CASE WHEN lane = 1 THEN exhibition_time_rank END) AS lane1_exhibition_rank,
    MAX(CASE WHEN lane = 2 THEN exhibition_time_rank END) AS lane2_exhibition_rank,
    MAX(CASE WHEN lane = 3 THEN exhibition_time_rank END) AS lane3_exhibition_rank,
    ROUND(MAX(CASE WHEN lane = 1 THEN exhibition_time_diff_from_top END), 3) AS lane1_exhibition_diff_from_top,
    ROUND(MAX(CASE WHEN lane = 1 THEN start_exhibition_st END), 3) AS lane1_start_exhibition_st,
    ROUND(MAX(CASE WHEN lane = 2 THEN start_exhibition_st END), 3) AS lane2_start_exhibition_st,
    ROUND(MAX(CASE WHEN lane = 3 THEN start_exhibition_st END), 3) AS lane3_start_exhibition_st,
    SUM(CASE WHEN lane IN (2, 3) AND racer_class IN ('A1', 'A2') THEN 1 ELSE 0 END) AS lane23_a_count,
    CASE WHEN MAX(first_place_lane) = 1 THEN 1 ELSE 0 END AS lane1_win,
    CASE WHEN MAX(first_place_lane) = 1 OR MAX(second_place_lane) = 1 THEN 1 ELSE 0 END AS lane1_top2,
    CASE WHEN MAX(first_place_lane) = 1 AND MAX(second_place_lane) = 2 THEN 1 ELSE 0 END AS exacta_12_hit,
    CASE WHEN MAX(first_place_lane) = 1 AND MAX(second_place_lane) = 3 THEN 1 ELSE 0 END AS exacta_13_hit,
    CASE WHEN MAX(trifecta_combo) = '1-2-3' THEN 1 ELSE 0 END AS trifecta_123_hit,
    CASE WHEN MAX(trifecta_combo) = '1-3-2' THEN 1 ELSE 0 END AS trifecta_132_hit,
    CASE
      WHEN MAX(exacta_payout) >= 5000 OR MAX(trifecta_payout) >= 10000 THEN 1
      ELSE 0
    END AS rough_race_flag
  FROM feature_base
  GROUP BY race_id
),
with_l23 AS (
  SELECT
    *,
    CASE
      WHEN lane2_start_exhibition_st IS NULL THEN lane3_start_exhibition_st
      WHEN lane3_start_exhibition_st IS NULL THEN lane2_start_exhibition_st
      ELSE LEAST(lane2_start_exhibition_st, lane3_start_exhibition_st)
    END AS best_l23_start_exhibition_st
  FROM race_base
),
bucketed AS (
  SELECT
    *,
    ROUND(
      lane1_start_exhibition_st - best_l23_start_exhibition_st,
      3
    ) AS lane1_st_vs_best_l23,
    CASE
      WHEN grade IN ('SG', 'G1') THEN grade
      ELSE 'general'
    END AS grade_group,
    CASE
      WHEN meeting_day_no IS NULL THEN 'unknown'
      WHEN is_final_day = 1 THEN 'final'
      WHEN meeting_day_no <= 2 THEN 'day1-2'
      WHEN meeting_day_no <= 4 THEN 'day3-4'
      ELSE 'day5+'
    END AS meeting_phase_bucket,
    CASE
      WHEN wind_speed_m IS NULL THEN 'unknown'
      WHEN wind_speed_m <= 2 THEN '0-2'
      WHEN wind_speed_m <= 4 THEN '3-4'
      WHEN wind_speed_m <= 6 THEN '5-6'
      ELSE '7+'
    END AS wind_bucket,
    CASE
      WHEN wave_height_cm IS NULL THEN 'unknown'
      WHEN wave_height_cm <= 4 THEN '0-4'
      WHEN wave_height_cm <= 9 THEN '5-9'
      ELSE '10+'
    END AS wave_bucket,
    CASE
      WHEN lane1_exhibition_rank IS NULL THEN 'missing'
      WHEN lane1_exhibition_rank = 1 THEN '1'
      WHEN lane1_exhibition_rank = 2 THEN '2'
      ELSE '3+'
    END AS lane1_exrank_bucket,
    CASE
      WHEN lane1_exhibition_diff_from_top IS NULL THEN 'missing'
      WHEN lane1_exhibition_diff_from_top <= 0.02 THEN '<=0.02'
      WHEN lane1_exhibition_diff_from_top <= 0.05 THEN '0.021-0.05'
      WHEN lane1_exhibition_diff_from_top <= 0.10 THEN '0.051-0.10'
      ELSE '>0.10'
    END AS lane1_exgap_bucket,
    CASE
      WHEN lane1_start_exhibition_st IS NULL OR best_l23_start_exhibition_st IS NULL THEN 'missing'
      WHEN lane1_start_exhibition_st - best_l23_start_exhibition_st <= -0.03 THEN 'lane1_faster'
      WHEN lane1_start_exhibition_st - best_l23_start_exhibition_st <= 0.02 THEN 'near_even'
      ELSE 'lane1_slower'
    END AS lane1_st_bucket,
    CASE
      WHEN lane23_a_count = 0 THEN 'lane23_weak'
      WHEN lane23_a_count = 1 THEN 'lane23_one_A'
      ELSE 'lane23_two_A'
    END AS lane23_pressure_group
  FROM with_l23
)
SELECT *
FROM bucketed
"""


def h4_group_discovery_query() -> str:
    race_ctx = build_race_context_query(build_feature_query(DISCOVERY_START, DISCOVERY_END))
    return f"""
WITH race_ctx AS ({race_ctx}),
aggregated AS (
  SELECT
    grade_group,
    wind_bucket,
    lane1_class,
    lane1_exgap_bucket,
    lane1_st_bucket,
    lane23_pressure_group,
    COUNT(*) AS races,
    SUM(lane1_win) AS lane1_win_count,
    SUM(CASE WHEN lane1_win = 1 AND second_place_lane = 2 THEN 1 ELSE 0 END) AS partner2_hits,
    SUM(CASE WHEN lane1_win = 1 AND second_place_lane = 3 THEN 1 ELSE 0 END) AS partner3_hits,
    SUM(CASE WHEN lane1_win = 1 AND second_place_lane = 4 THEN 1 ELSE 0 END) AS partner4_hits,
    SUM(CASE WHEN lane1_win = 1 AND second_place_lane = 5 THEN 1 ELSE 0 END) AS partner5_hits,
    SUM(CASE WHEN lane1_win = 1 AND second_place_lane = 6 THEN 1 ELSE 0 END) AS partner6_hits,
    ROUND(AVG(lane1_win) * 100, 2) AS lane1_win_rate_pct,
    ROUND(AVG(exacta_12_hit) * 100, 2) AS exacta_12_rate_pct,
    ROUND(AVG(exacta_13_hit) * 100, 2) AS exacta_13_rate_pct,
    ROUND(AVG(CASE WHEN first_place_lane = 1 AND second_place_lane = 4 THEN 1 ELSE 0 END) * 100, 2) AS exacta_14_rate_pct,
    ROUND(AVG(rough_race_flag) * 100, 2) AS rough_race_pct
  FROM race_ctx
  WHERE lane1_class IS NOT NULL
  GROUP BY 1, 2, 3, 4, 5, 6
),
scored AS (
  SELECT
    *,
    CASE
      WHEN partner2_hits >= partner3_hits AND partner2_hits >= partner4_hits AND partner2_hits >= partner5_hits AND partner2_hits >= partner6_hits THEN 2
      WHEN partner3_hits >= partner4_hits AND partner3_hits >= partner5_hits AND partner3_hits >= partner6_hits THEN 3
      WHEN partner4_hits >= partner5_hits AND partner4_hits >= partner6_hits THEN 4
      WHEN partner5_hits >= partner6_hits THEN 5
      ELSE 6
    END AS best_partner_lane,
    ROUND(
      GREATEST(partner2_hits, partner3_hits, partner4_hits, partner5_hits, partner6_hits) * 100.0 / NULLIF(lane1_win_count, 0),
      2
    ) AS best_partner_share_pct
  FROM aggregated
)
SELECT *
FROM scored
WHERE races >= 60
  AND lane1_win_count >= 20
  AND lane1_exgap_bucket = '>0.10'
  AND lane1_st_bucket = 'near_even'
  AND best_partner_lane = 3
ORDER BY exacta_13_rate_pct DESC, best_partner_share_pct DESC, races DESC
"""


def evaluate_h4_period_query(start_date: str, end_date: str) -> str:
    race_ctx = build_race_context_query(build_feature_query(start_date, end_date))
    discovery_groups = h4_group_discovery_query()
    join_keys = "\n      AND ".join([f"rc.{key} = dg.{key}" for key in H4_GROUP_KEYS])
    return f"""
WITH rc AS ({race_ctx}),
dg AS ({discovery_groups})
SELECT
  COUNT(*) AS races,
  COUNT(DISTINCT rc.race_id) AS unique_races,
  ROUND(AVG(rc.lane1_win) * 100, 2) AS lane1_win_rate_pct,
  ROUND(AVG(rc.exacta_12_hit) * 100, 2) AS exacta_12_rate_pct,
  ROUND(AVG(rc.exacta_13_hit) * 100, 2) AS exacta_13_rate_pct,
  ROUND(AVG(CASE WHEN rc.exacta_12_hit = 1 OR rc.exacta_13_hit = 1 THEN 1 ELSE 0 END) * 100, 2) AS exacta_12_or_13_rate_pct,
  ROUND(SUM(CASE WHEN rc.exacta_13_hit = 1 THEN rc.exacta_payout ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0) / 100.0, 2) AS roi_13_pct
FROM rc
JOIN dg
  ON {join_keys}
"""


def evaluate_h5_period_query(start_date: str, end_date: str) -> str:
    race_ctx = build_race_context_query(build_feature_query(start_date, end_date))
    return f"""
WITH rc AS ({race_ctx})
SELECT
  COUNT(*) AS races,
  ROUND(AVG(exacta_12_hit) * 100, 2) AS exacta_12_rate_pct,
  ROUND(AVG(exacta_13_hit) * 100, 2) AS exacta_13_rate_pct,
  ROUND(AVG(trifecta_123_hit) * 100, 2) AS trifecta_123_rate_pct,
  ROUND(AVG(trifecta_132_hit) * 100, 2) AS trifecta_132_rate_pct,
  ROUND(AVG(CASE WHEN trifecta_123_hit = 1 OR trifecta_132_hit = 1 THEN 1 ELSE 0 END) * 100, 2) AS trifecta_123_or_132_rate_pct,
  ROUND(SUM(CASE WHEN trifecta_123_hit = 1 THEN trifecta_payout ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0) / 100.0, 2) AS roi_123_pct,
  ROUND(SUM(CASE WHEN trifecta_123_hit = 1 OR trifecta_132_hit = 1 THEN trifecta_payout ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0) / 200.0, 2) AS roi_123_132_pair_pct
FROM rc
WHERE lane1_exrank_bucket = '1'
  AND lane23_pressure_group = 'lane23_weak'
  AND wind_bucket = '0-2'
"""


def to_markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "(no rows)"
    headers = list(df.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in df.iterrows():
        values = [str(row[col]) for col in headers]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def main() -> None:
    ensure_dir(OUTPUT_DIR)
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        h4_groups = con.execute(h4_group_discovery_query()).fetchdf()
        h4_groups.to_csv(OUTPUT_DIR / "h4_discovery_partner_groups.csv", index=False)

        h4_rows = []
        h5_rows = []
        for label, start_date, end_date in PERIODS:
            h4_metrics = con.execute(evaluate_h4_period_query(start_date, end_date)).fetchdf()
            h4_metrics.insert(0, "period", label)
            h4_rows.append(h4_metrics)

            h5_metrics = con.execute(evaluate_h5_period_query(start_date, end_date)).fetchdf()
            h5_metrics.insert(0, "period", label)
            h5_rows.append(h5_metrics)

        h4_summary = pd.concat(h4_rows, ignore_index=True)
        h5_summary = pd.concat(h5_rows, ignore_index=True)

        h4_summary.to_csv(OUTPUT_DIR / "h4_summary.csv", index=False)
        h5_summary.to_csv(OUTPUT_DIR / "h5_summary.csv", index=False)

        readme = f"""# H-004 / H-005 Follow-Up 2026-03-23

## Scope

- source package: `GPT/output/2023-03-11_2023-09-10_high_hit_discovery`
- origin note: `H-001/H-002/H-003` drove the later `1-2 / 1-3` structural exploration
- this follow-up checks the two deferred ideas:
  - `H-004`: exacta `1-3`
  - `H-005`: trifecta `1-2-3`

## Translation Rule

- `H-004` came from `summary_lane1_partner_scan.csv`, so it is evaluated by:
  - selecting discovery-time partner groups that satisfy:
    - `lane1_exgap_bucket = '>0.10'`
    - `lane1_st_bucket = 'near_even'`
    - `best_partner_lane = 3`
  - then applying those same group keys to later periods
- `H-005` came from `summary_lane1_context_scan.csv`, so it is evaluated directly on raw race rows with:
  - `lane1_exrank_bucket = '1'`
  - `lane23_pressure_group = 'lane23_weak'`
  - `wind_bucket = '0-2'`

## H-004 Discovery Partner Groups

{to_markdown_table(h4_groups)}

## H-004 Summary

{to_markdown_table(h4_summary)}

## H-005 Summary

{to_markdown_table(h5_summary)}
"""
        (OUTPUT_DIR / "README.md").write_text(readme, encoding="utf-8")
    finally:
        con.close()


if __name__ == "__main__":
    main()
