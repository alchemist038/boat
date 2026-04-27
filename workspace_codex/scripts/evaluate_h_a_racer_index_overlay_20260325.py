from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd
from runtime_paths import REPO_ROOT, default_reports_root, default_results_db_path

ROOT = REPO_ROOT
DB_PATH = default_results_db_path()
PRED_DIR = default_reports_root() / "racer_finish_score_feb_candidate_march_forward_20260324"
OUTPUT_DIR = (
    ROOT
    / "reports"
    / "strategies"
    / "zero_base_period_2025-03-11_to_2025-06-16_20260324"
)


@dataclass(frozen=True)
class PeriodConfig:
    label: str
    start: str
    end: str
    prediction_csv: Path


PERIODS = [
    PeriodConfig("2026_feb_tuning", "2026-02-01", "2026-02-28", PRED_DIR / "tuning_feb_predictions.csv"),
    PeriodConfig("2026_mar_forward", "2026-03-01", "2026-03-23", PRED_DIR / "forward_march_predictions.csv"),
]

QUERY_H_A = """
WITH base AS (
  SELECT
    cast(e.race_id as varchar) AS race_id,
    cast(e.race_date as date) AS race_date,
    e.stadium_code,
    e.race_no,
    e.lane,
    bi.start_exhibition_st,
    r.first_place_lane,
    r.second_place_lane,
    cast(r.exacta_payout as bigint) AS exacta_payout
  FROM entries e
  JOIN results r USING(race_id)
  LEFT JOIN beforeinfo_entries bi ON bi.race_id = e.race_id AND bi.lane = e.lane
  WHERE e.race_date BETWEEN cast(? as date) AND cast(? as date)
),
ranked AS (
  SELECT
    *,
    dense_rank() OVER (
      PARTITION BY race_id
      ORDER BY
        CASE WHEN start_exhibition_st IS NULL THEN 1 ELSE 0 END,
        start_exhibition_st ASC,
        lane ASC
    ) AS st_rank
  FROM base
  QUALIFY COUNT(*) OVER (PARTITION BY race_id) = 6
),
race_level AS (
  SELECT
    race_id,
    race_date,
    stadium_code,
    race_no,
    max(case when lane = 1 then st_rank end) AS lane1_st_rank,
    max(case when lane = 1 then start_exhibition_st end) AS lane1_st,
    max(case when lane = 4 then start_exhibition_st end) AS lane4_st,
    max(first_place_lane) AS first_place_lane,
    max(second_place_lane) AS second_place_lane,
    max(exacta_payout) AS exacta_payout
  FROM ranked
  GROUP BY race_id, race_date, stadium_code, race_no
)
SELECT
  *,
  100 AS bet_yen,
  CASE
    WHEN first_place_lane = 4 AND second_place_lane = 1 THEN exacta_payout
    ELSE 0
  END AS payout_yen
FROM race_level
WHERE lane1_st_rank <= 3
  AND lane1_st IS NOT NULL
  AND lane4_st IS NOT NULL
  AND lane1_st - lane4_st >= 0.05
ORDER BY race_date, race_id
"""


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def max_losing_streak(hit_series: pd.Series) -> int:
    longest = 0
    current = 0
    for hit in hit_series.astype(bool):
        if hit:
            current = 0
        else:
            current += 1
            longest = max(longest, current)
    return longest


def summarize(frame: pd.DataFrame) -> dict[str, object]:
    ordered = frame.sort_values(["race_date", "race_id"]).reset_index(drop=True)
    if ordered.empty:
        return {
            "bets": 0,
            "hits": 0,
            "investment_yen": 0,
            "return_yen": 0,
            "profit_yen": 0,
            "roi_pct": 0.0,
            "max_dd_yen": 0,
            "max_losing_streak": 0,
        }

    pnl = ordered["payout_yen"] - ordered["bet_yen"]
    balance = pnl.cumsum()
    drawdown = balance - balance.cummax()
    hits = int((ordered["payout_yen"] > 0).sum())
    returned = int(ordered["payout_yen"].sum())
    investment = int(ordered["bet_yen"].sum())
    return {
        "bets": int(len(ordered)),
        "hits": hits,
        "investment_yen": investment,
        "return_yen": returned,
        "profit_yen": returned - investment,
        "roi_pct": (returned / investment * 100.0) if investment else 0.0,
        "max_dd_yen": int(drawdown.min()) if not drawdown.empty else 0,
        "max_losing_streak": max_losing_streak(ordered["payout_yen"] > 0),
    }


def write_summary(path: Path, summary_rows: pd.DataFrame) -> None:
    lines = [
        "# H-A With Racer Index `pred1=lane4`",
        "",
        "## Scope",
        "",
        "- base logic: `H-A` exacta `4-1`",
        "- base conditions:",
        "  - `lane1_st_top3`",
        "  - `lane4_ahead_lane1_005`",
        "- settle source: `results.exacta_payout` official-settle proxy",
        "- overlay: keep only races where the current racer-index prototype predicts `pred1_lane = 4`",
        "",
        "## Caveat",
        "",
        "- this is **not** a full multi-year walkforward backtest",
        "- it uses the currently available prototype outputs only:",
        "  - `tuning_feb_predictions.csv`",
        "  - `forward_march_predictions.csv`",
        "- so this should be read as an initial compatibility check between `H-A` and the current racer-index prototype",
        "",
        "## Summary",
        "",
        "| period | base bets | base ROI | base profit | base max DD | base max losing streak | overlay bets | keep rate | overlay ROI | overlay profit | overlay max DD | overlay max losing streak | overlay hits / base hits |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for row in summary_rows.itertuples(index=False):
        lines.append(
            "| {period} | {base_bets} | {base_roi_pct:.2f}% | {base_profit_yen:,} | {base_max_dd_yen:,} | {base_max_losing_streak} | {overlay_bets} | {overlay_keep_rate_pct:.2f}% | {overlay_roi_pct:.2f}% | {overlay_profit_yen:,} | {overlay_max_dd_yen:,} | {overlay_max_losing_streak} | {overlay_hits} / {base_hits} |".format(
                **row._asdict()
            )
        )

    lines.extend(
        [
            "",
            "## Read",
            "",
            "- if `pred1=lane4` works, it should reduce `H-A` DD by confirming that lane 4 is a real head candidate",
            "- the most important read is whether it helps the weak 2026 forward slice without killing sample size too aggressively",
            "",
            "## Files",
            "",
            "- yearly-ish comparison: `h_a_racer_index_pred1_lane4_feb_mar_20260325.csv`",
            "- race-level joined rows: `h_a_racer_index_pred1_lane4_feb_mar_races_20260325.csv`",
        ]
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ensure_dir(OUTPUT_DIR)
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        summary_rows: list[dict[str, object]] = []
        race_frames: list[pd.DataFrame] = []

        for period in PERIODS:
            base = con.execute(QUERY_H_A, [period.start, period.end]).fetchdf()
            base["race_id"] = base["race_id"].astype(str)

            predictions = pd.read_csv(period.prediction_csv)
            predictions["race_id"] = predictions["race_id"].astype(str)
            pred1_lane4 = predictions.loc[
                (predictions["lane"] == 4) & (predictions["pred_rank"] == 1),
                ["race_id", "pred_score"],
            ].drop_duplicates(subset=["race_id"])

            joined = base.merge(pred1_lane4.assign(overlay_keep=True), on="race_id", how="left")
            joined["overlay_keep"] = joined["overlay_keep"].notna()
            overlay = joined.loc[joined["overlay_keep"]].copy()

            base_metrics = summarize(joined)
            overlay_metrics = summarize(overlay)

            summary_rows.append(
                {
                    "period": period.label,
                    "base_bets": base_metrics["bets"],
                    "base_hits": base_metrics["hits"],
                    "base_roi_pct": base_metrics["roi_pct"],
                    "base_profit_yen": base_metrics["profit_yen"],
                    "base_max_dd_yen": base_metrics["max_dd_yen"],
                    "base_max_losing_streak": base_metrics["max_losing_streak"],
                    "overlay_bets": overlay_metrics["bets"],
                    "overlay_hits": overlay_metrics["hits"],
                    "overlay_keep_rate_pct": (overlay_metrics["bets"] / base_metrics["bets"] * 100.0) if base_metrics["bets"] else 0.0,
                    "overlay_roi_pct": overlay_metrics["roi_pct"],
                    "overlay_profit_yen": overlay_metrics["profit_yen"],
                    "overlay_max_dd_yen": overlay_metrics["max_dd_yen"],
                    "overlay_max_losing_streak": overlay_metrics["max_losing_streak"],
                }
            )

            joined["period"] = period.label
            race_frames.append(joined)
    finally:
        con.close()

    summary_df = pd.DataFrame(summary_rows)
    race_df = pd.concat(race_frames, ignore_index=True)

    summary_csv = OUTPUT_DIR / "h_a_racer_index_pred1_lane4_feb_mar_20260325.csv"
    races_csv = OUTPUT_DIR / "h_a_racer_index_pred1_lane4_feb_mar_races_20260325.csv"
    summary_md = OUTPUT_DIR / "h_a_racer_index_pred1_lane4_feb_mar_20260325.md"

    summary_df.to_csv(summary_csv, index=False, encoding="utf-8-sig")
    race_df.to_csv(races_csv, index=False, encoding="utf-8-sig")
    write_summary(summary_md, summary_df)

    print(summary_df.to_string(index=False))
    print(f"wrote {summary_md}")


if __name__ == "__main__":
    main()
