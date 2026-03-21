from __future__ import annotations

import csv
import itertools
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import duckdb


DB_PATH = Path(r"D:\boat\data\silver\boat_race.duckdb")
OUTPUT_DIR = Path(r"D:\boat\reports\strategies\gpt_structural_hypotheses_2024_20260320")
START_DATE = "2024-01-01"
END_DATE = "2024-12-31"
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
    e.racer_class,
    e.national_win_rate,
    bi.exhibition_time,
    bi.start_exhibition_st,
    res.first_place_lane,
    res.second_place_lane,
    res.third_place_lane,
    res.exacta_combo,
    res.trifecta_combo,
    res.exacta_payout,
    res.trifecta_payout
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
    DENSE_RANK() OVER (
      PARTITION BY race_id
      ORDER BY
        CASE WHEN national_win_rate IS NULL THEN 1 ELSE 0 END,
        national_win_rate DESC,
        lane ASC
    ) AS win_rate_rank,
    ROUND(
      exhibition_time - MIN(exhibition_time) OVER (PARTITION BY race_id),
      3
    ) AS exhibition_time_diff_from_top
  FROM feature_base
),
race_base AS (
  SELECT
    race_id,
    MIN(race_date) AS race_date,
    MIN(stadium_code) AS stadium_code,
    MIN(stadium_name) AS stadium_name,
    MIN(race_no) AS race_no,
    MAX(first_place_lane) AS first_place_lane,
    MAX(second_place_lane) AS second_place_lane,
    MAX(third_place_lane) AS third_place_lane,
    MAX(exacta_combo) AS exacta_combo,
    MAX(exacta_payout) AS exacta_payout,
    MAX(trifecta_combo) AS trifecta_combo,
    MAX(trifecta_payout) AS trifecta_payout,
    MAX(CASE WHEN lane = 1 THEN win_rate_rank END) AS lane1_win_rate_rank,
    MAX(CASE WHEN lane = 1 THEN exhibition_time_rank END) AS lane1_exhibition_time_rank,
    MAX(CASE WHEN lane = 1 THEN exhibition_time_diff_from_top END) AS lane1_vs_best_exhibition_diff,
    MAX(CASE WHEN exhibition_time_rank = 1 THEN lane END) AS exhibition_top_lane,
    MAX(CASE WHEN exhibition_time_rank = 1 THEN win_rate_rank END) AS exhibition_top_lane_win_rate_rank,
    SUM(CASE WHEN racer_class = 'B2' THEN 1 ELSE 0 END) AS b2_count,
    MAX(CASE WHEN lane = 1 THEN racer_class END) AS lane1_class,
    MAX(CASE WHEN lane = 2 THEN racer_class END) AS lane2_class,
    MAX(CASE WHEN lane = 6 THEN racer_class END) AS lane6_class
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
    first_place_lane: int | None
    second_place_lane: int | None
    third_place_lane: int | None
    exacta_combo: str | None
    exacta_payout: int | None
    trifecta_combo: str | None
    trifecta_payout: int | None
    lane1_win_rate_rank: int | None
    lane1_exhibition_time_rank: int | None
    lane1_vs_best_exhibition_diff: float | None
    exhibition_top_lane: int | None
    exhibition_top_lane_win_rate_rank: int | None
    b2_count: int | None
    lane1_class: str | None
    lane2_class: str | None
    lane6_class: str | None


@dataclass(frozen=True, slots=True)
class StrategyDecision:
    played: bool
    combos: tuple[str, ...]
    skip_reason: str
    notes: str


@dataclass(frozen=True, slots=True)
class StrategySpec:
    name: str
    source_hypothesis_id: str
    description: str


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


def _has_trifecta_result(race: RaceContext) -> bool:
    return race.trifecta_combo is not None and race.trifecta_payout is not None


def _all_all(first_lane: int) -> tuple[str, ...]:
    combos: list[str] = []
    others = [lane for lane in range(1, 7) if lane != first_lane]
    for second, third in itertools.permutations(others, 2):
        combos.append(f"{first_lane}-{second}-{third}")
    return tuple(combos)


def _hypothesis_a(race: RaceContext) -> StrategyDecision:
    if not _has_trifecta_result(race):
        return _skip("trifecta_result_missing")
    if race.lane1_win_rate_rank is None:
        return _skip("lane1_win_rate_rank_missing")
    if race.lane1_exhibition_time_rank is None:
        return _skip("lane1_ex_rank_missing")
    if race.lane1_vs_best_exhibition_diff is None:
        return _skip("lane1_vs_best_ex_diff_missing")
    if race.lane1_win_rate_rank < 3:
        return _skip("lane1_win_rate_rank_not_3plus")
    if race.lane1_exhibition_time_rank < 3:
        return _skip("lane1_ex_rank_not_3plus")
    if race.lane1_vs_best_exhibition_diff > 0.02:
        return _skip("lane1_ex_diff_too_large")
    combos = _all_all(2) + _all_all(3)
    return _play(combos, "H-A: weak-but-not-obviously-weak lane1 -> 2/3 head trifecta spray")


def _hypothesis_b(race: RaceContext) -> StrategyDecision:
    if not _has_trifecta_result(race):
        return _skip("trifecta_result_missing")
    if race.exhibition_top_lane is None:
        return _skip("exhibition_top_lane_missing")
    if race.exhibition_top_lane_win_rate_rank is None:
        return _skip("exhibition_top_lane_win_rank_missing")
    if race.exhibition_top_lane < 4:
        return _skip("exhibition_top_not_outer")
    if race.exhibition_top_lane_win_rate_rank < 3:
        return _skip("exhibition_top_win_rank_not_3plus")
    return _play(
        _all_all(race.exhibition_top_lane),
        "H-B: outer-lane exhibition top undervaluation",
    )


def _hypothesis_c(race: RaceContext) -> StrategyDecision:
    if not _has_trifecta_result(race):
        return _skip("trifecta_result_missing")
    if race.b2_count != 1:
        return _skip("b2_count_not_1")
    if race.lane6_class != "B2":
        return _skip("lane6_not_b2")
    if race.lane1_class == "A1":
        return _skip("lane1_is_a1")
    if race.lane2_class != "A1":
        return _skip("lane2_not_a1")
    combos = tuple(
        [f"2-1-{lane}" for lane in (3, 4, 5, 6)]
        + [f"2-3-{lane}" for lane in (1, 4, 5, 6)]
    )
    return _play(combos, "H-C: single B2 simplification miss")


SPECS: tuple[tuple[StrategySpec, callable], ...] = (
    (
        StrategySpec(
            name="GPT_HA_Trifecta_WeakInsideBias",
            source_hypothesis_id="A",
            description="lane1 looks mediocre but not visibly weak; spray 2-ALL-ALL and 3-ALL-ALL",
        ),
        _hypothesis_a,
    ),
    (
        StrategySpec(
            name="GPT_HB_Trifecta_OuterExTop",
            source_hypothesis_id="B",
            description="outer-lane exhibition top with only middling win-rate rank; play top-lane-ALL-ALL",
        ),
        _hypothesis_b,
    ),
    (
        StrategySpec(
            name="GPT_HC_Trifecta_B2Simplification",
            source_hypothesis_id="C",
            description="single B2 at lane6, lane1 not A1, lane2 A1; play 2-1-ALL and 2-3-ALL",
        ),
        _hypothesis_c,
    ),
)


def _calc_drawdown(bets: list[dict[str, object]]) -> tuple[int, str]:
    balance = 0
    peak = 0
    max_dd = 0
    max_dd_race_id = ""
    for bet in bets:
        balance += int(bet["realized_payout"]) - int(bet["stake_yen"])
        if balance > peak:
            peak = balance
        drawdown = peak - balance
        if drawdown > max_dd:
            max_dd = drawdown
            max_dd_race_id = str(bet["race_id"])
    return max_dd, max_dd_race_id


def _calc_losing_streak(bets: list[dict[str, object]]) -> int:
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

    for spec, evaluator in SPECS:
        skip_counts: Counter[str] = Counter()
        strategy_bets: list[dict[str, object]] = []

        for race in races:
            decision = evaluator(race)
            if not decision.played:
                skip_counts[decision.skip_reason] += 1
                continue

            combos = set(decision.combos)
            is_hit = int((race.trifecta_combo or "") in combos)
            realized_payout = int(race.trifecta_payout or 0) if is_hit else 0
            stake_yen = len(combos) * STAKE_PER_BET_YEN
            row = {
                "strategy_name": spec.name,
                "source_hypothesis_id": spec.source_hypothesis_id,
                "race_id": race.race_id,
                "race_date": race.race_date,
                "stadium_code": race.stadium_code,
                "stadium_name": race.stadium_name,
                "race_no": race.race_no,
                "combo_count": len(combos),
                "settled_combo": race.trifecta_combo,
                "is_hit": is_hit,
                "stake_yen": stake_yen,
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
        max_drawdown_yen, max_dd_race_id = _calc_drawdown(strategy_bets)
        max_losing_streak = _calc_losing_streak(strategy_bets)
        top_skip_reason = ""
        top_skip_reason_count = 0
        if skip_counts:
            top_skip_reason, top_skip_reason_count = skip_counts.most_common(1)[0]

        summary_rows.append(
            {
                "strategy_name": spec.name,
                "source_hypothesis_id": spec.source_hypothesis_id,
                "description": spec.description,
                "played_races": played_races,
                "bet_count": bet_count,
                "stake_yen": stake_yen,
                "return_yen": return_yen,
                "profit_yen": return_yen - stake_yen,
                "roi_pct": round(return_yen * 100.0 / stake_yen, 2) if stake_yen else 0.0,
                "hit_races": hit_races,
                "hit_race_pct": round(hit_races * 100.0 / played_races, 2) if played_races else 0.0,
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
            "source_hypothesis_id",
            "race_id",
            "race_date",
            "stadium_code",
            "stadium_name",
            "race_no",
            "combo_count",
            "settled_combo",
            "is_hit",
            "stake_yen",
            "realized_payout",
            "notes",
        ],
        bet_rows,
    )

    lines = [
        f"# GPT Structural Hypotheses Backtest {START_DATE} to {END_DATE}",
        "",
        "## Purpose",
        "- First-pass backtest of 3 GPT-generated structural hypotheses.",
        "- All three were interpreted as trifecta ideas because the buy notation used `-ALL-ALL`.",
        "- Stake is fixed at 100 yen per combo.",
        "",
        "## Caveat",
        "- This is an exploratory 2024-only test, not an out-of-sample validation.",
        "- Hypotheses A and B are very wide spray structures, so raw ROI alone can overstate practical usability.",
        "",
        "## Summary",
        "| strategy_name | played_races | bet_count | roi_pct | hit_race_pct | max_drawdown_yen | max_losing_streak | top_skip_reason |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['strategy_name']} | {row['played_races']} | {row['bet_count']} | "
            f"{row['roi_pct']} | {row['hit_race_pct']} | {row['max_drawdown_yen']} | "
            f"{row['max_losing_streak']} | {row['top_skip_reason']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "- H-A is broad and expensive: 40 points per race.",
            "- H-B is even broader structurally: 20 points per race and fires very often.",
            "- H-C is the most practical of the three from a combination-count perspective.",
        ]
    )
    _write_text(OUTPUT_DIR / "README.md", "\n".join(lines))


if __name__ == "__main__":
    main()
