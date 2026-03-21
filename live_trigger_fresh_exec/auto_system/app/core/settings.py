from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

SYSTEM_ROOT = Path(__file__).resolve().parents[2]
BOAT_CLONE_ROOT = SYSTEM_ROOT.parent.parent
SHARED_LIVE_TRIGGER_ROOT = BOAT_CLONE_ROOT / "live_trigger"
SHARED_BOX_ROOT = SHARED_LIVE_TRIGGER_ROOT / "boxes"
SHARED_WATCHLIST_ROOT = SHARED_LIVE_TRIGGER_ROOT / "watchlists"
SHARED_RAW_ROOT = SHARED_LIVE_TRIGGER_ROOT / "raw"
SHARED_READY_ROOT = SHARED_LIVE_TRIGGER_ROOT / "ready"
SHARED_RUNTIME_ROOT = SHARED_LIVE_TRIGGER_ROOT / "runtime"
SHARED_BETS_PATH = SHARED_LIVE_TRIGGER_ROOT / "auto_system" / "app" / "core" / "bets.py"
SHARED_PROJECT_RULES_FILE = SHARED_LIVE_TRIGGER_ROOT / "PROJECT_RULES.md"

DATA_DIR = SYSTEM_ROOT / "data"
DB_PATH = DATA_DIR / "system.db"
SETTINGS_FILE = DATA_DIR / "settings.json"
AUTO_RUN_LOG_FILE = DATA_DIR / "auto_run.log"

WATCHLIST_ROOT = SHARED_WATCHLIST_ROOT
RAW_ROOT = SHARED_RAW_ROOT
READY_ROOT = SHARED_READY_ROOT
RUNTIME_ROOT = SHARED_RUNTIME_ROOT

VALID_EXECUTION_MODES = ("air", "assist_real", "armed_real")
VALID_REAL_SESSION_STRATEGIES = ("fresh_per_execution", "burst_reuse")

DEFAULT_SETTINGS: dict[str, Any] = {
    "system_running": False,
    "execution_mode": "air",
    "poll_seconds": 30,
    "check_window_start_minutes": 10,
    "check_window_end_minutes": 5,
    "default_bet_amount": 100,
    "profile_amounts": {},
    "active_profiles": {},
    "ui_auto_refresh": True,
    "ui_refresh_seconds": 10,
    "real_headless": False,
    "stop_on_insufficient_funds": True,
    "manual_action_timeout_seconds": 180,
    "login_timeout_seconds": 120,
    "real_session_strategy": "fresh_per_execution",
    "reuse_when_next_real_within_seconds": 180,
    "post_login_settle_seconds": 10,
    "top_stable_confirm_seconds": 3,
    "logout_after_execution": True,
    "close_browser_after_execution": True,
}


def bootstrap_runtime_path() -> None:
    runtime_text = str(RUNTIME_ROOT)
    if runtime_text not in sys.path:
        sys.path.insert(0, runtime_text)


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


def _normalize_settings(payload: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(DEFAULT_SETTINGS)
    if payload:
        merged.update(payload)

    if not isinstance(merged.get("profile_amounts"), dict):
        merged["profile_amounts"] = {}
    if not isinstance(merged.get("active_profiles"), dict):
        merged["active_profiles"] = {}

    merged["poll_seconds"] = max(5, int(merged.get("poll_seconds", DEFAULT_SETTINGS["poll_seconds"])))
    merged["check_window_start_minutes"] = max(
        1,
        int(merged.get("check_window_start_minutes", DEFAULT_SETTINGS["check_window_start_minutes"])),
    )
    merged["check_window_end_minutes"] = max(
        0,
        int(merged.get("check_window_end_minutes", DEFAULT_SETTINGS["check_window_end_minutes"])),
    )
    if merged["check_window_end_minutes"] >= merged["check_window_start_minutes"]:
        merged["check_window_end_minutes"] = max(0, merged["check_window_start_minutes"] - 1)

    merged["default_bet_amount"] = max(
        0,
        int(merged.get("default_bet_amount", DEFAULT_SETTINGS["default_bet_amount"])),
    )
    merged["ui_auto_refresh"] = _normalize_bool(
        merged.get("ui_auto_refresh"),
        default=bool(DEFAULT_SETTINGS["ui_auto_refresh"]),
    )
    merged["ui_refresh_seconds"] = max(
        5,
        int(merged.get("ui_refresh_seconds", DEFAULT_SETTINGS["ui_refresh_seconds"])),
    )
    merged["real_headless"] = _normalize_bool(
        merged.get("real_headless"),
        default=bool(DEFAULT_SETTINGS["real_headless"]),
    )
    merged["stop_on_insufficient_funds"] = _normalize_bool(
        merged.get("stop_on_insufficient_funds"),
        default=bool(DEFAULT_SETTINGS["stop_on_insufficient_funds"]),
    )
    merged["manual_action_timeout_seconds"] = max(
        30,
        int(merged.get("manual_action_timeout_seconds", DEFAULT_SETTINGS["manual_action_timeout_seconds"])),
    )
    merged["login_timeout_seconds"] = max(
        30,
        int(merged.get("login_timeout_seconds", DEFAULT_SETTINGS["login_timeout_seconds"])),
    )

    strategy = str(
        merged.get("real_session_strategy", DEFAULT_SETTINGS["real_session_strategy"])
    ).strip().lower()
    if strategy not in VALID_REAL_SESSION_STRATEGIES:
        strategy = str(DEFAULT_SETTINGS["real_session_strategy"])
    merged["real_session_strategy"] = strategy
    merged["reuse_when_next_real_within_seconds"] = max(
        0,
        int(
            merged.get(
                "reuse_when_next_real_within_seconds",
                DEFAULT_SETTINGS["reuse_when_next_real_within_seconds"],
            )
        ),
    )
    merged["post_login_settle_seconds"] = max(
        1,
        int(merged.get("post_login_settle_seconds", DEFAULT_SETTINGS["post_login_settle_seconds"])),
    )
    merged["top_stable_confirm_seconds"] = max(
        1,
        int(merged.get("top_stable_confirm_seconds", DEFAULT_SETTINGS["top_stable_confirm_seconds"])),
    )
    merged["logout_after_execution"] = _normalize_bool(
        merged.get("logout_after_execution"),
        default=bool(DEFAULT_SETTINGS["logout_after_execution"]),
    )
    merged["close_browser_after_execution"] = _normalize_bool(
        merged.get("close_browser_after_execution"),
        default=bool(DEFAULT_SETTINGS["close_browser_after_execution"]),
    )

    mode = str(merged.get("execution_mode", DEFAULT_SETTINGS["execution_mode"])).strip().lower()
    if mode not in VALID_EXECUTION_MODES:
        mode = str(DEFAULT_SETTINGS["execution_mode"])
    merged["execution_mode"] = mode
    return merged


def load_settings() -> dict[str, Any]:
    if not SETTINGS_FILE.exists():
        return _normalize_settings(None)
    raw = SETTINGS_FILE.read_text(encoding="utf-8-sig")
    return _normalize_settings(json.loads(raw))


def save_settings(settings: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_settings(settings)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8")
    return normalized


def execution_mode(settings: dict[str, Any]) -> str:
    mode = str(settings.get("execution_mode", "air")).strip().lower()
    if mode not in VALID_EXECUTION_MODES:
        return "air"
    return mode


def profile_enabled(settings: dict[str, Any], profile_id: str) -> bool:
    active_profiles = settings.get("active_profiles", {})
    if profile_id not in active_profiles:
        return True
    return bool(active_profiles.get(profile_id, True))


def profile_amount(settings: dict[str, Any], profile_id: str) -> int:
    profile_amounts = settings.get("profile_amounts", {})
    if profile_id in profile_amounts:
        return max(0, int(profile_amounts[profile_id]))
    return max(0, int(settings.get("default_bet_amount", 100)))
