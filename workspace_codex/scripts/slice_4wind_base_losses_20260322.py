from __future__ import annotations

import csv
from pathlib import Path

import duckdb


DB_PATH = Path(r"D:\boat\data\silver\boat_race.duckdb")
OUTPUT_DIR = Path(r"D:\boat\reports\strategies\gemini_registry\4wind\base_loss_slice_20260322")
START_DATE = "2025-04-01"
END_DATE = "2026-03-20"


BASE_CTE = """
WITH feature_base AS (
  SELECT
    e.race_id,
    e.race_date,
    e.stadium_code,
    r.stadium_name,
    e.race_no,
    e.lane,
    bi.exhibition_time,
    bi.start_exhibition_st,
    COALESCE(bi.wind_speed_m, res.wind_speed_m) AS wind_speed_m,
    COALESCE(bi.wave_height_cm, res.wave_height_cm) AS wave_height_cm,
    res.exacta_combo,
    res.exacta_payout
  FROM entries e
  JOIN races r USING (race_id)
  LEFT JOIN beforeinfo_entries bi ON bi.race_id = e.race_id AND bi.lane = e.lane
  LEFT JOIN results res USING (race_id)
  WHERE e.race_date BETWEEN DATE '{start_date}' AND DATE '{end_date}'
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
    MAX(wind_speed_m) AS wind_speed_m,
    MAX(wave_height_cm) AS wave_height_cm,
    MAX(exacta_combo) AS exacta_combo,
    MAX(exacta_payout) AS exacta_payout,
    MAX(CASE WHEN lane = 4 THEN exhibition_time_rank END) AS lane4_exhibition_time_rank,
    MAX(CASE WHEN lane = 4 THEN st_diff_from_inside END) AS lane4_st_diff_from_inside
  FROM entry_features
  GROUP BY race_id
),
odds_dedup AS (
  SELECT
    race_id,
    first_lane,
    second_lane,
    AVG(odds) AS avg_odds
  FROM odds_2t
  WHERE race_date BETWEEN DATE '{start_date}' AND DATE '{end_date}'
    AND (first_lane, second_lane) IN ((4, 1), (4, 5), (4, 6))
  GROUP BY race_id, first_lane, second_lane
),
race_odds AS (
  SELECT
    race_id,
    MAX(CASE WHEN first_lane = 4 AND second_lane = 1 THEN avg_odds END) AS odds_41,
    MAX(CASE WHEN first_lane = 4 AND second_lane = 5 THEN avg_odds END) AS odds_45,
    MAX(CASE WHEN first_lane = 4 AND second_lane = 6 THEN avg_odds END) AS odds_46
  FROM odds_dedup
  GROUP BY race_id
),
played AS (
  SELECT
    rb.*,
    ro.odds_41,
    ro.odds_45,
    ro.odds_46,
    LEAST(ro.odds_41, ro.odds_45, ro.odds_46) AS min_odds_played,
    GREATEST(ro.odds_41, ro.odds_45, ro.odds_46) AS max_odds_played,
    CASE WHEN rb.exacta_combo IN ('4-1', '4-5', '4-6') THEN 1 ELSE 0 END AS is_hit,
    CASE WHEN rb.exacta_combo IN ('4-1', '4-5', '4-6') THEN rb.exacta_payout ELSE 0 END AS realized_payout,
    300 AS stake_yen,
    CASE
      WHEN rb.wind_speed_m = 4 THEN 'wind_4'
      WHEN rb.wind_speed_m BETWEEN 5 AND 6 THEN 'wind_5_6'
      WHEN rb.wind_speed_m >= 7 THEN 'wind_7_plus'
      ELSE 'wind_other'
    END AS wind_bucket,
    CASE
      WHEN LEAST(ro.odds_41, ro.odds_45, ro.odds_46) < 10 THEN 'lt10'
      WHEN LEAST(ro.odds_41, ro.odds_45, ro.odds_46) < 15 THEN '10_15'
      WHEN LEAST(ro.odds_41, ro.odds_45, ro.odds_46) < 20 THEN '15_20'
      WHEN LEAST(ro.odds_41, ro.odds_45, ro.odds_46) < 30 THEN '20_30'
      WHEN LEAST(ro.odds_41, ro.odds_45, ro.odds_46) < 50 THEN '30_50'
      ELSE '50_plus'
    END AS min_odds_bucket
  FROM race_base rb
  JOIN race_odds ro USING (race_id)
  WHERE rb.exacta_combo IS NOT NULL
    AND rb.exacta_payout IS NOT NULL
    AND rb.wind_speed_m IS NOT NULL
    AND rb.wind_speed_m >= 4
    AND rb.lane4_st_diff_from_inside IS NOT NULL
    AND rb.lane4_st_diff_from_inside <= -0.05
    AND rb.lane4_exhibition_time_rank IS NOT NULL
    AND rb.lane4_exhibition_time_rank <= 3
    AND ro.odds_41 IS NOT NULL
    AND ro.odds_45 IS NOT NULL
    AND ro.odds_46 IS NOT NULL
)
"""


def _write_csv(path: Path, headers: list[str], rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        writer.writerows(rows)


def main() -> None:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        wind_rows = con.execute(
            BASE_CTE.format(start_date=START_DATE, end_date=END_DATE)
            + """
SELECT
  wind_bucket,
  COUNT(*) AS played_races,
  COUNT(*) * 3 AS bet_count,
  SUM(is_hit) AS hit_races,
  ROUND(SUM(is_hit) * 100.0 / COUNT(*), 2) AS hit_race_pct,
  SUM(realized_payout) AS return_yen,
  SUM(stake_yen) AS stake_yen,
  ROUND(SUM(realized_payout) * 100.0 / SUM(stake_yen), 2) AS roi_pct,
  ROUND(AVG(min_odds_played), 2) AS avg_min_odds_played
FROM played
GROUP BY wind_bucket
ORDER BY CASE wind_bucket
  WHEN 'wind_4' THEN 1
  WHEN 'wind_5_6' THEN 2
  WHEN 'wind_7_plus' THEN 3
  ELSE 4
END
"""
        ).fetchall()

        odds_rows = con.execute(
            BASE_CTE.format(start_date=START_DATE, end_date=END_DATE)
            + """
SELECT
  min_odds_bucket,
  COUNT(*) AS played_races,
  COUNT(*) * 3 AS bet_count,
  SUM(is_hit) AS hit_races,
  ROUND(SUM(is_hit) * 100.0 / COUNT(*), 2) AS hit_race_pct,
  SUM(realized_payout) AS return_yen,
  SUM(stake_yen) AS stake_yen,
  ROUND(SUM(realized_payout) * 100.0 / SUM(stake_yen), 2) AS roi_pct,
  ROUND(AVG(min_odds_played), 2) AS avg_min_odds_played
FROM played
GROUP BY min_odds_bucket
ORDER BY CASE min_odds_bucket
  WHEN 'lt10' THEN 1
  WHEN '10_15' THEN 2
  WHEN '15_20' THEN 3
  WHEN '20_30' THEN 4
  WHEN '30_50' THEN 5
  ELSE 6
END
"""
        ).fetchall()

        combo_loss_rows = con.execute(
            BASE_CTE.format(start_date=START_DATE, end_date=END_DATE)
            + """
SELECT
  exacta_combo,
  COUNT(*) AS races,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS share_pct
FROM played
WHERE is_hit = 0
GROUP BY exacta_combo
ORDER BY races DESC, exacta_combo
LIMIT 12
"""
        ).fetchall()

        summary_row = con.execute(
            BASE_CTE.format(start_date=START_DATE, end_date=END_DATE)
            + """
SELECT
  COUNT(*) AS played_races,
  SUM(is_hit) AS hit_races,
  ROUND(SUM(is_hit) * 100.0 / COUNT(*), 2) AS hit_race_pct,
  SUM(realized_payout) AS return_yen,
  SUM(stake_yen) AS stake_yen,
  ROUND(SUM(realized_payout) * 100.0 / SUM(stake_yen), 2) AS roi_pct
FROM played
"""
        ).fetchone()
    finally:
        con.close()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_csv(
        OUTPUT_DIR / "wind_bucket_slice.csv",
        [
            "wind_bucket",
            "played_races",
            "bet_count",
            "hit_races",
            "hit_race_pct",
            "return_yen",
            "stake_yen",
            "roi_pct",
            "avg_min_odds_played",
        ],
        wind_rows,
    )
    _write_csv(
        OUTPUT_DIR / "min_odds_bucket_slice.csv",
        [
            "min_odds_bucket",
            "played_races",
            "bet_count",
            "hit_races",
            "hit_race_pct",
            "return_yen",
            "stake_yen",
            "roi_pct",
            "avg_min_odds_played",
        ],
        odds_rows,
    )
    _write_csv(
        OUTPUT_DIR / "top_losing_settled_combos.csv",
        ["exacta_combo", "races", "share_pct"],
        combo_loss_rows,
    )

    lines = [
        "# 4Wind Base Loss Slice",
        "",
        f"- period: `{START_DATE}..{END_DATE}`",
        "- target: `base_4156`",
        f"- played races: `{summary_row[0]}`",
        f"- hit races: `{summary_row[1]}` (`{summary_row[2]}%`)",
        f"- ROI: `{summary_row[5]}%`",
        "",
        "## Chosen Slices",
        "- wind bucket: because the base rule clearly spans both the good 5-6m zone and weaker zones",
        "- min quoted odds bucket: because price compression looked like the most actionable market-side failure",
        "",
        "## Files",
        f"- [wind_bucket_slice.csv]({str((OUTPUT_DIR / 'wind_bucket_slice.csv')).replace('\\\\', '/')})",
        f"- [min_odds_bucket_slice.csv]({str((OUTPUT_DIR / 'min_odds_bucket_slice.csv')).replace('\\\\', '/')})",
        f"- [top_losing_settled_combos.csv]({str((OUTPUT_DIR / 'top_losing_settled_combos.csv')).replace('\\\\', '/')})",
    ]
    (OUTPUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8-sig")


if __name__ == "__main__":
    main()
