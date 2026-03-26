from __future__ import annotations

import json
import os
import sys
import time
import ctypes
from datetime import datetime
from pathlib import Path
from typing import Any

RUNTIME_ROOT = Path(__file__).resolve().parent
REPO_ROOT = RUNTIME_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from live_trigger_cli import runtime as base_runtime

SYNC_LOOP_PID_FILENAME = "sync_loop.pid"
BET_LOOP_PID_FILENAME = "bet_loop.pid"
SYNC_LOOP_LOG_FILENAME = "sync_loop.log"
BET_LOOP_LOG_FILENAME = "bet_loop.log"


def data_dir() -> Path:
    return base_runtime.data_dir(RUNTIME_ROOT)


def settings_path() -> Path:
    return base_runtime.settings_path(RUNTIME_ROOT)


def db_path() -> Path:
    return base_runtime.db_path(RUNTIME_ROOT)


def raw_root() -> Path:
    return base_runtime.raw_root(RUNTIME_ROOT)


def box_root() -> Path:
    return base_runtime.box_root(RUNTIME_ROOT)


def sync_loop_pid_path() -> Path:
    return data_dir() / SYNC_LOOP_PID_FILENAME


def bet_loop_pid_path() -> Path:
    return data_dir() / BET_LOOP_PID_FILENAME


def sync_loop_log_path() -> Path:
    return data_dir() / SYNC_LOOP_LOG_FILENAME


def bet_loop_log_path() -> Path:
    return data_dir() / BET_LOOP_LOG_FILENAME


def initialize_runtime() -> None:
    base_runtime.initialize_runtime(RUNTIME_ROOT)


def load_settings() -> dict[str, Any]:
    return base_runtime.load_settings(RUNTIME_ROOT)


def configure_runtime(
    *,
    execution_mode: str | None = None,
    setting_overrides: dict[str, Any] | None = None,
    profile_amount_updates: dict[str, int] | None = None,
    enabled_profiles: list[str] | None = None,
    disabled_profiles: list[str] | None = None,
) -> dict[str, Any]:
    return base_runtime.configure_runtime(
        RUNTIME_ROOT,
        execution_mode=execution_mode,
        setting_overrides=setting_overrides,
        profile_amount_updates=profile_amount_updates,
        enabled_profiles=enabled_profiles,
        disabled_profiles=disabled_profiles,
    )


def latest_summary() -> dict[str, Any]:
    return base_runtime.latest_summary(RUNTIME_ROOT)


def sync_watchlists(*, race_date: str | None = None) -> dict[str, Any]:
    return base_runtime.sync_watchlists(RUNTIME_ROOT, race_date=race_date)


def evaluate_targets(*, race_date: str | None = None, as_of: datetime | None = None) -> dict[str, Any]:
    return base_runtime.evaluate_targets(RUNTIME_ROOT, race_date=race_date, as_of=as_of)


def execute_bets(*, race_date: str | None = None, as_of: datetime | None = None) -> dict[str, Any]:
    return base_runtime.execute_bets(RUNTIME_ROOT, race_date=race_date, as_of=as_of)


def run_sync_cycle(*, race_date: str | None = None) -> dict[str, Any]:
    cycle_started_at = time.perf_counter()
    effective_race_date = base_runtime._normalize_race_date(race_date) if race_date else datetime.now().strftime("%Y-%m-%d")
    result = sync_watchlists(race_date=effective_race_date)
    return {
        "sync": result,
        "timings": {
            "sync_seconds": round(time.perf_counter() - cycle_started_at, 2),
        },
    }


def run_bet_cycle(*, race_date: str | None = None, as_of: datetime | None = None) -> dict[str, Any]:
    cycle_started_at = time.perf_counter()
    effective_as_of = as_of or datetime.now()
    effective_race_date = base_runtime._normalize_race_date(race_date) if race_date else effective_as_of.strftime("%Y-%m-%d")
    evaluate_started_at = time.perf_counter()
    evaluate_result = evaluate_targets(race_date=effective_race_date, as_of=effective_as_of)
    evaluate_seconds = round(time.perf_counter() - evaluate_started_at, 2)
    execute_started_at = time.perf_counter()
    execute_result = execute_bets(race_date=effective_race_date, as_of=effective_as_of)
    execute_seconds = round(time.perf_counter() - execute_started_at, 2)
    return {
        "evaluate": evaluate_result,
        "execute": execute_result,
        "timings": {
            "evaluate_seconds": evaluate_seconds,
            "execute_seconds": execute_seconds,
            "total_seconds": round(time.perf_counter() - cycle_started_at, 2),
        },
    }


def _loop_log(log_path: Path, message: str) -> None:
    timestamped = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}"
    print(timestamped)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(timestamped + "\n")


def _pid_is_running(pid: int | None) -> bool:
    if pid is None or pid <= 0:
        return False
    if os.name == "nt":
        process_query_limited_information = 0x1000
        still_active = 259
        handle = ctypes.windll.kernel32.OpenProcess(process_query_limited_information, False, pid)
        if not handle:
            return False
        try:
            exit_code = ctypes.c_ulong()
            if not ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return False
            return exit_code.value == still_active
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _read_pid(pid_path: Path) -> int | None:
    if not pid_path.exists():
        return None
    try:
        return int(pid_path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def _claim_pid(pid_path: Path) -> int | None:
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    current_pid = os.getpid()
    while True:
        try:
            descriptor = os.open(pid_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            existing_pid = _read_pid(pid_path)
            if existing_pid == current_pid:
                return None
            if existing_pid is not None and _pid_is_running(existing_pid):
                return existing_pid
            pid_path.unlink(missing_ok=True)
            continue
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(str(current_pid))
        return None


def _release_pid(pid_path: Path) -> None:
    if _read_pid(pid_path) == os.getpid():
        pid_path.unlink(missing_ok=True)


def sync_loop(*, max_cycles: int | None = None) -> dict[str, Any]:
    initialize_runtime()
    existing_pid = _claim_pid(sync_loop_pid_path())
    if existing_pid is not None:
        _loop_log(sync_loop_log_path(), f"sync loop already running on PID {existing_pid}; exiting duplicate process")
        return {"cycles": 0, "stopped": True, "already_running": True, "existing_pid": existing_pid}

    cycles = 0
    try:
        while True:
            settings = load_settings()
            if not settings.get("system_running", False):
                _loop_log(sync_loop_log_path(), "system_running=false, exiting sync loop")
                break

            poll_seconds = max(
                60,
                int(settings.get("sync_interval_seconds", base_runtime.DEFAULT_SETTINGS["sync_interval_seconds"])),
            )
            race_date = datetime.now().strftime("%Y-%m-%d")
            _loop_log(sync_loop_log_path(), f"sync cycle start: race_date={race_date}")
            cycle_result = run_sync_cycle(race_date=race_date)
            cycles += 1
            _loop_log(sync_loop_log_path(), f"sync cycle done: {json.dumps(cycle_result, ensure_ascii=False)}")
            if max_cycles is not None and cycles >= max_cycles:
                _loop_log(sync_loop_log_path(), f"reached max_cycles={max_cycles}, exiting sync loop")
                break
            _loop_log(sync_loop_log_path(), f"sleeping {poll_seconds}s until next sync cycle")
            time.sleep(poll_seconds)
    finally:
        _release_pid(sync_loop_pid_path())
    return {"cycles": cycles, "stopped": True}


def bet_loop(*, max_cycles: int | None = None) -> dict[str, Any]:
    initialize_runtime()
    existing_pid = _claim_pid(bet_loop_pid_path())
    if existing_pid is not None:
        _loop_log(bet_loop_log_path(), f"bet loop already running on PID {existing_pid}; exiting duplicate process")
        return {"cycles": 0, "stopped": True, "already_running": True, "existing_pid": existing_pid}

    cycles = 0
    try:
        while True:
            settings = load_settings()
            if not settings.get("system_running", False):
                _loop_log(bet_loop_log_path(), "system_running=false, exiting bet loop")
                break

            poll_seconds = max(
                5,
                int(settings.get("poll_seconds", base_runtime.DEFAULT_SETTINGS["poll_seconds"])),
            )
            now = datetime.now()
            race_date = now.strftime("%Y-%m-%d")
            _loop_log(bet_loop_log_path(), f"bet cycle start: race_date={race_date}")
            cycle_result = run_bet_cycle(race_date=race_date, as_of=now)
            cycles += 1
            _loop_log(bet_loop_log_path(), f"bet cycle done: {json.dumps(cycle_result, ensure_ascii=False)}")
            if max_cycles is not None and cycles >= max_cycles:
                _loop_log(bet_loop_log_path(), f"reached max_cycles={max_cycles}, exiting bet loop")
                break
            _loop_log(bet_loop_log_path(), f"sleeping {poll_seconds}s until next bet cycle")
            time.sleep(poll_seconds)
    finally:
        _release_pid(bet_loop_pid_path())
    return {"cycles": cycles, "stopped": True}

