from __future__ import annotations

import csv
from pathlib import Path

import duckdb


DB_PATH = Path(r"D:\boat\data\silver\boat_race.duckdb")
OUTPUT_DIR = Path(r"D:\boat\GPT\output\2024-01-01_2024-12-31_4wind_gemini_slice_pack")

START_DATE = "2024-01-01"
END_DATE = "2024-12-31"
STRATEGY_NAME = "4wind"
STRATEGY_LABEL = "Gemini_H002_Exacta_L4_WindyAttack"


BASE_QUERY = f"""
WITH feature_base AS (
  SELECT
    e.race_id,
    e.race_date,
    e.stadium_code,
    r.stadium_name,
    e.race_no,
    rm.grade,
    rm.meeting_day_no,
    rm.meeting_day_label,
    rm.is_final_day,
    e.lane,
    e.racer_class,
    e.national_win_rate,
    e.local_win_rate,
    bi.exhibition_time,
    bi.start_exhibition_st,
    COALESCE(bi.weather_condition, res.weather_condition) AS weather_condition,
    COALESCE(bi.wind_speed_m, res.wind_speed_m) AS wind_speed_m,
    COALESCE(bi.wave_height_cm, res.wave_height_cm) AS wave_height_cm,
    res.exacta_combo,
    res.exacta_payout
  FROM entries e
  JOIN races r USING (race_id)
  LEFT JOIN race_meta rm USING (race_id)
  LEFT JOIN beforeinfo_entries bi ON bi.race_id = e.race_id AND bi.lane = e.lane
  LEFT JOIN results res USING (race_id)
  WHERE e.race_date BETWEEN DATE '{START_DATE}' AND DATE '{END_DATE}'
),
entry_features AS (
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
    ROUND(
      start_exhibition_st - LAG(start_exhibition_st) OVER (PARTITION BY race_id ORDER BY lane),
      3
    ) AS st_diff_from_inside
  FROM feature_base
),
race_base AS (
  SELECT
    race_id,
    MIN(race_date) AS race_date,
    MIN(stadium_code) AS stadium_code,
    MIN(stadium_name) AS stadium_name,
    MIN(race_no) AS race_no,
    MAX(grade) AS grade,
    MAX(meeting_day_no) AS meeting_day_no,
    MAX(meeting_day_label) AS meeting_day_label,
    MAX(is_final_day) AS is_final_day,
    MAX(weather_condition) AS weather_condition,
    MAX(wind_speed_m) AS wind_speed_m,
    MAX(wave_height_cm) AS wave_height_cm,
    MAX(exacta_combo) AS exacta_combo,
    MAX(exacta_payout) AS exacta_payout,
    MAX(CASE WHEN lane = 1 THEN racer_class END) AS lane1_class,
    MAX(CASE WHEN lane = 3 THEN racer_class END) AS lane3_class,
    MAX(CASE WHEN lane = 4 THEN racer_class END) AS lane4_class,
    MAX(CASE WHEN lane = 1 THEN national_win_rate END) AS lane1_national_win_rate,
    MAX(CASE WHEN lane = 4 THEN national_win_rate END) AS lane4_national_win_rate,
    MAX(CASE WHEN lane = 1 THEN local_win_rate END) AS lane1_local_win_rate,
    MAX(CASE WHEN lane = 4 THEN local_win_rate END) AS lane4_local_win_rate,
    MAX(CASE WHEN lane = 4 THEN exhibition_time_rank END) AS lane4_exhibition_time_rank,
    MAX(CASE WHEN lane = 4 THEN exhibition_time_diff_from_top END) AS lane4_exhibition_time_diff_from_top,
    MAX(CASE WHEN lane = 4 THEN st_diff_from_inside END) AS lane4_st_diff_from_inside
  FROM entry_features
  GROUP BY race_id
),
plays AS (
  SELECT
    race_id,
    race_date,
    strftime(race_date, '%Y-%m') AS ym,
    stadium_code,
    stadium_name,
    race_no,
    COALESCE(grade, 'unknown') AS grade,
    meeting_day_no,
    COALESCE(meeting_day_label, 'unknown') AS meeting_day_label,
    CASE
      WHEN meeting_day_no IS NULL THEN 'unknown'
      WHEN meeting_day_no <= 2 THEN 'day1-2'
      WHEN meeting_day_no <= 4 THEN 'day3-4'
      ELSE 'day5+'
    END AS meeting_day_bucket,
    weather_condition,
    wind_speed_m,
    CASE
      WHEN wind_speed_m IS NULL THEN 'wind_unknown'
      WHEN wind_speed_m <= 2 THEN 'wind_0_2'
      WHEN wind_speed_m <= 4 THEN 'wind_3_4'
      WHEN wind_speed_m <= 6 THEN 'wind_5_6'
      ELSE 'wind_7_plus'
    END AS wind_bucket,
    wave_height_cm,
    CASE
      WHEN wave_height_cm IS NULL THEN 'wave_unknown'
      WHEN wave_height_cm <= 2 THEN 'wave_0_2'
      WHEN wave_height_cm <= 4 THEN 'wave_3_4'
      WHEN wave_height_cm <= 6 THEN 'wave_5_6'
      ELSE 'wave_7_plus'
    END AS wave_bucket,
    lane1_class,
    lane3_class,
    lane4_class,
    lane1_national_win_rate,
    lane4_national_win_rate,
    lane1_local_win_rate,
    lane4_local_win_rate,
    lane4_exhibition_time_rank,
    lane4_exhibition_time_diff_from_top,
    lane4_st_diff_from_inside,
    exacta_combo,
    exacta_payout,
    CASE WHEN exacta_combo IN ('4-1', '4-5', '4-6') THEN 1 ELSE 0 END AS is_hit_race,
    CASE WHEN exacta_combo IN ('4-1', '4-5', '4-6') THEN exacta_combo ELSE '' END AS hit_combo,
    CASE WHEN exacta_combo IN ('4-1', '4-5', '4-6') THEN exacta_payout ELSE 0 END AS return_yen,
    3 AS bet_count,
    300 AS stake_yen,
    ROUND(
      CASE
        WHEN exacta_combo IN ('4-1', '4-5', '4-6') THEN exacta_payout * 100.0 / 300.0
        ELSE 0
      END,
      2
    ) AS race_roi_pct
  FROM race_base
  WHERE exacta_combo IS NOT NULL
    AND exacta_payout IS NOT NULL
    AND wind_speed_m >= 4
    AND lane4_st_diff_from_inside <= -0.05
    AND lane4_exhibition_time_rank <= 3
)
"""


def write_query_csv(con: duckdb.DuckDBPyConnection, query: str, path: Path) -> int:
    result = con.execute(query)
    cols = [d[0] for d in result.description]
    rows = result.fetchall()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(cols)
        writer.writerows(rows)
    return len(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8-sig")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        plays_rows = write_query_csv(
            con,
            BASE_QUERY + "SELECT * FROM plays ORDER BY race_date, stadium_code, race_no",
            OUTPUT_DIR / "plays_4wind_2024.csv",
        )

        agg_stadium_wind_rows = write_query_csv(
            con,
            BASE_QUERY
            + """
            SELECT
              stadium_code,
              stadium_name,
              wind_bucket,
              COUNT(*) AS played_races,
              SUM(bet_count) AS bet_count,
              SUM(is_hit_race) AS hit_races,
              SUM(return_yen) AS return_yen,
              ROUND(SUM(return_yen) * 100.0 / NULLIF(SUM(stake_yen), 0), 2) AS roi_pct,
              ROUND(AVG(wind_speed_m), 3) AS avg_wind_speed_m,
              ROUND(AVG(wave_height_cm), 3) AS avg_wave_height_cm,
              ROUND(AVG(lane4_st_diff_from_inside), 3) AS avg_lane4_st_diff_from_inside,
              ROUND(AVG(lane4_exhibition_time_diff_from_top), 3) AS avg_lane4_exhibition_time_diff_from_top
            FROM plays
            GROUP BY 1, 2, 3
            ORDER BY played_races DESC, roi_pct DESC, stadium_code, wind_bucket
            """,
            OUTPUT_DIR / "agg_stadium_wind_4wind_2024.csv",
        )

        agg_stadium_month_rows = write_query_csv(
            con,
            BASE_QUERY
            + """
            SELECT
              stadium_code,
              stadium_name,
              ym,
              COUNT(*) AS played_races,
              SUM(bet_count) AS bet_count,
              SUM(is_hit_race) AS hit_races,
              SUM(return_yen) AS return_yen,
              ROUND(SUM(return_yen) * 100.0 / NULLIF(SUM(stake_yen), 0), 2) AS roi_pct
            FROM plays
            GROUP BY 1, 2, 3
            ORDER BY stadium_code, ym
            """,
            OUTPUT_DIR / "agg_stadium_month_4wind_2024.csv",
        )

        agg_meetingday_wind_rows = write_query_csv(
            con,
            BASE_QUERY
            + """
            SELECT
              meeting_day_bucket,
              wind_bucket,
              COUNT(*) AS played_races,
              SUM(bet_count) AS bet_count,
              SUM(is_hit_race) AS hit_races,
              SUM(return_yen) AS return_yen,
              ROUND(SUM(return_yen) * 100.0 / NULLIF(SUM(stake_yen), 0), 2) AS roi_pct
            FROM plays
            GROUP BY 1, 2
            ORDER BY meeting_day_bucket, wind_bucket
            """,
            OUTPUT_DIR / "agg_meetingday_wind_4wind_2024.csv",
        )

        agg_wave_wind_rows = write_query_csv(
            con,
            BASE_QUERY
            + """
            SELECT
              wave_bucket,
              wind_bucket,
              COUNT(*) AS played_races,
              SUM(bet_count) AS bet_count,
              SUM(is_hit_race) AS hit_races,
              SUM(return_yen) AS return_yen,
              ROUND(SUM(return_yen) * 100.0 / NULLIF(SUM(stake_yen), 0), 2) AS roi_pct
            FROM plays
            GROUP BY 1, 2
            ORDER BY wave_bucket, wind_bucket
            """,
            OUTPUT_DIR / "agg_wave_wind_4wind_2024.csv",
        )

        summary = con.execute(
            BASE_QUERY
            + """
            SELECT
              COUNT(*) AS played_races,
              SUM(bet_count) AS bet_count,
              SUM(is_hit_race) AS hit_races,
              SUM(return_yen) AS return_yen,
              ROUND(SUM(return_yen) * 100.0 / NULLIF(SUM(stake_yen), 0), 2) AS roi_pct
            FROM plays
            """
        ).fetchone()
    finally:
        con.close()

    write_text(
        OUTPUT_DIR / "README.md",
        "\n".join(
            [
                "# 4Wind Gemini Slice Pack",
                "",
                "- target strategy: `4wind` / `Gemini_H002_Exacta_L4_WindyAttack`",
                f"- discovery period: `{START_DATE}..{END_DATE}`",
                "- intended use: new Gemini thread for slice analysis",
                "- file count: `9`",
                "",
                "## Upload Order",
                "",
                "1. `work_summary.md`",
                "2. `strategy_definition_4wind.md`",
                "3. `data_dictionary.md`",
                "4. `prompt_4wind_slice_analysis.md`",
                "5. `plays_4wind_2024.csv`",
                "6. `agg_stadium_wind_4wind_2024.csv`",
                "7. `agg_stadium_month_4wind_2024.csv`",
                "8. `agg_meetingday_wind_4wind_2024.csv`",
                "9. `agg_wave_wind_4wind_2024.csv`",
            ]
        ),
    )

    write_text(
        OUTPUT_DIR / "work_summary.md",
        "\n".join(
            [
                "# Work Summary For Gemini",
                "",
                "## Purpose",
                "",
                "- We are not asking for a brand-new zero-base strategy here.",
                "- We already normalized one Gemini-derived branch called `4wind`.",
                "- This thread is only for slicing the 2024 discovery period and identifying where that branch is structurally strong.",
                "",
                "## Important Rules",
                "",
                "- Treat `2024-01-01..2024-12-31` as discovery material only.",
                "- Do not assume access to later years.",
                "- Do not optimize to unseen data.",
                "- Focus on interpretable strength factors rather than complicated combinations.",
                "",
                "## Current Known Facts",
                "",
                f"- 2024 played races: `{summary[0]}`",
                f"- 2024 bet count: `{summary[1]}`",
                f"- 2024 hit races: `{summary[2]}`",
                f"- 2024 total return: `{summary[3]}` yen",
                f"- 2024 total ROI: `{summary[4]}%`",
                "",
                "## What We Want From You",
                "",
                "- Identify which context slices seem to explain the strength of `4wind`.",
                "- Prefer factors such as stadium, wind bucket, wave bucket, month, meeting-day bucket, and combinations of those.",
                "- Point out where the edge looks broad versus where it looks concentrated.",
                "- Suggest simple strengthening filters or exclusion filters, but do not turn this into a wildly overfit rule.",
            ]
        ),
    )

    write_text(
        OUTPUT_DIR / "strategy_definition_4wind.md",
        "\n".join(
            [
                "# Strategy Definition: 4Wind",
                "",
                f"- normalized strategy name: `{STRATEGY_LABEL}`",
                "- ticket type: `2連単`",
                "- fixed combos: `4-1`, `4-5`, `4-6`",
                "",
                "## Rule",
                "",
                "Play only when all conditions are true:",
                "",
                "- `wind_speed_m >= 4`",
                "- `lane4_st_diff_from_inside <= -0.05`",
                "- `lane4_exhibition_time_rank <= 3`",
                "",
                "## Interpretation",
                "",
                "- lane 4 attacks under windy conditions",
                "- lane 4 is stepping ahead of lane 3 at exhibition ST",
                "- lane 4 is not weak on exhibition relative to the race",
                "",
                "## What We Need",
                "",
                "- not a new strategy from scratch",
                "- a decomposition of where this rule is actually strong",
                "- especially whether the edge is driven by stadium, wind, wave, month, or meeting-day structure",
            ]
        ),
    )

    write_text(
        OUTPUT_DIR / "data_dictionary.md",
        "\n".join(
            [
                "# Data Dictionary",
                "",
                "## Shared Concepts",
                "",
                "- one played race means one race where the 4wind rule fired",
                "- stake is fixed at `300 yen` per played race because the rule buys 3 exacta combos",
                "- `return_yen` is the official exacta payout if one of `4-1`, `4-5`, `4-6` hit, else `0`",
                "- `roi_pct` is always `return / stake * 100` on the aggregated slice",
                "",
                "## plays_4wind_2024.csv",
                "",
                "- `race_id`: unique race key",
                "- `race_date`: race date",
                "- `ym`: year-month bucket",
                "- `stadium_code`, `stadium_name`: venue identifiers",
                "- `race_no`: race number",
                "- `grade`: meeting grade",
                "- `meeting_day_no`, `meeting_day_label`, `meeting_day_bucket`: meeting progression features",
                "- `weather_condition`: weather text",
                "- `wind_speed_m`, `wind_bucket`: wind context",
                "- `wave_height_cm`, `wave_bucket`: wave context",
                "- `lane1_class`, `lane3_class`, `lane4_class`: class structure around the attack lane",
                "- `lane1_national_win_rate`, `lane4_national_win_rate`: long-term strength markers",
                "- `lane1_local_win_rate`, `lane4_local_win_rate`: local strength markers",
                "- `lane4_exhibition_time_rank`: race-internal exhibition rank for lane 4",
                "- `lane4_exhibition_time_diff_from_top`: lane 4 exhibition gap from race best",
                "- `lane4_st_diff_from_inside`: lane 4 exhibition ST minus lane 3 ST",
                "- `exacta_combo`, `exacta_payout`: official exacta result",
                "- `is_hit_race`: 1 if the strategy hit on that race, else 0",
                "- `hit_combo`: the matched hit combo if any",
                "- `return_yen`: return from the race under this strategy",
                "- `bet_count`: fixed at 3",
                "- `stake_yen`: fixed at 300",
                "- `race_roi_pct`: single-race ROI under this rule",
                "",
                "## Aggregated CSVs",
                "",
                "- `played_races`: number of races where the rule fired in that slice",
                "- `bet_count`: total bets in that slice",
                "- `hit_races`: races where one of the 3 combos hit",
                "- `return_yen`: total return in yen",
                "- `roi_pct`: total return divided by total stake times 100",
                "- `avg_*`: average numeric context values inside the slice",
            ]
        ),
    )

    write_text(
        OUTPUT_DIR / "prompt_4wind_slice_analysis.md",
        "\n".join(
            [
                "# Prompt: 4Wind Slice Analysis",
                "",
                "You are analyzing one already-defined BOAT RACE rule called `4wind`.",
                "",
                "This is not a zero-base ideation task.",
                "This is a decomposition task: find what seems to explain the strength of the rule inside the 2024 discovery period.",
                "",
                "## Files",
                "",
                "- `work_summary.md`",
                "- `strategy_definition_4wind.md`",
                "- `data_dictionary.md`",
                "- `plays_4wind_2024.csv`",
                "- `agg_stadium_wind_4wind_2024.csv`",
                "- `agg_stadium_month_4wind_2024.csv`",
                "- `agg_meetingday_wind_4wind_2024.csv`",
                "- `agg_wave_wind_4wind_2024.csv`",
                "",
                "## What To Do",
                "",
                "- identify which slices look strongest",
                "- separate broad strength from narrow spikes",
                "- tell us whether stadium, wind bucket, wave bucket, month, or meeting-day bucket looks most explanatory",
                "- propose simple strengthening filters or exclusion filters",
                "- avoid overfit combinations unless you explicitly label them as fragile",
                "",
                "## Output Format",
                "",
                "1. Overall read on where the edge seems to come from",
                "2. Top slice findings",
                "3. Which factors seem genuinely explanatory",
                "4. Which factors look noisy or overfit",
                "5. Up to 3 candidate refinement rules",
                "6. Which one refinement should be tested first",
                "",
                "## Guardrails",
                "",
                "- treat 2024 as discovery only",
                "- do not assume unseen future data",
                "- do not optimize using unknown 2025 results",
                "- prefer simple rules that can be backtested directly",
            ]
        ),
    )

    print(f"output_dir={OUTPUT_DIR}")
    print(f"plays_4wind_2024.csv rows={plays_rows}")
    print(f"agg_stadium_wind_4wind_2024.csv rows={agg_stadium_wind_rows}")
    print(f"agg_stadium_month_4wind_2024.csv rows={agg_stadium_month_rows}")
    print(f"agg_meetingday_wind_4wind_2024.csv rows={agg_meetingday_wind_rows}")
    print(f"agg_wave_wind_4wind_2024.csv rows={agg_wave_wind_rows}")


if __name__ == "__main__":
    main()
