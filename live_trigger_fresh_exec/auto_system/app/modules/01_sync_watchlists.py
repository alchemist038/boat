from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.core.database import SessionLocal, TargetRace, initialize_database, json_dumps, log_event
from app.core.settings import WATCHLIST_ROOT, bootstrap_runtime_path
from app.core.time_utils import parse_watch_datetime

bootstrap_runtime_path()

from boat_race_data.live_trigger import read_watchlist


EARLY_TARGET_STATUSES = {"imported", "monitoring", "checked_waiting"}
EVALUATED_PAYLOAD_KEYS = {
    "status",
    "final_reason",
    "lane1_exhibition_time",
    "lane1_exhibition_best_gap",
    "lane2_exhibition_time",
    "lane3_exhibition_time",
    "lane1_start_exhibition_st",
    "min_other_start_exhibition_st",
    "lane1_start_gap_over_rest",
    "beforeinfo_fetched_at",
}
TERMINAL_TARGET_STATUSES = {
    "air_bet_logged",
    "real_bet_placed",
    "error",
    "insufficient_funds",
    "assist_timeout",
    "assist_window_closed",
    "expired",
    "withdrawn",
}


def _target_key(row: dict[str, object]) -> str:
    return f"{row.get('race_id', '')}::{row.get('profile_id', '')}"


def _preserve_evaluated_payload(target: TargetRace, row: dict[str, object]) -> dict[str, object]:
    if target.beforeinfo_checked_at is None and target.status in EARLY_TARGET_STATUSES:
        return dict(row)

    merged = dict(row)
    try:
        existing = json.loads(target.payload_json or "{}")
    except json.JSONDecodeError:
        existing = {}

    for key in EVALUATED_PAYLOAD_KEYS:
        if key in existing and existing[key] not in {"", None}:
            merged[key] = existing[key]

    if target.row_status and target.row_status not in {"", "waiting_beforeinfo"}:
        merged["status"] = target.row_status
    if target.last_reason:
        if target.row_status == "trigger_ready":
            merged["final_reason"] = target.last_reason
        elif not merged.get("final_reason"):
            merged["final_reason"] = target.last_reason

    return merged


def _withdraw_missing_targets(
    session,
    *,
    today_iso: str,
    watchlist_names: list[str],
    seen_target_keys: set[str],
) -> int:
    if not watchlist_names:
        return 0

    withdrawn = 0
    targets = (
        session.query(TargetRace)
        .filter(TargetRace.race_date == today_iso)
        .filter(TargetRace.source_watchlist_file.in_(watchlist_names))
        .all()
    )
    for target in targets:
        if target.target_key in seen_target_keys:
            continue
        if target.status in TERMINAL_TARGET_STATUSES:
            continue

        target.status = "withdrawn"
        target.row_status = "watchlist_removed"
        target.last_reason = "removed from current watchlist"
        try:
            payload = json.loads(target.payload_json or "{}")
        except json.JSONDecodeError:
            payload = {}
        payload["status"] = "watchlist_removed"
        payload["final_reason"] = target.last_reason
        target.payload_json = json_dumps(payload)

        for intent in target.intents:
            if intent.status == "pending":
                intent.status = "cancelled"
                log_event(
                    session,
                    target=target,
                    intent=intent,
                    event_type="intent_cancelled",
                    message=target.last_reason,
                )

        log_event(
            session,
            target=target,
            event_type="target_withdrawn",
            message=target.last_reason,
        )
        withdrawn += 1
    return withdrawn


def main() -> None:
    initialize_database()
    now = datetime.now()
    today_iso = now.strftime("%Y-%m-%d")
    watchlist_files = sorted(WATCHLIST_ROOT.glob("*.csv")) if WATCHLIST_ROOT.exists() else []
    imported = 0
    updated = 0
    withdrawn = 0
    seen_target_keys: set[str] = set()
    watchlist_names = [path.name for path in watchlist_files]

    session = SessionLocal()
    try:
        for watchlist_path in watchlist_files:
            for row in read_watchlist(watchlist_path):
                if str(row.get("race_date", "")) != today_iso:
                    continue
                if not row.get("race_id") or not row.get("profile_id"):
                    continue

                deadline_at = parse_watch_datetime(f"{row.get('race_date', '')} {row.get('deadline_time', '')}")
                if deadline_at is None:
                    continue
                watch_start_at = parse_watch_datetime(str(row.get("watch_start_time", "")))

                target_key = _target_key(row)
                seen_target_keys.add(target_key)
                target = session.query(TargetRace).filter(TargetRace.target_key == target_key).first()
                if target is None:
                    target = TargetRace(
                        target_key=target_key,
                        race_id=str(row.get("race_id", "")),
                        race_date=str(row.get("race_date", "")),
                        stadium_code=str(row.get("stadium_code", "")),
                        stadium_name=str(row.get("stadium_name", "")),
                        race_no=int(row.get("race_no", 0) or 0),
                        profile_id=str(row.get("profile_id", "")),
                        strategy_id=str(row.get("strategy_id", "")),
                        source_watchlist_file=watchlist_path.name,
                        deadline_at=deadline_at,
                        watch_start_at=watch_start_at,
                        status="imported",
                        row_status=str(row.get("status", "")),
                        last_reason=str(row.get("pre_reason", "")),
                        payload_json=json_dumps(row),
                    )
                    session.add(target)
                    log_event(
                        session,
                        target=target,
                        event_type="watchlist_imported",
                        message=f"Imported from {watchlist_path.name}",
                    )
                    imported += 1
                    continue

                target.race_id = str(row.get("race_id", ""))
                target.race_date = str(row.get("race_date", ""))
                target.stadium_code = str(row.get("stadium_code", ""))
                target.stadium_name = str(row.get("stadium_name", ""))
                target.race_no = int(row.get("race_no", 0) or 0)
                target.profile_id = str(row.get("profile_id", ""))
                target.strategy_id = str(row.get("strategy_id", ""))
                target.source_watchlist_file = watchlist_path.name
                target.deadline_at = deadline_at
                target.watch_start_at = watch_start_at
                merged_row = _preserve_evaluated_payload(target, row)
                target.row_status = str(merged_row.get("status", ""))
                target.payload_json = json_dumps(merged_row)
                if target.status in EARLY_TARGET_STATUSES:
                    target.last_reason = str(merged_row.get("final_reason") or merged_row.get("pre_reason") or "")
                updated += 1

        withdrawn = _withdraw_missing_targets(
            session,
            today_iso=today_iso,
            watchlist_names=watchlist_names,
            seen_target_keys=seen_target_keys,
        )

        session.commit()
        print(
            f"[{now:%Y-%m-%d %H:%M:%S}] fresh sync completed: "
            f"imported={imported} updated={updated} withdrawn={withdrawn} files={len(watchlist_files)}"
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
