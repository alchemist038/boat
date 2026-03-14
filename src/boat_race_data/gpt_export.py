from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import duckdb

from boat_race_data.utils import ensure_dir


@dataclass(frozen=True, slots=True)
class ExportSpec:
    filename: str
    description: str
    query: str


FEATURES_QUERY = """
WITH base AS (
  SELECT
    e.race_id,
    e.race_date,
    e.stadium_code,
    r.stadium_name,
    e.race_no,
    rm.meeting_title,
    rm.grade,
    rm.grade_raw,
    rm.meeting_day_no,
    rm.meeting_day_label,
    rm.is_final_day,
    r.race_title,
    r.distance_m,
    r.deadline_time,
    e.lane,
    e.racer_id,
    e.racer_name,
    e.racer_class,
    e.branch,
    e.hometown,
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
    e.motor_no,
    e.motor_place_rate,
    e.motor_top3_rate,
    e.boat_no,
    e.boat_place_rate,
    e.boat_top3_rate,
    bi.weight_kg_before,
    bi.adjust_weight_kg,
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
)
SELECT *
FROM base
WHERE race_date BETWEEN DATE '{start_date}' AND DATE '{end_date}'
ORDER BY race_date, stadium_code, race_no, lane
"""

MARKET_RESULTS_QUERY = """
WITH markets AS (
  SELECT
    o.race_id,
    o.race_date,
    o.stadium_code,
    r.stadium_name,
    o.race_no,
    rm.meeting_title,
    rm.grade,
    rm.meeting_day_no,
    rm.meeting_day_label,
    COALESCE(res.weather_condition, '') AS weather_condition,
    res.wind_speed_m,
    res.wind_direction_code,
    res.wave_height_cm,
    o.bet_type,
    o.first_lane,
    o.second_lane,
    NULL::INTEGER AS third_lane,
    o.odds,
    o.odds_status,
    CASE
      WHEN o.bet_type = '2連単'
        AND res.first_place_lane = o.first_lane
        AND res.second_place_lane = o.second_lane
      THEN 1
      WHEN o.bet_type = '2連複'
        AND LEAST(res.first_place_lane, res.second_place_lane) = LEAST(o.first_lane, o.second_lane)
        AND GREATEST(res.first_place_lane, res.second_place_lane) = GREATEST(o.first_lane, o.second_lane)
      THEN 1
      ELSE 0
    END AS is_hit,
    CASE
      WHEN o.bet_type = '2連単'
        AND res.first_place_lane = o.first_lane
        AND res.second_place_lane = o.second_lane
      THEN res.exacta_payout
      WHEN o.bet_type = '2連複'
        AND LEAST(res.first_place_lane, res.second_place_lane) = LEAST(o.first_lane, o.second_lane)
        AND GREATEST(res.first_place_lane, res.second_place_lane) = GREATEST(o.first_lane, o.second_lane)
      THEN res.quinella_payout
      ELSE 0
    END AS realized_payout,
    CASE
      WHEN o.bet_type = '2連単' THEN res.exacta_combo
      WHEN o.bet_type = '2連複' THEN res.quinella_combo
      ELSE NULL
    END AS settled_combo,
    CASE
      WHEN o.bet_type = '2連単' THEN res.exacta_payout
      WHEN o.bet_type = '2連複' THEN res.quinella_payout
      ELSE NULL
    END AS official_payout
  FROM odds_2t o
  JOIN races r USING (race_id)
  LEFT JOIN race_meta rm USING (race_id)
  LEFT JOIN results res USING (race_id)
  WHERE o.race_date BETWEEN DATE '{start_date}' AND DATE '{end_date}'
  UNION ALL
  SELECT
    o.race_id,
    o.race_date,
    o.stadium_code,
    r.stadium_name,
    o.race_no,
    rm.meeting_title,
    rm.grade,
    rm.meeting_day_no,
    rm.meeting_day_label,
    COALESCE(res.weather_condition, '') AS weather_condition,
    res.wind_speed_m,
    res.wind_direction_code,
    res.wave_height_cm,
    o.bet_type,
    o.first_lane,
    o.second_lane,
    o.third_lane,
    o.odds,
    o.odds_status,
    CASE
      WHEN res.first_place_lane = o.first_lane
        AND res.second_place_lane = o.second_lane
        AND res.third_place_lane = o.third_lane
      THEN 1
      ELSE 0
    END AS is_hit,
    CASE
      WHEN res.first_place_lane = o.first_lane
        AND res.second_place_lane = o.second_lane
        AND res.third_place_lane = o.third_lane
      THEN res.trifecta_payout
      ELSE 0
    END AS realized_payout,
    res.trifecta_combo AS settled_combo,
    res.trifecta_payout AS official_payout
  FROM odds_3t o
  JOIN races r USING (race_id)
  LEFT JOIN race_meta rm USING (race_id)
  LEFT JOIN results res USING (race_id)
  WHERE o.race_date BETWEEN DATE '{start_date}' AND DATE '{end_date}'
)
SELECT *
FROM markets
ORDER BY race_date, stadium_code, race_no, bet_type, first_lane, second_lane, third_lane
"""

SUMMARY_STADIUM_LANE_QUERY = """
WITH feature_base AS (
  SELECT * FROM ({features_query})
)
SELECT
  stadium_code,
  stadium_name,
  lane,
  COUNT(*) AS races,
  ROUND(AVG(is_winner) * 100, 2) AS win_rate_pct,
  ROUND(AVG(is_top2) * 100, 2) AS top2_rate_pct,
  ROUND(AVG(is_top3) * 100, 2) AS top3_rate_pct,
  ROUND(AVG(national_win_rate), 3) AS avg_national_win_rate,
  ROUND(AVG(local_win_rate), 3) AS avg_local_win_rate,
  ROUND(AVG(motor_place_rate), 3) AS avg_motor_place_rate
FROM feature_base
GROUP BY 1, 2, 3
ORDER BY stadium_code, lane
"""

SUMMARY_CLASS_LANE_QUERY = """
WITH feature_base AS (
  SELECT * FROM ({features_query})
)
SELECT
  racer_class,
  lane,
  COUNT(*) AS races,
  ROUND(AVG(is_winner) * 100, 2) AS win_rate_pct,
  ROUND(AVG(is_top2) * 100, 2) AS top2_rate_pct,
  ROUND(AVG(is_top3) * 100, 2) AS top3_rate_pct,
  ROUND(AVG(avg_start_timing), 3) AS avg_start_timing
FROM feature_base
GROUP BY 1, 2
ORDER BY racer_class, lane
"""

SUMMARY_WEATHER_LANE_QUERY = """
WITH feature_base AS (
  SELECT
    *,
    CASE
      WHEN wind_speed_m IS NULL THEN 'unknown'
      WHEN wind_speed_m <= 2 THEN '0-2'
      WHEN wind_speed_m <= 4 THEN '3-4'
      WHEN wind_speed_m <= 6 THEN '5-6'
      ELSE '7+'
    END AS wind_bucket
  FROM ({features_query})
)
SELECT
  wind_bucket,
  lane,
  COUNT(*) AS races,
  ROUND(AVG(is_winner) * 100, 2) AS win_rate_pct,
  ROUND(AVG(is_top2) * 100, 2) AS top2_rate_pct,
  ROUND(AVG(is_top3) * 100, 2) AS top3_rate_pct
FROM feature_base
GROUP BY 1, 2
ORDER BY wind_bucket, lane
"""

SUMMARY_MARKET_ROI_QUERY = """
WITH market_base AS (
  SELECT
    *,
    CASE
      WHEN odds IS NULL THEN 'no_price'
      WHEN odds < 10 THEN '<10'
      WHEN odds < 20 THEN '10-19.9'
      WHEN odds < 50 THEN '20-49.9'
      WHEN odds < 100 THEN '50-99.9'
      ELSE '100+'
    END AS odds_bucket
  FROM ({market_query})
)
SELECT
  bet_type,
  odds_bucket,
  COUNT(*) AS bets,
  SUM(is_hit) AS hits,
  ROUND(AVG(is_hit) * 100, 3) AS hit_rate_pct,
  ROUND(SUM(realized_payout) / (COUNT(*) * 100.0) * 100, 2) AS roi_pct
FROM market_base
GROUP BY 1, 2
ORDER BY bet_type, odds_bucket
"""

TERM_REFERENCE_QUERY = """
SELECT
  racer_id,
  racer_name_kanji,
  branch,
  hometown,
  current_class,
  age,
  weight_kg,
  win_rate,
  place_rate,
  average_start_timing,
  course_1_entry_count,
  course_1_place_rate,
  course_1_average_start_timing,
  course_2_entry_count,
  course_2_place_rate,
  course_3_entry_count,
  course_3_place_rate,
  course_4_entry_count,
  course_4_place_rate,
  course_5_entry_count,
  course_5_place_rate,
  course_6_entry_count,
  course_6_place_rate,
  previous_class_1,
  previous_class_2,
  previous_class_3,
  previous_term_ability_index,
  current_term_ability_index,
  term_year,
  term_half,
  term_start_date,
  term_end_date,
  term_file
FROM racer_stats_term
ORDER BY racer_id
"""


def _write_query_csv(con: duckdb.DuckDBPyConnection, query: str, output_path: Path) -> int:
    result = con.execute(query)
    columns = [description[0] for description in result.description]
    rows = result.fetchall()
    ensure_dir(output_path.parent)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows(rows)
    return len(rows)


def export_gpt_package(db_path: Path, start_date: str, end_date: str, output_dir: Path) -> dict[str, int]:
    ensure_dir(output_dir)
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        features_query = FEATURES_QUERY.format(start_date=start_date, end_date=end_date)
        market_query = MARKET_RESULTS_QUERY.format(start_date=start_date, end_date=end_date)

        specs = [
            ExportSpec("race_boat_features.csv", "1レース1艇の戦略用特徴量。", features_query),
            ExportSpec("market_results_joined.csv", "市場価格と結果を同じ行で見られる市場テーブル。", market_query),
            ExportSpec(
                "summary_stadium_lane.csv",
                "場別×枠別の基本統計。",
                SUMMARY_STADIUM_LANE_QUERY.format(features_query=features_query),
            ),
            ExportSpec(
                "summary_class_lane.csv",
                "級別×枠別の基本統計。",
                SUMMARY_CLASS_LANE_QUERY.format(features_query=features_query),
            ),
            ExportSpec(
                "summary_weather_lane.csv",
                "風速帯×枠別の基本統計。",
                SUMMARY_WEATHER_LANE_QUERY.format(features_query=features_query),
            ),
            ExportSpec(
                "summary_market_roi.csv",
                "券種×オッズ帯の100円フラットROI。",
                SUMMARY_MARKET_ROI_QUERY.format(market_query=market_query),
            ),
            ExportSpec("racer_term_reference.csv", "期別成績の参照用スナップショット。", TERM_REFERENCE_QUERY),
        ]

        row_counts: dict[str, int] = {}
        for spec in specs:
            row_counts[spec.filename] = _write_query_csv(con, spec.query, output_dir / spec.filename)

        summary = con.execute(
            f"""
            WITH feature_base AS ({features_query}),
                 market_base AS ({market_query})
            SELECT
              (SELECT COUNT(DISTINCT race_id) FROM feature_base) AS races,
              (SELECT COUNT(*) FROM feature_base) AS feature_rows,
              (SELECT COUNT(*) FROM market_base) AS market_rows,
              (SELECT MIN(race_date) FROM feature_base) AS min_race_date,
              (SELECT MAX(race_date) FROM feature_base) AS max_race_date
            """
        ).fetchone()
    finally:
        con.close()

    strategy_brief = "\n".join(
        [
            f"# Strategy Brief {start_date} to {end_date}",
            "",
            "## Goal",
            "- GPTには予想ではなく、再現可能な戦略仮説を提案させる。",
            "- 実際の採用判断はこのローカル環境のバックテストで行う。",
            "- マーチンゲール系ではなく、見送り条件と期待値フィルタを重視する。",
            "",
            "## Export Summary",
            f"- race_count: {summary[0] or 0}",
            f"- race_boat_feature_rows: {summary[1] or 0}",
            f"- market_rows: {summary[2] or 0}",
            f"- min_race_date: {summary[3] or ''}",
            f"- max_race_date: {summary[4] or ''}",
            "",
            "## Files",
            "- `race_boat_features.csv`: 1レース1艇。レース前に見える要素と結果ラベル。",
            "- `market_results_joined.csv`: オッズ、欠場状態、的中可否、確定払戻。",
            "- `summary_stadium_lane.csv`: 場別×枠別の基礎成績。",
            "- `summary_class_lane.csv`: 級別×枠別の基礎成績。",
            "- `summary_weather_lane.csv`: 風速帯×枠別の基礎成績。",
            "- `summary_market_roi.csv`: 券種×オッズ帯の100円フラットROI。",
            "- `racer_term_reference.csv`: 期別成績の参照用。",
            "",
            "## Notes",
            "- `odds_status` には `欠場` など価格が付かない状態が残る。",
            "- `is_winner`, `is_top2`, `is_top3` はバックテスト用ラベルであり、実運用時の入力に混ぜない。",
            "- 期別成績は参照用で、期間をまたぐ検証ではリーク確認が必要。",
            "",
            "## What GPT Should Return",
            "- 券種を絞った戦略候補を3本前後。",
            "- 買う条件と見送る条件を明文化したルール。",
            "- 期待値が出そうな理由と、過学習になりやすい点。",
            "- このローカルで検証するための優先順位。",
            "",
        ]
    )
    prompt_to_send = "\n".join(
        [
            f"# Prompt To Send ({start_date} to {end_date})",
            "",
            "以下のファイルを前提に、ボートレースの戦略案を提案してください。",
            "",
            "使うファイル:",
            "- `strategy_brief.md`",
            "- `race_boat_features.csv`",
            "- `market_results_joined.csv`",
            "- `summary_stadium_lane.csv`",
            "- `summary_class_lane.csv`",
            "- `summary_weather_lane.csv`",
            "- `summary_market_roi.csv`",
            "- `racer_term_reference.csv`",
            "",
            "目的:",
            "- 長期運用候補になりうる、再現可能なルールベース戦略の仮説を3本まで出す",
            "- 予想そのものより、見送り条件、券種の絞り込み、期待値の出やすい条件整理を優先する",
            "- 最終判断はローカルバックテストで行う",
            "",
            "制約:",
            "- マーチンゲール、倍掛け、取り返し型は提案しない",
            "- `見送り条件` を必ず含める",
            "- 券種はまず `2連単` または `3連単` を中心にする",
            "- 過学習しやすい複雑な条件分岐は避ける",
            "",
            "出力形式:",
            "1. 戦略候補を3本まで",
            "2. 各戦略について以下を記載",
            "   - 戦略名",
            "   - 想定券種",
            "   - 狙うレース条件",
            "   - 見送る条件",
            "   - 買い目の作り方",
            "   - 期待値が出る可能性の理由",
            "   - 崩れやすさ、過学習リスク",
            "   - ローカルで優先して確認すべき指標",
            "3. 最後に一番先に検証すべき戦略を1つ選び、その理由を書く",
            "",
            "注意:",
            "- `race_boat_features.csv` の `is_winner`, `is_top2`, `is_top3` は検証用ラベルであり、実運用入力には使わない",
            "- `market_results_joined.csv` の `odds_status` には `欠場` などの状態が入る",
            "- `racer_term_reference.csv` は参照用。期間またぎではリークに注意する",
            "",
        ]
    )
    (output_dir / "strategy_brief.md").write_text(strategy_brief, encoding="utf-8-sig")
    (output_dir / "prompt_to_send.md").write_text(prompt_to_send, encoding="utf-8-sig")
    row_counts["strategy_brief.md"] = 1
    row_counts["prompt_to_send.md"] = 1
    return row_counts
