from __future__ import annotations

import csv
import os
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import duckdb

from boat_race_data.gpt_export import FEATURES_QUERY


DB_PATH = Path(r"D:\boat\data\silver\boat_race.duckdb")
START_DATE = os.environ.get("GEMINI_BT_START_DATE", "2024-01-01")
END_DATE = os.environ.get("GEMINI_BT_END_DATE", "2024-12-31")
OUTPUT_DIR = Path(
    os.environ.get(
        "GEMINI_BT_OUTPUT_DIR",
        fr"D:\boat\reports\strategies\gemini_zero_base_{START_DATE}_to_{END_DATE}",
    )
)
STAKE_PER_BET_YEN = 100


STADIUM_BRANCH_MAP = {
    "01": "群馬",
    "02": "埼玉",
    "03": "東京",
    "04": "東京",
    "05": "東京",
    "06": "静岡",
    "07": "愛知",
    "08": "愛知",
    "09": "三重",
    "10": "福井",
    "11": "滋賀",
    "12": "大阪",
    "13": "兵庫",
    "14": "徳島",
    "15": "香川",
    "16": "岡山",
    "17": "広島",
    "18": "山口",
    "19": "山口",
    "20": "福岡",
    "21": "福岡",
    "22": "福岡",
    "23": "佐賀",
    "24": "長崎",
}


RACE_QUERY = """
WITH feature_base AS ({features_query}),
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
    MAX(trifecta_combo) AS trifecta_combo,
    MAX(trifecta_payout) AS trifecta_payout,
    SUM(CASE WHEN racer_class = 'A1' THEN 1 ELSE 0 END) AS a1_count,
    SUM(CASE WHEN racer_class = 'A2' THEN 1 ELSE 0 END) AS a2_count,
    SUM(CASE WHEN racer_class = 'B1' THEN 1 ELSE 0 END) AS b1_count,
    SUM(CASE WHEN racer_class = 'B2' THEN 1 ELSE 0 END) AS b2_count,
    MAX(CASE WHEN lane = 1 THEN racer_class END) AS lane1_class,
    MAX(CASE WHEN lane = 1 THEN branch END) AS lane1_branch,
    MAX(CASE WHEN lane = 1 THEN exhibition_time_rank END) AS lane1_exhibition_time_rank,
    MAX(CASE WHEN lane = 2 THEN exhibition_time_rank END) AS lane2_exhibition_time_rank,
    MAX(CASE WHEN lane = 4 THEN exhibition_time_rank END) AS lane4_exhibition_time_rank,
    MAX(CASE WHEN lane = 5 THEN exhibition_time_rank END) AS lane5_exhibition_time_rank,
    MAX(CASE WHEN lane = 2 THEN st_diff_from_inside END) AS lane2_st_diff_from_inside,
    MAX(CASE WHEN lane = 4 THEN st_diff_from_inside END) AS lane4_st_diff_from_inside,
    MAX(CASE WHEN lane = 2 THEN racer_class END) AS lane2_class,
    MAX(CASE WHEN lane = 3 THEN racer_class END) AS lane3_class,
    MAX(CASE WHEN lane = 5 THEN win_rate_rank END) AS lane5_win_rate_rank
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
    is_final_day: bool | None
    weather_condition: str | None
    wind_speed_m: float | None
    wave_height_cm: int | None
    exacta_combo: str | None
    exacta_payout: int | None
    trifecta_combo: str | None
    trifecta_payout: int | None
    a1_count: int | None
    a2_count: int | None
    b1_count: int | None
    b2_count: int | None
    lane1_class: str | None
    lane1_branch: str | None
    lane1_exhibition_time_rank: int | None
    lane2_exhibition_time_rank: int | None
    lane4_exhibition_time_rank: int | None
    lane5_exhibition_time_rank: int | None
    lane2_st_diff_from_inside: float | None
    lane4_st_diff_from_inside: float | None
    lane2_class: str | None
    lane3_class: str | None
    lane5_win_rate_rank: int | None


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
    source_hypothesis_id: str


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


def _has_exacta_result(race: RaceContext) -> bool:
    return race.exacta_combo is not None and race.exacta_payout is not None


def _has_trifecta_result(race: RaceContext) -> bool:
    return race.trifecta_combo is not None and race.trifecta_payout is not None


def _lane1_is_hometown(race: RaceContext) -> bool:
    expected_branch = STADIUM_BRANCH_MAP.get(race.stadium_code)
    return expected_branch is not None and race.lane1_branch == expected_branch


def _play(race: RaceContext, combos: tuple[str, ...], note: str) -> StrategyDecision:
    return StrategyDecision(True, combos, "", note)


def _skip(reason: str, note: str = "") -> StrategyDecision:
    return StrategyDecision(False, (), reason, note)


def _evaluate_h001(race: RaceContext) -> StrategyDecision:
    if not _has_exacta_result(race):
        return _skip("exacta_result_missing")
    if race.lane1_exhibition_time_rank is None:
        return _skip("lane1_ex_rank_missing")
    if race.lane2_exhibition_time_rank is None:
        return _skip("lane2_ex_rank_missing")
    if race.lane2_st_diff_from_inside is None:
        return _skip("lane2_st_diff_missing")
    if race.lane1_exhibition_time_rank < 4:
        return _skip("lane1_not_weak_enough")
    if race.lane2_exhibition_time_rank > 2:
        return _skip("lane2_not_fast_enough")
    if race.lane2_st_diff_from_inside > -0.05:
        return _skip("lane2_st_edge_missing")
    return _play(race, ("2-1", "2-3", "2-4"), "Normalized H-001 exacta")


def _evaluate_h002(race: RaceContext) -> StrategyDecision:
    if not _has_exacta_result(race):
        return _skip("exacta_result_missing")
    if race.wind_speed_m is None:
        return _skip("wind_missing")
    if race.lane4_st_diff_from_inside is None:
        return _skip("lane4_st_diff_missing")
    if race.lane4_exhibition_time_rank is None:
        return _skip("lane4_ex_rank_missing")
    if race.wind_speed_m < 4:
        return _skip("wind_not_target")
    if race.lane4_st_diff_from_inside > -0.05:
        return _skip("lane4_st_edge_missing")
    if race.lane4_exhibition_time_rank > 3:
        return _skip("lane4_not_fast_enough")
    return _play(race, ("4-1", "4-5", "4-6"), "Normalized H-002 exacta")


def _evaluate_h003(race: RaceContext) -> StrategyDecision:
    if not _has_trifecta_result(race):
        return _skip("trifecta_result_missing")
    if race.a1_count != 2:
        return _skip("a1_count_not_2")
    if race.lane1_class != "A1":
        return _skip("lane1_class_not_a1")
    if race.lane2_class != "A1" and race.lane3_class != "A1":
        return _skip("lane23_no_a1_wall")
    if race.lane4_exhibition_time_rank is None:
        return _skip("lane4_ex_rank_missing")
    if race.lane4_exhibition_time_rank < 3:
        return _skip("lane4_too_strong")
    return _play(race, ("1-2-3", "1-3-2", "1-2-4"), "Normalized H-003 trifecta")


def _evaluate_h004(race: RaceContext) -> StrategyDecision:
    if not _has_exacta_result(race):
        return _skip("exacta_result_missing")
    if race.wave_height_cm is None:
        return _skip("wave_missing")
    if race.lane1_exhibition_time_rank is None:
        return _skip("lane1_ex_rank_missing")
    if race.wave_height_cm < 5:
        return _skip("wave_not_target")
    if not _lane1_is_hometown(race):
        return _skip("lane1_not_hometown")
    if race.lane1_exhibition_time_rank > 3:
        return _skip("lane1_not_fast_enough")
    return _play(race, ("1-2", "1-3"), "Normalized H-004 exacta with corrected hometown mapping")


def _evaluate_h005(race: RaceContext) -> StrategyDecision:
    if not _has_trifecta_result(race):
        return _skip("trifecta_result_missing")
    if race.lane5_win_rate_rank is None:
        return _skip("lane5_win_rank_missing")
    if race.lane5_exhibition_time_rank is None:
        return _skip("lane5_ex_rank_missing")
    if race.lane4_st_diff_from_inside is None:
        return _skip("lane4_st_diff_missing")
    if race.lane5_win_rate_rank < 4:
        return _skip("lane5_not_underestimated")
    if race.lane5_exhibition_time_rank != 1:
        return _skip("lane5_not_best_ex")
    if race.lane4_st_diff_from_inside < 0.05:
        return _skip("lane4_delay_not_enough")
    return _play(race, ("5-1-2", "5-1-6"), "Normalized H-005 trifecta")


STRATEGIES = (
    StrategySpec(
        name="Gemini_H001_Exacta_L2_Pressure",
        bet_type="2連単",
        description="Lane 1 weak on exhibition, lane 2 strong on exhibition and ST edge. Buy 2-1, 2-3, 2-4.",
        evaluator=_evaluate_h001,
        source_hypothesis_id="H-001",
    ),
    StrategySpec(
        name="Gemini_H002_Exacta_L4_WindyAttack",
        bet_type="2連単",
        description="Wind >= 4m, lane 4 has ST edge and good exhibition. Buy 4-1, 4-5, 4-6.",
        evaluator=_evaluate_h002,
        source_hypothesis_id="H-002",
    ),
    StrategySpec(
        name="Gemini_H003_Trifecta_InnerA1Wall",
        bet_type="3連単",
        description="Exactly two A1s with lane 1 as A1 and another A1 in lane 2 or 3, lane 4 not too strong. Buy 1-2-3, 1-3-2, 1-2-4.",
        evaluator=_evaluate_h003,
        source_hypothesis_id="H-003",
    ),
    StrategySpec(
        name="Gemini_H004_Exacta_HometownRoughWater",
        bet_type="2連単",
        description="Wave >= 5cm, lane 1 is hometown by corrected venue-branch mapping, lane 1 exhibition rank <= 3. Buy 1-2, 1-3.",
        evaluator=_evaluate_h004,
        source_hypothesis_id="H-004",
    ),
    StrategySpec(
        name="Gemini_H005_Trifecta_L5_OverlookedRocket",
        bet_type="3連単",
        description="Lane 5 low prior rank but best exhibition, lane 4 delayed on ST. Buy 5-1-2, 5-1-6.",
        evaluator=_evaluate_h005,
        source_hypothesis_id="H-005",
    ),
)


def _load_races() -> list[RaceContext]:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        query = RACE_QUERY.format(features_query=FEATURES_QUERY.format(start_date=START_DATE, end_date=END_DATE))
        rows = con.execute(query).fetchall()
        return [RaceContext(*row) for row in rows]
    finally:
        con.close()


def _calculate_drawdown(bets: list[dict[str, object]]) -> tuple[int, str]:
    balance = 0
    peak = 0
    max_drawdown = 0
    max_race_id = ""
    for bet in bets:
        balance += int(bet["realized_payout"]) - STAKE_PER_BET_YEN
        peak = max(peak, balance)
        drawdown = peak - balance
        if drawdown > max_drawdown:
            max_drawdown = drawdown
            max_race_id = str(bet["race_id"])
    return max_drawdown, max_race_id


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


def _build_normalized_logic_md() -> str:
    return "\n".join(
        [
            "# Gemini Zero-Base Hypotheses Normalized For Backtest",
            "",
            f"- source period used by Gemini sample: `2024-01-01..2024-04-30`",
            f"- first backtest window here: `{START_DATE}..{END_DATE}`",
            "- Gemini conversation is kept untouched in `GPT/gemini.md`.",
            "- This file is the human-side normalization layer for mechanical backtesting.",
            "",
            "## Notes",
            "- `H-004` used a broken sample-side `is_hometown` flag. For backtest, it is corrected by mapping each stadium code to its venue branch prefecture and comparing against `lane1_branch`.",
            "- The first 2024 run is exploratory, not a clean OOS validation, because the Gemini sample was drawn from `2024-01-01..2024-04-30`.",
            "",
            "## Normalized Rules",
            "",
            "### H-001 -> Gemini_H001_Exacta_L2_Pressure",
            "- bet type: `2連単`",
            "- combos: `2-1`, `2-3`, `2-4`",
            "- conditions:",
            "- `lane1_exhibition_time_rank >= 4`",
            "- `lane2_exhibition_time_rank <= 2`",
            "- `lane2_st_diff_from_inside <= -0.05`",
            "",
            "### H-002 -> Gemini_H002_Exacta_L4_WindyAttack",
            "- bet type: `2連単`",
            "- combos: `4-1`, `4-5`, `4-6`",
            "- conditions:",
            "- `wind_speed_m >= 4`",
            "- `lane4_st_diff_from_inside <= -0.05`",
            "- `lane4_exhibition_time_rank <= 3`",
            "",
            "### H-003 -> Gemini_H003_Trifecta_InnerA1Wall",
            "- bet type: `3連単`",
            "- combos: `1-2-3`, `1-3-2`, `1-2-4`",
            "- conditions:",
            "- `a1_count = 2`",
            "- `lane1_class = 'A1'`",
            "- `(lane2_class = 'A1' OR lane3_class = 'A1')`",
            "- `lane4_exhibition_time_rank >= 3`",
            "",
            "### H-004 -> Gemini_H004_Exacta_HometownRoughWater",
            "- bet type: `2連単`",
            "- combos: `1-2`, `1-3`",
            "- conditions:",
            "- `wave_height_cm >= 5`",
            "- `lane1_is_hometown = 1` using corrected venue-branch mapping",
            "- `lane1_exhibition_time_rank <= 3`",
            "",
            "### H-005 -> Gemini_H005_Trifecta_L5_OverlookedRocket",
            "- bet type: `3連単`",
            "- combos: `5-1-2`, `5-1-6`",
            "- conditions:",
            "- `lane5_win_rate_rank >= 4`",
            "- `lane5_exhibition_time_rank = 1`",
            "- `lane4_st_diff_from_inside >= 0.05`",
        ]
    )


def _build_report(summary_rows: list[dict[str, object]]) -> str:
    lines = [
        f"# Gemini Zero-Base Backtest {START_DATE} to {END_DATE}",
        "",
        "## Purpose",
        "- Human-side normalization and first-pass 2024 backtest for Gemini-generated zero-base hypotheses.",
        "- Gemini conversation itself was left untouched and preserved separately.",
        "- Settlement uses official exacta/trifecta result combos and payouts from `results`.",
        "- Stake is fixed at 100 yen per combo.",
        "",
        "## Important Caveat",
        "- This is not a clean out-of-sample validation because the Gemini sample package came from `2024-01-01..2024-04-30`.",
        "- Treat this as a first 2024 exploratory screen, not a final adoption test.",
        "",
        "## Summary",
        "| strategy_name | bet_type | played_races | bet_count | roi_pct | hit_count | max_drawdown_yen | max_losing_streak | top_skip_reason |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['strategy_name']} | {row['bet_type']} | {row['played_races']} | {row['bet_count']} | "
            f"{row['roi_pct']} | {row['hit_count']} | {row['max_drawdown_yen']} | {row['max_losing_streak']} | {row['top_skip_reason']} |"
        )
    return "\n".join(lines)


def main() -> None:
    races = _load_races()

    variant_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    skip_rows: list[dict[str, object]] = []
    bet_rows: list[dict[str, object]] = []
    decision_rows: list[dict[str, object]] = []

    for strategy in STRATEGIES:
        variant_rows.append(
            {
                "strategy_name": strategy.name,
                "source_hypothesis_id": strategy.source_hypothesis_id,
                "bet_type": strategy.bet_type,
                "description": strategy.description,
            }
        )

        strategy_bets: list[dict[str, object]] = []
        skip_reasons: Counter[str] = Counter()
        played_races = 0

        for race in races:
            decision = strategy.evaluator(race)
            decision_rows.append(
                {
                    "strategy_name": strategy.name,
                    "source_hypothesis_id": strategy.source_hypothesis_id,
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
            settled_combo = race.exacta_combo if strategy.bet_type == "2連単" else race.trifecta_combo
            settled_payout = race.exacta_payout if strategy.bet_type == "2連単" else race.trifecta_payout
            for combo in decision.combos:
                is_hit = int(combo == settled_combo)
                realized_payout = int(settled_payout or 0) if is_hit else 0
                row = {
                    "strategy_name": strategy.name,
                    "source_hypothesis_id": strategy.source_hypothesis_id,
                    "race_id": race.race_id,
                    "race_date": race.race_date,
                    "stadium_code": race.stadium_code,
                    "stadium_name": race.stadium_name,
                    "race_no": race.race_no,
                    "bet_type": strategy.bet_type,
                    "combo": combo,
                    "is_hit": is_hit,
                    "realized_payout": realized_payout,
                    "notes": decision.notes,
                }
                strategy_bets.append(row)
                bet_rows.append(row)

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
            skip_rows.append(
                {
                    "strategy_name": strategy.name,
                    "skip_reason": reason,
                    "skip_count": count,
                }
            )
        summary_rows.append(
            {
                "strategy_name": strategy.name,
                "source_hypothesis_id": strategy.source_hypothesis_id,
                "bet_type": strategy.bet_type,
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

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_text(OUTPUT_DIR / "normalized_hypotheses.md", _build_normalized_logic_md())
    _write_text(OUTPUT_DIR / "backtest_report.md", _build_report(summary_rows))
    _write_csv(
        OUTPUT_DIR / "backtest_variant_specs.csv",
        ["strategy_name", "source_hypothesis_id", "bet_type", "description"],
        variant_rows,
    )
    _write_csv(
        OUTPUT_DIR / "backtest_strategy_summary.csv",
        [
            "strategy_name",
            "source_hypothesis_id",
            "bet_type",
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
    )
    _write_csv(
        OUTPUT_DIR / "backtest_skip_reason_summary.csv",
        ["strategy_name", "skip_reason", "skip_count"],
        skip_rows,
    )
    _write_csv(
        OUTPUT_DIR / "backtest_bets.csv",
        [
            "strategy_name",
            "source_hypothesis_id",
            "race_id",
            "race_date",
            "stadium_code",
            "stadium_name",
            "race_no",
            "bet_type",
            "combo",
            "is_hit",
            "realized_payout",
            "notes",
        ],
        bet_rows,
    )
    _write_csv(
        OUTPUT_DIR / "backtest_race_decisions.csv",
        [
            "strategy_name",
            "source_hypothesis_id",
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
        decision_rows,
    )

    print(f"wrote_output_dir={OUTPUT_DIR}")
    for row in summary_rows:
        print(
            row["strategy_name"],
            f"played_races={row['played_races']}",
            f"bet_count={row['bet_count']}",
            f"roi_pct={row['roi_pct']}",
            f"hit_count={row['hit_count']}",
        )


if __name__ == "__main__":
    main()
