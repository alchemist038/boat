from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.core.database import (
    AirBetAudit,
    BetExecution,
    BetIntent,
    SessionLocal,
    TargetRace,
    initialize_database,
    json_dumps,
    log_event,
    log_session_event,
)
from app.core.fresh_executor import FreshTeleboatExecutor, get_legacy_teleboat_module
from app.core.settings import DATA_DIR, load_settings, save_settings

LEGACY = get_legacy_teleboat_module()
TeleboatConfigurationError = LEGACY.TeleboatConfigurationError
TeleboatError = LEGACY.TeleboatError
TeleboatInsufficientFundsError = LEGACY.TeleboatInsufficientFundsError


def _expire_intents(session, *, intents: list[BetIntent], seconds_before_deadline: int, min_seconds: int, max_seconds: int) -> None:
    target = intents[0].target
    target.status = "expired"
    target.last_reason = (
        f"timing window miss ({seconds_before_deadline}s before deadline / expected {min_seconds}-{max_seconds}s)"
    )
    for intent in intents:
        intent.status = "expired"
        log_event(
            session,
            target=target,
            intent=intent,
            event_type="intent_expired",
            message=target.last_reason,
        )


def _record_air_execution(session, *, intent: BetIntent, now: datetime, seconds_before_deadline: int) -> None:
    target = intent.target
    execution = BetExecution(
        intent=intent,
        target=target,
        execution_mode="air",
        execution_status="logged",
        executed_at=now,
        seconds_before_deadline=seconds_before_deadline,
        details_json=json_dumps(
            {
                "profile_id": target.profile_id,
                "race_id": target.race_id,
                "deadline_at": target.deadline_at.isoformat(sep=" "),
            }
        ),
    )
    session.add(execution)

    audit = AirBetAudit(
        target=target,
        intent=intent,
        target_key=target.target_key,
        race_id=target.race_id,
        race_date=target.race_date,
        stadium_code=target.stadium_code,
        stadium_name=target.stadium_name,
        race_no=target.race_no,
        profile_id=target.profile_id,
        strategy_id=target.strategy_id,
        bet_type=intent.bet_type,
        combo=intent.combo,
        amount=intent.amount,
        deadline_at=target.deadline_at,
        air_bet_at=now,
        seconds_before_deadline=seconds_before_deadline,
        execution_status="logged",
        reason=target.last_reason,
        source_watchlist_file=target.source_watchlist_file,
        details_json=json_dumps(
            {
                "target_status": target.status,
                "intent_status": intent.status,
            }
        ),
    )
    session.add(audit)

    intent.status = "executed"
    target.air_bet_executed_at = now
    target.status = "air_bet_logged"
    target.last_reason = f"Air bet logged at {now:%H:%M:%S} ({seconds_before_deadline}s)"
    log_event(
        session,
        target=target,
        intent=intent,
        event_type="air_bet_logged",
        message=target.last_reason,
        details={
            "bet_type": intent.bet_type,
            "combo": intent.combo,
            "amount": intent.amount,
            "seconds_before_deadline": seconds_before_deadline,
        },
    )


def _record_real_execution(session, *, intents: list[BetIntent], result, seconds_before_deadline: int) -> None:
    target = intents[0].target
    status = result.execution_status

    if status == "submitted":
        target.status = "real_bet_placed"
        target.last_reason = result.message
        intent_status = "executed"
        event_type = "real_bet_placed"
    elif status in {"assist_timeout", "assist_window_closed"}:
        target.status = status
        target.last_reason = result.message
        intent_status = status
        event_type = status
    else:
        target.status = "error"
        target.last_reason = result.message
        intent_status = "error"
        event_type = "real_bet_error"

    for intent in intents:
        execution = BetExecution(
            intent=intent,
            target=target,
            execution_mode=intent.execution_mode,
            execution_status=status,
            executed_at=result.submitted_at,
            seconds_before_deadline=seconds_before_deadline,
            contract_no=result.contract_no,
            screenshot_path=result.screenshot_path,
            error_message=None if status == "submitted" else result.message,
            details_json=json_dumps({"html_path": result.html_path, **result.details}),
        )
        session.add(execution)
        intent.status = intent_status
        log_event(
            session,
            target=target,
            intent=intent,
            event_type=event_type,
            message=result.message,
            details={
                "contract_no": result.contract_no,
                "screenshot_path": result.screenshot_path,
                "html_path": result.html_path,
                "execution_status": status,
            },
        )


def _record_real_error(
    session,
    *,
    intents: list[BetIntent],
    mode: str,
    seconds_before_deadline: int,
    execution_status: str,
    message: str,
    event_type: str,
    target_status: str,
    intent_status: str,
    screenshot_path: str | None = None,
    html_path: str | None = None,
    extra_details: dict | None = None,
) -> None:
    target = intents[0].target
    target.status = target_status
    target.last_reason = message

    details = {"html_path": html_path, **(extra_details or {})}
    for intent in intents:
        intent.status = intent_status
        session.add(
            BetExecution(
                intent=intent,
                target=target,
                execution_mode=mode,
                execution_status=execution_status,
                executed_at=datetime.now(),
                seconds_before_deadline=seconds_before_deadline,
                screenshot_path=screenshot_path,
                error_message=message,
                details_json=json_dumps(details),
            )
        )
        log_event(
            session,
            target=target,
            intent=intent,
            event_type=event_type,
            message=message,
            details={
                "screenshot_path": screenshot_path,
                "html_path": html_path,
                "execution_status": execution_status,
                **(extra_details or {}),
            },
        )


def _auto_stop_system(settings: dict[str, object]) -> bool:
    if not bool(settings.get("stop_on_insufficient_funds", True)):
        return False
    if not bool(settings.get("system_running", False)):
        return False

    settings["system_running"] = False
    save_settings(settings)
    return True


def _executor_settings(settings: dict[str, object]) -> dict[str, object]:
    payload = dict(settings)
    payload["headless"] = bool(settings.get("real_headless", False))
    return payload


def _next_real_target_in_seconds(grouped_items: list[list[BetIntent]], current_index: int) -> int | None:
    current_deadline = grouped_items[current_index][0].target.deadline_at
    for next_index in range(current_index + 1, len(grouped_items)):
        next_intents = grouped_items[next_index]
        if not next_intents:
            continue
        next_mode = next_intents[0].execution_mode
        if next_mode == "air":
            continue
        return int((next_intents[0].target.deadline_at - current_deadline).total_seconds())
    return None


def main() -> None:
    initialize_database()
    settings = load_settings()
    today_iso = datetime.now().strftime("%Y-%m-%d")
    min_seconds = int(settings["check_window_end_minutes"]) * 60
    max_seconds = int(settings["check_window_start_minutes"]) * 60

    processed = 0
    skipped = 0
    errors = 0
    halted = False

    session = SessionLocal()
    try:
        pending_intents = (
            session.query(BetIntent)
            .join(BetIntent.target)
            .filter(BetIntent.status == "pending")
            .filter(BetIntent.target.has(race_date=today_iso))
            .order_by(TargetRace.deadline_at.asc(), BetIntent.target_race_id.asc(), BetIntent.created_at.asc(), BetIntent.id.asc())
            .all()
        )

        if not pending_intents:
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] fresh execute: no pending intents for today")
            return

        grouped: dict[int, list[BetIntent]] = defaultdict(list)
        for intent in pending_intents:
            grouped[int(intent.target_race_id)].append(intent)
        grouped_items = list(grouped.values())

        needs_real = any(any(item.execution_mode != "air" for item in items) for items in grouped_items)
        context = (
            FreshTeleboatExecutor(data_dir=DATA_DIR, settings=_executor_settings(settings))
            if needs_real
            else _nullcontext()
        )

        with context as executor:
            for index, intents in enumerate(grouped_items):
                target = intents[0].target
                modes = {intent.execution_mode for intent in intents}
                if len(modes) != 1:
                    target.status = "error"
                    target.last_reason = f"execution mode conflict: {sorted(modes)}"
                    for intent in intents:
                        intent.status = "error"
                        log_event(
                            session,
                            target=target,
                            intent=intent,
                            event_type="execution_mode_conflict",
                            message=target.last_reason,
                        )
                    errors += len(intents)
                    session.commit()
                    continue

                mode = next(iter(modes))
                now = datetime.now()
                seconds_before_deadline = int((target.deadline_at - now).total_seconds())
                if seconds_before_deadline < min_seconds or seconds_before_deadline > max_seconds:
                    _expire_intents(
                        session,
                        intents=intents,
                        seconds_before_deadline=seconds_before_deadline,
                        min_seconds=min_seconds,
                        max_seconds=max_seconds,
                    )
                    skipped += len(intents)
                    session.commit()
                    continue

                if mode == "air":
                    for intent in intents:
                        _record_air_execution(
                            session,
                            intent=intent,
                            now=now,
                            seconds_before_deadline=seconds_before_deadline,
                        )
                        processed += 1
                    session.commit()
                    continue

                next_real_target_in_seconds = _next_real_target_in_seconds(grouped_items, index)

                try:
                    result = executor.execute_target(
                        target=target,
                        intents=intents,
                        mode=mode,
                        next_real_target_in_seconds=next_real_target_in_seconds,
                    )
                    log_session_event(
                        session,
                        event_type="fresh_execution",
                        message=result.message,
                        details={
                            "race_id": target.race_id,
                            "mode": mode,
                            "contract_no": result.contract_no,
                            "execution_status": result.execution_status,
                            **result.details,
                        },
                    )
                    _record_real_execution(
                        session,
                        intents=intents,
                        result=result,
                        seconds_before_deadline=seconds_before_deadline,
                    )
                    processed += len(intents)
                except TeleboatConfigurationError as exc:
                    _record_real_error(
                        session,
                        intents=intents,
                        mode=mode,
                        seconds_before_deadline=seconds_before_deadline,
                        execution_status="error",
                        message=str(exc),
                        event_type="credentials_missing",
                        target_status="error",
                        intent_status="error",
                    )
                    log_session_event(
                        session,
                        event_type="credentials_missing",
                        message=str(exc),
                        details={"race_id": target.race_id, "mode": mode},
                    )
                    errors += len(intents)
                except TeleboatInsufficientFundsError as exc:
                    auto_stopped = _auto_stop_system(settings)
                    _record_real_error(
                        session,
                        intents=intents,
                        mode=mode,
                        seconds_before_deadline=seconds_before_deadline,
                        execution_status="insufficient_funds",
                        message=str(exc),
                        event_type="insufficient_funds",
                        target_status="insufficient_funds",
                        intent_status="insufficient_funds",
                        screenshot_path=getattr(exc, "screenshot_path", None),
                        html_path=getattr(exc, "html_path", None),
                        extra_details={
                            "auto_stopped": auto_stopped,
                            **getattr(exc, "details", {}),
                        },
                    )
                    log_session_event(
                        session,
                        event_type="insufficient_funds",
                        message=str(exc),
                        details={
                            "race_id": target.race_id,
                            "mode": mode,
                            "auto_stopped": auto_stopped,
                            **getattr(exc, "details", {}),
                        },
                    )
                    if auto_stopped:
                        log_session_event(
                            session,
                            event_type="system_auto_stopped",
                            message="fresh auto loop stopped after insufficient funds",
                            details={"race_id": target.race_id, "mode": mode},
                        )
                        halted = True
                    errors += len(intents)
                except TeleboatError as exc:
                    _record_real_error(
                        session,
                        intents=intents,
                        mode=mode,
                        seconds_before_deadline=seconds_before_deadline,
                        execution_status="error",
                        message=str(exc),
                        event_type="real_bet_error",
                        target_status="error",
                        intent_status="error",
                        screenshot_path=getattr(exc, "screenshot_path", None),
                        html_path=getattr(exc, "html_path", None),
                        extra_details=getattr(exc, "details", {}),
                    )
                    log_session_event(
                        session,
                        event_type="teleboat_error",
                        message=str(exc),
                        details={"race_id": target.race_id, "mode": mode},
                    )
                    errors += len(intents)

                session.commit()
                if halted:
                    break

            if halted:
                print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] fresh execute halted: insufficient funds")

        session.commit()
        print(
            f"[{datetime.now():%Y-%m-%d %H:%M:%S}] fresh execute completed: "
            f"processed={processed} skipped={skipped} errors={errors}"
        )
    finally:
        session.close()


class _nullcontext:
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb):
        return False


if __name__ == "__main__":
    main()
