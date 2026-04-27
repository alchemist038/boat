from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb
from runtime_paths import default_results_db_path

import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
BETS_CORE_DIR = REPO_ROOT / "live_trigger" / "auto_system" / "app" / "core"
if str(BETS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(BETS_CORE_DIR))

from bets import _expand_trifecta_combo, _lane_class_map_for_race, _lane_class_map_from_context


def _default_runtime_root() -> Path:
    explicit = os.environ.get("BOAT_ACTIVE_RUNTIME_ROOT")
    if explicit:
        return Path(explicit)
    c_boat_runtime = Path(r"C:\boat")
    if (c_boat_runtime / "live_trigger_cli" / "data" / "system.db").exists():
        return c_boat_runtime
    return REPO_ROOT


DEFAULT_RUNTIME_ROOT = _default_runtime_root()
DEFAULT_SYSTEM_DB = DEFAULT_RUNTIME_ROOT / "live_trigger_cli" / "data" / "system.db"
DEFAULT_REPORT_ROOT = REPO_ROOT / "reports" / "live_trade"


def _default_results_db() -> Path:
    return default_results_db_path()


DEFAULT_RESULTS_DB = _default_results_db()


@dataclass
class ExpandedBetRow:
    race_date: str
    race_id: str
    profile_id: str
    strategy_id: str
    execution_mode: str
    executed_at: str
    contract_no: str | None
    bet_type: str
    combo: str
    amount: int


def _normalize_combo(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    text = re.sub(r"\s*-\s*", "-", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _expand_intent_rows(
    *,
    bet_type: str,
    combo: str,
    amount: int,
    context: dict[str, Any],
) -> list[tuple[str, str, int]]:
    normalized_bet_type = str(bet_type).lower()
    raw_combo = str(combo)
    if "ALL" not in raw_combo:
        return [(normalized_bet_type, _normalize_combo(raw_combo) or raw_combo, int(amount))]

    lane_class_map = _lane_class_map_from_context(context)
    if not lane_class_map:
        race_id = context.get("race_id")
        if race_id:
            lane_class_map = _lane_class_map_for_race(race_id)
    if not lane_class_map:
        return [(normalized_bet_type, _normalize_combo(raw_combo) or raw_combo, int(amount))]

    excluded_lanes = {
        lane for lane, racer_class in lane_class_map.items() if str(racer_class).upper() == "B2"
    }
    if normalized_bet_type != "trifecta":
        return [(normalized_bet_type, _normalize_combo(raw_combo) or raw_combo, int(amount))]

    return [
        ("trifecta", _normalize_combo(expanded_combo) or expanded_combo, int(amount))
        for expanded_combo in _expand_trifecta_combo(raw_combo, excluded_lanes=excluded_lanes)
    ]


def _load_submitted_bets(system_db_path: Path) -> list[ExpandedBetRow]:
    connection = sqlite3.connect(system_db_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT
                be.execution_mode,
                be.execution_status,
                be.executed_at,
                be.contract_no,
                tr.race_id,
                tr.race_date,
                tr.profile_id,
                tr.strategy_id,
                tr.payload_json,
                bi.bet_type,
                bi.combo,
                bi.amount
            FROM bet_executions AS be
            JOIN target_races AS tr ON tr.id = be.target_race_id
            JOIN bet_intents AS bi ON bi.id = be.intent_id
            WHERE be.execution_status = 'submitted'
              AND be.execution_mode IN ('assist_real', 'armed_real')
            ORDER BY tr.race_date, tr.race_id, be.executed_at, bi.id
            """
        ).fetchall()
    finally:
        connection.close()

    expanded_rows: list[ExpandedBetRow] = []
    for row in rows:
        context: dict[str, Any] = {}
        payload_json = row["payload_json"]
        if payload_json:
            try:
                context = json.loads(payload_json)
            except json.JSONDecodeError:
                context = {}
        if row["race_id"] and "race_id" not in context:
            context["race_id"] = row["race_id"]

        for expanded_bet_type, expanded_combo, expanded_amount in _expand_intent_rows(
            bet_type=row["bet_type"],
            combo=row["combo"],
            amount=int(row["amount"]),
            context=context,
        ):
            expanded_rows.append(
                ExpandedBetRow(
                    race_date=str(row["race_date"]),
                    race_id=str(row["race_id"]),
                    profile_id=str(row["profile_id"]),
                    strategy_id=str(row["strategy_id"]),
                    execution_mode=str(row["execution_mode"]),
                    executed_at=str(row["executed_at"]),
                    contract_no=row["contract_no"],
                    bet_type=expanded_bet_type,
                    combo=expanded_combo,
                    amount=expanded_amount,
                )
            )
    return expanded_rows


def _load_results(results_db_path: Path) -> dict[str, dict[tuple[str, str], int]]:
    connection = duckdb.connect(str(results_db_path))
    try:
        rows = connection.execute(
            """
            SELECT
                race_id,
                exacta_combo,
                exacta_payout,
                trifecta_combo,
                trifecta_payout
            FROM results
            """
        ).fetchall()
    finally:
        connection.close()

    result_map: dict[str, dict[tuple[str, str], int]] = {}
    for race_id, exacta_combo, exacta_payout, trifecta_combo, trifecta_payout in rows:
        normalized: dict[tuple[str, str], int] = {}
        if exacta_combo:
            normalized[("exacta", _normalize_combo(exacta_combo) or str(exacta_combo))] = int(
                exacta_payout or 0
            )
        if trifecta_combo:
            normalized[("trifecta", _normalize_combo(trifecta_combo) or str(trifecta_combo))] = int(
                trifecta_payout or 0
            )
        result_map[str(race_id)] = normalized
    return result_map


def _compute_max_drawdown(daily_rows: list[dict[str, Any]]) -> tuple[int, str | None, str | None]:
    cumulative = 0
    peak = 0
    peak_date: str | None = None
    max_drawdown = 0
    max_drawdown_start: str | None = None
    max_drawdown_end: str | None = None

    for row in daily_rows:
        cumulative += int(row["pnl"])
        if cumulative > peak:
            peak = cumulative
            peak_date = row["date"]
        drawdown = peak - cumulative
        if drawdown > max_drawdown:
            max_drawdown = drawdown
            max_drawdown_start = peak_date
            max_drawdown_end = row["date"]
    return max_drawdown, max_drawdown_start, max_drawdown_end


def _build_report_rows(expanded_bets: list[ExpandedBetRow], results_map: dict[str, dict[tuple[str, str], int]]):
    settled_bets: list[dict[str, Any]] = []
    unsettled_strategy_races: set[tuple[str, str, str]] = set()

    for row in expanded_bets:
        payouts = results_map.get(row.race_id)
        if payouts is None:
            unsettled_strategy_races.add((row.race_date, row.race_id, row.profile_id))
            continue
        payout = int(payouts.get((row.bet_type, row.combo), 0))
        settled_bets.append(
            {
                "race_date": row.race_date,
                "race_id": row.race_id,
                "profile_id": row.profile_id,
                "strategy_id": row.strategy_id,
                "execution_mode": row.execution_mode,
                "executed_at": row.executed_at,
                "contract_no": row.contract_no,
                "bet_type": row.bet_type,
                "combo": row.combo,
                "amount": row.amount,
                "return": payout,
                "hit": 1 if payout > 0 else 0,
            }
        )

    overall_stake = sum(int(row["amount"]) for row in settled_bets)
    overall_return = sum(int(row["return"]) for row in settled_bets)
    overall_pnl = overall_return - overall_stake
    overall_hits = sum(int(row["hit"]) for row in settled_bets)
    overall_bet_rows = len(settled_bets)
    overall_race_keys = {(row["race_date"], row["race_id"], row["profile_id"]) for row in settled_bets}
    overall_hit_race_keys = {
        (row["race_date"], row["race_id"], row["profile_id"]) for row in settled_bets if int(row["hit"]) > 0
    }

    by_profile: list[dict[str, Any]] = []
    for profile_id in sorted({row["profile_id"] for row in settled_bets}):
        subset = [row for row in settled_bets if row["profile_id"] == profile_id]
        stake = sum(int(row["amount"]) for row in subset)
        returned = sum(int(row["return"]) for row in subset)
        pnl = returned - stake
        hits = sum(int(row["hit"]) for row in subset)
        race_keys = {(row["race_date"], row["race_id"], row["profile_id"]) for row in subset}
        hit_race_keys = {
            (row["race_date"], row["race_id"], row["profile_id"]) for row in subset if int(row["hit"]) > 0
        }
        by_profile.append(
            {
                "profile_id": profile_id,
                "sample_races": len(race_keys),
                "bet_rows": len(subset),
                "winning_races": len(hit_race_keys),
                "winning_bet_rows": hits,
                "race_hit_rate_pct": round(len(hit_race_keys) / len(race_keys) * 100, 2) if race_keys else 0.0,
                "bet_row_hit_rate_pct": round(hits / len(subset) * 100, 2) if subset else 0.0,
                "stake_yen": stake,
                "return_yen": returned,
                "pnl_yen": pnl,
                "roi_pct": round(returned / stake * 100, 2) if stake else 0.0,
            }
        )

    daily_map: dict[str, dict[str, int]] = defaultdict(lambda: {"stake": 0, "return": 0, "bet_rows": 0, "hits": 0})
    for row in settled_bets:
        bucket = daily_map[row["race_date"]]
        bucket["stake"] += int(row["amount"])
        bucket["return"] += int(row["return"])
        bucket["bet_rows"] += 1
        bucket["hits"] += int(row["hit"])

    daily_rows: list[dict[str, Any]] = []
    cumulative_pnl = 0
    for date in sorted(daily_map):
        values = daily_map[date]
        pnl = values["return"] - values["stake"]
        cumulative_pnl += pnl
        daily_rows.append(
            {
                "date": date,
                "stake_yen": values["stake"],
                "return_yen": values["return"],
                "pnl": pnl,
                "cumulative_pnl_yen": cumulative_pnl,
                "bet_rows": values["bet_rows"],
                "winning_bet_rows": values["hits"],
                "bet_row_hit_rate_pct": round(values["hits"] / values["bet_rows"] * 100, 2)
                if values["bet_rows"]
                else 0.0,
            }
        )

    max_drawdown_yen, max_drawdown_from, max_drawdown_to = _compute_max_drawdown(daily_rows)

    overall = {
        "submitted_bet_rows_settled": overall_bet_rows,
        "sample_races_settled": len(overall_race_keys),
        "winning_bet_rows": overall_hits,
        "winning_races": len(overall_hit_race_keys),
        "bet_row_hit_rate_pct": round(overall_hits / overall_bet_rows * 100, 2) if overall_bet_rows else 0.0,
        "race_hit_rate_pct": round(len(overall_hit_race_keys) / len(overall_race_keys) * 100, 2)
        if overall_race_keys
        else 0.0,
        "stake_yen": overall_stake,
        "return_yen": overall_return,
        "pnl_yen": overall_pnl,
        "roi_pct": round(overall_return / overall_stake * 100, 2) if overall_stake else 0.0,
        "max_drawdown_yen": max_drawdown_yen,
        "max_drawdown_from": max_drawdown_from,
        "max_drawdown_to": max_drawdown_to,
        "unsettled_sample_races": len(unsettled_strategy_races),
    }

    unsettled_rows = [
        {"race_date": race_date, "race_id": race_id, "profile_id": profile_id}
        for race_date, race_id, profile_id in sorted(unsettled_strategy_races)
    ]
    return overall, by_profile, daily_rows, unsettled_rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown(
    path: Path,
    *,
    generated_at: str,
    system_db_path: Path,
    results_db_path: Path,
    overall: dict[str, Any],
    by_profile: list[dict[str, Any]],
    unsettled_rows: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Live Trigger CLI Real Trade Performance",
        "",
        f"- generated_at: {generated_at}",
        f"- system_db: `{system_db_path}`",
        f"- results_db: `{results_db_path}`",
        "- scope: `bet_executions.execution_status=submitted` and `execution_mode in (assist_real, armed_real)`",
        "- note: `live_trigger_fresh_exec` validation DB is excluded from this report",
        "",
        "## Overall",
        "",
        f"- sample_races: `{overall['sample_races_settled']}`",
        f"- submitted_bet_rows: `{overall['submitted_bet_rows_settled']}`",
        f"- winning_races: `{overall['winning_races']}`",
        f"- winning_bet_rows: `{overall['winning_bet_rows']}`",
        f"- race_hit_rate: `{overall['race_hit_rate_pct']:.2f}%`",
        f"- bet_row_hit_rate: `{overall['bet_row_hit_rate_pct']:.2f}%`",
        f"- stake: `{overall['stake_yen']:,} yen`",
        f"- return: `{overall['return_yen']:,} yen`",
        f"- pnl: `{overall['pnl_yen']:,} yen`",
        f"- ROI: `{overall['roi_pct']:.2f}%`",
        f"- max_drawdown: `-{overall['max_drawdown_yen']:,} yen`",
        f"- max_drawdown_window: `{overall['max_drawdown_from']}` -> `{overall['max_drawdown_to']}`",
        f"- unsettled_sample_races: `{overall['unsettled_sample_races']}`",
        "",
        "## By Profile",
        "",
        "| profile_id | sample_races | bet_rows | winning_races | race_hit_rate | winning_bet_rows | bet_row_hit_rate | stake | return | pnl | ROI |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in by_profile:
        lines.append(
            f"| {row['profile_id']} | {row['sample_races']} | {row['bet_rows']} | {row['winning_races']} | "
            f"{row['race_hit_rate_pct']:.2f}% | {row['winning_bet_rows']} | {row['bet_row_hit_rate_pct']:.2f}% | "
            f"{row['stake_yen']:,} yen | {row['return_yen']:,} yen | {row['pnl_yen']:,} yen | {row['roi_pct']:.2f}% |"
        )

    lines.extend(["", "## Unsettled Sample Races", ""])
    if unsettled_rows:
        lines.append("| race_date | race_id | profile_id |")
        lines.append("| --- | --- | --- |")
        for row in unsettled_rows[-20:]:
            lines.append(f"| {row['race_date']} | {row['race_id']} | {row['profile_id']} |")
        if len(unsettled_rows) > 20:
            lines.append("")
            lines.append(f"- only the latest 20 unsettled rows are shown here; total is `{len(unsettled_rows)}`")
    else:
        lines.append("- none")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a reusable live trade performance report.")
    parser.add_argument("--system-db", type=Path, default=DEFAULT_SYSTEM_DB)
    parser.add_argument("--results-db", type=Path, default=DEFAULT_RESULTS_DB)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_REPORT_ROOT)
    parser.add_argument("--report-name", default="")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_name = args.report_name or f"live_trigger_cli_real_trade_performance_{timestamp}"
    output_dir = args.output_root / report_name

    expanded_bets = _load_submitted_bets(args.system_db)
    results_map = _load_results(args.results_db)
    overall, by_profile, daily_rows, unsettled_rows = _build_report_rows(expanded_bets, results_map)

    _write_markdown(
        output_dir / "README.md",
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S JST"),
        system_db_path=args.system_db,
        results_db_path=args.results_db,
        overall=overall,
        by_profile=by_profile,
        unsettled_rows=unsettled_rows,
    )
    _write_csv(output_dir / "profile_summary.csv", by_profile)
    _write_csv(output_dir / "daily_equity.csv", daily_rows)
    _write_csv(output_dir / "unsettled_sample_races.csv", unsettled_rows)
    (output_dir / "overall_summary.json").write_text(
        json.dumps(overall, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps({"report_dir": str(output_dir), "overall": overall}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
