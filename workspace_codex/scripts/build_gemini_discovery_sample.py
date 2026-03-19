from __future__ import annotations

import csv
from pathlib import Path

import duckdb


DB_PATH = Path(r"D:\boat\data\silver\boat_race.duckdb")
OUTPUT_DIR = Path(r"D:\boat\GPT\output\2024-01-01_2024-04-30_gemini_discovery")
PROMPT_PATH = Path(r"D:\boat\GPT\prompts\gemini_request_2024-01-01_2024-04-30_discovery.md")

START_DATE = "2024-01-01"
END_DATE = "2024-04-30"
SAMPLE_RACES = 1000
SEED = 20260319


def write_csv(con: duckdb.DuckDBPyConnection, query: str, path: Path) -> int:
    result = con.execute(query)
    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(columns)
        writer.writerows(rows)
    return len(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8-sig")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        sampled_race_ids_query = f"""
        WITH eligible AS (
          SELECT DISTINCT race_id
          FROM races
          WHERE race_date BETWEEN DATE '{START_DATE}' AND DATE '{END_DATE}'
        )
        SELECT race_id
        FROM eligible
        ORDER BY hash(race_id || '{SEED}')
        LIMIT {SAMPLE_RACES}
        """
        sampled_ids = [row[0] for row in con.execute(sampled_race_ids_query).fetchall()]
        if len(sampled_ids) != SAMPLE_RACES:
            raise RuntimeError(f"expected {SAMPLE_RACES} race_ids, got {len(sampled_ids)}")

        sampled_ids_sql = ", ".join("'" + rid + "'" for rid in sampled_ids)

        race_sample_query = f"""
        WITH sample_races AS (
          SELECT race_id
          FROM (VALUES {", ".join(f"('{rid}')" for rid in sampled_ids)}) AS t(race_id)
        ),
        feature_base AS (
          SELECT
            e.race_id,
            e.race_date,
            e.stadium_code,
            r.stadium_name,
            e.race_no,
            r.distance_m,
            rm.grade,
            rm.meeting_day_no,
            rm.meeting_day_label,
            rm.is_final_day,
            COALESCE(bi.weather_condition, res.weather_condition) AS weather_condition,
            COALESCE(bi.weather_temp_c, res.weather_temp_c) AS weather_temp_c,
            COALESCE(bi.wind_speed_m, res.wind_speed_m) AS wind_speed_m,
            COALESCE(bi.wind_direction_code, res.wind_direction_code) AS wind_direction_code,
            COALESCE(bi.water_temp_c, res.water_temp_c) AS water_temp_c,
            COALESCE(bi.wave_height_cm, res.wave_height_cm) AS wave_height_cm,
            e.lane,
            e.racer_class,
            e.national_win_rate,
            e.local_win_rate,
            e.motor_place_rate,
            bi.exhibition_time,
            res.first_place_lane,
            res.second_place_lane,
            res.third_place_lane,
            res.exacta_combo,
            res.exacta_payout,
            res.trifecta_combo,
            res.trifecta_payout,
            res.winning_technique
          FROM entries e
          JOIN sample_races s USING (race_id)
          JOIN races r USING (race_id)
          LEFT JOIN race_meta rm USING (race_id)
          LEFT JOIN beforeinfo_entries bi ON bi.race_id = e.race_id AND bi.lane = e.lane
          LEFT JOIN results res USING (race_id)
        ),
        race_agg AS (
          SELECT
            race_id,
            MIN(race_date) AS race_date,
            MIN(stadium_code) AS stadium_code,
            MIN(stadium_name) AS stadium_name,
            MIN(race_no) AS race_no,
            MIN(distance_m) AS distance_m,
            MIN(grade) AS grade,
            MAX(meeting_day_no) AS meeting_day_no,
            MIN(meeting_day_label) AS meeting_day_label,
            MAX(is_final_day) AS is_final_day,
            MIN(weather_condition) AS weather_condition,
            MAX(weather_temp_c) AS weather_temp_c,
            MAX(wind_speed_m) AS wind_speed_m,
            MAX(wind_direction_code) AS wind_direction_code,
            MAX(water_temp_c) AS water_temp_c,
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
            ROUND(AVG(national_win_rate), 3) AS avg_national_win_rate,
            ROUND(MAX(national_win_rate), 3) AS max_national_win_rate,
            ROUND(MAX(CASE WHEN lane = 1 THEN national_win_rate END), 3) AS lane1_national_win_rate,
            ROUND(MAX(CASE WHEN lane = 1 THEN local_win_rate END), 3) AS lane1_local_win_rate,
            ROUND(MAX(CASE WHEN lane = 1 THEN motor_place_rate END), 3) AS lane1_motor_place_rate,
            ROUND(MIN(exhibition_time), 3) AS best_exhibition_time,
            MIN_BY(lane, exhibition_time) FILTER (WHERE exhibition_time IS NOT NULL) AS best_exhibition_lane,
            ROUND(MAX(CASE WHEN lane = 1 THEN exhibition_time END) - MIN(exhibition_time), 3) AS lane1_vs_best_exhibition_diff,
            CASE
              WHEN MAX(exacta_payout) >= 5000 OR MAX(trifecta_payout) >= 10000 THEN 1
              ELSE 0
            END AS is_rough_race
          FROM feature_base
          GROUP BY race_id
        )
        SELECT *
        FROM race_agg
        ORDER BY race_date, stadium_code, race_no
        """

        entry_sample_query = f"""
        WITH sample_races AS (
          SELECT race_id
          FROM (VALUES {", ".join(f"('{rid}')" for rid in sampled_ids)}) AS t(race_id)
        ),
        feature_base AS (
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
            CASE WHEN res.first_place_lane = e.lane THEN 1 ELSE 0 END AS is_winner,
            CASE WHEN e.lane IN (res.first_place_lane, res.second_place_lane) THEN 1 ELSE 0 END AS is_top2,
            CASE WHEN e.lane IN (res.first_place_lane, res.second_place_lane, res.third_place_lane) THEN 1 ELSE 0 END AS is_top3,
            DENSE_RANK() OVER (
              PARTITION BY e.race_id
              ORDER BY
                CASE WHEN bi.exhibition_time IS NULL THEN 1 ELSE 0 END,
                bi.exhibition_time ASC,
                e.lane ASC
            ) AS exhibition_time_rank,
            ROUND(
              bi.exhibition_time
              - MIN(bi.exhibition_time) OVER (PARTITION BY e.race_id),
              3
            ) AS exhibition_time_diff_from_top,
            DENSE_RANK() OVER (
              PARTITION BY e.race_id
              ORDER BY
                CASE WHEN e.national_win_rate IS NULL THEN 1 ELSE 0 END,
                e.national_win_rate DESC,
                e.lane ASC
            ) AS win_rate_rank,
            ROUND(
              bi.start_exhibition_st
              - LAG(bi.start_exhibition_st) OVER (PARTITION BY e.race_id ORDER BY e.lane),
              3
            ) AS st_diff_from_inside,
            CASE
              WHEN e.branch IS NOT NULL AND e.branch = e.stadium_code THEN 1
              ELSE 0
            END AS is_hometown
          FROM entries e
          JOIN sample_races s USING (race_id)
          JOIN races r USING (race_id)
          LEFT JOIN race_meta rm USING (race_id)
          LEFT JOIN beforeinfo_entries bi ON bi.race_id = e.race_id AND bi.lane = e.lane
          LEFT JOIN results res USING (race_id)
        )
        SELECT *
        FROM feature_base
        ORDER BY race_date, stadium_code, race_no, lane
        """

        race_rows = write_csv(con, race_sample_query, OUTPUT_DIR / "races_sample.csv")
        entry_rows = write_csv(con, entry_sample_query, OUTPUT_DIR / "entries_sample.csv")

        summary = con.execute(
            f"""
            SELECT
              COUNT(DISTINCT race_id) AS sampled_races,
              MIN(race_date) AS min_race_date,
              MAX(race_date) AS max_race_date
            FROM races
            WHERE race_id IN ({sampled_ids_sql})
            """
        ).fetchone()

        dict_text = f"""# Data Dictionary

## Package Scope

- discovery period: `{START_DATE}` to `{END_DATE}`
- sample size: `{SAMPLE_RACES}` races
- sampling rule: deterministic hash order by `race_id` with seed `{SEED}`
- included files:
  - `races_sample.csv`
  - `entries_sample.csv`
  - `data_dictionary.md`
  - `package_note.md`
  - `gemini_request_2024-01-01_2024-04-30_discovery.md`

## Join Key

- `race_id` is the primary join key between race-level and entry-level files.

## races_sample.csv

- `race_id`: unique race key
- `race_date`: race date
- `stadium_code`: 2-digit stadium code
- `stadium_name`: stadium name
- `race_no`: race number
- `distance_m`: course distance in meters
- `grade`: meeting grade such as SG/G1/general
- `meeting_day_no`: numeric day index within the meeting
- `meeting_day_label`: text label for meeting day
- `is_final_day`: 1 if final day, else 0
- `weather_condition`: resolved weather text
- `weather_temp_c`: air temperature in Celsius
- `wind_speed_m`: wind speed in m/s
- `wind_direction_code`: official wind-direction code
- `water_temp_c`: water temperature in Celsius
- `wave_height_cm`: wave height in cm
- `first_place_lane`: winning lane
- `second_place_lane`: second-place lane
- `third_place_lane`: third-place lane
- `exacta_combo`: official 2T combo
- `exacta_payout`: official 2T payout in yen
- `trifecta_combo`: official 3T combo
- `trifecta_payout`: official 3T payout in yen
- `winning_technique`: official kimarite
- `a1_count`: number of A1 racers in the field
- `a2_count`: number of A2 racers in the field
- `b1_count`: number of B1 racers in the field
- `b2_count`: number of B2 racers in the field
- `avg_national_win_rate`: race-level average of national win rate across 6 boats
- `max_national_win_rate`: highest national win rate in the race
- `lane1_national_win_rate`: lane-1 racer national win rate
- `lane1_local_win_rate`: lane-1 racer local win rate
- `lane1_motor_place_rate`: lane-1 racer motor place rate
- `best_exhibition_time`: fastest exhibition time in the race
- `best_exhibition_lane`: lane with fastest exhibition time
- `lane1_vs_best_exhibition_diff`: lane-1 exhibition time minus best exhibition time
- `is_rough_race`: 1 if exacta payout >= 5000 or trifecta payout >= 10000, else 0

## entries_sample.csv

- `race_id`: foreign key to race-level file
- `race_date`: race date
- `stadium_code`: 2-digit stadium code
- `stadium_name`: stadium name
- `race_no`: race number
- `grade`: meeting grade
- `meeting_day_no`: numeric day index within the meeting
- `meeting_day_label`: text label for meeting day
- `is_final_day`: 1 if final day, else 0
- `lane`: official lane number
- `racer_id`: racer id
- `racer_name`: racer name
- `racer_class`: A1/A2/B1/B2
- `branch`: branch text from source
- `hometown`: hometown text from source
- `age`: racer age
- `weight_kg`: listed racer weight
- `weight_kg_before`: pre-race weight
- `adjust_weight_kg`: adjustment weight
- `f_count`: F count
- `l_count`: L count
- `avg_start_timing`: average start timing
- `national_win_rate`: national win rate
- `national_place_rate`: national place rate
- `national_top3_rate`: national top-3 rate
- `local_win_rate`: local win rate
- `local_place_rate`: local place rate
- `local_top3_rate`: local top-3 rate
- `motor_no`: motor number
- `motor_place_rate`: motor place rate
- `motor_top3_rate`: motor top-3 rate
- `boat_no`: boat number
- `boat_place_rate`: boat place rate
- `boat_top3_rate`: boat top-3 rate
- `exhibition_time`: exhibition time
- `tilt`: tilt
- `course_entry`: exhibition course entry
- `start_exhibition_st`: exhibition ST
- `start_exhibition_status`: exhibition status text
- `weather_condition`: resolved weather text
- `weather_temp_c`: air temperature in Celsius
- `wind_speed_m`: wind speed in m/s
- `wind_direction_code`: official wind-direction code
- `water_temp_c`: water temperature in Celsius
- `wave_height_cm`: wave height in cm
- `first_place_lane`: winning lane
- `second_place_lane`: second-place lane
- `third_place_lane`: third-place lane
- `is_winner`: 1 if this lane won
- `is_top2`: 1 if this lane finished top 2
- `is_top3`: 1 if this lane finished top 3
- `exhibition_time_rank`: race-internal rank of exhibition time, smaller is better
- `exhibition_time_diff_from_top`: exhibition time minus best exhibition time in the same race
- `win_rate_rank`: race-internal rank of national win rate, smaller is stronger
- `st_diff_from_inside`: exhibition ST minus inside-adjacent lane ST; null for lane 1
- `is_hometown`: 1 if `branch == stadium_code`, else 0

## Notes

- This package is for discovery only.
- Existing human strategy names and ROI summaries should not be used.
- These files are intentionally compact to stay well under a 10-file upload limit.
"""
        write_text(OUTPUT_DIR / "data_dictionary.md", dict_text)

        note_text = f"""# Package Note

- prompt file copied into this folder for one-batch upload convenience
- sampled races: {summary[0]}
- date range inside sampled set: {summary[1]} to {summary[2]}
- `races_sample.csv` rows: {race_rows}
- `entries_sample.csv` rows: {entry_rows}

## Suggested Upload Set

1. `gemini_request_2024-01-01_2024-04-30_discovery.md`
2. `data_dictionary.md`
3. `races_sample.csv`
4. `entries_sample.csv`

This keeps the first pass to 4 files total.
"""
        write_text(OUTPUT_DIR / "package_note.md", note_text)

        prompt_copy = OUTPUT_DIR / PROMPT_PATH.name
        prompt_copy.write_text(PROMPT_PATH.read_text(encoding="utf-8-sig"), encoding="utf-8-sig")

        print(f"sampled_races={summary[0]}")
        print(f"races_sample_rows={race_rows}")
        print(f"entries_sample_rows={entry_rows}")
        print(f"output_dir={OUTPUT_DIR}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
