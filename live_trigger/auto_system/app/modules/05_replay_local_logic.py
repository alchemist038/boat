from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

AUTO_SYSTEM_ROOT = Path(__file__).resolve().parents[2]
LIVE_TRIGGER_ROOT = AUTO_SYSTEM_ROOT.parent
for import_root in (AUTO_SYSTEM_ROOT, LIVE_TRIGGER_ROOT):
    import_text = str(import_root)
    if import_text not in sys.path:
        sys.path.append(import_text)

from app.core.database import SessionLocal, TargetRace, initialize_database
from app.core.settings import DATA_DIR, RAW_ROOT, bootstrap_runtime_path, load_settings, profile_enabled
from shared_contract import SHARED_BOX_ROOT

bootstrap_runtime_path()

from boat_race_data.constants import STADIUMS
from boat_race_data.live_trigger import (
    TriggerProfile,
    build_final_reason,
    build_watchlist_row,
    compute_best_gap,
    compute_lane_gap,
    compute_start_gap_over_rest,
    load_trigger_profiles,
)
from boat_race_data.parsers import parse_beforeinfo, parse_racelist


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay current logic against local raw racelist/beforeinfo without network or DB writes.")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="Target date in YYYY-MM-DD or YYYYMMDD.")
    parser.add_argument("--profile", action="append", dest="profiles", default=[], help="Profile id to replay. Repeatable.")
    parser.add_argument("--all-profiles", action="store_true", help="Include disabled profiles too.")
    return parser.parse_args()


def _normalize_date(value: str) -> tuple[str, str]:
    text = str(value).strip()
    if len(text) == 8 and text.isdigit():
        return f"{text[0:4]}-{text[4:6]}-{text[6:8]}", text
    parsed = datetime.strptime(text, "%Y-%m-%d")
    return parsed.strftime("%Y-%m-%d"), parsed.strftime("%Y%m%d")


def _entry_by_lane(rows: list[dict[str, object]], lane: int) -> dict[str, object] | None:
    for row in rows:
        if int(row.get("lane", 0) or 0) == lane:
            return row
    return None


def _passes_min_filter(value: object, minimum: float | None) -> bool:
    if minimum is None:
        return True
    try:
        return float(value) >= minimum
    except (TypeError, ValueError):
        return False


def _passes_max_filter(value: float | None, maximum: float | None) -> bool:
    if maximum is None:
        return True
    return value is not None and value <= maximum


def _matches_final_filters(
    *,
    best_gap: float | None,
    lane2_gap: float | None,
    lane3_gap: float | None,
    start_gap: float | None,
    profile: TriggerProfile,
) -> bool:
    return (
        _passes_max_filter(best_gap, profile.lane1_exhibition_best_gap_max)
        and _passes_max_filter(lane2_gap, profile.lane1_exhibition_vs_lane2_max_gap)
        and _passes_max_filter(lane3_gap, profile.lane1_exhibition_vs_lane3_max_gap)
        and _passes_min_filter(start_gap, profile.lane1_start_gap_over_rest_min)
    )


def _load_profile_list(*, settings: dict[str, Any], selected: list[str], include_all: bool) -> list[TriggerProfile]:
    profiles = load_trigger_profiles(SHARED_BOX_ROOT, include_disabled=True)
    selected_set = {item.strip() for item in selected if item.strip()}
    resolved: list[TriggerProfile] = []
    for profile in profiles:
        if selected_set and profile.profile_id not in selected_set:
            continue
        if not include_all and not profile_enabled(settings, profile.profile_id):
            continue
        resolved.append(profile)
    return resolved


def _load_target_map(race_date_iso: str) -> dict[str, dict[str, Any]]:
    initialize_database()
    session = SessionLocal()
    try:
        targets = session.query(TargetRace).filter(TargetRace.race_date == race_date_iso).all()
        mapped: dict[str, dict[str, Any]] = {}
        for target in targets:
            mapped[target.target_key] = {
                "db_status": target.status,
                "db_row_status": target.row_status,
                "db_last_reason": target.last_reason,
                "target_id": target.id,
            }
        return mapped
    finally:
        session.close()


def _discover_local_stadiums(compact_date: str) -> list[str]:
    racelist_dir = RAW_ROOT / "racelist" / compact_date
    codes = sorted({path.stem.split("_")[0] for path in racelist_dir.glob("*.html") if "_" in path.stem})
    return codes


def _simulate_candidate(
    *,
    profile: TriggerProfile,
    race_date_iso: str,
    compact_date: str,
    stadium_code: str,
    race_no: int,
    db_map: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    racelist_path = RAW_ROOT / "racelist" / compact_date / f"{stadium_code}_{race_no:02d}.html"
    if not racelist_path.exists():
        return None

    racelist_text = racelist_path.read_text(encoding="utf-8", errors="replace")
    race_row, entry_rows = parse_racelist(
        racelist_text,
        compact_date,
        stadium_code,
        STADIUMS.get(stadium_code, ""),
        race_no,
        str(racelist_path),
        datetime.fromtimestamp(racelist_path.stat().st_mtime).isoformat(),
    )
    if race_row is None or not entry_rows:
        return None

    row = build_watchlist_row(race_row, entry_rows, profile)
    if row is None:
        return None

    beforeinfo_path = RAW_ROOT / "beforeinfo" / compact_date / f"{stadium_code}_{race_no:02d}.html"
    if not beforeinfo_path.exists():
        row["status"] = "waiting_beforeinfo"
        row["final_reason"] = "local beforeinfo missing"
    else:
        beforeinfo_text = beforeinfo_path.read_text(encoding="utf-8", errors="replace")
        beforeinfo_rows = parse_beforeinfo(
            beforeinfo_text,
            compact_date,
            stadium_code,
            race_no,
            str(beforeinfo_path),
            datetime.fromtimestamp(beforeinfo_path.stat().st_mtime).isoformat(),
        )
        lane1 = _entry_by_lane(beforeinfo_rows, 1)
        row["beforeinfo_fetched_at"] = datetime.fromtimestamp(beforeinfo_path.stat().st_mtime).isoformat()
        if lane1 is None or lane1.get("exhibition_time") in ("", None):
            row["status"] = "waiting_beforeinfo"
            row["final_reason"] = "beforeinfo not ready"
        else:
            best_gap = compute_best_gap(beforeinfo_rows, lane=1)
            lane2_gap = compute_lane_gap(beforeinfo_rows, 1, 2)
            lane3_gap = compute_lane_gap(beforeinfo_rows, 1, 3)
            start_gap = compute_start_gap_over_rest(beforeinfo_rows, lane=1)
            lane2 = _entry_by_lane(beforeinfo_rows, 2)
            lane3 = _entry_by_lane(beforeinfo_rows, 3)
            row["lane1_exhibition_time"] = lane1.get("exhibition_time", "")
            row["lane1_exhibition_best_gap"] = "" if best_gap is None else f"{best_gap:.3f}"
            row["lane2_exhibition_time"] = "" if lane2 is None else lane2.get("exhibition_time", "")
            row["lane3_exhibition_time"] = "" if lane3 is None else lane3.get("exhibition_time", "")
            row["lane1_start_exhibition_st"] = lane1.get("start_exhibition_st", "")
            row["lane1_start_gap_over_rest"] = "" if start_gap is None else f"{start_gap:.3f}"
            if _matches_final_filters(
                best_gap=best_gap,
                lane2_gap=lane2_gap,
                lane3_gap=lane3_gap,
                start_gap=start_gap,
                profile=profile,
            ):
                row["status"] = "trigger_ready"
                row["final_reason"] = build_final_reason(best_gap, lane2_gap, lane3_gap, start_gap, profile)
            else:
                row["status"] = "filtered_out"
                row["final_reason"] = build_final_reason(
                    best_gap,
                    lane2_gap,
                    lane3_gap,
                    start_gap,
                    profile,
                    matched=False,
                )

    target_key = f"{row.get('race_id', '')}::{profile.profile_id}"
    row["target_key"] = target_key
    row["race_date"] = race_date_iso
    row["db_match"] = db_map.get(target_key)
    return row


def main() -> None:
    args = _parse_args()
    race_date_iso, compact_date = _normalize_date(args.date)
    settings = load_settings()
    profiles = _load_profile_list(settings=settings, selected=args.profiles, include_all=args.all_profiles)
    db_map = _load_target_map(race_date_iso)
    local_stadiums = _discover_local_stadiums(compact_date)

    results: list[dict[str, Any]] = []
    summary: dict[str, Counter[str]] = {}

    for profile in profiles:
        profile_counter: Counter[str] = Counter()
        stadium_codes = profile.stadiums or local_stadiums
        for stadium_code in stadium_codes:
            for race_no in range(1, 13):
                row = _simulate_candidate(
                    profile=profile,
                    race_date_iso=race_date_iso,
                    compact_date=compact_date,
                    stadium_code=stadium_code,
                    race_no=race_no,
                    db_map=db_map,
                )
                if row is None:
                    continue
                profile_counter["pre_candidates"] += 1
                profile_counter[str(row.get("status", ""))] += 1
                results.append(row)
        summary[profile.profile_id] = profile_counter

    results.sort(key=lambda item: (str(item.get("profile_id", "")), str(item.get("stadium_code", "")), int(item.get("race_no", 0) or 0)))

    report = {
        "generated_at": datetime.now().isoformat(),
        "mode": "local_raw_replay",
        "race_date": race_date_iso,
        "active_profiles_only": not args.all_profiles and not args.profiles,
        "profiles": [profile.profile_id for profile in profiles],
        "summary": {profile_id: dict(counter) for profile_id, counter in summary.items()},
        "results": results,
    }

    report_dir = DATA_DIR / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"local_replay_{compact_date}_{datetime.now():%H%M%S}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"report={report_path}")
    for profile_id, counter in summary.items():
        print(
            f"{profile_id}: pre={counter.get('pre_candidates', 0)} "
            f"ready={counter.get('trigger_ready', 0)} "
            f"filtered={counter.get('filtered_out', 0)} "
            f"waiting={counter.get('waiting_beforeinfo', 0)}"
        )
    for row in results:
        print(
            f"{row.get('profile_id')} {row.get('stadium_name')} {row.get('race_no')}R "
            f"{row.get('status')} :: {row.get('final_reason') or row.get('pre_reason')}"
        )


if __name__ == "__main__":
    main()
