from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import duckdb

from boat_race_data.gpt_export import FEATURES_QUERY, export_gpt_package
from boat_race_data.utils import ensure_dir


@dataclass(frozen=True, slots=True)
class QueryExport:
    filename: str
    query: str


RACE_CONTEXT_CTE = """
WITH feature_base AS ({features_query}),
race_base AS (
  SELECT
    race_id,
    MIN(race_date) AS race_date,
    MIN(stadium_code) AS stadium_code,
    MIN(stadium_name) AS stadium_name,
    MIN(grade) AS grade,
    MAX(meeting_day_no) AS meeting_day_no,
    MAX(meeting_day_label) AS meeting_day_label,
    MAX(CASE WHEN lane = 1 THEN racer_class END) AS lane1_class,
    MAX(CASE WHEN lane = 1 THEN national_win_rate END) AS lane1_national_win_rate,
    MAX(CASE WHEN lane = 1 THEN local_win_rate END) AS lane1_local_win_rate,
    MAX(CASE WHEN lane = 1 THEN motor_place_rate END) AS lane1_motor_place_rate,
    MAX(CASE WHEN lane = 1 THEN boat_place_rate END) AS lane1_boat_place_rate,
    MAX(weather_condition) AS weather_condition,
    MAX(wind_speed_m) AS wind_speed_m,
    MAX(wind_direction_code) AS wind_direction_code,
    MAX(wave_height_cm) AS wave_height_cm,
    MAX(exacta_combo) AS exacta_combo,
    MAX(exacta_payout) AS exacta_payout,
    MAX(trifecta_combo) AS trifecta_combo,
    MAX(trifecta_payout) AS trifecta_payout
  FROM feature_base
  GROUP BY race_id
)
"""


DISCOVERY_QUERY_EXPORTS = [
    QueryExport(
        filename="summary_meeting_day_lane.csv",
        query="""
{race_context_cte}
SELECT
  meeting_day_no,
  lane,
  COUNT(*) AS rows,
  ROUND(AVG(is_winner) * 100, 2) AS win_rate_pct,
  ROUND(AVG(is_top2) * 100, 2) AS top2_rate_pct,
  ROUND(AVG(is_top3) * 100, 2) AS top3_rate_pct,
  ROUND(AVG(national_win_rate), 3) AS avg_national_win_rate,
  ROUND(AVG(local_win_rate), 3) AS avg_local_win_rate,
  ROUND(AVG(motor_place_rate), 3) AS avg_motor_place_rate,
  ROUND(AVG(avg_start_timing), 3) AS avg_start_timing
FROM feature_base
GROUP BY 1, 2
ORDER BY 1, 2
""",
    ),
    QueryExport(
        filename="summary_context_signal_matrix.csv",
        query="""
{race_context_cte}
SELECT
  grade,
  meeting_day_no,
  COALESCE(lane1_class, 'unknown') AS lane1_class,
  COUNT(*) AS races,
  ROUND(AVG(lane1_national_win_rate), 3) AS avg_lane1_national_win_rate,
  ROUND(AVG(lane1_local_win_rate), 3) AS avg_lane1_local_win_rate,
  ROUND(AVG(lane1_motor_place_rate), 3) AS avg_lane1_motor_place_rate,
  ROUND(AVG(lane1_boat_place_rate), 3) AS avg_lane1_boat_place_rate,
  ROUND(AVG(wind_speed_m), 3) AS avg_wind_speed_m,
  ROUND(AVG(wave_height_cm), 3) AS avg_wave_height_cm,
  ROUND(SUM(CASE WHEN split_part(exacta_combo, '-', 1) = '1' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS lane1_head_rate_pct,
  ROUND(SUM(CASE WHEN exacta_combo = '1-2' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS exacta_1_2_rate_pct,
  ROUND(SUM(CASE WHEN exacta_combo = '1-3' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS exacta_1_3_rate_pct,
  ROUND(SUM(CASE WHEN exacta_combo = '1-4' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS exacta_1_4_rate_pct,
  ROUND(SUM(CASE WHEN exacta_combo = '1-5' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS exacta_1_5_rate_pct,
  ROUND(SUM(CASE WHEN exacta_combo = '1-6' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS exacta_1_6_rate_pct
FROM race_base
GROUP BY 1, 2, 3
ORDER BY grade, meeting_day_no, lane1_class
""",
    ),
    QueryExport(
        filename="summary_stadium_day_signal_matrix.csv",
        query="""
{race_context_cte}
SELECT
  stadium_code,
  stadium_name,
  grade,
  meeting_day_no,
  COUNT(*) AS races,
  ROUND(AVG(lane1_national_win_rate), 3) AS avg_lane1_national_win_rate,
  ROUND(AVG(lane1_motor_place_rate), 3) AS avg_lane1_motor_place_rate,
  ROUND(AVG(wind_speed_m), 3) AS avg_wind_speed_m,
  ROUND(SUM(CASE WHEN exacta_combo = '1-2' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS exacta_1_2_rate_pct,
  ROUND(SUM(CASE WHEN exacta_combo = '1-3' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS exacta_1_3_rate_pct,
  ROUND(SUM(CASE WHEN exacta_combo = '1-4' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS exacta_1_4_rate_pct,
  ROUND(SUM(CASE WHEN exacta_combo = '1-5' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS exacta_1_5_rate_pct,
  ROUND(SUM(CASE WHEN exacta_combo = '1-6' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS exacta_1_6_rate_pct
FROM race_base
GROUP BY 1, 2, 3, 4
ORDER BY stadium_code, grade, meeting_day_no
""",
    ),
    QueryExport(
        filename="summary_exacta_context_roi.csv",
        query="""
{race_context_cte}
, context_races AS (
  SELECT
    grade,
    meeting_day_no,
    COALESCE(lane1_class, 'unknown') AS lane1_class,
    COUNT(*) AS races
  FROM race_base
  GROUP BY 1, 2, 3
),
combo_hits AS (
  SELECT
    grade,
    meeting_day_no,
    COALESCE(lane1_class, 'unknown') AS lane1_class,
    exacta_combo,
    COUNT(*) AS hits,
    SUM(exacta_payout) AS return_yen
  FROM race_base
  WHERE exacta_combo IS NOT NULL
  GROUP BY 1, 2, 3, 4
)
SELECT
  h.grade,
  h.meeting_day_no,
  h.lane1_class,
  c.races,
  h.exacta_combo,
  h.hits,
  ROUND(h.hits * 100.0 / c.races, 3) AS hit_rate_pct,
  ROUND(h.return_yen / (c.races * 100.0) * 100, 2) AS flat_roi_pct,
  ROUND(h.return_yen * 1.0 / NULLIF(h.hits, 0), 1) AS avg_hit_payout
FROM combo_hits h
JOIN context_races c
  ON c.grade = h.grade
 AND c.meeting_day_no = h.meeting_day_no
 AND c.lane1_class = h.lane1_class
ORDER BY h.grade, h.meeting_day_no, h.lane1_class, flat_roi_pct DESC, h.hits DESC, h.exacta_combo
""",
    ),
]


def _write_query_csv(con: duckdb.DuckDBPyConnection, query: str, output_path: Path) -> int:
    result = con.execute(query)
    columns = [description[0] for description in result.description]
    rows = result.fetchall()
    ensure_dir(output_path.parent)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows(rows)
    return len(rows)


def _write_markdown(path: Path, lines: list[str]) -> None:
    ensure_dir(path.parent)
    path.write_text("\n".join(lines), encoding="utf-8-sig")


def export_correlation_study(
    db_path: Path,
    discovery_start: str,
    discovery_end: str,
    validation_start: str,
    validation_end: str,
    output_dir: Path,
) -> dict[str, int]:
    ensure_dir(output_dir)

    discovery_dir = output_dir / "discovery"
    validation_dir = output_dir / "validation"

    row_counts: dict[str, int] = {}
    for prefix, counts in [
        (
            "discovery",
            export_gpt_package(
                db_path=db_path,
                start_date=discovery_start,
                end_date=discovery_end,
                output_dir=discovery_dir,
            ),
        ),
        (
            "validation",
            export_gpt_package(
                db_path=db_path,
                start_date=validation_start,
                end_date=validation_end,
                output_dir=validation_dir,
            ),
        ),
    ]:
        for filename, count in counts.items():
            row_counts[f"{prefix}/{filename}"] = count

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        discovery_features_query = FEATURES_QUERY.format(start_date=discovery_start, end_date=discovery_end)
        race_context_cte = RACE_CONTEXT_CTE.format(features_query=discovery_features_query)

        for spec in DISCOVERY_QUERY_EXPORTS:
            query = spec.query.format(race_context_cte=race_context_cte)
            row_counts[f"discovery/{spec.filename}"] = _write_query_csv(con, query, discovery_dir / spec.filename)

        discovery_summary = con.execute(
            f"""
            WITH feature_base AS ({discovery_features_query})
            SELECT
              COUNT(DISTINCT race_id) AS race_count,
              COUNT(*) AS feature_rows,
              MIN(race_date) AS min_race_date,
              MAX(race_date) AS max_race_date
            FROM feature_base
            """
        ).fetchone()
        validation_summary = con.execute(
            f"""
            WITH feature_base AS ({FEATURES_QUERY.format(start_date=validation_start, end_date=validation_end)})
            SELECT
              COUNT(DISTINCT race_id) AS race_count,
              COUNT(*) AS feature_rows,
              MIN(race_date) AS min_race_date,
              MAX(race_date) AS max_race_date
            FROM feature_base
            """
        ).fetchone()
    finally:
        con.close()

    readme_lines = [
        "# Correlation Study Package",
        "",
        "## Purpose",
        "- `2025-01-01..2025-03-31` を発見用区間として使う。",
        "- `2025-04-01..2025-06-30` を固定の検証用区間として残す。",
        "- LLM にはまず discovery だけを見せて、相関仮説を作らせる。",
        "- validation は、仮説が固まるまで見せない。",
        "",
        "## Folders",
        f"- `discovery/`: {discovery_start} から {discovery_end}",
        f"- `validation/`: {validation_start} から {validation_end}",
        "",
        "## Discovery Summary",
        f"- race_count: {discovery_summary[0] or 0}",
        f"- feature_rows: {discovery_summary[1] or 0}",
        f"- min_race_date: {discovery_summary[2] or ''}",
        f"- max_race_date: {discovery_summary[3] or ''}",
        "",
        "## Validation Summary",
        f"- race_count: {validation_summary[0] or 0}",
        f"- feature_rows: {validation_summary[1] or 0}",
        f"- min_race_date: {validation_summary[2] or ''}",
        f"- max_race_date: {validation_summary[3] or ''}",
        "",
        "## Recommended Workflow",
        "1. discovery フォルダだけを GPT / Gemini に渡す。",
        "2. 相関仮説を 3〜5 本まで作らせる。",
        "3. validation フォルダは見せずに、ローカルでBT仕様に落とす。",
        "4. その後、validation 区間でだけ検証する。",
        "",
        "## Discovery-Only Files To Prioritize",
        "- `summary_context_signal_matrix.csv`",
        "- `summary_stadium_day_signal_matrix.csv`",
        "- `summary_exacta_context_roi.csv`",
        "- `summary_meeting_day_lane.csv`",
        "- `summary_stadium_lane.csv`",
        "- `summary_class_lane.csv`",
        "- `race_boat_features.csv`",
        "",
    ]
    _write_markdown(output_dir / "README.md", readme_lines)
    row_counts["README.md"] = 1

    prompt_lines = [
        "# Prompt For GPT",
        "",
        "以下は BOAT RACE の発見用データです。",
        "",
        "重要:",
        f"- discovery 区間は `{discovery_start}` から `{discovery_end}`",
        f"- validation 区間は `{validation_start}` から `{validation_end}`",
        "- 今回は discovery データだけを使ってください。",
        "- validation データはまだ見ないでください。",
        "- 目的は予想ではなく、検証可能な相関仮説を作ることです。",
        "",
        "見てほしいファイル:",
        "- `discovery/strategy_brief.md`",
        "- `discovery/race_boat_features.csv`",
        "- `discovery/summary_stadium_lane.csv`",
        "- `discovery/summary_class_lane.csv`",
        "- `discovery/summary_weather_lane.csv`",
        "- `discovery/summary_meeting_day_lane.csv`",
        "- `discovery/summary_context_signal_matrix.csv`",
        "- `discovery/summary_stadium_day_signal_matrix.csv`",
        "- `discovery/summary_exacta_context_roi.csv`",
        "",
        "やってほしいこと:",
        "1. 相関がありそうな仮説を 3〜5 本に絞る",
        "2. 各仮説について、具体的な条件を人が判定できるルールに落とす",
        "3. 各仮説について、どのファイルのどの傾向を根拠にしたかを明記する",
        "4. 過学習になりやすい点を添える",
        "5. 最後に、validation 区間で優先検証すべき仮説を 1 本だけ選ぶ",
        "",
        "禁止:",
        "- `is_winner`, `is_top2`, `is_top3` を未来特徴量として使うこと",
        "- validation データを前提に話を進めること",
        "- マーチンゲールや資金管理で勝とうとすること",
        "",
        "出力形式:",
        "- 仮説名",
        "- 条件",
        "- 買い目",
        "- 根拠",
        "- 崩れやすさ",
        "- validation 優先度",
        "",
    ]
    _write_markdown(output_dir / "prompt_for_gpt.md", prompt_lines)
    row_counts["prompt_for_gpt.md"] = 1

    gemini_prompt_lines = [
        "# Prompt For Gemini",
        "",
        "以下は BOAT RACE の発見用データです。",
        "",
        "前提:",
        f"- discovery 区間: `{discovery_start}` から `{discovery_end}`",
        f"- validation 区間: `{validation_start}` から `{validation_end}`",
        "- 今回は discovery データだけを材料にしてください。",
        "- validation 側の数字を見て最適化しないでください。",
        "",
        "ファイル優先順位:",
        "1. `discovery/summary_context_signal_matrix.csv`",
        "2. `discovery/summary_exacta_context_roi.csv`",
        "3. `discovery/summary_stadium_day_signal_matrix.csv`",
        "4. `discovery/summary_meeting_day_lane.csv`",
        "5. `discovery/race_boat_features.csv`",
        "",
        "依頼:",
        "- 相関がありそうな条件群を洗い出す",
        "- その中から、validation に回す価値がある仮説を 3 本以内に絞る",
        "- 最後に 1 本だけ本命を選ぶ",
        "",
        "条件:",
        "- 人が読めるルールにする",
        "- 予測モデル化の抽象論では逃げない",
        "- 資金管理ではなく条件と買い目に集中する",
        "- 根拠ファイルと根拠傾向を書く",
        "",
    ]
    _write_markdown(output_dir / "prompt_for_gemini.md", gemini_prompt_lines)
    row_counts["prompt_for_gemini.md"] = 1

    validation_note_lines = [
        "# Validation Holdout Note",
        "",
        f"- Validation period: `{validation_start}` から `{validation_end}`",
        "- このフォルダは discovery 仮説を見た後でだけ使う。",
        "- 先に開くとリークになるので、相関探索段階では使わない。",
        "",
    ]
    _write_markdown(validation_dir / "holdout_note.md", validation_note_lines)
    row_counts["validation/holdout_note.md"] = 1

    return row_counts
