from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import duckdb

from boat_race_data.gpt_export import FEATURES_QUERY
from boat_race_data.utils import ensure_dir

STAKE_PER_BET_YEN = 100
EXACTA_BET_TYPE = "2連単"

RACE_CONTEXT_QUERY = """
WITH feature_base AS ({features_query}),
race_base AS (
  SELECT
    race_id,
    MIN(race_date) AS race_date,
    MIN(stadium_code) AS stadium_code,
    MIN(stadium_name) AS stadium_name,
    MIN(race_no) AS race_no,
    MAX(grade) AS grade,
    MAX(meeting_day_no) AS meeting_day_no,
    MAX(CASE WHEN lane = 1 THEN racer_class END) AS lane1_class,
    MAX(CASE WHEN lane = 1 THEN national_win_rate END) AS lane1_national_win_rate,
    MAX(CASE WHEN lane = 1 THEN local_win_rate END) AS lane1_local_win_rate,
    MAX(CASE WHEN lane = 1 THEN motor_place_rate END) AS lane1_motor_place_rate,
    MAX(CASE WHEN lane = 1 THEN boat_place_rate END) AS lane1_boat_place_rate,
    MAX(wind_speed_m) AS wind_speed_m,
    MAX(exacta_combo) AS exacta_combo,
    MAX(exacta_payout) AS exacta_payout
  FROM feature_base
  GROUP BY race_id
)
SELECT
  race_id,
  race_date,
  stadium_code,
  stadium_name,
  race_no,
  grade,
  meeting_day_no,
  lane1_class,
  lane1_national_win_rate,
  lane1_local_win_rate,
  lane1_motor_place_rate,
  lane1_boat_place_rate,
  wind_speed_m,
  exacta_combo,
  exacta_payout
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
    lane1_class: str | None
    lane1_national_win_rate: float | None
    lane1_local_win_rate: float | None
    lane1_motor_place_rate: float | None
    lane1_boat_place_rate: float | None
    wind_speed_m: float | None
    exacta_combo: str | None
    exacta_payout: int | None


@dataclass(frozen=True, slots=True)
class StrategyDecision:
    played: bool
    combos: tuple[str, ...]
    skip_reason: str
    notes: str


StrategyEvaluator = Callable[[RaceContext], StrategyDecision]


@dataclass(frozen=True, slots=True)
class StrategySpec:
    name: str
    bet_type: str
    description: str
    evaluator: StrategyEvaluator


def _race_note(race: RaceContext) -> str:
    return (
        f"grade={race.grade or 'NA'} "
        f"day={race.meeting_day_no if race.meeting_day_no is not None else 'NA'} "
        f"lane1_class={race.lane1_class or 'NA'} "
        f"wind={race.wind_speed_m if race.wind_speed_m is not None else 'NA'} "
        f"exacta={race.exacta_combo or 'NA'}"
    )


def _has_result(race: RaceContext) -> bool:
    return race.exacta_combo is not None and race.exacta_payout is not None


def _play(race: RaceContext, combos: tuple[str, ...], reason_note: str) -> StrategyDecision:
    return StrategyDecision(played=True, combos=combos, skip_reason="", notes=f"{reason_note}; {_race_note(race)}")


def _skip(race: RaceContext, skip_reason: str) -> StrategyDecision:
    return StrategyDecision(played=False, combos=(), skip_reason=skip_reason, notes=_race_note(race))


def _evaluate_v6_a(race: RaceContext) -> StrategyDecision:
    if not _has_result(race):
        return _skip(race, "result_missing")
    if race.grade not in {"SG", "G1"}:
        return _skip(race, "grade_not_target")
    if race.meeting_day_no not in {1, 2, 3}:
        return _skip(race, "meeting_day_not_target")
    if race.lane1_class not in {"A1", "A2"}:
        return _skip(race, "lane1_class_not_target")
    return _play(race, ("1-3",), "SG/G1 early-days exacta 1-3")


def _evaluate_v6_b(race: RaceContext) -> StrategyDecision:
    if not _has_result(race):
        return _skip(race, "result_missing")
    if race.stadium_code not in {"14", "09", "02", "01", "04"}:
        return _skip(race, "stadium_not_target")
    if race.lane1_class not in {"A2", "B1", "B2"}:
        return _skip(race, "lane1_class_not_target")
    return _play(race, ("2-1", "3-1"), "weak-lane1 stadium exacta 2-1 / 3-1")


def _evaluate_v6_c(race: RaceContext) -> StrategyDecision:
    if not _has_result(race):
        return _skip(race, "result_missing")
    if race.wind_speed_m is None or race.wind_speed_m < 6:
        return _skip(race, "wind_not_target")
    if race.lane1_class != "A1":
        return _skip(race, "lane1_class_not_target")
    return _play(race, ("1-3", "3-1"), "high-wind exacta 1-3 / 3-1")


STRATEGIES: tuple[StrategySpec, ...] = (
    StrategySpec(
        name="StrategyV6_A_G1_EarlyDays_1_3",
        bet_type=EXACTA_BET_TYPE,
        description="SG/G1 and meeting day 1-3 with lane 1 in A1/A2. Buy exacta 1-3 only.",
        evaluator=_evaluate_v6_a,
    ),
    StrategySpec(
        name="StrategyV6_B_WeakInStadium_21_31",
        bet_type=EXACTA_BET_TYPE,
        description="Stadium in {14,09,02,01,04} and lane 1 class in A2/B1/B2. Buy exacta 2-1 and 3-1.",
        evaluator=_evaluate_v6_b,
    ),
    StrategySpec(
        name="StrategyV6_C_HighWind_13_31",
        bet_type=EXACTA_BET_TYPE,
        description="Wind speed >= 6m and lane 1 in A1. Buy exacta 1-3 and 3-1.",
        evaluator=_evaluate_v6_c,
    ),
)


def _load_race_contexts(con: duckdb.DuckDBPyConnection, start_date: str, end_date: str) -> list[RaceContext]:
    query = RACE_CONTEXT_QUERY.format(
        features_query=FEATURES_QUERY.format(start_date=start_date, end_date=end_date)
    )
    rows = con.execute(query).fetchall()
    return [RaceContext(*row) for row in rows]


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> int:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def _write_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8-sig")


def _calculate_drawdown(bets: list[dict[str, object]]) -> tuple[int, str]:
    balance = 0
    peak = 0
    max_drawdown = 0
    max_drawdown_race_id = ""
    for bet in bets:
        balance += int(bet["realized_payout"]) - STAKE_PER_BET_YEN
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
            continue
        streak += 1
        max_streak = max(max_streak, streak)
    return max_streak


def _build_report(
    start_date: str,
    end_date: str,
    summary_rows: list[dict[str, object]],
) -> str:
    lines = [
        f"# Backtest Report {start_date} to {end_date}",
        "",
        "## Purpose",
        "- Validation run for discovery-derived v6 exacta strategies.",
        "- Stake is fixed at 100 yen per combo.",
        "- Settlement uses official exacta results and payouts from `results`.",
        "",
        "## Tested Strategies",
    ]
    for strategy in STRATEGIES:
        lines.append(f"- `{strategy.name}`: {strategy.description}")
    lines.extend(
        [
            "",
            "## Summary",
            "| strategy_name | played_races | bet_count | roi_pct | hit_count | max_drawdown_yen | max_losing_streak | top_skip_reason |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in summary_rows:
        lines.append(
            f"| {row['strategy_name']} | {row['played_races']} | {row['bet_count']} | {row['roi_pct']} | "
            f"{row['hit_count']} | {row['max_drawdown_yen']} | {row['max_losing_streak']} | {row['top_skip_reason']} |"
        )
    lines.extend(
        [
            "",
            "## Files",
            "- `backtest_variant_specs.csv`: one row per tested strategy.",
            "- `backtest_strategy_summary.csv`: aggregate metrics by strategy.",
            "- `backtest_skip_reason_summary.csv`: skip counts by strategy.",
            "- `backtest_bets.csv`: actual bet rows with realized payouts.",
            "- `backtest_race_decisions.csv`: one decision row per race and strategy.",
        ]
    )
    return "\n".join(lines)


def _build_prompt_after_backtest(start_date: str, end_date: str) -> str:
    lines = [
        "# Prompt After Backtest",
        "",
        "Use the attached validation backtest outputs to assess robustness of the v6 strategies.",
        "",
        "Focus on:",
        f"- Validation period: `{start_date}` to `{end_date}`",
        "- Whether ROI is supported by reasonable sample size",
        "- Whether max drawdown and losing streak are acceptable",
        "- Which filters should be simplified, tightened, or discarded",
        "",
        "Files:",
        "- `backtest_strategy_summary.csv`",
        "- `backtest_skip_reason_summary.csv`",
        "- `backtest_bets.csv`",
        "- `backtest_race_decisions.csv`",
    ]
    return "\n".join(lines)


def run_backtest(
    db_path: Path,
    start_date: str,
    end_date: str,
    output_dir: Path,
) -> dict[str, int]:
    ensure_dir(output_dir)

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        races = _load_race_contexts(con, start_date=start_date, end_date=end_date)
    finally:
        con.close()

    variant_spec_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    skip_reason_rows: list[dict[str, object]] = []
    bet_rows: list[dict[str, object]] = []
    race_decision_rows: list[dict[str, object]] = []

    for strategy in STRATEGIES:
        variant_spec_rows.append(
            {
                "strategy_name": strategy.name,
                "bet_type": strategy.bet_type,
                "description": strategy.description,
            }
        )

        strategy_bets: list[dict[str, object]] = []
        skip_reasons: Counter[str] = Counter()
        played_races = 0

        for race in races:
            decision = strategy.evaluator(race)
            race_decision_rows.append(
                {
                    "strategy_name": strategy.name,
                    "race_id": race.race_id,
                    "race_date": race.race_date,
                    "stadium_code": race.stadium_code,
                    "stadium_name": race.stadium_name,
                    "race_no": race.race_no,
                    "played": 1 if decision.played else 0,
                    "bet_count": len(decision.combos),
                    "skip_reason": decision.skip_reason,
                    "notes": decision.notes,
                }
            )

            if not decision.played:
                skip_reasons[decision.skip_reason] += 1
                continue

            played_races += 1
            for combo in decision.combos:
                is_hit = int(combo == race.exacta_combo)
                realized_payout = int(race.exacta_payout or 0) if is_hit else 0
                bet_row = {
                    "strategy_name": strategy.name,
                    "race_id": race.race_id,
                    "race_date": race.race_date,
                    "stadium_code": race.stadium_code,
                    "stadium_name": race.stadium_name,
                    "race_no": race.race_no,
                    "bet_type": strategy.bet_type,
                    "combo": combo,
                    "odds": "",
                    "odds_status": "",
                    "is_hit": is_hit,
                    "realized_payout": realized_payout,
                    "notes": strategy.description,
                }
                strategy_bets.append(bet_row)
                bet_rows.append(bet_row)

        evaluated_races = len(races)
        skipped_races = evaluated_races - played_races
        bet_count = len(strategy_bets)
        stake_yen = bet_count * STAKE_PER_BET_YEN
        return_yen = sum(int(row["realized_payout"]) for row in strategy_bets)
        profit_yen = return_yen - stake_yen
        hit_count = sum(int(row["is_hit"]) for row in strategy_bets)
        max_drawdown_yen, max_drawdown_race_id = _calculate_drawdown(strategy_bets)
        max_losing_streak = _calculate_losing_streak(strategy_bets)
        top_skip_reason = ""
        top_skip_reason_count = 0
        if skip_reasons:
            top_skip_reason, top_skip_reason_count = skip_reasons.most_common(1)[0]
        for reason, count in skip_reasons.most_common():
            skip_reason_rows.append(
                {
                    "strategy_name": strategy.name,
                    "skip_reason": reason,
                    "skip_count": count,
                }
            )
        summary_rows.append(
            {
                "strategy_name": strategy.name,
                "description": strategy.description,
                "evaluated_races": evaluated_races,
                "played_races": played_races,
                "skipped_races": skipped_races,
                "skip_rate_pct": round(skipped_races * 100.0 / evaluated_races, 2) if evaluated_races else 0.0,
                "bet_count": bet_count,
                "stake_yen": stake_yen,
                "return_yen": return_yen,
                "profit_yen": profit_yen,
                "roi_pct": round(return_yen * 100.0 / stake_yen, 2) if stake_yen else 0.0,
                "hit_count": hit_count,
                "hit_rate_pct": round(hit_count * 100.0 / bet_count, 2) if bet_count else 0.0,
                "max_drawdown_yen": max_drawdown_yen,
                "max_drawdown_race_id": max_drawdown_race_id,
                "max_losing_streak": max_losing_streak,
                "avg_bets_per_played_race": round(bet_count / played_races, 2) if played_races else 0.0,
                "top_skip_reason": top_skip_reason,
                "top_skip_reason_count": top_skip_reason_count,
            }
        )

    row_counts = {
        "backtest_variant_specs.csv": _write_csv(
            output_dir / "backtest_variant_specs.csv",
            ["strategy_name", "bet_type", "description"],
            variant_spec_rows,
        ),
        "backtest_strategy_summary.csv": _write_csv(
            output_dir / "backtest_strategy_summary.csv",
            [
                "strategy_name",
                "description",
                "evaluated_races",
                "played_races",
                "skipped_races",
                "skip_rate_pct",
                "bet_count",
                "stake_yen",
                "return_yen",
                "profit_yen",
                "roi_pct",
                "hit_count",
                "hit_rate_pct",
                "max_drawdown_yen",
                "max_drawdown_race_id",
                "max_losing_streak",
                "avg_bets_per_played_race",
                "top_skip_reason",
                "top_skip_reason_count",
            ],
            summary_rows,
        ),
        "backtest_skip_reason_summary.csv": _write_csv(
            output_dir / "backtest_skip_reason_summary.csv",
            ["strategy_name", "skip_reason", "skip_count"],
            skip_reason_rows,
        ),
        "backtest_bets.csv": _write_csv(
            output_dir / "backtest_bets.csv",
            [
                "strategy_name",
                "race_id",
                "race_date",
                "stadium_code",
                "stadium_name",
                "race_no",
                "bet_type",
                "combo",
                "odds",
                "odds_status",
                "is_hit",
                "realized_payout",
                "notes",
            ],
            bet_rows,
        ),
        "backtest_race_decisions.csv": _write_csv(
            output_dir / "backtest_race_decisions.csv",
            [
                "strategy_name",
                "race_id",
                "race_date",
                "stadium_code",
                "stadium_name",
                "race_no",
                "played",
                "bet_count",
                "skip_reason",
                "notes",
            ],
            race_decision_rows,
        ),
    }

    _write_text(output_dir / "backtest_report.md", _build_report(start_date, end_date, summary_rows))
    _write_text(output_dir / "prompt_after_backtest.md", _build_prompt_after_backtest(start_date, end_date))
    row_counts["backtest_report.md"] = 1
    row_counts["prompt_after_backtest.md"] = 1
    return row_counts
