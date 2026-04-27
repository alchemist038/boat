from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import duckdb

from boat_race_data.gpt_export import FEATURES_QUERY
from runtime_paths import REPO_ROOT, default_results_db_path


DB_PATH = default_results_db_path()
OUTPUT_DIR = Path(
    REPO_ROOT / "reports" / "strategies" / "zero_base_period_2025-03-11_to_2025-06-16_20260324"
)
STAKE_YEN = 100


RACE_QUERY = """
WITH feature_base AS ({features_query}),
entry_features AS (
  SELECT
    *,
    DENSE_RANK() OVER (
      PARTITION BY race_id
      ORDER BY
        CASE WHEN start_exhibition_st IS NULL THEN 1 ELSE 0 END,
        start_exhibition_st ASC,
        lane ASC
    ) AS st_rank
  FROM feature_base
),
race_base AS (
  SELECT
    race_id,
    MIN(race_date) AS race_date,
    MIN(stadium_code) AS stadium_code,
    MIN(stadium_name) AS stadium_name,
    MIN(race_no) AS race_no,
    MAX(is_final_day) AS is_final_day,
    MAX(wave_height_cm) AS wave_height_cm,
    MAX(exacta_combo) AS exacta_combo,
    MAX(exacta_payout) AS exacta_payout,
    MAX(CASE WHEN lane = 1 THEN start_exhibition_st END) AS lane1_start_exhibition_st,
    MAX(CASE WHEN lane = 4 THEN start_exhibition_st END) AS lane4_start_exhibition_st
  FROM entry_features
  GROUP BY race_id
)
SELECT *
FROM race_base
ORDER BY race_date, stadium_code, race_no, race_id
"""


@dataclass(frozen=True, slots=True)
class PeriodSpec:
    label: str
    start_date: str
    end_date: str


PERIODS = (
    PeriodSpec("2024", "2024-01-01", "2024-12-31"),
    PeriodSpec("2025", "2025-01-01", "2025-12-31"),
    PeriodSpec("2026_ytd", "2026-01-01", "2026-03-24"),
)


def _normalize_combo(value: str | None) -> str:
    if not value:
        return ""
    return value.replace(" ", "").replace("　", "")


def _load_rows(period: PeriodSpec) -> list[dict[str, object]]:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        query = RACE_QUERY.format(
            features_query=FEATURES_QUERY.format(start_date=period.start_date, end_date=period.end_date)
        )
        cursor = con.execute(query)
        columns = [item[0] for item in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        con.close()


def _passes_h_b(row: dict[str, object]) -> bool:
    wave_height_cm = row.get("wave_height_cm")
    lane1_st = row.get("lane1_start_exhibition_st")
    lane4_st = row.get("lane4_start_exhibition_st")
    if wave_height_cm is None or lane1_st is None or lane4_st is None:
        return False
    try:
        wave = int(wave_height_cm)
        lane1_value = float(lane1_st)
        lane4_value = float(lane4_st)
    except (TypeError, ValueError):
        return False
    return wave >= 6 and (lane1_value - lane4_value) >= 0.05


def _calculate_drawdown(bets: list[dict[str, object]]) -> tuple[int, str, str]:
    balance = 0
    peak = 0
    max_drawdown = 0
    peak_race_id = ""
    bottom_race_id = ""
    current_peak_race_id = ""
    for bet in bets:
        balance += int(bet["return_yen"]) - STAKE_YEN
        if balance > peak:
            peak = balance
            current_peak_race_id = str(bet["race_id"])
        drawdown = peak - balance
        if drawdown > max_drawdown:
            max_drawdown = drawdown
            peak_race_id = current_peak_race_id
            bottom_race_id = str(bet["race_id"])
    return max_drawdown, peak_race_id, bottom_race_id


def _calculate_losing_streak(bets: list[dict[str, object]]) -> tuple[int, str, str]:
    streak = 0
    max_streak = 0
    start_race_id = ""
    end_race_id = ""
    current_start = ""
    for bet in bets:
        if int(bet["is_hit"]):
            streak = 0
            current_start = ""
            continue
        if streak == 0:
            current_start = str(bet["race_id"])
        streak += 1
        if streak > max_streak:
            max_streak = streak
            start_race_id = current_start
            end_race_id = str(bet["race_id"])
    return max_streak, start_race_id, end_race_id


def _evaluate_period(period: PeriodSpec) -> dict[str, object]:
    bets: list[dict[str, object]] = []
    rows = _load_rows(period)
    for row in rows:
        if not _passes_h_b(row):
            continue
        combo = _normalize_combo(str(row.get("exacta_combo") or ""))
        payout = int(row.get("exacta_payout") or 0)
        is_hit = 1 if combo == "4-2" and payout > 0 else 0
        bets.append(
            {
                "race_id": str(row["race_id"]),
                "return_yen": payout if is_hit else 0,
                "is_hit": is_hit,
                "is_final_day": int(row.get("is_final_day") or 0),
                "wave_height_cm": int(row.get("wave_height_cm") or 0),
            }
        )

    investment_yen = len(bets) * STAKE_YEN
    return_yen = sum(int(item["return_yen"]) for item in bets)
    profit_yen = return_yen - investment_yen
    hits = sum(int(item["is_hit"]) for item in bets)
    avg_hit_payout = round(return_yen / hits, 2) if hits else 0.0
    roi_pct = round(return_yen * 100.0 / investment_yen, 2) if investment_yen else 0.0
    max_dd_yen, dd_peak_race_id, dd_bottom_race_id = _calculate_drawdown(bets)
    max_losing_streak, losing_start_race_id, losing_end_race_id = _calculate_losing_streak(bets)
    final_day_count = sum(int(item["is_final_day"]) for item in bets)
    return {
        "period": period.label,
        "start_date": period.start_date,
        "end_date": period.end_date,
        "bets": len(bets),
        "hits": hits,
        "investment_yen": investment_yen,
        "return_yen": return_yen,
        "profit_yen": profit_yen,
        "roi_pct": roi_pct,
        "avg_hit_payout": avg_hit_payout,
        "max_dd_yen": -max_dd_yen,
        "max_losing_streak": max_losing_streak,
        "dd_peak_race_id": dd_peak_race_id,
        "dd_bottom_race_id": dd_bottom_race_id,
        "losing_streak_start_race_id": losing_start_race_id,
        "losing_streak_end_race_id": losing_end_race_id,
        "final_day_count": final_day_count,
    }


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _build_md(rows: list[dict[str, object]]) -> str:
    lines = [
        "# H-B Yearly Comparison 2024 to 2026 YTD",
        "",
        "## Rule",
        "",
        "- target combo: `exacta 4-2`",
        "- `wave_6p`",
        "  - implemented as `wave_height_cm >= 6`",
        "- `lane4_ahead_lane1_005`",
        "  - implemented as `lane1_st - lane4_st >= 0.05`",
        "- settle source: `results.exacta_payout`",
        "",
        "## Important Caveat",
        "",
        "- this is an `official settle proxy` comparison",
        "- it is not the original quoted-odds discovery scan",
        "- `2026_ytd` ends at shared DB max result date: `2026-03-24`",
        "- exacta combo matching is normalized so both `4-2` and `4 - 2` are treated as the same settle result",
        "",
        "## Summary",
        "",
        "| period | bets | hits | investment_yen | return_yen | profit_yen | ROI | avg_hit_payout | max_dd_yen | max_losing_streak | final_day_count |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['period']} | {row['bets']} | {row['hits']} | {row['investment_yen']:,} | {row['return_yen']:,} | "
            f"{row['profit_yen']:,} | {row['roi_pct']:.2f}% | {row['avg_hit_payout']:.2f} | {row['max_dd_yen']:,} | "
            f"{row['max_losing_streak']} | {row['final_day_count']} |"
        )

    lines.extend(
        [
            "",
            "## Read",
            "",
            "- `H-B` is the rough-water `4-2` branch, so sample size and hit count are expected to be lower than `H-A`.",
            "- Use this note as the first pass to decide whether H-B is still alive across years before any refinement.",
            "",
            "## Detail",
            "",
        ]
    )
    for row in rows:
        lines.extend(
            [
                f"### {row['period']}",
                "",
                f"- period: `{row['start_date']}` to `{row['end_date']}`",
                f"- bets: `{row['bets']}`",
                f"- hits: `{row['hits']}`",
                f"- ROI: `{row['roi_pct']:.2f}%`",
                f"- max drawdown: `{row['max_dd_yen']} yen`",
                f"- drawdown peak race: `{row['dd_peak_race_id']}`",
                f"- drawdown bottom race: `{row['dd_bottom_race_id']}`",
                f"- longest losing streak: `{row['max_losing_streak']}`",
                f"- losing streak start: `{row['losing_streak_start_race_id']}`",
                f"- losing streak end: `{row['losing_streak_end_race_id']}`",
                f"- final day count: `{row['final_day_count']}`",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> None:
    rows = [_evaluate_period(period) for period in PERIODS]
    out_csv = OUTPUT_DIR / "h_b_yearly_comparison_2024_2026ytd_20260326.csv"
    out_md = OUTPUT_DIR / "h_b_yearly_comparison_2024_2026ytd_20260326.md"
    _write_csv(out_csv, rows)
    out_md.write_text(_build_md(rows), encoding="utf-8-sig")
    print(f"wrote_csv={out_csv}")
    print(f"wrote_md={out_md}")
    for row in rows:
        print(
            row["period"],
            f"bets={row['bets']}",
            f"hits={row['hits']}",
            f"roi_pct={row['roi_pct']:.2f}",
            f"max_dd_yen={row['max_dd_yen']}",
        )


if __name__ == "__main__":
    main()
