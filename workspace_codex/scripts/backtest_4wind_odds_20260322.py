from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import duckdb


DB_PATH = Path(r"D:\boat\data\silver\boat_race.duckdb")
OUTPUT_DIR = Path(r"D:\boat\reports\strategies\gemini_registry\4wind\odds_backtest_20260322")
START_DATE = "2025-04-01"
END_DATE = "2026-03-20"
STAKE_PER_BET_YEN = 100


RACE_QUERY = """
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
)
SELECT
  rb.*,
  ro.odds_41,
  ro.odds_45,
  ro.odds_46
FROM race_base rb
LEFT JOIN race_odds ro USING (race_id)
ORDER BY race_date, stadium_code, race_no, race_id
"""


@dataclass(frozen=True, slots=True)
class RaceContext:
    race_id: str
    race_date: object
    stadium_code: str
    stadium_name: str
    race_no: int
    wind_speed_m: float | None
    wave_height_cm: int | None
    exacta_combo: str | None
    exacta_payout: int | None
    lane4_exhibition_time_rank: int | None
    lane4_st_diff_from_inside: float | None
    odds_41: float | None
    odds_45: float | None
    odds_46: float | None


@dataclass(frozen=True, slots=True)
class StrategyDecision:
    played: bool
    combos: tuple[str, ...]
    skip_reason: str
    notes: str


@dataclass(frozen=True, slots=True)
class StrategySpec:
    name: str
    description: str
    evaluator: Callable[[RaceContext], StrategyDecision]


def _load_races() -> list[RaceContext]:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        rows = con.execute(
            RACE_QUERY.format(start_date=START_DATE, end_date=END_DATE)
        ).fetchall()
        return [RaceContext(*row) for row in rows]
    finally:
        con.close()


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8-sig")


def _play(combos: tuple[str, ...], note: str) -> StrategyDecision:
    return StrategyDecision(True, combos, "", note)


def _skip(reason: str, note: str = "") -> StrategyDecision:
    return StrategyDecision(False, (), reason, note)


def _has_exacta_result(race: RaceContext) -> bool:
    return race.exacta_combo is not None and race.exacta_payout is not None


def _base_structural_match(race: RaceContext) -> tuple[bool, str]:
    if not _has_exacta_result(race):
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


def _need_odds(race: RaceContext, needed: tuple[str, ...]) -> tuple[bool, str]:
    for combo in needed:
        if combo == "4-1" and race.odds_41 is None:
            return False, "odds_41_missing"
        if combo == "4-5" and race.odds_45 is None:
            return False, "odds_45_missing"
        if combo == "4-6" and race.odds_46 is None:
            return False, "odds_46_missing"
    return True, ""


def _evaluate_base_4156(race: RaceContext) -> StrategyDecision:
    ok, reason = _base_structural_match(race)
    if not ok:
        return _skip(reason)
    needed = ("4-1", "4-5", "4-6")
    ok, reason = _need_odds(race, needed)
    if not ok:
        return _skip(reason)
    return _play(needed, "Base 4wind with odds coverage")


def _evaluate_only_wind_5_6_4156(race: RaceContext) -> StrategyDecision:
    ok, reason = _base_structural_match(race)
    if not ok:
        return _skip(reason)
    if race.wind_speed_m is None or race.wind_speed_m < 5 or race.wind_speed_m > 6:
        return _skip("not_wind_5_6")
    needed = ("4-1", "4-5", "4-6")
    ok, reason = _need_odds(race, needed)
    if not ok:
        return _skip(reason)
    return _play(needed, "4wind only_wind_5_6 with 4-1/4-5/4-6")


def _evaluate_only_wind_5_6_415(race: RaceContext) -> StrategyDecision:
    ok, reason = _base_structural_match(race)
    if not ok:
        return _skip(reason)
    if race.wind_speed_m is None or race.wind_speed_m < 5 or race.wind_speed_m > 6:
        return _skip("not_wind_5_6")
    needed = ("4-1", "4-5")
    ok, reason = _need_odds(race, needed)
    if not ok:
        return _skip(reason)
    return _play(needed, "4wind only_wind_5_6 narrowed to 4-1/4-5")


def _evaluate_only_wind_5_6_415_skip_lt(threshold: float) -> Callable[[RaceContext], StrategyDecision]:
    def _inner(race: RaceContext) -> StrategyDecision:
        ok, reason = _base_structural_match(race)
        if not ok:
            return _skip(reason)
        if race.wind_speed_m is None or race.wind_speed_m < 5 or race.wind_speed_m > 6:
            return _skip("not_wind_5_6")
        needed = ("4-1", "4-5")
        ok, reason = _need_odds(race, needed)
        if not ok:
            return _skip(reason)
        if min(float(race.odds_41), float(race.odds_45)) < threshold:
            return _skip(f"min_odds_lt_{threshold:g}")
        return _play(needed, f"4wind only_wind_5_6 4-1/4-5 skip if min odds < {threshold:g}")

    return _inner


SPECS: tuple[StrategySpec, ...] = (
    StrategySpec(
        name="base_4156",
        description="Base 4wind with quoted odds coverage for 4-1/4-5/4-6.",
        evaluator=_evaluate_base_4156,
    ),
    StrategySpec(
        name="only_wind_5_6_4156",
        description="Refined 4wind (wind 5-6m) with 4-1/4-5/4-6.",
        evaluator=_evaluate_only_wind_5_6_4156,
    ),
    StrategySpec(
        name="only_wind_5_6_415",
        description="Refined 4wind (wind 5-6m) narrowed to 4-1/4-5.",
        evaluator=_evaluate_only_wind_5_6_415,
    ),
    StrategySpec(
        name="only_wind_5_6_415_skip_lt15",
        description="Refined 4wind 4-1/4-5; skip race if min quoted odds < 15.",
        evaluator=_evaluate_only_wind_5_6_415_skip_lt(15.0),
    ),
    StrategySpec(
        name="only_wind_5_6_415_skip_lt18",
        description="Refined 4wind 4-1/4-5; skip race if min quoted odds < 18.",
        evaluator=_evaluate_only_wind_5_6_415_skip_lt(18.0),
    ),
    StrategySpec(
        name="only_wind_5_6_415_skip_lt20",
        description="Refined 4wind 4-1/4-5; skip race if min quoted odds < 20.",
        evaluator=_evaluate_only_wind_5_6_415_skip_lt(20.0),
    ),
)


def _calculate_drawdown(bets: list[dict[str, object]]) -> tuple[int, str]:
    balance = 0
    peak = 0
    max_drawdown = 0
    max_drawdown_race_id = ""
    for bet in bets:
        balance += int(bet["realized_payout"]) - int(bet["stake_yen"])
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


def main() -> None:
    races = _load_races()
    summary_rows: list[dict[str, object]] = []
    bet_rows: list[dict[str, object]] = []

    for spec in SPECS:
        strategy_bets: list[dict[str, object]] = []
        skip_counts: Counter[str] = Counter()

        for race in races:
            decision = spec.evaluator(race)
            if not decision.played:
                skip_counts[decision.skip_reason] += 1
                continue

            hit_combo = race.exacta_combo or ""
            is_hit = int(hit_combo in set(decision.combos))
            realized_payout = int(race.exacta_payout or 0) if is_hit else 0
            combo_count = len(decision.combos)
            stake_yen = combo_count * STAKE_PER_BET_YEN
            min_odds = min(
                [
                    float(race.odds_41) if "4-1" in decision.combos and race.odds_41 is not None else float("inf"),
                    float(race.odds_45) if "4-5" in decision.combos and race.odds_45 is not None else float("inf"),
                    float(race.odds_46) if "4-6" in decision.combos and race.odds_46 is not None else float("inf"),
                ]
            )
            max_odds = max(
                [
                    float(race.odds_41) if "4-1" in decision.combos and race.odds_41 is not None else 0.0,
                    float(race.odds_45) if "4-5" in decision.combos and race.odds_45 is not None else 0.0,
                    float(race.odds_46) if "4-6" in decision.combos and race.odds_46 is not None else 0.0,
                ]
            )
            row = {
                "strategy_name": spec.name,
                "race_id": race.race_id,
                "race_date": race.race_date,
                "stadium_code": race.stadium_code,
                "stadium_name": race.stadium_name,
                "race_no": race.race_no,
                "wind_speed_m": race.wind_speed_m,
                "wave_height_cm": race.wave_height_cm,
                "odds_41": race.odds_41,
                "odds_45": race.odds_45,
                "odds_46": race.odds_46,
                "min_odds_played": None if min_odds == float("inf") else round(min_odds, 2),
                "max_odds_played": round(max_odds, 2),
                "combo_count": combo_count,
                "stake_yen": stake_yen,
                "settled_combo": race.exacta_combo,
                "is_hit": is_hit,
                "realized_payout": realized_payout,
                "notes": decision.notes,
            }
            strategy_bets.append(row)
            bet_rows.append(row)

        played_races = len(strategy_bets)
        bet_count = sum(int(row["combo_count"]) for row in strategy_bets)
        stake_yen = sum(int(row["stake_yen"]) for row in strategy_bets)
        return_yen = sum(int(row["realized_payout"]) for row in strategy_bets)
        hit_races = sum(int(row["is_hit"]) for row in strategy_bets)
        max_drawdown_yen, max_dd_race_id = _calculate_drawdown(strategy_bets)
        max_losing_streak = _calculate_losing_streak(strategy_bets)
        top_skip_reason = ""
        top_skip_reason_count = 0
        if skip_counts:
            top_skip_reason, top_skip_reason_count = skip_counts.most_common(1)[0]
        avg_min_odds_played = None
        if strategy_bets:
            odds_vals = [
                float(row["min_odds_played"])
                for row in strategy_bets
                if row["min_odds_played"] is not None
            ]
            if odds_vals:
                avg_min_odds_played = round(sum(odds_vals) / len(odds_vals), 2)

        summary_rows.append(
            {
                "strategy_name": spec.name,
                "description": spec.description,
                "played_races": played_races,
                "bet_count": bet_count,
                "stake_yen": stake_yen,
                "return_yen": return_yen,
                "profit_yen": return_yen - stake_yen,
                "roi_pct": round(return_yen * 100.0 / stake_yen, 2) if stake_yen else 0.0,
                "hit_races": hit_races,
                "hit_race_pct": round(hit_races * 100.0 / played_races, 2) if played_races else 0.0,
                "avg_min_odds_played": avg_min_odds_played,
                "max_drawdown_yen": max_drawdown_yen,
                "max_drawdown_race_id": max_dd_race_id,
                "max_losing_streak": max_losing_streak,
                "top_skip_reason": top_skip_reason,
                "top_skip_reason_count": top_skip_reason_count,
            }
        )

    _write_csv(
        OUTPUT_DIR / "backtest_summary.csv",
        list(summary_rows[0].keys()),
        summary_rows,
    )
    _write_csv(
        OUTPUT_DIR / "backtest_bets.csv",
        list(bet_rows[0].keys()) if bet_rows else [
            "strategy_name",
            "race_id",
            "race_date",
            "stadium_code",
            "stadium_name",
            "race_no",
            "wind_speed_m",
            "wave_height_cm",
            "odds_41",
            "odds_45",
            "odds_46",
            "min_odds_played",
            "max_odds_played",
            "combo_count",
            "stake_yen",
            "settled_combo",
            "is_hit",
            "realized_payout",
            "notes",
        ],
        bet_rows,
    )

    lines = [
        f"# 4Wind Odds Backtest {START_DATE} to {END_DATE}",
        "",
        "## Purpose",
        "- Re-run 4wind with the expanded `odds_2t` coverage.",
        "- All filtering uses quoted 2-exacta odds aggregated as the average per race/combo because `odds_2t` still contains duplicate combo rows.",
        "- Settlement uses official exacta payouts from `results`.",
        "- Stake is fixed at 100 yen per combo.",
        "",
        "## Summary",
        "| strategy_name | played_races | bet_count | roi_pct | hit_race_pct | avg_min_odds_played | max_drawdown_yen | max_losing_streak | top_skip_reason |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['strategy_name']} | {row['played_races']} | {row['bet_count']} | "
            f"{row['roi_pct']} | {row['hit_race_pct']} | {row['avg_min_odds_played']} | "
            f"{row['max_drawdown_yen']} | {row['max_losing_streak']} | {row['top_skip_reason']} |"
        )
    _write_text(OUTPUT_DIR / "README.md", "\n".join(lines))


if __name__ == "__main__":
    main()
