from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.core.fresh_executor import FreshTeleboatExecutor, STADIUM_CODE_TO_NAME
from app.core.fresh_settings import DATA_DIR, load_settings


def _parse_datetime(value: Any) -> datetime | None:
    if value in {None, ""}:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    candidates = [text]
    if text.endswith("Z"):
        candidates.append(text[:-1] + "+00:00")
    for candidate in candidates:
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone().replace(tzinfo=None)
            return parsed
        except ValueError:
            continue
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _build_target(payload: dict[str, Any]) -> SimpleNamespace:
    stadium_code = str(payload["stadium_code"]).zfill(2)
    race_no = int(payload["race_no"])
    race_id = str(payload.get("race_id") or f"fresh_{stadium_code}_{race_no:02d}")
    stadium_name = str(payload.get("stadium_name") or STADIUM_CODE_TO_NAME.get(stadium_code, stadium_code))
    deadline_at = _parse_datetime(payload.get("deadline_at"))
    return SimpleNamespace(
        stadium_code=stadium_code,
        stadium_name=stadium_name,
        race_no=race_no,
        race_id=race_id,
        deadline_at=deadline_at,
    )


def _build_intents(payload: dict[str, Any]) -> list[SimpleNamespace]:
    intents: list[SimpleNamespace] = []
    for index, row in enumerate(payload.get("bets") or [], start=1):
        intents.append(
            SimpleNamespace(
                id=index,
                bet_type=str(row["bet_type"]),
                combo=str(row["combo"]),
                amount=int(row["amount"]),
            )
        )
    return intents


def _normalize_bool(value: Any, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def _result_payload(
    *,
    ok: bool,
    status: str,
    message: str,
    details: dict[str, Any] | None = None,
    screenshot_path: str | None = None,
    html_path: str | None = None,
) -> dict[str, Any]:
    payload = {
        "ok": ok,
        "status": status,
        "message": message,
        "details": details or {},
    }
    if screenshot_path:
        payload["screenshot_path"] = screenshot_path
    if html_path:
        payload["html_path"] = html_path
    return payload


def _sync_trace(details: dict[str, Any], executor: FreshTeleboatExecutor) -> None:
    details["planned_steps"] = list(executor.trace.planned_steps)
    details["completed_steps"] = list(executor.trace.completed_steps)
    details["warnings"] = list(executor.trace.warnings)


def main() -> None:
    raw_input = sys.stdin.buffer.read().decode("utf-8-sig", errors="ignore").strip()
    payload = json.loads(raw_input or "{}")
    test_mode = str(payload.get("test_mode") or "login_only").strip().lower()
    settings = load_settings()
    settings.update(payload.get("settings") or {})
    settings["login_timeout_seconds"] = max(30, int(settings.get("login_timeout_seconds", 120)))
    settings["manual_action_timeout_seconds"] = max(30, int(settings.get("manual_action_timeout_seconds", 180)))

    cleanup_after_test = _normalize_bool(payload.get("cleanup_after_test"), default=False)
    hold_open_seconds = max(0, int(payload.get("hold_open_seconds", 0)))
    next_real_target_in_seconds = payload.get("next_real_target_in_seconds")
    next_real_target_in_seconds = None if next_real_target_in_seconds in {None, ""} else int(next_real_target_in_seconds)

    target = None
    intents: list[SimpleNamespace] = []
    if test_mode != "login_only":
        target = _build_target(payload)
        intents = _build_intents(payload)
        if not intents:
            print(
                json.dumps(
                    _result_payload(
                        ok=False,
                        status="error",
                        message="No bets were provided.",
                    ),
                    ensure_ascii=False,
                )
            )
            return

    try:
        with FreshTeleboatExecutor(data_dir=DATA_DIR, settings=settings) as executor:
            if test_mode == "login_only":
                result = executor.login_only()
            elif test_mode == "confirm_only":
                result = executor.prepare_target_confirmation(target=target, intents=intents, prefill=False)
            elif test_mode == "confirm_prefill":
                result = executor.prepare_target_confirmation(target=target, intents=intents, prefill=True)
            elif test_mode in {"assist_real", "armed_real"}:
                result = executor.execute_target(
                    target=target,
                    intents=intents,
                    mode=test_mode,
                    next_real_target_in_seconds=next_real_target_in_seconds,
                )
            else:
                raise RuntimeError(f"Unsupported test_mode: {test_mode}")

            output = _result_payload(
                ok=True,
                status=result.execution_status,
                message=result.message,
                details=result.details,
                screenshot_path=result.screenshot_path,
                html_path=result.html_path,
            )

            if cleanup_after_test and executor.has_active_session():
                try:
                    output["details"]["cleanup_logout"] = "completed" if executor.logout() else "skipped"
                except Exception as exc:  # noqa: BLE001
                    output["details"]["cleanup_logout"] = "failed"
                    output["details"]["cleanup_logout_error"] = str(exc)
                _sync_trace(output["details"], executor)

            if hold_open_seconds > 0:
                output["details"]["hold_open_seconds"] = hold_open_seconds
                _sync_trace(output["details"], executor)
                print(json.dumps(output, ensure_ascii=False))
                sys.stdout.flush()
                time.sleep(hold_open_seconds)
                return

        print(json.dumps(output, ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001
        print(
            json.dumps(
                _result_payload(
                    ok=False,
                    status="error",
                    message=str(exc),
                    details=getattr(exc, "details", {}),
                    screenshot_path=getattr(exc, "screenshot_path", None),
                    html_path=getattr(exc, "html_path", None),
                ),
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
