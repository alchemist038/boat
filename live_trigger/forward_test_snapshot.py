from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

LIVE_TRIGGER_ROOT = Path(__file__).resolve().parent
AUTO_SYSTEM_ROOT = LIVE_TRIGGER_ROOT / "auto_system"
DATA_DIR = AUTO_SYSTEM_ROOT / "data"
DB_PATH = DATA_DIR / "system.db"
SETTINGS_PATH = DATA_DIR / "settings.json"
SESSION_STATE_PATH = DATA_DIR / "teleboat_session_state.json"
RESIDENT_STATE_PATH = DATA_DIR / "teleboat_resident_browser.json"
AUTO_RUN_LOG_PATH = DATA_DIR / "auto_run.log"

FINAL_TARGET_STATUSES = {
    "checked_skip",
    "air_bet_logged",
    "real_bet_placed",
    "assist_timeout",
    "expired",
    "error",
}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        return {"_error": f"json decode error: {exc}"}


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _read_text_best_effort(path: Path, *, encodings: tuple[str, ...]) -> str:
    raw = path.read_bytes()
    for encoding in encodings:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode(encodings[0], errors="replace")


def _load_log_tail(path: Path, *, limit: int) -> list[str]:
    if not path.exists():
        return []
    lines = _read_text_best_effort(path, encodings=("utf-8-sig", "cp932", "utf-8")).splitlines()
    return lines[-limit:]


def _sqlite_rows(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    if not DB_PATH.exists():
        return []
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def _format_ts(value: Any) -> str:
    dt = _parse_dt(value)
    if dt is None:
        return "-"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _format_yes_no(value: Any) -> str:
    return "yes" if bool(value) else "no"


def _format_seconds(value: Any) -> str:
    if value is None:
        return "-"
    return f"{int(value)} sec"


def _group_count_text(rows: list[dict[str, Any]], *, key: str, count_key: str = "count") -> str:
    if not rows:
        return "-"
    return ", ".join(
        f"{row.get(key, 'unknown')}={row.get(count_key, 0)}"
        for row in rows
    )


def _writeln(text: str = "") -> None:
    encoding = sys.stdout.encoding or "utf-8"
    payload = f"{text}\n".encode(encoding, errors="replace")
    sys.stdout.buffer.write(payload)


def _detect_warnings(
    *,
    now: datetime,
    settings: dict[str, Any],
    session_state: dict[str, Any],
    resident_state: dict[str, Any],
    active_targets: list[dict[str, Any]],
    log_tail: list[str],
    log_mtime: datetime | None,
    pending_intents: list[dict[str, Any]],
) -> list[str]:
    warnings: list[str] = []

    mode = str(settings.get("execution_mode", "air"))
    system_running = bool(settings.get("system_running", False))
    poll_seconds = int(settings.get("poll_seconds", 30))
    start_minutes = int(settings.get("check_window_start_minutes", 10))
    active_profiles = [
        profile_id
        for profile_id, enabled in dict(settings.get("active_profiles", {})).items()
        if bool(enabled)
    ]

    if not active_profiles:
        warnings.append("有効 profile が 1 つもありません。対象があっても自動運用では見送ります。")

    if system_running and log_mtime is not None:
        stale_seconds = int((now - log_mtime).total_seconds())
        if stale_seconds > max(poll_seconds * 3, 90):
            warnings.append(
                f"auto_run.log の更新が {stale_seconds} 秒止まっています。auto loop 停止や別プロセス異常を確認してください。"
            )

    if system_running and not log_tail:
        warnings.append("system_running=true ですが auto_run.log が読めません。loop 起動状態を確認してください。")

    if mode != "air":
        warnings.append(
            f"settings.json の execution_mode は {mode} です。再起動時は launcher が air に戻しますが、現設定は実投票系です。"
        )

    if mode in {"assist_real", "armed_real"}:
        session_status = str(session_state.get("status", "unknown"))
        resident_status = str(resident_state.get("status", "unknown"))
        if session_status != "verified":
            warnings.append(
                f"実投票系モードですが Teleboat session 状態が {session_status} です。実行前にログイン確認を取り直してください。"
            )
        if resident_status != "running":
            warnings.append(
                f"実投票系モードですが resident browser 状態が {resident_status} です。セッション準備からやり直してください。"
            )

    if pending_intents and not system_running:
        warnings.append("pending intent が残っていますが system_running=false です。意図した停止か確認してください。")

    if active_targets:
        next_target = active_targets[0]
        deadline = _parse_dt(next_target.get("deadline_at"))
        if deadline is not None:
            seconds_to_deadline = int((deadline - now).total_seconds())
            if 0 < seconds_to_deadline <= start_minutes * 60 and next_target.get("status") == "imported":
                warnings.append(
                    "次対象が監視ウィンドウ内に近いのに status=imported のままです。evaluate_targets の進行を確認してください。"
                )

    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Forward test snapshot for live_trigger.")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="target race date (YYYY-MM-DD)")
    parser.add_argument("--limit", type=int, default=8, help="number of rows for tables")
    parser.add_argument("--log-lines", type=int, default=20, help="tail line count for auto_run.log")
    args = parser.parse_args()

    now = datetime.now()
    settings = _load_json(SETTINGS_PATH)
    session_state = _load_json(SESSION_STATE_PATH)
    resident_state = _load_json(RESIDENT_STATE_PATH)
    log_tail = _load_log_tail(AUTO_RUN_LOG_PATH, limit=max(5, args.log_lines))
    log_mtime = datetime.fromtimestamp(AUTO_RUN_LOG_PATH.stat().st_mtime) if AUTO_RUN_LOG_PATH.exists() else None

    target_counts = _sqlite_rows(
        """
        SELECT status, COUNT(*) AS count
        FROM target_races
        WHERE race_date = ?
        GROUP BY status
        ORDER BY count DESC, status ASC
        """,
        (args.date,),
    )
    active_targets = _sqlite_rows(
        """
        SELECT race_date, stadium_code, stadium_name, race_no, profile_id, status, row_status, deadline_at
        FROM target_races
        WHERE race_date = ?
          AND status NOT IN ('checked_skip', 'air_bet_logged', 'real_bet_placed', 'assist_timeout', 'expired', 'error')
        ORDER BY deadline_at ASC, id ASC
        LIMIT ?
        """,
        (args.date, max(1, args.limit)),
    )
    pending_intents = _sqlite_rows(
        """
        SELECT execution_mode, COUNT(*) AS count
        FROM bet_intents
        WHERE status = 'pending'
          AND target_race_id IN (SELECT id FROM target_races WHERE race_date = ?)
        GROUP BY execution_mode
        ORDER BY execution_mode ASC
        """,
        (args.date,),
    )
    recent_executions = _sqlite_rows(
        """
        SELECT execution_mode, execution_status, executed_at, seconds_before_deadline, error_message
        FROM bet_executions
        ORDER BY executed_at DESC, id DESC
        LIMIT ?
        """,
        (max(3, args.limit),),
    )
    recent_sessions = _sqlite_rows(
        """
        SELECT event_type, event_at, message
        FROM session_events
        ORDER BY event_at DESC, id DESC
        LIMIT ?
        """,
        (max(3, args.limit),),
    )

    warnings = _detect_warnings(
        now=now,
        settings=settings,
        session_state=session_state,
        resident_state=resident_state,
        active_targets=active_targets,
        log_tail=log_tail,
        log_mtime=log_mtime,
        pending_intents=pending_intents,
    )

    active_profiles = [
        profile_id
        for profile_id, enabled in dict(settings.get("active_profiles", {})).items()
        if bool(enabled)
    ]
    active_profile_text = ", ".join(active_profiles) if active_profiles else "-"

    _writeln("=== Live Trigger Forward Test Snapshot ===")
    _writeln(f"now: {now:%Y-%m-%d %H:%M:%S}")
    _writeln(f"target_date: {args.date}")
    _writeln()

    _writeln("[運用設定]")
    _writeln(f"- system_running: {_format_yes_no(settings.get('system_running'))}")
    _writeln(f"- execution_mode: {settings.get('execution_mode', '-')}")
    _writeln(
        "- watch_window: "
        f"{settings.get('check_window_start_minutes', '-')}m -> {settings.get('check_window_end_minutes', '-')}m before deadline"
    )
    _writeln(f"- poll_seconds: {settings.get('poll_seconds', '-')}")
    _writeln(f"- default_bet_amount: {settings.get('default_bet_amount', '-')}")
    _writeln(f"- active_profiles: {active_profile_text}")
    _writeln()

    _writeln("[Teleboat]")
    _writeln(f"- session_status: {session_state.get('status', '-')}")
    _writeln(f"- session_state: {session_state.get('session_state', '-')}")
    _writeln(f"- last_verified_at: {_format_ts(session_state.get('last_verified_at'))}")
    _writeln(f"- assumed_valid_until: {_format_ts(session_state.get('assumed_valid_until'))}")
    _writeln(f"- resident_browser: {resident_state.get('status', '-')}")
    _writeln(f"- resident_debug_url: {resident_state.get('debug_url', '-')}")
    _writeln(f"- resident_pid: {resident_state.get('pid', '-')}")
    _writeln()

    _writeln("[当日対象]")
    _writeln(f"- status_counts: {_group_count_text(target_counts, key='status')}")
    if pending_intents:
        pending_text = ", ".join(f"{row['execution_mode']}={row['count']}" for row in pending_intents)
    else:
        pending_text = "-"
    _writeln(f"- pending_intents: {pending_text}")
    if active_targets:
        _writeln("- next_targets:")
        for row in active_targets:
            _writeln(
                "  "
                f"{row.get('deadline_at', '-')} / {row.get('stadium_name') or row.get('stadium_code')} "
                f"{row.get('race_no')}R / {row.get('profile_id')} / {row.get('status')} / {row.get('row_status') or '-'}"
            )
    else:
        _writeln("- next_targets: -")
    _writeln()

    _writeln("[最新実行]")
    if recent_executions:
        for row in recent_executions:
            error = f" / error={row['error_message']}" if row.get("error_message") else ""
            _writeln(
                "  "
                f"{row.get('executed_at', '-')} / {row.get('execution_mode')} / {row.get('execution_status')} "
                f"/ {_format_seconds(row.get('seconds_before_deadline'))}{error}"
            )
    else:
        _writeln("  -")
    _writeln()

    _writeln("[最新 Session Event]")
    if recent_sessions:
        for row in recent_sessions:
            _writeln(f"  {row.get('event_at', '-')} / {row.get('event_type')} / {row.get('message') or '-'}")
    else:
        _writeln("  -")
    _writeln()

    _writeln("[auto_run.log]")
    _writeln(f"- last_updated_at: {_format_ts(log_mtime.isoformat() if log_mtime else None)}")
    if log_tail:
        for line in log_tail:
            _writeln(f"  {line}")
    else:
        _writeln("  -")
    _writeln()

    _writeln("[warnings]")
    if warnings:
        for warning in warnings:
            _writeln(f"- {warning}")
    else:
        _writeln("- none")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
