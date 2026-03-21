from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import duckdb


DB_PATH = Path(r"D:\boat\data\silver\boat_race.duckdb")
OUTPUT_DIR = Path(r"D:\boat\reports\strategies\gemini_registry\4wind\refinement_eval_20260320")
STAKE_PER_RACE_YEN = 300


RACE_QUERY = """
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
    e.lane,
    bi.exhibition_time,
    bi.start_exhibition_st,
    COALESCE(bi.wind_speed_m, res.wind_speed_m) AS wind_speed_m,
    COALESCE(bi.wave_height_cm, res.wave_height_cm) AS wave_height_cm,
    res.exacta_combo,
    res.exacta_payout
  FROM entries e
  JOIN races r USING (race_id)
  LEFT JOIN race_meta rm USING (race_id)
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
    MAX(grade) AS grade,
    MAX(meeting_day_no) AS meeting_day_no,
    MAX(meeting_day_label) AS meeting_day_label,
    MAX(wind_speed_m) AS wind_speed_m,
    MAX(wave_height_cm) AS wave_height_cm,
    MAX(exacta_combo) AS exacta_combo,
    MAX(exacta_payout) AS exacta_payout,
    MAX(CASE WHEN lane = 4 THEN exhibition_time_rank END) AS lane4_exhibition_time_rank,
    MAX(CASE WHEN lane = 4 THEN st_diff_from_inside END) AS lane4_st_diff_from_inside
  FROM entry_features
  GROUP BY race_id
)
SELECT *
FROM race_base
ORDER BY race_date, stadium_code, race_no, race_id
"""


@dataclass(frozen=True, slots=True)
class RaceContext:
    race_id: str
    race_date: object
    stadium_code: str
    stadium_name: str
    race_no: int
    grade: str | None
    meeting_day_no: int | None
    meeting_day_label: str | None
    wind_speed_m: float | None
    wave_height_cm: int | None
    exacta_combo: str | None
    exacta_payout: int | None
    lane4_exhibition_time_rank: int | None
    lane4_st_diff_from_inside: float | None


@dataclass(frozen=True, slots=True)
class VariantSpec:
    name: str
    description: str


VARIANTS = (
    VariantSpec(
        name="base",
        description="Base 4wind: wind>=4, lane4 ST diff<=-0.05, lane4 exhibition rank<=3.",
    ),
    VariantSpec(
        name="exclude_wind_7_plus",
        description="Base 4wind plus wind_speed_m<=6.",
    ),
    VariantSpec(
        name="exclude_wave56_wind34",
        description="Base 4wind plus exclude wave 5-6cm when wind is in 3-4 bucket. Under base rule this is effectively wave 5-6cm with wind=4.",
    ),
    VariantSpec(
        name="only_wind_5_6",
        description="Base 4wind plus restrict to wind 5-6m.",
    ),
)


def _load_races(start_date: str, end_date: str) -> list[RaceContext]:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
      rows = con.execute(RACE_QUERY.format(start_date=start_date, end_date=end_date)).fetchall()
      return [RaceContext(*row) for row in rows]
    finally:
      con.close()


def _base_match(race: RaceContext) -> tuple[bool, str]:
    if race.exacta_combo is None or race.exacta_payout is None:
        return False, "exacta_result_missing"
    if race.wind_speed_m is None or race.wind_speed_m < 4:
        return False, "wind_not_target"
    if race.lane4_st_diff_from_inside is None:
        return False, "lane4_st_diff_missing"
    if race.lane4_st_diff_from_inside > -0.05:
        return False, "lane4_st_edge_missing"
    if race.lane4_exhibition_time_rank is None:
        return False, "lane4_ex_rank_missing"
    if race.lane4_exhibition_time_rank > 3:
        return False, "lane4_not_fast_enough"
    return True, ""


def _variant_match(variant_name: str, race: RaceContext) -> tuple[bool, str]:
    ok, reason = _base_match(race)
    if not ok:
        return False, reason
    if variant_name == "base":
        return True, ""
    if variant_name == "exclude_wind_7_plus":
        if race.wind_speed_m is None or race.wind_speed_m > 6:
            return False, "wind_7_plus_excluded"
        return True, ""
    if variant_name == "exclude_wave56_wind34":
        if race.wave_height_cm is not None and 5 <= race.wave_height_cm <= 6:
            if race.wind_speed_m is not None and 3 <= race.wind_speed_m <= 4:
                return False, "wave56_wind34_excluded"
        return True, ""
    if variant_name == "only_wind_5_6":
        if race.wind_speed_m is None or race.wind_speed_m < 5 or race.wind_speed_m > 6:
            return False, "not_wind_5_6"
        return True, ""
    raise ValueError(f"unknown variant {variant_name}")


def _calculate_drawdown(bets: list[dict[str, object]]) -> tuple[int, str]:
    balance = 0
    peak = 0
    max_drawdown = 0
    max_drawdown_race_id = ""
    for bet in bets:
        balance += int(bet["realized_payout"]) - STAKE_PER_RACE_YEN
        peak = max(peak, balance)
        drawdown = peak - balance
        if drawdown > max_drawdown:
            max_drawdown = drawdown
            max_drawdown_race_id = str(bet["race_id"])
    return max_drawdown, max_drawdown_race_id


def _calculate_losing_streak(bets: list[dict[str, object]]) -> int:
    streak = 0
    max_streak = 0
    for bet in bets:
        if int(bet["is_hit"]):
            streak = 0
        else:
            streak += 1
            max_streak = max(max_streak, streak)
    return max_streak


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8-sig")


def evaluate_period(start_date: str, end_date: str) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    races = _load_races(start_date=start_date, end_date=end_date)
    summary_rows: list[dict[str, object]] = []
    bet_rows: list[dict[str, object]] = []

    for variant in VARIANTS:
        variant_bets: list[dict[str, object]] = []
        skip_counts: dict[str, int] = {}
        played_races = 0
        for race in races:
            ok, reason = _variant_match(variant.name, race)
            if not ok:
                skip_counts[reason] = skip_counts.get(reason, 0) + 1
                continue
            played_races += 1
            is_hit = int((race.exacta_combo or "") in {"4-1", "4-5", "4-6"})
            realized_payout = int(race.exacta_payout or 0) if is_hit else 0
            row = {
                "period": f"{start_date}_to_{end_date}",
                "variant_name": variant.name,
                "race_id": race.race_id,
                "race_date": race.race_date,
                "stadium_code": race.stadium_code,
                "stadium_name": race.stadium_name,
                "race_no": race.race_no,
                "wind_speed_m": race.wind_speed_m,
                "wave_height_cm": race.wave_height_cm,
                "lane4_exhibition_time_rank": race.lane4_exhibition_time_rank,
                "lane4_st_diff_from_inside": race.lane4_st_diff_from_inside,
                "settled_combo": race.exacta_combo,
                "is_hit": is_hit,
                "realized_payout": realized_payout,
            }
            variant_bets.append(row)
            bet_rows.append(row)

        bet_count = played_races * 3
        stake_yen = played_races * STAKE_PER_RACE_YEN
        return_yen = sum(int(r["realized_payout"]) for r in variant_bets)
        hit_races = sum(int(r["is_hit"]) for r in variant_bets)
        max_drawdown_yen, max_drawdown_race_id = _calculate_drawdown(variant_bets)
        max_losing_streak = _calculate_losing_streak(variant_bets)
        top_skip_reason = ""
        top_skip_reason_count = 0
        if skip_counts:
            top_skip_reason, top_skip_reason_count = max(skip_counts.items(), key=lambda x: x[1])
        summary_rows.append(
            {
                "period": f"{start_date}_to_{end_date}",
                "variant_name": variant.name,
                "description": variant.description,
                "evaluated_races": len(races),
                "played_races": played_races,
                "bet_count": bet_count,
                "stake_yen": stake_yen,
                "return_yen": return_yen,
                "profit_yen": return_yen - stake_yen,
                "roi_pct": round(return_yen * 100.0 / stake_yen, 2) if stake_yen else 0.0,
                "hit_races": hit_races,
                "hit_race_pct": round(hit_races * 100.0 / played_races, 2) if played_races else 0.0,
                "max_drawdown_yen": max_drawdown_yen,
                "max_drawdown_race_id": max_drawdown_race_id,
                "max_losing_streak": max_losing_streak,
                "top_skip_reason": top_skip_reason,
                "top_skip_reason_count": top_skip_reason_count,
            }
        )
    return summary_rows, bet_rows


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_summaries: list[dict[str, object]] = []
    all_bets: list[dict[str, object]] = []
    for start_date, end_date in [
        ("2024-01-01", "2024-12-31"),
        ("2025-01-01", "2025-12-31"),
        ("2026-01-01", "2026-03-18"),
    ]:
        summary_rows, bet_rows = evaluate_period(start_date, end_date)
        all_summaries.extend(summary_rows)
        all_bets.extend(bet_rows)

    _write_csv(
        OUTPUT_DIR / "4wind_refinement_summary.csv",
        [
            "period",
            "variant_name",
            "description",
            "evaluated_races",
            "played_races",
            "bet_count",
            "stake_yen",
            "return_yen",
            "profit_yen",
            "roi_pct",
            "hit_races",
            "hit_race_pct",
            "max_drawdown_yen",
            "max_drawdown_race_id",
            "max_losing_streak",
            "top_skip_reason",
            "top_skip_reason_count",
        ],
        all_summaries,
    )
    _write_csv(
        OUTPUT_DIR / "4wind_refinement_bets.csv",
        [
            "period",
            "variant_name",
            "race_id",
            "race_date",
            "stadium_code",
            "stadium_name",
            "race_no",
            "wind_speed_m",
            "wave_height_cm",
            "lane4_exhibition_time_rank",
            "lane4_st_diff_from_inside",
            "settled_combo",
            "is_hit",
            "realized_payout",
        ],
        all_bets,
    )

    lines = [
        "# 4Wind Refinement Evaluation",
        "",
        "- Compared the base rule against three Gemini-suggested refinement directions.",
        "- Periods tested: `2024` and `2025`.",
        "- Stake remains `300 yen per played race`.",
        "",
        "## Variants",
        "- `base`: original 4wind",
        "- `exclude_wind_7_plus`: keep only wind `<= 6`",
        "- `exclude_wave56_wind34`: exclude wave `5-6cm` with wind in `3-4` bucket",
        "- `only_wind_5_6`: keep only wind `5-6m`",
    ]
    for row in all_summaries:
        lines.append(
            f"- `{row['period']} / {row['variant_name']}`: played `{row['played_races']}`, ROI `{row['roi_pct']}%`, "
            f"maxDD `{row['max_drawdown_yen']}`, hit_race_pct `{row['hit_race_pct']}%`"
        )
    _write_text(OUTPUT_DIR / "README.md", "\n".join(lines))

    print(f"output_dir={OUTPUT_DIR}")
    for row in all_summaries:
        print(
            row["period"],
            row["variant_name"],
            f"played_races={row['played_races']}",
            f"roi_pct={row['roi_pct']}",
            f"max_drawdown_yen={row['max_drawdown_yen']}",
        )


if __name__ == "__main__":
    main()
