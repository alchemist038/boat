from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.core.bets import build_bet_rows
from app.core.database import BetIntent, SessionLocal, TargetRace, initialize_database, json_dumps, log_event
from app.core.settings import (
    RAW_ROOT,
    SHARED_BOX_ROOT,
    bootstrap_runtime_path,
    execution_mode,
    load_settings,
    profile_amount,
    profile_enabled,
)

bootstrap_runtime_path()

from boat_race_data.client import BoatRaceClient
from boat_race_data.live_trigger import enrich_watchlist_row_with_beforeinfo, load_trigger_profiles

ACTIVE_TARGET_STATUSES = {"imported", "monitoring", "checked_waiting", "checked_go", "intent_created"}


def _load_profile_map():
    profiles = load_trigger_profiles(SHARED_BOX_ROOT, include_disabled=True)
    return {profile.profile_id: profile for profile in profiles}


def _ensure_intents(session, *, target: TargetRace, settings: dict[str, object]) -> int:
    amount = profile_amount(settings, target.profile_id)
    target_mode = execution_mode(settings)
    bet_rows = build_bet_rows(strategy_id=target.strategy_id, profile_id=target.profile_id, amount=amount)
    if not bet_rows:
        return 0

    created = 0
    for bet_row in bet_rows:
        intent_key = f"{target.target_key}::{bet_row['bet_type']}::{bet_row['combo']}"
        existing = session.query(BetIntent).filter(BetIntent.intent_key == intent_key).first()
        if existing is not None:
            if existing.status == "pending" and existing.execution_mode != target_mode:
                existing.execution_mode = target_mode
                log_event(
                    session,
                    target=target,
                    intent=existing,
                    event_type="intent_mode_updated",
                    message=f"{existing.bet_type} {existing.combo} -> {target_mode}",
                )
            continue

        intent = BetIntent(
            target=target,
            intent_key=intent_key,
            execution_mode=target_mode,
            status="pending",
            bet_type=str(bet_row["bet_type"]),
            combo=str(bet_row["combo"]),
            amount=int(bet_row["amount"]),
        )
        session.add(intent)
        created += 1
        log_event(
            session,
            target=target,
            intent=intent,
            event_type="intent_created",
            message=f"{bet_row['bet_type']} {bet_row['combo']} / {bet_row['amount']} ({target_mode})",
        )
    return created


def main() -> None:
    initialize_database()
    settings = load_settings()
    profile_map = _load_profile_map()
    now = datetime.now()
    today_iso = now.strftime("%Y-%m-%d")
    window_start_minutes = int(settings["check_window_start_minutes"])
    window_end_minutes = int(settings["check_window_end_minutes"])

    checked = 0
    go_count = 0
    skip_count = 0
    waiting_count = 0
    expired_count = 0

    session = SessionLocal()
    try:
        targets = (
            session.query(TargetRace)
            .filter(TargetRace.race_date == today_iso)
            .filter(TargetRace.status.in_(tuple(ACTIVE_TARGET_STATUSES)))
            .order_by(TargetRace.deadline_at.asc(), TargetRace.id.asc())
            .all()
        )

        if not targets:
            print(f"[{now:%Y-%m-%d %H:%M:%S}] fresh evaluate: no active targets for today")
            return

        with BoatRaceClient(timeout_seconds=30) as client:
            for target in targets:
                window_open_at = target.deadline_at - timedelta(minutes=window_start_minutes)
                window_close_at = target.deadline_at - timedelta(minutes=window_end_minutes)

                if now < window_open_at:
                    continue

                if now >= window_close_at:
                    if target.status not in {"checked_skip", "air_bet_logged", "real_bet_placed", "expired"}:
                        target.status = "expired"
                        target.last_reason = f"window closed at {window_close_at:%H:%M:%S}"
                        log_event(
                            session,
                            target=target,
                            event_type="window_closed",
                            message=target.last_reason,
                        )
                        expired_count += 1
                    continue

                if not profile_enabled(settings, target.profile_id):
                    if target.status != "checked_skip":
                        target.status = "checked_skip"
                        target.last_reason = "profile disabled in fresh_exec"
                        log_event(
                            session,
                            target=target,
                            event_type="target_skipped",
                            message=target.last_reason,
                        )
                        skip_count += 1
                    continue

                profile = profile_map.get(target.profile_id)
                if profile is None:
                    target.status = "error"
                    target.last_reason = "profile not found"
                    log_event(
                        session,
                        target=target,
                        event_type="profile_missing",
                        message=target.last_reason,
                    )
                    continue

                if target.monitoring_started_at is None:
                    target.monitoring_started_at = now
                    target.status = "monitoring"
                    log_event(
                        session,
                        target=target,
                        event_type="monitoring_started",
                        message=f"watch window {window_start_minutes}-{window_end_minutes} minutes before deadline",
                    )

                previous_status = target.status
                previous_row_status = target.row_status or ""

                row = json.loads(target.payload_json or "{}")
                result = enrich_watchlist_row_with_beforeinfo(row, profile, client, RAW_ROOT)

                target.beforeinfo_checked_at = now
                target.row_status = str(row.get("status", ""))
                target.last_reason = str(row.get("final_reason") or row.get("pre_reason") or "")
                target.payload_json = json_dumps(row)
                checked += 1

                if result["ready"]:
                    target.go_decided_at = target.go_decided_at or now
                    target.status = "checked_go"
                    created = _ensure_intents(session, target=target, settings=settings)
                    if created > 0 or session.query(BetIntent).filter(BetIntent.target_race_id == target.id).count() > 0:
                        target.status = "intent_created"
                    if previous_status != target.status or previous_row_status != target.row_status:
                        log_event(
                            session,
                            target=target,
                            event_type="go_decided",
                            message=target.last_reason,
                            details={
                                "created_intents": created,
                                "execution_mode": execution_mode(settings),
                            },
                        )
                    go_count += 1
                    continue

                if target.row_status == "filtered_out":
                    target.status = "checked_skip"
                    if previous_status != target.status or previous_row_status != target.row_status:
                        log_event(
                            session,
                            target=target,
                            event_type="target_skipped",
                            message=target.last_reason,
                        )
                    skip_count += 1
                    continue

                target.status = "checked_waiting"
                if previous_status != target.status or previous_row_status != target.row_status:
                    log_event(
                        session,
                        target=target,
                        event_type="beforeinfo_waiting",
                        message=target.last_reason,
                    )
                waiting_count += 1

        session.commit()
        print(
            f"[{now:%Y-%m-%d %H:%M:%S}] fresh evaluate completed: "
            f"checked={checked} go={go_count} skip={skip_count} "
            f"waiting={waiting_count} expired={expired_count}"
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
