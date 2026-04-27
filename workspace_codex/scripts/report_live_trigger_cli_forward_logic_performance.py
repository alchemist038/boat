from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sqlite3
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb
from runtime_paths import default_results_db_path

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
DEFAULT_SETTINGS_JSON = DEFAULT_RUNTIME_ROOT / "live_trigger_cli" / "data" / "settings.json"
DEFAULT_REPORT_ROOT = REPO_ROOT / "reports" / "live_trade"
DEFAULT_REPORT_NAME = "live_trigger_cli_forward_logic_performance_latest"

LOGIC_NAME_MAP = {
    "125_broad_four_stadium": "125",
    "4wind_base_415": "4wind",
    "c2_provisional_v1": "c2",
    "h_a_final_day_cut_v1": "H-A",
    "l1_weak_234_box_v1": "l1_234",
    "l3_weak_124_box_one_a_ex241_v1": "l3_124",
}


def _default_results_db() -> str:
    return str(default_results_db_path())


DEFAULT_RESULTS_DB = _default_results_db()


@dataclass
class ExpandedBetRow:
    race_date: str
    race_id: str
    profile_id: str
    logic_name: str
    bet_type: str
    combo: str


def _normalize_combo(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    text = re.sub(r"\s*-\s*", "-", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _default_cutoff_date() -> str:
    return (date.today() - timedelta(days=1)).isoformat()


def _load_active_profiles(settings_path: Path) -> list[str]:
    if not settings_path.exists():
        return []
    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    active_profiles = payload.get("active_profiles", {})
    return [profile_id for profile_id, enabled in active_profiles.items() if bool(enabled)]


def _expand_intent_rows(
    *,
    race_id: str,
    profile_id: str,
    payload_json: str | None,
    bet_type: str,
    combo: str,
) -> list[ExpandedBetRow]:
    context: dict[str, Any] = {}
    if payload_json:
        try:
            context = json.loads(payload_json)
        except json.JSONDecodeError:
            context = {}
    if race_id and "race_id" not in context:
        context["race_id"] = race_id

    normalized_bet_type = str(bet_type).lower()
    raw_combo = str(combo)
    if "ALL" not in raw_combo:
        return [
            ExpandedBetRow(
                race_date="",
                race_id=race_id,
                profile_id=profile_id,
                logic_name=LOGIC_NAME_MAP.get(profile_id, profile_id),
                bet_type=normalized_bet_type,
                combo=_normalize_combo(raw_combo) or raw_combo,
            )
        ]

    lane_class_map = _lane_class_map_from_context(context)
    if not lane_class_map and race_id:
        lane_class_map = _lane_class_map_for_race(race_id)
    if not lane_class_map or normalized_bet_type != "trifecta":
        return [
            ExpandedBetRow(
                race_date="",
                race_id=race_id,
                profile_id=profile_id,
                logic_name=LOGIC_NAME_MAP.get(profile_id, profile_id),
                bet_type=normalized_bet_type,
                combo=_normalize_combo(raw_combo) or raw_combo,
            )
        ]

    excluded_lanes = {
        lane for lane, racer_class in lane_class_map.items() if str(racer_class).upper() == "B2"
    }
    return [
        ExpandedBetRow(
            race_date="",
            race_id=race_id,
            profile_id=profile_id,
            logic_name=LOGIC_NAME_MAP.get(profile_id, profile_id),
            bet_type="trifecta",
            combo=_normalize_combo(expanded_combo) or expanded_combo,
        )
        for expanded_combo in _expand_trifecta_combo(raw_combo, excluded_lanes=excluded_lanes)
    ]


def _load_expanded_submitted_rows(system_db_path: Path, cutoff_date: str) -> list[ExpandedBetRow]:
    connection = sqlite3.connect(system_db_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT
                tr.race_date,
                tr.race_id,
                tr.profile_id,
                tr.payload_json,
                bi.bet_type,
                bi.combo
            FROM bet_executions AS be
            JOIN target_races AS tr ON tr.id = be.target_race_id
            JOIN bet_intents AS bi ON bi.id = be.intent_id
            WHERE be.execution_status = 'submitted'
              AND be.execution_mode IN ('assist_real', 'armed_real')
              AND tr.race_date <= ?
            ORDER BY tr.race_date, tr.race_id, bi.id
            """,
            (cutoff_date,),
        ).fetchall()
    finally:
        connection.close()

    expanded_rows: list[ExpandedBetRow] = []
    for row in rows:
        expanded = _expand_intent_rows(
            race_id=str(row["race_id"]),
            profile_id=str(row["profile_id"]),
            payload_json=row["payload_json"],
            bet_type=str(row["bet_type"]),
            combo=str(row["combo"]),
        )
        for item in expanded:
            item.race_date = str(row["race_date"])
            expanded_rows.append(item)
    return expanded_rows


def _load_results(results_db_path: str, cutoff_date: str) -> dict[str, dict[tuple[str, str], int]]:
    connection = duckdb.connect(results_db_path, read_only=True)
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
            WHERE race_date <= ?
            """,
            [cutoff_date],
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


def _compute_profile_summary(
    expanded_rows: list[ExpandedBetRow],
    result_map: dict[str, dict[tuple[str, str], int]],
    active_profiles: list[str],
    *,
    include_inactive: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    settled_rows: list[dict[str, Any]] = []
    unsettled_races: set[tuple[str, str, str]] = set()
    active_set = set(active_profiles)

    for row in expanded_rows:
        payouts = result_map.get(row.race_id)
        if payouts is None:
            unsettled_races.add((row.race_date, row.race_id, row.profile_id))
            continue
        if not include_inactive and row.profile_id not in active_set:
            continue
        payout = int(payouts.get((row.bet_type, row.combo), 0))
        settled_rows.append(
            {
                "race_date": row.race_date,
                "race_id": row.race_id,
                "profile_id": row.profile_id,
                "logic_name": row.logic_name,
                "return_yen": payout,
                "hit": 1 if payout > 0 else 0,
            }
        )

    if include_inactive:
        profile_order = sorted({row["profile_id"] for row in settled_rows})
    else:
        profile_order = [profile_id for profile_id in active_profiles if any(row["profile_id"] == profile_id for row in settled_rows)]

    profile_rows: list[dict[str, Any]] = []
    for profile_id in profile_order:
        subset = [row for row in settled_rows if row["profile_id"] == profile_id]
        if not subset:
            continue
        logic_name = subset[0]["logic_name"]
        race_keys = {(row["race_date"], row["race_id"], row["profile_id"]) for row in subset}
        hit_race_keys = {
            (row["race_date"], row["race_id"], row["profile_id"])
            for row in subset
            if int(row["hit"]) > 0
        }
        flat_stake_yen = len(subset) * 100
        flat_return_yen = sum(int(row["return_yen"]) for row in subset)
        hit_races = len(hit_race_keys)
        profile_rows.append(
            {
                "logic_name": logic_name,
                "profile_id": profile_id,
                "sample_races": len(race_keys),
                "hit_races": hit_races,
                "race_hit_rate_pct": round(hit_races / len(race_keys) * 100, 2) if race_keys else 0.0,
                "avg_tickets_per_race": round(len(subset) / len(race_keys), 2) if race_keys else 0.0,
                "flat_stake_yen": flat_stake_yen,
                "flat_return_yen": flat_return_yen,
                "flat_pnl_yen": flat_return_yen - flat_stake_yen,
                "flat_roi_pct": round(flat_return_yen / flat_stake_yen * 100, 2) if flat_stake_yen else 0.0,
                "avg_hit_payout_yen": round(flat_return_yen / hit_races) if hit_races else 0,
                "active": "yes" if profile_id in active_set else "no",
            }
        )

    daily_logic_map: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: {"bet_rows": 0, "return_yen": 0, "hit_rows": 0}
    )
    for row in settled_rows:
        bucket = daily_logic_map[(row["race_date"], row["profile_id"])]
        bucket["bet_rows"] += 1
        bucket["return_yen"] += int(row["return_yen"])
        bucket["hit_rows"] += int(row["hit"])

    cumulative_by_profile: dict[str, int] = defaultdict(int)
    daily_logic_rows: list[dict[str, Any]] = []
    for race_date, profile_id in sorted(daily_logic_map):
        values = daily_logic_map[(race_date, profile_id)]
        flat_stake_yen = values["bet_rows"] * 100
        flat_return_yen = values["return_yen"]
        flat_pnl_yen = flat_return_yen - flat_stake_yen
        cumulative_by_profile[profile_id] += flat_pnl_yen
        daily_logic_rows.append(
            {
                "date": race_date,
                "logic_name": LOGIC_NAME_MAP.get(profile_id, profile_id),
                "profile_id": profile_id,
                "sample_races": 1,
                "hit_races": 1 if values["hit_rows"] > 0 else 0,
                "race_hit_rate_pct": 100.0 if values["hit_rows"] > 0 else 0.0,
                "bet_rows": values["bet_rows"],
                "flat_stake_yen": flat_stake_yen,
                "flat_return_yen": flat_return_yen,
                "flat_pnl_yen": flat_pnl_yen,
                "cumulative_pnl_yen": cumulative_by_profile[profile_id],
            }
        )

    overall_race_keys = {(row["race_date"], row["race_id"], row["profile_id"]) for row in settled_rows}
    overall_hit_race_keys = {
        (row["race_date"], row["race_id"], row["profile_id"]) for row in settled_rows if int(row["hit"]) > 0
    }
    overall_flat_stake_yen = len(settled_rows) * 100
    overall_flat_return_yen = sum(int(row["return_yen"]) for row in settled_rows)
    overall = {
        "sample_races": len(overall_race_keys),
        "hit_races": len(overall_hit_race_keys),
        "race_hit_rate_pct": round(len(overall_hit_race_keys) / len(overall_race_keys) * 100, 2)
        if overall_race_keys
        else 0.0,
        "bet_rows": len(settled_rows),
        "avg_tickets_per_race": round(len(settled_rows) / len(overall_race_keys), 2) if overall_race_keys else 0.0,
        "flat_stake_yen": overall_flat_stake_yen,
        "flat_return_yen": overall_flat_return_yen,
        "flat_pnl_yen": overall_flat_return_yen - overall_flat_stake_yen,
        "flat_roi_pct": round(overall_flat_return_yen / overall_flat_stake_yen * 100, 2)
        if overall_flat_stake_yen
        else 0.0,
        "unsettled_sample_races": len(
            {row for row in unsettled_races if include_inactive or row[2] in active_set}
        ),
    }
    return overall, profile_rows, daily_logic_rows


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
    cutoff_date: str,
    system_db_path: Path,
    settings_path: Path,
    results_db_path: str,
    active_profiles: list[str],
    overall: dict[str, Any],
    profile_rows: list[dict[str, Any]],
    include_inactive: bool,
) -> None:
    title = "Live Trigger CLI Forward Logic Performance"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {title}",
        "",
        f"- generated_at: {generated_at}",
        f"- cutoff_date: `{cutoff_date}`",
        f"- scope: `bet_executions.execution_status=submitted` and `execution_mode in (assist_real, armed_real)`",
        "- normalization: `100 yen flat per expanded bet row`",
        "- unit: race-level performance, not bet-row hit rate",
        f"- system_db: `{system_db_path}`",
        f"- settings_json: `{settings_path}`",
        f"- results_db: `{results_db_path}`",
        f"- active_forward_profiles: `{', '.join(active_profiles) if active_profiles else '-'}`",
        f"- include_inactive_profiles: `{include_inactive}`",
        "",
        "## Overall",
        "",
        f"- sample_races: `{overall['sample_races']}`",
        f"- hit_races: `{overall['hit_races']}`",
        f"- race_hit_rate: `{overall['race_hit_rate_pct']:.2f}%`",
        f"- avg_tickets_per_race: `{overall['avg_tickets_per_race']:.2f}`",
        f"- flat_stake: `{overall['flat_stake_yen']:,} yen`",
        f"- flat_return: `{overall['flat_return_yen']:,} yen`",
        f"- flat_pnl: `{overall['flat_pnl_yen']:,} yen`",
        f"- flat_roi: `{overall['flat_roi_pct']:.2f}%`",
        f"- unsettled_sample_races: `{overall['unsettled_sample_races']}`",
        "",
        "## By Logic",
        "",
        "| logic | profile_id | sample_races | hit_races | race_hit_rate | avg_tickets_per_race | flat_stake | flat_return | flat_pnl | flat_roi | avg_hit_payout |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in profile_rows:
        lines.append(
            f"| {row['logic_name']} | {row['profile_id']} | {row['sample_races']} | {row['hit_races']} | "
            f"{row['race_hit_rate_pct']:.2f}% | {row['avg_tickets_per_race']:.2f} | "
            f"{row['flat_stake_yen']:,} yen | {row['flat_return_yen']:,} yen | "
            f"{row['flat_pnl_yen']:,} yen | {row['flat_roi_pct']:.2f}% | {row['avg_hit_payout_yen']:,} yen |"
        )
    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `logic_summary.csv`: one row per current logic/profile",
            "- `daily_logic_equity.csv`: daily forward progression per logic",
            "- `overall_summary.json`: top-line summary for automation",
            "",
            "## Refresh",
            "",
            "Run this command to overwrite the latest report:",
            "",
            "```powershell",
            ".\\.venv\\Scripts\\python.exe workspace_codex\\scripts\\report_live_trigger_cli_forward_logic_performance.py",
            "```",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a reusable forward-logic performance report for the current live_trigger_cli set."
    )
    parser.add_argument("--system-db", type=Path, default=DEFAULT_SYSTEM_DB)
    parser.add_argument("--settings-json", type=Path, default=DEFAULT_SETTINGS_JSON)
    parser.add_argument("--results-db", default=DEFAULT_RESULTS_DB)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_REPORT_ROOT)
    parser.add_argument("--report-name", default=DEFAULT_REPORT_NAME)
    parser.add_argument("--cutoff-date", default=_default_cutoff_date(), help="settlement cutoff date in YYYY-MM-DD")
    parser.add_argument("--include-inactive", action="store_true")
    args = parser.parse_args()

    active_profiles = _load_active_profiles(args.settings_json)
    expanded_rows = _load_expanded_submitted_rows(args.system_db, args.cutoff_date)
    result_map = _load_results(args.results_db, args.cutoff_date)
    overall, profile_rows, daily_logic_rows = _compute_profile_summary(
        expanded_rows,
        result_map,
        active_profiles,
        include_inactive=args.include_inactive,
    )

    output_dir = args.output_root / args.report_name
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S JST")
    _write_markdown(
        output_dir / "README.md",
        generated_at=generated_at,
        cutoff_date=args.cutoff_date,
        system_db_path=args.system_db,
        settings_path=args.settings_json,
        results_db_path=args.results_db,
        active_profiles=active_profiles,
        overall=overall,
        profile_rows=profile_rows,
        include_inactive=args.include_inactive,
    )
    _write_csv(output_dir / "logic_summary.csv", profile_rows)
    _write_csv(output_dir / "daily_logic_equity.csv", daily_logic_rows)
    (output_dir / "overall_summary.json").write_text(
        json.dumps(overall, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "report_dir": str(output_dir),
                "cutoff_date": args.cutoff_date,
                "active_profiles": active_profiles,
                "overall": overall,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
