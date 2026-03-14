from __future__ import annotations

import csv
from pathlib import Path

import duckdb

from boat_race_data.parsers import TERM_STAT_COLUMNS
from boat_race_data.utils import ensure_dir

RACES_COLUMNS = [
    "race_id",
    "race_date",
    "stadium_code",
    "stadium_name",
    "race_no",
    "meeting_title",
    "race_title",
    "distance_m",
    "deadline_time",
    "source_url",
    "fetched_at",
]

ENTRIES_COLUMNS = [
    "race_id",
    "race_date",
    "stadium_code",
    "race_no",
    "lane",
    "racer_id",
    "racer_name",
    "racer_class",
    "branch",
    "hometown",
    "age",
    "weight_kg",
    "photo_url",
    "f_count",
    "l_count",
    "avg_start_timing",
    "national_win_rate",
    "national_place_rate",
    "national_top3_rate",
    "local_win_rate",
    "local_place_rate",
    "local_top3_rate",
    "motor_no",
    "motor_place_rate",
    "motor_top3_rate",
    "boat_no",
    "boat_place_rate",
    "boat_top3_rate",
    "quick_view_race_no",
    "source_url",
    "fetched_at",
]

ODDS_2T_COLUMNS = [
    "race_id",
    "race_date",
    "stadium_code",
    "race_no",
    "bet_type",
    "first_lane",
    "second_lane",
    "odds",
    "odds_status",
    "source_url",
    "fetched_at",
]

ODDS_3T_COLUMNS = [
    "race_id",
    "race_date",
    "stadium_code",
    "race_no",
    "bet_type",
    "first_lane",
    "second_lane",
    "third_lane",
    "odds",
    "odds_status",
    "source_url",
    "fetched_at",
]

RESULTS_COLUMNS = [
    "race_id",
    "race_date",
    "stadium_code",
    "race_no",
    "first_place_lane",
    "second_place_lane",
    "third_place_lane",
    "fourth_place_lane",
    "fifth_place_lane",
    "sixth_place_lane",
    "finish_order_json",
    "start_timing_json",
    "payouts_json",
    "refund_info",
    "winning_technique",
    "note",
    "weather_condition",
    "weather_temp_c",
    "wind_speed_m",
    "wind_direction_code",
    "water_temp_c",
    "wave_height_cm",
    "exacta_combo",
    "exacta_payout",
    "quinella_combo",
    "quinella_payout",
    "trifecta_combo",
    "trifecta_payout",
    "trio_combo",
    "trio_payout",
    "source_url",
    "fetched_at",
]

BEFOREINFO_ENTRIES_COLUMNS = [
    "race_id",
    "race_date",
    "stadium_code",
    "race_no",
    "lane",
    "racer_id",
    "racer_name",
    "weight_kg_before",
    "adjust_weight_kg",
    "exhibition_time",
    "tilt",
    "course_entry",
    "start_exhibition_st",
    "start_exhibition_status",
    "weather_condition",
    "weather_temp_c",
    "wind_speed_m",
    "wind_direction_code",
    "water_temp_c",
    "wave_height_cm",
    "source_url",
    "fetched_at",
]

RACE_META_COLUMNS = [
    "race_id",
    "race_date",
    "stadium_code",
    "meeting_title",
    "grade",
    "grade_raw",
    "meeting_day_no",
    "meeting_day_label",
    "is_final_day",
    "source_url",
    "fetched_at",
]

BRONZE_COLUMNS = {
    "races": RACES_COLUMNS,
    "entries": ENTRIES_COLUMNS,
    "odds_2t": ODDS_2T_COLUMNS,
    "odds_3t": ODDS_3T_COLUMNS,
    "results": RESULTS_COLUMNS,
    "beforeinfo_entries": BEFOREINFO_ENTRIES_COLUMNS,
    "race_meta": RACE_META_COLUMNS,
    "racer_stats_term": TERM_STAT_COLUMNS,
}


def write_table_csv(path: Path, columns: list[str], rows: list[dict[str, object]]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def _csv_glob(bronze_root: Path, table_name: str) -> str:
    return str((bronze_root / table_name / "*.csv").resolve()).replace("\\", "/")


def _create_bronze_tables(con: duckdb.DuckDBPyConnection, bronze_root: Path) -> None:
    for table_name in BRONZE_COLUMNS:
        con.execute(
            f"""
            CREATE OR REPLACE TABLE bronze_{table_name} AS
            SELECT *
            FROM read_csv_auto(
              '{_csv_glob(bronze_root, table_name)}',
              header=true,
              union_by_name=true,
              nullstr='',
              all_varchar=true
            )
            """
        )


def _create_collection_views(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE OR REPLACE VIEW collection_day_summary AS
        WITH race_days AS (
          SELECT race_date, COUNT(*) AS race_count
          FROM races
          GROUP BY 1
        ),
        entry_days AS (
          SELECT race_date, COUNT(*) AS entry_count
          FROM entries
          GROUP BY 1
        ),
        odds_2t_days AS (
          SELECT race_date, COUNT(*) AS odds_2t_count
          FROM odds_2t
          GROUP BY 1
        ),
        odds_3t_days AS (
          SELECT race_date, COUNT(*) AS odds_3t_count
          FROM odds_3t
          GROUP BY 1
        ),
        result_days AS (
          SELECT race_date, COUNT(*) AS result_count
          FROM results
          GROUP BY 1
        ),
        beforeinfo_days AS (
          SELECT race_date, COUNT(*) AS beforeinfo_entry_count
          FROM beforeinfo_entries
          GROUP BY 1
        ),
        race_meta_days AS (
          SELECT race_date, COUNT(*) AS race_meta_count
          FROM race_meta
          GROUP BY 1
        )
        SELECT
          race_days.race_date,
          race_days.race_count,
          COALESCE(entry_days.entry_count, 0) AS entry_count,
          COALESCE(odds_2t_days.odds_2t_count, 0) AS odds_2t_count,
          COALESCE(odds_3t_days.odds_3t_count, 0) AS odds_3t_count,
          COALESCE(result_days.result_count, 0) AS result_count,
          COALESCE(beforeinfo_days.beforeinfo_entry_count, 0) AS beforeinfo_entry_count,
          COALESCE(race_meta_days.race_meta_count, 0) AS race_meta_count
        FROM race_days
        LEFT JOIN entry_days USING (race_date)
        LEFT JOIN odds_2t_days USING (race_date)
        LEFT JOIN odds_3t_days USING (race_date)
        LEFT JOIN result_days USING (race_date)
        LEFT JOIN beforeinfo_days USING (race_date)
        LEFT JOIN race_meta_days USING (race_date)
        ORDER BY race_date
        """
    )


def refresh_duckdb(db_path: Path, bronze_root: Path) -> None:
    ensure_dir(db_path.parent)
    con = duckdb.connect(str(db_path))
    try:
        _create_bronze_tables(con, bronze_root)
        con.execute(
            f"""
            CREATE OR REPLACE TABLE races AS
            SELECT
              CAST(race_id AS VARCHAR) AS race_id,
              CAST(race_date AS DATE) AS race_date,
              LPAD(CAST(stadium_code AS VARCHAR), 2, '0') AS stadium_code,
              CAST(stadium_name AS VARCHAR) AS stadium_name,
              CAST(race_no AS INTEGER) AS race_no,
              CAST(meeting_title AS VARCHAR) AS meeting_title,
              CAST(race_title AS VARCHAR) AS race_title,
              CAST(distance_m AS INTEGER) AS distance_m,
              CAST(deadline_time AS VARCHAR) AS deadline_time,
              CAST(source_url AS VARCHAR) AS source_url,
              CAST(fetched_at AS TIMESTAMP) AS fetched_at
            FROM bronze_races
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE TABLE entries AS
            SELECT
              CAST(race_id AS VARCHAR) AS race_id,
              CAST(race_date AS DATE) AS race_date,
              LPAD(CAST(stadium_code AS VARCHAR), 2, '0') AS stadium_code,
              CAST(race_no AS INTEGER) AS race_no,
              CAST(lane AS INTEGER) AS lane,
              CAST(racer_id AS INTEGER) AS racer_id,
              CAST(racer_name AS VARCHAR) AS racer_name,
              CAST(racer_class AS VARCHAR) AS racer_class,
              CAST(branch AS VARCHAR) AS branch,
              CAST(hometown AS VARCHAR) AS hometown,
              CAST(age AS INTEGER) AS age,
              CAST(weight_kg AS DOUBLE) AS weight_kg,
              CAST(photo_url AS VARCHAR) AS photo_url,
              CAST(f_count AS INTEGER) AS f_count,
              CAST(l_count AS INTEGER) AS l_count,
              CAST(avg_start_timing AS DOUBLE) AS avg_start_timing,
              CAST(national_win_rate AS DOUBLE) AS national_win_rate,
              CAST(national_place_rate AS DOUBLE) AS national_place_rate,
              CAST(national_top3_rate AS DOUBLE) AS national_top3_rate,
              CAST(local_win_rate AS DOUBLE) AS local_win_rate,
              CAST(local_place_rate AS DOUBLE) AS local_place_rate,
              CAST(local_top3_rate AS DOUBLE) AS local_top3_rate,
              CAST(motor_no AS INTEGER) AS motor_no,
              CAST(motor_place_rate AS DOUBLE) AS motor_place_rate,
              CAST(motor_top3_rate AS DOUBLE) AS motor_top3_rate,
              CAST(boat_no AS INTEGER) AS boat_no,
              CAST(boat_place_rate AS DOUBLE) AS boat_place_rate,
              CAST(boat_top3_rate AS DOUBLE) AS boat_top3_rate,
              CAST(quick_view_race_no AS INTEGER) AS quick_view_race_no,
              CAST(source_url AS VARCHAR) AS source_url,
              CAST(fetched_at AS TIMESTAMP) AS fetched_at
            FROM bronze_entries
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE TABLE odds_2t AS
            SELECT
              CAST(race_id AS VARCHAR) AS race_id,
              CAST(race_date AS DATE) AS race_date,
              LPAD(CAST(stadium_code AS VARCHAR), 2, '0') AS stadium_code,
              CAST(race_no AS INTEGER) AS race_no,
              CAST(bet_type AS VARCHAR) AS bet_type,
              CAST(first_lane AS INTEGER) AS first_lane,
              CAST(second_lane AS INTEGER) AS second_lane,
              CAST(odds AS DOUBLE) AS odds,
              CAST(odds_status AS VARCHAR) AS odds_status,
              CAST(source_url AS VARCHAR) AS source_url,
              CAST(fetched_at AS TIMESTAMP) AS fetched_at
            FROM bronze_odds_2t
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE TABLE odds_3t AS
            SELECT
              CAST(race_id AS VARCHAR) AS race_id,
              CAST(race_date AS DATE) AS race_date,
              LPAD(CAST(stadium_code AS VARCHAR), 2, '0') AS stadium_code,
              CAST(race_no AS INTEGER) AS race_no,
              CAST(bet_type AS VARCHAR) AS bet_type,
              CAST(first_lane AS INTEGER) AS first_lane,
              CAST(second_lane AS INTEGER) AS second_lane,
              CAST(third_lane AS INTEGER) AS third_lane,
              CAST(odds AS DOUBLE) AS odds,
              CAST(odds_status AS VARCHAR) AS odds_status,
              CAST(source_url AS VARCHAR) AS source_url,
              CAST(fetched_at AS TIMESTAMP) AS fetched_at
            FROM bronze_odds_3t
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE TABLE results AS
            SELECT
              CAST(race_id AS VARCHAR) AS race_id,
              CAST(race_date AS DATE) AS race_date,
              LPAD(CAST(stadium_code AS VARCHAR), 2, '0') AS stadium_code,
              CAST(race_no AS INTEGER) AS race_no,
              CAST(first_place_lane AS INTEGER) AS first_place_lane,
              CAST(second_place_lane AS INTEGER) AS second_place_lane,
              CAST(third_place_lane AS INTEGER) AS third_place_lane,
              CAST(fourth_place_lane AS INTEGER) AS fourth_place_lane,
              CAST(fifth_place_lane AS INTEGER) AS fifth_place_lane,
              CAST(sixth_place_lane AS INTEGER) AS sixth_place_lane,
              CAST(finish_order_json AS VARCHAR) AS finish_order_json,
              CAST(start_timing_json AS VARCHAR) AS start_timing_json,
              CAST(payouts_json AS VARCHAR) AS payouts_json,
              CAST(refund_info AS VARCHAR) AS refund_info,
              CAST(winning_technique AS VARCHAR) AS winning_technique,
              CAST(note AS VARCHAR) AS note,
              CAST(weather_condition AS VARCHAR) AS weather_condition,
              CAST(weather_temp_c AS DOUBLE) AS weather_temp_c,
              CAST(wind_speed_m AS INTEGER) AS wind_speed_m,
              CAST(wind_direction_code AS INTEGER) AS wind_direction_code,
              CAST(water_temp_c AS DOUBLE) AS water_temp_c,
              CAST(wave_height_cm AS INTEGER) AS wave_height_cm,
              CAST(exacta_combo AS VARCHAR) AS exacta_combo,
              CAST(exacta_payout AS INTEGER) AS exacta_payout,
              CAST(quinella_combo AS VARCHAR) AS quinella_combo,
              CAST(quinella_payout AS INTEGER) AS quinella_payout,
              CAST(trifecta_combo AS VARCHAR) AS trifecta_combo,
              CAST(trifecta_payout AS INTEGER) AS trifecta_payout,
              CAST(trio_combo AS VARCHAR) AS trio_combo,
              CAST(trio_payout AS INTEGER) AS trio_payout,
              CAST(source_url AS VARCHAR) AS source_url,
              CAST(fetched_at AS TIMESTAMP) AS fetched_at
            FROM bronze_results
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE TABLE racer_stats_term AS
            SELECT *
            FROM bronze_racer_stats_term
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE TABLE beforeinfo_entries AS
            SELECT
              CAST(race_id AS VARCHAR) AS race_id,
              CAST(race_date AS DATE) AS race_date,
              LPAD(CAST(stadium_code AS VARCHAR), 2, '0') AS stadium_code,
              CAST(race_no AS INTEGER) AS race_no,
              CAST(lane AS INTEGER) AS lane,
              CAST(racer_id AS INTEGER) AS racer_id,
              CAST(racer_name AS VARCHAR) AS racer_name,
              CAST(weight_kg_before AS DOUBLE) AS weight_kg_before,
              CAST(adjust_weight_kg AS DOUBLE) AS adjust_weight_kg,
              CAST(exhibition_time AS DOUBLE) AS exhibition_time,
              CAST(tilt AS DOUBLE) AS tilt,
              CAST(course_entry AS INTEGER) AS course_entry,
              CAST(start_exhibition_st AS DOUBLE) AS start_exhibition_st,
              CAST(start_exhibition_status AS VARCHAR) AS start_exhibition_status,
              CAST(weather_condition AS VARCHAR) AS weather_condition,
              CAST(weather_temp_c AS DOUBLE) AS weather_temp_c,
              CAST(wind_speed_m AS INTEGER) AS wind_speed_m,
              CAST(wind_direction_code AS INTEGER) AS wind_direction_code,
              CAST(water_temp_c AS DOUBLE) AS water_temp_c,
              CAST(wave_height_cm AS INTEGER) AS wave_height_cm,
              CAST(source_url AS VARCHAR) AS source_url,
              CAST(fetched_at AS TIMESTAMP) AS fetched_at
            FROM bronze_beforeinfo_entries
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE TABLE race_meta AS
            SELECT
              CAST(race_id AS VARCHAR) AS race_id,
              CAST(race_date AS DATE) AS race_date,
              LPAD(CAST(stadium_code AS VARCHAR), 2, '0') AS stadium_code,
              CAST(meeting_title AS VARCHAR) AS meeting_title,
              CAST(grade AS VARCHAR) AS grade,
              CAST(grade_raw AS VARCHAR) AS grade_raw,
              CAST(meeting_day_no AS INTEGER) AS meeting_day_no,
              CAST(meeting_day_label AS VARCHAR) AS meeting_day_label,
              CAST(is_final_day AS BOOLEAN) AS is_final_day,
              CAST(source_url AS VARCHAR) AS source_url,
              CAST(fetched_at AS TIMESTAMP) AS fetched_at
            FROM bronze_race_meta
            """
        )
        _create_collection_views(con)
    finally:
        con.close()
