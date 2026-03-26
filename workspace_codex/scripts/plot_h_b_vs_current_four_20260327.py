from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(r"C:\CODEX_WORK\boat_clone")
DB_PATH = Path(os.environ.get("BOAT_DB_PATH", r"\\038INS\boat\data\silver\boat_race.duckdb"))
START_DATE = "2025-04-01"
END_DATE = "2026-03-09"

COMBINED_DIR = (
    ROOT
    / "reports"
    / "strategies"
    / "combined"
    / "c2_125_4wind_2025-04-01_to_2026-03-09_20260322"
)
C2_OVERLAY_DIR = (
    ROOT
    / "reports"
    / "strategies"
    / "c2"
    / "c2_pred1_non_lane1_overlay_walkforward_2025-04-01_to_2026-03-09_5m_20260325"
)
OUTPUT_DIR = (
    ROOT
    / "reports"
    / "strategies"
    / "combined"
    / "h_b_vs_current_four_2025-04-01_to_2026-03-09_20260327"
)
HB_DIR = (
    ROOT
    / "reports"
    / "strategies"
    / "zero_base_period_2025-04-01_to_2026-03-09_h_b_racer_index_overlay_pred6_not2_5m_20260327"
)


QUERY_H_A_FINAL_DAY_CUT = """
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
    cast(r.exacta_payout as bigint) AS exacta_payout,
    coalesce(rm.is_final_day, false) AS is_final_day
  FROM entries e
  JOIN results r USING(race_id)
  LEFT JOIN beforeinfo_entries bi ON bi.race_id = e.race_id AND bi.lane = e.lane
  LEFT JOIN race_meta rm USING(race_id)
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
    max(exacta_payout) AS exacta_payout,
    max(is_final_day) AS is_final_day
  FROM ranked
  GROUP BY race_id, race_date, stadium_code, race_no
)
SELECT
  race_id,
  race_date,
  100 AS bet_amount,
  CASE
    WHEN first_place_lane = 4 AND second_place_lane = 1 THEN exacta_payout
    ELSE 0
  END AS payout
FROM race_level
WHERE lane1_st_rank <= 3
  AND lane1_st IS NOT NULL
  AND lane4_st IS NOT NULL
  AND lane1_st - lane4_st >= 0.05
  AND is_final_day = false
ORDER BY race_date, race_id
"""


@dataclass(frozen=True)
class StrategySeries:
    logic: str
    variant: str
    source_note: str
    frame: pd.DataFrame


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_final_day_map() -> pd.Series:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        frame = con.execute(
            """
            SELECT
              cast(race_id as varchar) AS race_id,
              coalesce(is_final_day, false) AS is_final_day
            FROM race_meta
            WHERE race_date BETWEEN cast(? as date) AND cast(? as date)
            """,
            [START_DATE, END_DATE],
        ).fetchdf()
    finally:
        con.close()
    return frame.set_index("race_id")["is_final_day"]


def compute_drawdown(profit_series: pd.Series) -> pd.Series:
    cumulative = profit_series.cumsum()
    return cumulative - cumulative.cummax()


def prepare_standard_frame(frame: pd.DataFrame, logic: str, variant: str, source_note: str) -> StrategySeries:
    ordered = frame.copy()
    ordered["race_id"] = ordered["race_id"].astype(str)
    ordered["race_date"] = pd.to_datetime(ordered["race_date"])
    ordered = ordered.sort_values(["race_date", "race_id"]).reset_index(drop=True)
    ordered["bet_amount"] = ordered["bet_amount"].astype(int)
    ordered["payout"] = ordered["payout"].astype(int)
    ordered["profit"] = ordered["profit"].astype(int)
    ordered["cumulative_profit"] = ordered["profit"].cumsum()
    ordered["drawdown"] = compute_drawdown(ordered["profit"])
    ordered["profit_100yen"] = ordered.apply(
        lambda row: (row["profit"] / row["bet_amount"] * 100.0) if row["bet_amount"] else 0.0,
        axis=1,
    )
    ordered["cumulative_profit_100yen"] = ordered["profit_100yen"].cumsum()
    ordered["logic"] = logic
    ordered["variant"] = variant
    ordered["source_note"] = source_note
    return StrategySeries(logic=logic, variant=variant, source_note=source_note, frame=ordered)


def load_125_series(final_day_map: pd.Series) -> StrategySeries:
    frame = pd.read_csv(COMBINED_DIR / "125_four_stadium_x1_race_results.csv")
    frame = frame.loc[
        (frame["race_date"] >= START_DATE)
        & (frame["race_date"] <= END_DATE)
    ].copy()
    frame["is_final_day"] = frame["race_id"].astype(str).map(final_day_map).fillna(False)
    frame = frame.loc[~frame["is_final_day"]].copy()
    frame = frame.rename(columns={"bet_amount": "bet_amount", "payout": "payout", "profit": "profit"})
    return prepare_standard_frame(
        frame[["race_id", "race_date", "bet_amount", "payout", "profit"]],
        logic="125_broad_four_stadium",
        variant="existing_aligned_x1 + final_day_cut",
        source_note="best aligned 125 race-results with final-day rows removed by current shared filter",
    )


def load_4wind_series(final_day_map: pd.Series) -> StrategySeries:
    frame = pd.read_csv(COMBINED_DIR / "4wind_only_wind_5_6_415_race_results.csv")
    frame = frame.loc[
        (frame["race_date"] >= START_DATE)
        & (frame["race_date"] <= END_DATE)
    ].copy()
    frame["is_final_day"] = frame["race_id"].astype(str).map(final_day_map).fillna(False)
    frame = frame.loc[~frame["is_final_day"]].copy()
    return prepare_standard_frame(
        frame[["race_id", "race_date", "bet_amount", "payout", "profit"]],
        logic="4wind_base_415",
        variant="existing_aligned_4-1_4-5 + final_day_cut",
        source_note="best aligned 4wind race-results with final-day rows removed by current shared filter",
    )


def load_c2_overlay_series() -> StrategySeries:
    frame = pd.read_csv(C2_OVERLAY_DIR / "C2_pred1_non_lane1_overlay_race_results.csv")
    frame = frame.loc[
        (frame["race_date"] >= START_DATE)
        & (frame["race_date"] <= END_DATE)
        & (frame["overlay_bet"] > 0)
    ].copy()
    frame = frame.rename(
        columns={
            "overlay_bet": "bet_amount",
            "overlay_payout": "payout",
            "overlay_profit": "profit",
        }
    )
    return prepare_standard_frame(
        frame[["race_id", "race_date", "bet_amount", "payout", "profit"]],
        logic="c2_provisional_v1",
        variant="walkforward_pred1_non_lane1_overlay",
        source_note="current-ish C2 proxy with B2 cut, final-day cut, and racer-index pred1!=lane1 overlay",
    )


def load_h_a_series() -> StrategySeries:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        frame = con.execute(QUERY_H_A_FINAL_DAY_CUT, [START_DATE, END_DATE]).fetchdf()
    finally:
        con.close()

    frame["profit"] = frame["payout"] - frame["bet_amount"]
    return prepare_standard_frame(
        frame[["race_id", "race_date", "bet_amount", "payout", "profit"]],
        logic="H-A",
        variant="final_day_cut_proxy",
        source_note="H-A exacta 4-1 official-settle proxy with final-day cut",
    )


def load_h_b_series() -> StrategySeries:
    frame = pd.read_csv(HB_DIR / "overlay_race_results.csv")
    return prepare_standard_frame(
        frame[["race_id", "race_date", "bet_amount", "payout", "profit"]],
        logic="H-B",
        variant="pred6_not2_overlay",
        source_note="H-B exacta 4-2 official-settle proxy with racer-index pred6_lane != 2",
    )


def summarize_series(series: StrategySeries) -> dict[str, object]:
    frame = series.frame
    max_dd = int(frame["drawdown"].min()) if not frame.empty else 0
    hits = int((frame["payout"] > 0).sum())
    investment = int(frame["bet_amount"].sum())
    payout = int(frame["payout"].sum())
    max_losing = 0
    current_losing = 0
    for hit in (frame["payout"] > 0).tolist():
        if hit:
            current_losing = 0
        else:
            current_losing += 1
            max_losing = max(max_losing, current_losing)
    return {
        "logic": series.logic,
        "variant": series.variant,
        "races": int(len(frame)),
        "hits": hits,
        "hit_rate_pct": (hits / len(frame) * 100.0) if len(frame) else 0.0,
        "bet_total_yen": investment,
        "payout_total_yen": payout,
        "profit_yen": payout - investment,
        "roi_pct": (payout / investment * 100.0) if investment else 0.0,
        "max_dd_yen": max_dd,
        "max_losing_streak": max_losing,
        "normalized_profit_100yen": round(float(frame["profit_100yen"].sum()), 2),
        "source_note": series.source_note,
    }


def write_note(path: Path, summary_df: pd.DataFrame) -> None:
    lines = [
        "# H-B vs Current Four Equity Overlay",
        "",
        "## Scope",
        "",
        f"- aligned period: `{START_DATE}` .. `{END_DATE}`",
        "- current four used in this note:",
        "  - `125_broad_four_stadium`",
        "  - `c2_provisional_v1`",
        "  - `4wind_base_415`",
        "  - `H-A`",
        "- candidate branch:",
        "  - `H-B`",
        "",
        "## Plot Files",
        "",
        "- `h_b_vs_current_four_equity.png`",
        "- `h_b_vs_current_four_equity_summary.csv`",
        "- `h_b_vs_current_four_equity_race_results.csv`",
        "",
        "## Assumptions",
        "",
        "- `H-A` is shown as the current first refinement candidate: `final day cut` applied",
        "- `H-B` is shown as the current rough-water candidate: `pred6_lane != 2`",
        "- `C2` uses the current walk-forward overlay file with `pred1 != lane1`",
        "- `125` and `4wind` use the best aligned race-result files, then apply current shared `final day cut` by `race_meta.is_final_day`",
        "- because source stakes differ, the figure contains:",
        "  - raw cumulative profit in source yen",
        "  - `100-yen normalized` cumulative profit for shape comparison",
        "",
        "## Summary",
        "",
        "| logic | variant | races | hits | hit rate | profit | ROI | max DD | max losing streak | 100-yen normalized profit |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for row in summary_df.itertuples(index=False):
        lines.append(
            f"| {row.logic} | {row.variant} | {row.races} | {row.hits} | {row.hit_rate_pct:.2f}% | {row.profit_yen:,}円 | {row.roi_pct:.2f}% | {row.max_dd_yen:,}円 | {row.max_losing_streak} | {row.normalized_profit_100yen:,.2f}円 |"
        )

    lines.extend(["", "## Notes", ""])
    for row in summary_df.itertuples(index=False):
        lines.append(f"- `{row.logic}`: {row.source_note}")

    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def plot_series(series_list: list[StrategySeries], out_path: Path) -> None:
    plt.style.use("default")
    fig, axes = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

    colors = {
        "125_broad_four_stadium": "#0f766e",
        "c2_provisional_v1": "#dc2626",
        "4wind_base_415": "#2563eb",
        "H-A": "#7c3aed",
        "H-B": "#d97706",
    }

    for series in series_list:
        frame = series.frame
        axes[0].plot(
            frame["race_date"],
            frame["cumulative_profit"],
            label=series.logic,
            linewidth=2.0,
            color=colors.get(series.logic),
        )
        axes[1].plot(
            frame["race_date"],
            frame["cumulative_profit_100yen"],
            label=series.logic,
            linewidth=2.0,
            color=colors.get(series.logic),
        )

    axes[0].set_title("Cumulative Profit (Source Stake)")
    axes[0].set_ylabel("Yen")
    axes[0].grid(alpha=0.25)
    axes[0].legend()

    axes[1].set_title("Cumulative Profit (100-yen Normalized)")
    axes[1].set_ylabel("Yen")
    axes[1].grid(alpha=0.25)
    axes[1].legend()

    fig.suptitle("H-B vs Current Four | 2025-04-01 .. 2026-03-09", fontsize=15)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ensure_dir(OUTPUT_DIR)
    final_day_map = load_final_day_map()

    series_list = [
        load_125_series(final_day_map),
        load_c2_overlay_series(),
        load_4wind_series(final_day_map),
        load_h_a_series(),
        load_h_b_series(),
    ]

    combined = pd.concat([series.frame for series in series_list], ignore_index=True)
    summary_df = pd.DataFrame([summarize_series(series) for series in series_list])

    combined.to_csv(
        OUTPUT_DIR / "h_b_vs_current_four_equity_race_results.csv",
        index=False,
        encoding="utf-8-sig",
    )
    summary_df.to_csv(
        OUTPUT_DIR / "h_b_vs_current_four_equity_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    write_note(OUTPUT_DIR / "README.md", summary_df)
    plot_series(series_list, OUTPUT_DIR / "h_b_vs_current_four_equity.png")

    print(summary_df.to_string(index=False))
    print(f"wrote {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
