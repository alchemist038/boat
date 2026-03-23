from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

RUNTIME_ROOT = Path(__file__).resolve().parent
REPO_ROOT = RUNTIME_ROOT.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from boat_race_data.client import BoatRaceClient, FetchResult
from boat_race_data.constants import STADIUMS
from boat_race_data.live_trigger import (
    build_watchlist_row,
    compute_watch_start_time,
    enrich_watchlist_row_with_beforeinfo,
    load_trigger_profiles,
)
from boat_race_data.parsers import parse_beforeinfo, parse_odds_2t, parse_racelist

DATA_DIR_NAME = "data"
SETTINGS_FILENAME = "settings.json"
DB_FILENAME = "system.db"
AUTO_RUN_LOG_FILENAME = "auto_run.log"
AUTO_LOOP_PID_FILENAME = "auto_loop.pid"

SHARED_LIVE_TRIGGER_ROOT = REPO_ROOT / "live_trigger"
SHARED_BOX_ROOT = SHARED_LIVE_TRIGGER_ROOT / "boxes"
SHARED_BETS_PATH = SHARED_LIVE_TRIGGER_ROOT / "auto_system" / "app" / "core" / "bets.py"
FRESH_AUTO_SYSTEM_ROOT = REPO_ROOT / "live_trigger_fresh_exec" / "auto_system"
CANONICAL_DUCKDB_PATH = Path(r"\\038INS\boat\data\silver\boat_race.duckdb")
LOCAL_SOURCE_PREFIX = "local::"
SHARED_SOURCE_PREFIX = "shared::"

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

EARLY_TARGET_STATUSES = {"imported", "monitoring", "checked_waiting"}
ACTIVE_TARGET_STATUSES = {"imported", "monitoring", "checked_waiting", "checked_go", "intent_created"}
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
    "wind_speed_m",
    "lane4_exhibition_time",
    "lane4_exhibition_time_rank",
    "lane4_start_exhibition_st",
    "lane4_st_diff_from_inside",
    "quoted_odds_exacta_4_1",
    "quoted_odds_exacta_4_5",
    "min_quoted_odds",
}

_BETS_MODULE: ModuleType | None = None
_FRESH_EXECUTOR_MODULE: ModuleType | None = None
_LEGACY_TELEBOAT_MODULE: ModuleType | None = None
_LEGACY_TELEBOAT_PATCHED = False
_INITIALIZED_DB_PATHS: set[str] = set()


@dataclass(slots=True)
class RuntimeProfileSpec:
    box_id: str
    profile_id: str
    strategy_id: str
    display_name: str
    description: str
    accent_color: str
    enabled: bool
    watch_minutes_before_deadline: int
    source_kind: str
    evaluator_kind: str
    data: dict[str, Any]
    shared_profile: Any | None = None


def data_dir(runtime_root: Path = RUNTIME_ROOT) -> Path:
    return Path(runtime_root) / DATA_DIR_NAME


def settings_path(runtime_root: Path = RUNTIME_ROOT) -> Path:
    return data_dir(runtime_root) / SETTINGS_FILENAME


def db_path(runtime_root: Path = RUNTIME_ROOT) -> Path:
    return data_dir(runtime_root) / DB_FILENAME


def auto_run_log_path(runtime_root: Path = RUNTIME_ROOT) -> Path:
    return data_dir(runtime_root) / AUTO_RUN_LOG_FILENAME


def auto_loop_pid_path(runtime_root: Path = RUNTIME_ROOT) -> Path:
    return data_dir(runtime_root) / AUTO_LOOP_PID_FILENAME


def box_root(runtime_root: Path = RUNTIME_ROOT) -> Path:
    return Path(runtime_root) / "boxes"


def raw_root(runtime_root: Path = RUNTIME_ROOT) -> Path:
    return Path(runtime_root) / "raw"


def _json_dumps(payload: dict[str, Any] | list[Any] | None) -> str | None:
    if payload is None:
        return None
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


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


def _normalize_datetime(value: Any) -> datetime | None:
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
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _normalize_race_date(value: str | None) -> str:
    if not value:
        return datetime.now().strftime("%Y-%m-%d")
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(f"Unsupported race date format: {value}")


def _maybe_float(value: Any) -> float | None:
    if value in {"", None}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _passes_min_filter(value: Any, minimum: float | None) -> bool:
    if minimum is None:
        return True
    parsed = _maybe_float(value)
    if parsed is None:
        return False
    return parsed >= minimum


def _fetch_text_cached(client: BoatRaceClient, url: str, raw_path: Path) -> FetchResult:
    if raw_path.exists():
        content = raw_path.read_bytes()
        return FetchResult(
            url=url,
            fetched_at=datetime.fromtimestamp(raw_path.stat().st_mtime).isoformat(),
            raw_path=raw_path,
            content=content,
            text=content.decode("utf-8", errors="replace"),
        )
    return client.fetch_text(url, raw_path)


def _entry_by_lane(rows: list[dict[str, object]], lane: int) -> dict[str, object] | None:
    for row in rows:
        if int(row.get("lane", 0) or 0) == lane:
            return row
    return None


def _wrap_shared_profile(profile: Any) -> RuntimeProfileSpec:
    return RuntimeProfileSpec(
        box_id=str(profile.box_id),
        profile_id=str(profile.profile_id),
        strategy_id=str(profile.strategy_id),
        display_name=str(profile.display_name),
        description=str(profile.description),
        accent_color=str(profile.accent_color),
        enabled=bool(profile.enabled),
        watch_minutes_before_deadline=int(profile.watch_minutes_before_deadline),
        source_kind="shared",
        evaluator_kind="shared",
        data={},
        shared_profile=profile,
    )


def _load_local_profile_specs(
    runtime_root: Path = RUNTIME_ROOT,
    *,
    include_disabled: bool = False,
) -> list[RuntimeProfileSpec]:
    local_root = box_root(runtime_root)
    if not local_root.exists():
        return []

    profiles: list[RuntimeProfileSpec] = []
    for path in sorted(local_root.rglob("*.json")):
        if path.name == "box.json":
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        enabled = bool(payload.get("enabled", True))
        if not include_disabled and not enabled:
            continue
        profiles.append(
            RuntimeProfileSpec(
                box_id=str(payload.get("box_id") or path.parent.parent.name),
                profile_id=str(payload["profile_id"]),
                strategy_id=str(payload["strategy_id"]),
                display_name=str(payload.get("display_name", payload["profile_id"])),
                description=str(payload.get("description", "")),
                accent_color=str(payload.get("accent_color", "#365c8d")),
                enabled=enabled,
                watch_minutes_before_deadline=int(payload.get("watch_minutes_before_deadline", 25)),
                source_kind="local",
                evaluator_kind=str(payload.get("local_runtime_kind") or payload.get("strategy_id") or "local"),
                data=payload,
            )
        )
    return profiles


def load_runtime_profiles(
    runtime_root: Path = RUNTIME_ROOT,
    *,
    include_disabled: bool = False,
) -> list[RuntimeProfileSpec]:
    merged: dict[str, RuntimeProfileSpec] = {}
    for profile in load_trigger_profiles(SHARED_BOX_ROOT, include_disabled=include_disabled):
        merged[profile.profile_id] = _wrap_shared_profile(profile)
    for profile in _load_local_profile_specs(runtime_root, include_disabled=include_disabled):
        merged[profile.profile_id] = profile
    return [merged[key] for key in sorted(merged)]


def _build_4wind_watchlist_row(
    race_row: dict[str, object],
    entry_rows: list[dict[str, object]],
    profile: RuntimeProfileSpec,
) -> dict[str, object] | None:
    lane1 = _entry_by_lane(entry_rows, 1)
    lane3 = _entry_by_lane(entry_rows, 3)
    lane4 = _entry_by_lane(entry_rows, 4)
    if lane1 is None or lane3 is None or lane4 is None:
        return None

    allowed_lane3_classes = {str(value) for value in profile.data.get("lane3_class_include", [])}
    lane3_class = str(lane3.get("racer_class", "") or "")
    if allowed_lane3_classes and lane3_class not in allowed_lane3_classes:
        return None

    deadline_time = str(race_row.get("deadline_time", "") or "")
    if not deadline_time:
        return None

    return {
        "box_id": profile.box_id,
        "profile_id": profile.profile_id,
        "strategy_id": profile.strategy_id,
        "race_id": str(race_row.get("race_id", "")),
        "race_date": str(race_row.get("race_date", "")),
        "stadium_code": str(race_row.get("stadium_code", "")),
        "stadium_name": str(race_row.get("stadium_name", "")),
        "race_no": int(race_row.get("race_no", 0) or 0),
        "meeting_title": str(race_row.get("meeting_title", "")),
        "race_title": str(race_row.get("race_title", "")),
        "deadline_time": deadline_time,
        "watch_start_time": compute_watch_start_time(
            str(race_row.get("race_date", "")),
            deadline_time,
            profile.watch_minutes_before_deadline,
        ),
        "status": "waiting_beforeinfo",
        "pre_reason": f"lane3_class={lane3_class}",
        "final_reason": "",
        "lane1_racer_id": lane1.get("racer_id", ""),
        "lane1_racer_name": lane1.get("racer_name", ""),
        "lane1_racer_class": lane1.get("racer_class", ""),
        "lane1_motor_no": lane1.get("motor_no", ""),
        "lane1_motor_place_rate": lane1.get("motor_place_rate", ""),
        "lane1_motor_top3_rate": lane1.get("motor_top3_rate", ""),
        "lane1_exhibition_time": "",
        "lane1_exhibition_best_gap": "",
        "lane2_exhibition_time": "",
        "lane3_exhibition_time": "",
        "lane1_start_exhibition_st": "",
        "min_other_start_exhibition_st": "",
        "lane1_start_gap_over_rest": "",
        "beforeinfo_fetched_at": "",
        "lane3_racer_class": lane3_class,
        "lane4_racer_id": lane4.get("racer_id", ""),
        "lane4_racer_name": lane4.get("racer_name", ""),
        "lane4_racer_class": lane4.get("racer_class", ""),
        "local_runtime_kind": "4wind",
    }


@lru_cache(maxsize=1)
def _latest_racer_sex_index() -> dict[str, str]:
    if not CANONICAL_DUCKDB_PATH.exists():
        return {}
    try:
        import duckdb
    except ImportError:
        return {}

    connection = duckdb.connect(str(CANONICAL_DUCKDB_PATH), read_only=True)
    try:
        rows = connection.execute(
            """
            SELECT racer_id, sex
            FROM (
                SELECT
                    racer_id,
                    sex,
                    ROW_NUMBER() OVER (
                        PARTITION BY racer_id
                        ORDER BY
                            TRY_CAST(term_year AS INTEGER) DESC NULLS LAST,
                            TRY_CAST(term_half AS INTEGER) DESC NULLS LAST,
                            TRY_CAST(term_end_date AS DATE) DESC NULLS LAST,
                            fetched_at DESC NULLS LAST
                    ) AS row_no
                FROM racer_stats_term
                WHERE racer_id IS NOT NULL
                  AND sex IS NOT NULL
                  AND TRIM(racer_id) <> ''
                  AND TRIM(sex) <> ''
            )
            WHERE row_no = 1
            """
        ).fetchall()
    finally:
        connection.close()

    return {str(racer_id).strip(): str(sex).strip() for racer_id, sex in rows}


def _normalize_racer_id(value: Any) -> str | None:
    if value in {"", None}:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def _c2_all_women_reason(entry_rows: list[dict[str, object]]) -> str | None:
    lane_rows = [_entry_by_lane(entry_rows, lane) for lane in range(1, 7)]
    if any(row is None for row in lane_rows):
        return None

    sex_index = _latest_racer_sex_index()
    if not sex_index:
        return None

    sexes: list[str] = []
    for row in lane_rows:
        racer_id = _normalize_racer_id(row.get("racer_id")) if row is not None else None
        if racer_id is None:
            return None
        sex = sex_index.get(racer_id)
        if sex is None:
            return None
        sexes.append(sex)

    if all(sex == "2" for sex in sexes):
        return "women6_proxy"
    return None


def _build_c2_watchlist_row(
    race_row: dict[str, object],
    entry_rows: list[dict[str, object]],
    profile: RuntimeProfileSpec,
) -> dict[str, object] | None:
    shared_profile = profile.shared_profile
    if shared_profile is None:
        return None

    row = build_watchlist_row(race_row, entry_rows, shared_profile)
    if row is not None:
        return row

    women_reason = _c2_all_women_reason(entry_rows)
    if women_reason is None:
        return None

    lane1 = _entry_by_lane(entry_rows, 1)
    if lane1 is None:
        return None
    if lane1.get("racer_class", "") in shared_profile.lane1_class_exclude:
        return None
    if shared_profile.lane1_class_include and lane1.get("racer_class", "") not in shared_profile.lane1_class_include:
        return None

    lane5 = _entry_by_lane(entry_rows, 5)
    lane6 = _entry_by_lane(entry_rows, 6)
    if lane5 and (lane5.get("racer_class", "") in shared_profile.lane5_class_exclude):
        return None
    if lane6 and shared_profile.lane6_class_include and (lane6.get("racer_class", "") not in shared_profile.lane6_class_include):
        return None

    if not _passes_min_filter(lane1.get("motor_place_rate"), shared_profile.lane1_motor_place_rate_min):
        return None
    if not _passes_min_filter(lane1.get("motor_top3_rate"), shared_profile.lane1_motor_top3_rate_min):
        return None

    deadline_time = str(race_row.get("deadline_time", ""))
    row = {
        "box_id": shared_profile.box_id,
        "profile_id": shared_profile.profile_id,
        "strategy_id": shared_profile.strategy_id,
        "race_id": race_row.get("race_id", ""),
        "race_date": race_row.get("race_date", ""),
        "stadium_code": race_row.get("stadium_code", ""),
        "stadium_name": race_row.get("stadium_name", ""),
        "race_no": race_row.get("race_no", ""),
        "meeting_title": race_row.get("meeting_title", ""),
        "race_title": race_row.get("race_title", ""),
        "deadline_time": deadline_time,
        "watch_start_time": compute_watch_start_time(
            str(race_row.get("race_date", "")),
            deadline_time,
            shared_profile.watch_minutes_before_deadline,
        ),
        "status": "waiting_beforeinfo",
        "pre_reason": "",
        "final_reason": "",
        "lane1_racer_id": lane1.get("racer_id", ""),
        "lane1_racer_name": lane1.get("racer_name", ""),
        "lane1_racer_class": lane1.get("racer_class", ""),
        "lane1_motor_no": lane1.get("motor_no", ""),
        "lane1_motor_place_rate": lane1.get("motor_place_rate", ""),
        "lane1_motor_top3_rate": lane1.get("motor_top3_rate", ""),
        "lane1_exhibition_time": "",
        "lane1_exhibition_best_gap": "",
        "lane2_exhibition_time": "",
        "lane3_exhibition_time": "",
        "lane1_start_exhibition_st": "",
        "min_other_start_exhibition_st": "",
        "lane1_start_gap_over_rest": "",
        "beforeinfo_fetched_at": "",
    }

    row["pre_reason"] = f"{women_reason}, class={lane1.get('racer_class', '')}"
    return row


def _build_runtime_watchlist_row(
    race_row: dict[str, object],
    entry_rows: list[dict[str, object]],
    profile: RuntimeProfileSpec,
) -> dict[str, object] | None:
    if profile.strategy_id == "c2" and profile.source_kind == "shared":
        return _build_c2_watchlist_row(race_row, entry_rows, profile)
    if profile.source_kind == "shared" and profile.shared_profile is not None:
        return build_watchlist_row(race_row, entry_rows, profile.shared_profile)
    if profile.evaluator_kind == "4wind":
        return _build_4wind_watchlist_row(race_row, entry_rows, profile)
    return None


def _build_runtime_watchlist_sources(
    runtime_root: Path = RUNTIME_ROOT,
    *,
    race_date: str,
) -> tuple[list[tuple[str, dict[str, object]]], list[str]]:
    profiles = load_runtime_profiles(runtime_root, include_disabled=False)
    if not profiles:
        return [], []

    settings = load_settings(runtime_root)
    race_date_compact = race_date.replace("-", "")
    source_rows: list[tuple[str, dict[str, object]]] = []
    source_names: list[str] = []
    with BoatRaceClient(timeout_seconds=30) as client:
        discovered_stadiums: list[str] | None = None
        for profile in profiles:
            source_prefix = SHARED_SOURCE_PREFIX if profile.source_kind == "shared" else LOCAL_SOURCE_PREFIX
            source_name = f"{source_prefix}{profile.profile_id}"
            source_names.append(source_name)
            if not profile_enabled(settings, profile.profile_id):
                continue
            stadiums: list[str] = []
            if profile.source_kind == "shared" and profile.shared_profile is not None:
                stadiums = [str(code) for code in profile.shared_profile.stadiums if str(code)]
            else:
                stadiums = [str(code) for code in profile.data.get("stadiums", []) if str(code)]
            if not stadiums:
                if discovered_stadiums is None:
                    discovered_stadiums = client.discover_active_stadiums(race_date_compact)
                stadiums = list(discovered_stadiums)
            for stadium_code in stadiums:
                stadium_name = STADIUMS.get(stadium_code, "")
                for race_no in range(1, 13):
                    prefix = f"{stadium_code}_{race_no:02d}"
                    fetch = _fetch_text_cached(
                        client,
                        client.build_race_url("racelist", race_date_compact, stadium_code, race_no),
                        raw_root(runtime_root) / "racelist" / race_date / f"{prefix}.html",
                    )
                    race_row, entry_rows = parse_racelist(
                        fetch.text or "",
                        race_date_compact,
                        stadium_code,
                        stadium_name,
                        race_no,
                        fetch.url,
                        fetch.fetched_at,
                    )
                    if race_row is None or not entry_rows:
                        continue
                    row = _build_runtime_watchlist_row(race_row, entry_rows, profile)
                    if row is not None:
                        source_rows.append((source_name, row))
    return source_rows, source_names


def _lane4_st_diff_from_inside(beforeinfo_rows: list[dict[str, object]]) -> float | None:
    lane4 = _entry_by_lane(beforeinfo_rows, 4)
    if lane4 is None:
        return None
    lane4_start = _maybe_float(lane4.get("start_exhibition_st"))
    if lane4_start is None:
        return None
    inside_starts = [
        value
        for value in (
            _maybe_float(_entry_by_lane(beforeinfo_rows, lane).get("start_exhibition_st"))  # type: ignore[union-attr]
            if _entry_by_lane(beforeinfo_rows, lane) is not None
            else None
            for lane in (1, 2, 3)
        )
        if value is not None
    ]
    if not inside_starts:
        return None
    return lane4_start - min(inside_starts)


def _exhibition_time_rank(beforeinfo_rows: list[dict[str, object]], lane: int) -> int | None:
    lane_row = _entry_by_lane(beforeinfo_rows, lane)
    lane_time = _maybe_float(lane_row.get("exhibition_time")) if lane_row is not None else None
    if lane_time is None:
        return None
    valid_times = sorted(value for value in (_maybe_float(row.get("exhibition_time")) for row in beforeinfo_rows) if value is not None)
    if not valid_times:
        return None
    return valid_times.index(lane_time) + 1


def _exacta_odds_map(odds_rows: list[dict[str, object]]) -> dict[str, float]:
    odds_map: dict[str, float] = {}
    for row in odds_rows:
        if str(row.get("bet_type", "")) != "2連単":
            continue
        first = int(row.get("first_lane", 0) or 0)
        second = int(row.get("second_lane", 0) or 0)
        odds = _maybe_float(row.get("odds"))
        if first <= 0 or second <= 0 or odds is None:
            continue
        odds_map[f"{first}-{second}"] = odds
    return odds_map


def _decide_4wind_evaluation(
    *,
    row: dict[str, object],
    profile: RuntimeProfileSpec,
    beforeinfo_rows: list[dict[str, object]],
    odds_map: dict[str, float],
) -> dict[str, Any]:
    lane4 = _entry_by_lane(beforeinfo_rows, 4)
    if lane4 is None or _maybe_float(lane4.get("exhibition_time")) is None:
        return {
            "status": "waiting_beforeinfo",
            "ready": False,
            "reason": "beforeinfo not ready",
            "details": {},
        }

    required_combos = [str(combo) for combo in profile.data.get("combos", []) if str(combo)]
    combo_odds = {combo: odds_map.get(combo) for combo in required_combos}
    if not required_combos or any(combo_odds.get(combo) is None for combo in required_combos):
        return {
            "status": "waiting_market",
            "ready": False,
            "reason": "quoted odds not ready",
            "details": {},
        }

    wind_speed = _maybe_float(lane4.get("wind_speed_m"))
    lane4_st_diff = _lane4_st_diff_from_inside(beforeinfo_rows)
    lane4_rank = _exhibition_time_rank(beforeinfo_rows, 4)
    min_quoted_odds = min(float(combo_odds[combo]) for combo in required_combos)

    details = {
        "wind_speed_m": wind_speed,
        "lane4_exhibition_time": _maybe_float(lane4.get("exhibition_time")),
        "lane4_exhibition_time_rank": lane4_rank,
        "lane4_start_exhibition_st": _maybe_float(lane4.get("start_exhibition_st")),
        "lane4_st_diff_from_inside": lane4_st_diff,
        "quoted_odds_exacta_4_1": combo_odds.get("4-1"),
        "quoted_odds_exacta_4_5": combo_odds.get("4-5"),
        "min_quoted_odds": min_quoted_odds,
    }

    wind_min = _maybe_float(profile.data.get("wind_speed_min"))
    wind_max = _maybe_float(profile.data.get("wind_speed_max"))
    st_diff_max = _maybe_float(profile.data.get("lane4_st_diff_from_inside_max"))
    rank_max = int(profile.data.get("lane4_exhibition_time_rank_max", 3))
    min_odds_min = _maybe_float(profile.data.get("min_quoted_odds_min"))
    min_odds_lt = _maybe_float(profile.data.get("min_quoted_odds_max_exclusive"))

    checks = [
        wind_speed is not None and (wind_min is None or wind_speed >= wind_min) and (wind_max is None or wind_speed <= wind_max),
        lane4_st_diff is not None and (st_diff_max is None or lane4_st_diff <= st_diff_max),
        lane4_rank is not None and lane4_rank <= rank_max,
        min_quoted_odds is not None
        and (min_odds_min is None or min_quoted_odds >= min_odds_min)
        and (min_odds_lt is None or min_quoted_odds < min_odds_lt),
    ]
    matched = all(checks)
    reason = (
        f"lane3_class={row.get('lane3_racer_class', '')}, "
        f"wind={wind_speed if wind_speed is not None else 'NA'}, "
        f"lane4_st_diff={lane4_st_diff if lane4_st_diff is not None else 'NA'}, "
        f"lane4_rank={lane4_rank if lane4_rank is not None else 'NA'}, "
        f"min_odds={min_quoted_odds:.2f}"
    )
    return {
        "status": "trigger_ready" if matched else "filtered_out",
        "ready": matched,
        "reason": reason,
        "details": details,
    }


def _evaluate_runtime_row(
    *,
    runtime_root: Path,
    row: dict[str, object],
    profile: RuntimeProfileSpec,
    client: BoatRaceClient,
) -> dict[str, bool]:
    if profile.evaluator_kind == "shared" and profile.shared_profile is not None:
        return enrich_watchlist_row_with_beforeinfo(row, profile.shared_profile, client, raw_root(runtime_root))

    if profile.evaluator_kind != "4wind":
        row["status"] = "error"
        row["final_reason"] = f"unsupported evaluator: {profile.evaluator_kind}"
        return {"changed": True, "ready": False}

    race_date_compact = str(row["race_date"]).replace("-", "")
    stadium_code = str(row["stadium_code"])
    race_no = int(row["race_no"])
    prefix = f"{stadium_code}_{race_no:02d}"

    beforeinfo_fetch = _fetch_text_cached(
        client,
        client.build_race_url("beforeinfo", race_date_compact, stadium_code, race_no),
        raw_root(runtime_root) / "beforeinfo" / str(row["race_date"]) / f"{prefix}.html",
    )
    beforeinfo_rows = parse_beforeinfo(
        beforeinfo_fetch.text or "",
        race_date_compact,
        stadium_code,
        race_no,
        beforeinfo_fetch.url,
        beforeinfo_fetch.fetched_at,
    )
    row["beforeinfo_fetched_at"] = beforeinfo_fetch.fetched_at

    odds_fetch = _fetch_text_cached(
        client,
        client.build_race_url("odds2t", race_date_compact, stadium_code, race_no),
        raw_root(runtime_root) / "odds2t" / str(row["race_date"]) / f"{prefix}.html",
    )
    odds_rows = parse_odds_2t(
        odds_fetch.text or "",
        race_date_compact,
        stadium_code,
        race_no,
        odds_fetch.url,
        odds_fetch.fetched_at,
    )
    decision = _decide_4wind_evaluation(
        row=row,
        profile=profile,
        beforeinfo_rows=beforeinfo_rows,
        odds_map=_exacta_odds_map(odds_rows),
    )
    for key, value in decision["details"].items():
        row[key] = "" if value is None else value
    row["status"] = decision["status"]
    row["final_reason"] = decision["reason"]
    return {"changed": True, "ready": bool(decision["ready"])}


def _normalize_settings(payload: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(DEFAULT_SETTINGS)
    if payload:
        merged.update(payload)

    if not isinstance(merged.get("profile_amounts"), dict):
        merged["profile_amounts"] = {}
    if not isinstance(merged.get("active_profiles"), dict):
        merged["active_profiles"] = {}

    merged["system_running"] = _normalize_bool(
        merged.get("system_running"),
        default=bool(DEFAULT_SETTINGS["system_running"]),
    )
    mode = str(merged.get("execution_mode", DEFAULT_SETTINGS["execution_mode"])).strip().lower()
    if mode not in VALID_EXECUTION_MODES:
        mode = str(DEFAULT_SETTINGS["execution_mode"])
    merged["execution_mode"] = mode
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
    return merged


def _connect_db(runtime_root: Path = RUNTIME_ROOT) -> sqlite3.Connection:
    runtime_root = Path(runtime_root)
    runtime_root.mkdir(parents=True, exist_ok=True)
    target_db_path = db_path(runtime_root)
    target_db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(target_db_path, timeout=30.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 30000")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_runtime(runtime_root: Path = RUNTIME_ROOT) -> None:
    runtime_root = Path(runtime_root)
    target_data_dir = data_dir(runtime_root)
    target_data_dir.mkdir(parents=True, exist_ok=True)
    target_db_path = db_path(runtime_root)

    target_settings_path = settings_path(runtime_root)
    if not target_settings_path.exists():
        target_settings_path.write_text(
            json.dumps(DEFAULT_SETTINGS, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    cache_key = str(target_db_path.resolve())
    if cache_key in _INITIALIZED_DB_PATHS and target_db_path.exists():
        return

    with _connect_db(runtime_root) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS target_races (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_key TEXT NOT NULL UNIQUE,
                race_id TEXT NOT NULL,
                race_date TEXT NOT NULL,
                stadium_code TEXT NOT NULL,
                stadium_name TEXT,
                race_no INTEGER NOT NULL,
                profile_id TEXT NOT NULL,
                strategy_id TEXT NOT NULL,
                source_watchlist_file TEXT,
                deadline_at TEXT NOT NULL,
                watch_start_at TEXT,
                imported_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                monitoring_started_at TEXT,
                beforeinfo_checked_at TEXT,
                go_decided_at TEXT,
                air_bet_executed_at TEXT,
                status TEXT NOT NULL,
                row_status TEXT,
                last_reason TEXT,
                payload_json TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_target_races_race_date ON target_races (race_date);
            CREATE INDEX IF NOT EXISTS idx_target_races_status ON target_races (status);
            CREATE INDEX IF NOT EXISTS idx_target_races_deadline ON target_races (deadline_at);

            CREATE TABLE IF NOT EXISTS bet_intents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_race_id INTEGER NOT NULL REFERENCES target_races(id) ON DELETE CASCADE,
                intent_key TEXT NOT NULL UNIQUE,
                execution_mode TEXT NOT NULL,
                status TEXT NOT NULL,
                bet_type TEXT NOT NULL,
                combo TEXT NOT NULL,
                amount INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_bet_intents_target_race_id ON bet_intents (target_race_id);
            CREATE INDEX IF NOT EXISTS idx_bet_intents_status ON bet_intents (status);

            CREATE TABLE IF NOT EXISTS bet_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                intent_id INTEGER NOT NULL REFERENCES bet_intents(id) ON DELETE CASCADE,
                target_race_id INTEGER NOT NULL REFERENCES target_races(id) ON DELETE CASCADE,
                execution_mode TEXT NOT NULL,
                execution_status TEXT NOT NULL,
                executed_at TEXT NOT NULL,
                seconds_before_deadline INTEGER,
                contract_no TEXT,
                screenshot_path TEXT,
                error_message TEXT,
                details_json TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_bet_executions_target_race_id ON bet_executions (target_race_id);
            CREATE INDEX IF NOT EXISTS idx_bet_executions_status ON bet_executions (execution_status);

            CREATE TABLE IF NOT EXISTS execution_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_race_id INTEGER REFERENCES target_races(id) ON DELETE CASCADE,
                intent_id INTEGER REFERENCES bet_intents(id) ON DELETE CASCADE,
                event_type TEXT NOT NULL,
                event_at TEXT NOT NULL,
                message TEXT,
                details_json TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_execution_events_target_race_id ON execution_events (target_race_id);
            CREATE INDEX IF NOT EXISTS idx_execution_events_intent_id ON execution_events (intent_id);
            CREATE INDEX IF NOT EXISTS idx_execution_events_event_type ON execution_events (event_type);

            CREATE TABLE IF NOT EXISTS session_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                event_at TEXT NOT NULL,
                message TEXT,
                details_json TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_session_events_event_type ON session_events (event_type);
            """
        )
    _INITIALIZED_DB_PATHS.add(cache_key)


def load_settings(runtime_root: Path = RUNTIME_ROOT) -> dict[str, Any]:
    initialize_runtime(runtime_root)
    raw = settings_path(runtime_root).read_text(encoding="utf-8-sig")
    return _normalize_settings(json.loads(raw))


def save_settings(runtime_root: Path, settings: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_settings(settings)
    settings_path(runtime_root).write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return normalized


def configure_runtime(
    runtime_root: Path = RUNTIME_ROOT,
    *,
    execution_mode: str | None = None,
    setting_overrides: dict[str, Any] | None = None,
    profile_amount_updates: dict[str, int] | None = None,
    enabled_profiles: list[str] | None = None,
    disabled_profiles: list[str] | None = None,
) -> dict[str, Any]:
    settings = load_settings(runtime_root)
    if execution_mode is not None:
        settings["execution_mode"] = str(execution_mode).strip().lower()
    if setting_overrides:
        settings.update(setting_overrides)

    profile_amounts = dict(settings.get("profile_amounts", {}))
    if profile_amount_updates:
        for profile_id, amount in profile_amount_updates.items():
            profile_amounts[str(profile_id)] = max(0, int(amount))
    settings["profile_amounts"] = profile_amounts

    active_profiles = dict(settings.get("active_profiles", {}))
    for profile_id in enabled_profiles or []:
        active_profiles[str(profile_id)] = True
    for profile_id in disabled_profiles or []:
        active_profiles[str(profile_id)] = False
    settings["active_profiles"] = active_profiles

    return save_settings(runtime_root, settings)


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


def _log(runtime_root: Path, message: str) -> None:
    timestamped = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}"
    print(timestamped)
    log_file = auto_run_log_path(runtime_root)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(timestamped + "\n")


def _pid_is_running(pid: int | None) -> bool:
    if pid is None or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _read_auto_loop_pid(runtime_root: Path = RUNTIME_ROOT) -> int | None:
    pid_path = auto_loop_pid_path(runtime_root)
    if not pid_path.exists():
        return None
    try:
        return int(pid_path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def _claim_auto_loop_pid(runtime_root: Path = RUNTIME_ROOT) -> int | None:
    pid_path = auto_loop_pid_path(runtime_root)
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    current_pid = os.getpid()
    while True:
        try:
            descriptor = os.open(pid_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            existing_pid = _read_auto_loop_pid(runtime_root)
            if existing_pid == current_pid:
                return None
            if existing_pid is not None and _pid_is_running(existing_pid):
                return existing_pid
            pid_path.unlink(missing_ok=True)
            continue
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(str(current_pid))
        return None


def _release_auto_loop_pid(runtime_root: Path = RUNTIME_ROOT) -> None:
    pid_path = auto_loop_pid_path(runtime_root)
    if _read_auto_loop_pid(runtime_root) == os.getpid():
        pid_path.unlink(missing_ok=True)


def _load_module_from_path(module_name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_shared_bets_module() -> ModuleType:
    global _BETS_MODULE
    if _BETS_MODULE is None:
        _BETS_MODULE = _load_module_from_path("live_trigger_shared_bets", SHARED_BETS_PATH)
    return _BETS_MODULE


def _build_local_bet_rows(*, strategy_id: str, profile_id: str, amount: int) -> list[dict[str, Any]]:
    if amount <= 0:
        return []

    normalized_strategy = str(strategy_id).strip().lower()
    normalized_profile = str(profile_id).strip().lower()
    if normalized_strategy in {"4wind", "4w"} or "4wind" in normalized_profile or normalized_profile.startswith("4w"):
        return [
            {"bet_type": "exacta", "combo": "4-1", "amount": int(amount)},
            {"bet_type": "exacta", "combo": "4-5", "amount": int(amount)},
        ]
    return []


def _build_bet_rows(*, strategy_id: str, profile_id: str, amount: int) -> list[dict[str, Any]]:
    local_rows = _build_local_bet_rows(strategy_id=strategy_id, profile_id=profile_id, amount=amount)
    if local_rows:
        return local_rows
    module = _load_shared_bets_module()
    return list(module.build_bet_rows(strategy_id=strategy_id, profile_id=profile_id, amount=amount))


def _load_fresh_executor_module() -> ModuleType:
    global _FRESH_EXECUTOR_MODULE
    if _FRESH_EXECUTOR_MODULE is None:
        fresh_path_text = str(FRESH_AUTO_SYSTEM_ROOT)
        if fresh_path_text not in sys.path:
            sys.path.insert(0, fresh_path_text)
        import app.core.fresh_executor as fresh_executor_module  # type: ignore[import-not-found]

        _FRESH_EXECUTOR_MODULE = fresh_executor_module
    return _FRESH_EXECUTOR_MODULE


def _visible_selector_texts(page: Any, selector: str) -> list[str]:
    try:
        values = page.eval_on_selector_all(
            selector,
            """
            (elements) => elements
              .filter((element) => !!element && element.offsetParent !== null)
              .map((element) => (element.textContent || "").replace(/\\s+/g, " ").trim())
              .filter((text) => !!text)
            """,
        )
    except Exception:  # noqa: BLE001
        return []
    return [str(value) for value in values if str(value).strip()]


def _runtime_select_race(page: Any, *, stadium_code: str, stadium_name: str | None, race_no: int) -> None:
    legacy = _LEGACY_TELEBOAT_MODULE
    if legacy is None:
        raise RuntimeError("Legacy Teleboat module is not loaded.")

    normalized_stadium_code = str(stadium_code).zfill(2)
    normalized_race_no = f"{int(race_no):02d}"
    resolved_name = str(stadium_name or legacy.STADIUM_CODE_TO_NAME.get(normalized_stadium_code, normalized_stadium_code))

    legacy._open_bet_top(page)

    stadium_selectors = [
        f"#jyo{normalized_stadium_code} a",
        f"#jyo{normalized_stadium_code}",
    ]
    if not legacy._wait_for_any_selector(page, stadium_selectors, timeout_ms=8_000):
        available_cards = _visible_selector_texts(page, "li[id^='jyo'] a")
        raise legacy.TeleboatError(
            f"Could not find stadium card for {resolved_name} ({normalized_stadium_code}). "
            f"Visible cards: {available_cards or ['<none>']}"
        )
    legacy._click_first(
        page,
        stadium_selectors,
        description=f"stadium card ({resolved_name})",
        timeout_ms=8_000,
    )
    legacy._settle(page, milliseconds=700)

    race_selectors = [
        f"#selRaceNo{normalized_race_no} a",
        f"#selRaceNo{normalized_race_no}",
    ]
    if not legacy._wait_for_any_selector(page, race_selectors, timeout_ms=8_000):
        available_races = _visible_selector_texts(page, "li[id^='selRaceNo'] a")
        raise legacy.TeleboatError(
            f"Could not find race tab {int(race_no)}R for {resolved_name} ({normalized_stadium_code}). "
            f"Visible races: {available_races or ['<none>']}"
        )
    legacy._click_first(
        page,
        race_selectors,
        description=f"race tab ({int(race_no)}R)",
        timeout_ms=8_000,
    )
    legacy._settle(page, milliseconds=700)


def _patch_legacy_teleboat_module(module: ModuleType) -> None:
    global _LEGACY_TELEBOAT_PATCHED
    if _LEGACY_TELEBOAT_PATCHED:
        return
    module._select_race = _runtime_select_race
    _LEGACY_TELEBOAT_PATCHED = True


def _load_legacy_teleboat_module() -> ModuleType:
    global _LEGACY_TELEBOAT_MODULE
    if _LEGACY_TELEBOAT_MODULE is None:
        module = _load_fresh_executor_module()
        _LEGACY_TELEBOAT_MODULE = module.get_legacy_teleboat_module()
        _patch_legacy_teleboat_module(_LEGACY_TELEBOAT_MODULE)
    return _LEGACY_TELEBOAT_MODULE


def _log_event(
    connection: sqlite3.Connection,
    *,
    event_type: str,
    message: str | None = None,
    target_race_id: int | None = None,
    intent_id: int | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO execution_events (
            target_race_id,
            intent_id,
            event_type,
            event_at,
            message,
            details_json
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            target_race_id,
            intent_id,
            event_type,
            _format_datetime(datetime.now()),
            message,
            _json_dumps(details),
        ),
    )


def _log_session_event(
    connection: sqlite3.Connection,
    *,
    event_type: str,
    message: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO session_events (
            event_type,
            event_at,
            message,
            details_json
        ) VALUES (?, ?, ?, ?)
        """,
        (
            event_type,
            _format_datetime(datetime.now()),
            message,
            _json_dumps(details),
        ),
    )


def _count_target_intents(connection: sqlite3.Connection, target_race_id: int) -> int:
    row = connection.execute(
        "SELECT COUNT(*) AS count FROM bet_intents WHERE target_race_id = ?",
        (target_race_id,),
    ).fetchone()
    return int(row["count"] if row else 0)


def _target_key(row: dict[str, object]) -> str:
    return f"{row.get('race_id', '')}::{row.get('profile_id', '')}"


def _preserve_evaluated_payload(existing_target: sqlite3.Row, row: dict[str, object]) -> dict[str, object]:
    if existing_target["beforeinfo_checked_at"] is None and existing_target["status"] in EARLY_TARGET_STATUSES:
        return dict(row)

    merged = dict(row)
    try:
        existing_payload = json.loads(existing_target["payload_json"] or "{}")
    except json.JSONDecodeError:
        existing_payload = {}

    for key in EVALUATED_PAYLOAD_KEYS:
        if key in existing_payload and existing_payload[key] not in {"", None}:
            merged[key] = existing_payload[key]

    if existing_target["row_status"] and existing_target["row_status"] not in {"", "waiting_beforeinfo"}:
        merged["status"] = existing_target["row_status"]
    if existing_target["last_reason"]:
        if existing_target["row_status"] == "trigger_ready":
            merged["final_reason"] = existing_target["last_reason"]
        elif not merged.get("final_reason"):
            merged["final_reason"] = existing_target["last_reason"]
    return merged


def sync_watchlists(runtime_root: Path = RUNTIME_ROOT, *, race_date: str | None = None) -> dict[str, Any]:
    initialize_runtime(runtime_root)
    target_race_date = _normalize_race_date(race_date)
    settings = load_settings(runtime_root)
    profiles = load_runtime_profiles(runtime_root, include_disabled=False)
    active_profiles = [profile for profile in profiles if profile_enabled(settings, profile.profile_id)]
    source_rows, source_names = _build_runtime_watchlist_sources(runtime_root, race_date=target_race_date)
    shared_profiles = sum(1 for profile in active_profiles if profile.source_kind == "shared")
    local_profiles = sum(1 for profile in active_profiles if profile.source_kind == "local")
    imported = 0
    updated = 0
    withdrawn = 0
    seen_target_keys: set[str] = set()
    now = datetime.now()

    with _connect_db(runtime_root) as connection:
        for source_name, row in source_rows:
            deadline_at = _normalize_datetime(f"{row.get('race_date', '')} {row.get('deadline_time', '')}")
            if deadline_at is None:
                continue
            watch_start_at = _normalize_datetime(str(row.get("watch_start_time", "")))
            target_key = _target_key(row)
            seen_target_keys.add(target_key)

            existing_target = connection.execute(
                "SELECT * FROM target_races WHERE target_key = ?",
                (target_key,),
            ).fetchone()
            if existing_target is None:
                cursor = connection.execute(
                    """
                    INSERT INTO target_races (
                        target_key,
                        race_id,
                        race_date,
                        stadium_code,
                        stadium_name,
                        race_no,
                        profile_id,
                        strategy_id,
                        source_watchlist_file,
                        deadline_at,
                        watch_start_at,
                        imported_at,
                        updated_at,
                        status,
                        row_status,
                        last_reason,
                        payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        target_key,
                        str(row.get("race_id", "")),
                        str(row.get("race_date", "")),
                        str(row.get("stadium_code", "")),
                        str(row.get("stadium_name", "")),
                        int(row.get("race_no", 0) or 0),
                        str(row.get("profile_id", "")),
                        str(row.get("strategy_id", "")),
                        source_name,
                        _format_datetime(deadline_at),
                        _format_datetime(watch_start_at),
                        _format_datetime(now),
                        _format_datetime(now),
                        "imported",
                        str(row.get("status", "")),
                        str(row.get("pre_reason", "")),
                        _json_dumps(row),
                    ),
                )
                _log_event(
                    connection,
                    target_race_id=int(cursor.lastrowid),
                    event_type="watchlist_imported",
                    message=f"Imported from {source_name}",
                )
                imported += 1
                continue

            merged_row = _preserve_evaluated_payload(existing_target, row)
            last_reason = existing_target["last_reason"]
            if existing_target["status"] in EARLY_TARGET_STATUSES:
                last_reason = str(merged_row.get("final_reason") or merged_row.get("pre_reason") or "")

            connection.execute(
                """
                UPDATE target_races
                SET race_id = ?,
                    race_date = ?,
                    stadium_code = ?,
                    stadium_name = ?,
                    race_no = ?,
                    profile_id = ?,
                    strategy_id = ?,
                    source_watchlist_file = ?,
                    deadline_at = ?,
                    watch_start_at = ?,
                    updated_at = ?,
                    row_status = ?,
                    last_reason = ?,
                    payload_json = ?
                WHERE id = ?
                """,
                (
                    str(row.get("race_id", "")),
                    str(row.get("race_date", "")),
                    str(row.get("stadium_code", "")),
                    str(row.get("stadium_name", "")),
                    int(row.get("race_no", 0) or 0),
                    str(row.get("profile_id", "")),
                    str(row.get("strategy_id", "")),
                    source_name,
                    _format_datetime(deadline_at),
                    _format_datetime(watch_start_at),
                    _format_datetime(now),
                    str(merged_row.get("status", "")),
                    last_reason,
                    _json_dumps(merged_row),
                    int(existing_target["id"]),
                ),
            )
            updated += 1

        if source_names:
            placeholders = ", ".join("?" for _ in source_names)
            stale_targets = connection.execute(
                f"""
                SELECT * FROM target_races
                WHERE race_date = ?
                  AND source_watchlist_file IN ({placeholders})
                """,
                [target_race_date, *source_names],
            ).fetchall()
            for target in stale_targets:
                if target["target_key"] in seen_target_keys:
                    continue
                if target["status"] in TERMINAL_TARGET_STATUSES:
                    continue

                message = "removed from current watchlist"
                try:
                    payload = json.loads(target["payload_json"] or "{}")
                except json.JSONDecodeError:
                    payload = {}
                payload["status"] = "watchlist_removed"
                payload["final_reason"] = message

                connection.execute(
                    """
                    UPDATE target_races
                    SET status = ?,
                        row_status = ?,
                        last_reason = ?,
                        updated_at = ?,
                        payload_json = ?
                    WHERE id = ?
                    """,
                    (
                        "withdrawn",
                        "watchlist_removed",
                        message,
                        _format_datetime(now),
                        _json_dumps(payload),
                        int(target["id"]),
                    ),
                )
                pending_intents = connection.execute(
                    """
                    SELECT id FROM bet_intents
                    WHERE target_race_id = ?
                      AND status = 'pending'
                    """,
                    (int(target["id"]),),
                ).fetchall()
                for intent in pending_intents:
                    connection.execute(
                        "UPDATE bet_intents SET status = ? WHERE id = ?",
                        ("cancelled", int(intent["id"])),
                    )
                    _log_event(
                        connection,
                        target_race_id=int(target["id"]),
                        intent_id=int(intent["id"]),
                        event_type="intent_cancelled",
                        message=message,
                    )
                _log_event(
                    connection,
                    target_race_id=int(target["id"]),
                    event_type="target_withdrawn",
                    message=message,
                )
                withdrawn += 1

        connection.commit()

    return {
        "race_date": target_race_date,
        "shared_profiles": shared_profiles,
        "local_profiles": local_profiles,
        "source_rows": len(source_rows),
        "imported": imported,
        "updated": updated,
        "withdrawn": withdrawn,
    }


def _load_profile_map(runtime_root: Path = RUNTIME_ROOT) -> dict[str, RuntimeProfileSpec]:
    profiles = load_runtime_profiles(runtime_root, include_disabled=True)
    return {profile.profile_id: profile for profile in profiles}


def _ensure_intents(
    connection: sqlite3.Connection,
    *,
    target: sqlite3.Row,
    settings: dict[str, Any],
) -> int:
    amount = profile_amount(settings, str(target["profile_id"]))
    target_mode = execution_mode(settings)
    bet_rows = _build_bet_rows(
        strategy_id=str(target["strategy_id"]),
        profile_id=str(target["profile_id"]),
        amount=amount,
    )
    if not bet_rows:
        return 0

    created = 0
    for bet_row in bet_rows:
        intent_key = f"{target['target_key']}::{bet_row['bet_type']}::{bet_row['combo']}"
        existing = connection.execute(
            "SELECT * FROM bet_intents WHERE intent_key = ?",
            (intent_key,),
        ).fetchone()
        if existing is not None:
            if existing["status"] == "pending" and existing["execution_mode"] != target_mode:
                connection.execute(
                    "UPDATE bet_intents SET execution_mode = ? WHERE id = ?",
                    (target_mode, int(existing["id"])),
                )
                _log_event(
                    connection,
                    target_race_id=int(target["id"]),
                    intent_id=int(existing["id"]),
                    event_type="intent_mode_updated",
                    message=f"{existing['bet_type']} {existing['combo']} -> {target_mode}",
                )
            continue

        cursor = connection.execute(
            """
            INSERT INTO bet_intents (
                target_race_id,
                intent_key,
                execution_mode,
                status,
                bet_type,
                combo,
                amount,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(target["id"]),
                intent_key,
                target_mode,
                "pending",
                str(bet_row["bet_type"]),
                str(bet_row["combo"]),
                int(bet_row["amount"]),
                _format_datetime(datetime.now()),
            ),
        )
        _log_event(
            connection,
            target_race_id=int(target["id"]),
            intent_id=int(cursor.lastrowid),
            event_type="intent_created",
            message=f"{bet_row['bet_type']} {bet_row['combo']} / {bet_row['amount']} ({target_mode})",
        )
        created += 1
    return created


def evaluate_targets(
    runtime_root: Path = RUNTIME_ROOT,
    *,
    race_date: str | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    initialize_runtime(runtime_root)
    settings = load_settings(runtime_root)
    profile_map = _load_profile_map(runtime_root)
    now = as_of or datetime.now()
    target_race_date = _normalize_race_date(race_date) if race_date else now.strftime("%Y-%m-%d")
    window_start_minutes = int(settings["check_window_start_minutes"])
    window_end_minutes = int(settings["check_window_end_minutes"])

    checked = 0
    go_count = 0
    skip_count = 0
    waiting_count = 0
    expired_count = 0

    with _connect_db(runtime_root) as connection:
        targets = connection.execute(
            f"""
            SELECT * FROM target_races
            WHERE race_date = ?
              AND status IN ({", ".join("?" for _ in ACTIVE_TARGET_STATUSES)})
            ORDER BY deadline_at ASC, id ASC
            """,
            [target_race_date, *sorted(ACTIVE_TARGET_STATUSES)],
        ).fetchall()

        if not targets:
            return {
                "race_date": target_race_date,
                "checked": checked,
                "go": go_count,
                "skip": skip_count,
                "waiting": waiting_count,
                "expired": expired_count,
            }

        with BoatRaceClient(timeout_seconds=30) as client:
            for target in targets:
                deadline_at = _normalize_datetime(target["deadline_at"])
                if deadline_at is None:
                    continue
                window_open_at = deadline_at - timedelta(minutes=window_start_minutes)
                window_close_at = deadline_at - timedelta(minutes=window_end_minutes)

                if now < window_open_at:
                    continue

                if now >= window_close_at:
                    if target["status"] not in {"checked_skip", "air_bet_logged", "real_bet_placed", "expired"}:
                        message = f"window closed at {window_close_at:%H:%M:%S}"
                        connection.execute(
                            """
                            UPDATE target_races
                            SET status = ?,
                                last_reason = ?,
                                updated_at = ?
                            WHERE id = ?
                            """,
                            ("expired", message, _format_datetime(now), int(target["id"])),
                        )
                        _log_event(
                            connection,
                            target_race_id=int(target["id"]),
                            event_type="window_closed",
                            message=message,
                        )
                        expired_count += 1
                    continue

                if not profile_enabled(settings, str(target["profile_id"])):
                    if target["status"] != "checked_skip":
                        message = "profile disabled in live_trigger_cli"
                        connection.execute(
                            """
                            UPDATE target_races
                            SET status = ?,
                                last_reason = ?,
                                updated_at = ?
                            WHERE id = ?
                            """,
                            ("checked_skip", message, _format_datetime(now), int(target["id"])),
                        )
                        _log_event(
                            connection,
                            target_race_id=int(target["id"]),
                            event_type="target_skipped",
                            message=message,
                        )
                        skip_count += 1
                    continue

                profile = profile_map.get(str(target["profile_id"]))
                if profile is None:
                    message = "profile not found"
                    connection.execute(
                        """
                        UPDATE target_races
                        SET status = ?,
                            last_reason = ?,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        ("error", message, _format_datetime(now), int(target["id"])),
                    )
                    _log_event(
                        connection,
                        target_race_id=int(target["id"]),
                        event_type="profile_missing",
                        message=message,
                    )
                    continue

                if target["monitoring_started_at"] is None:
                    connection.execute(
                        """
                        UPDATE target_races
                        SET monitoring_started_at = ?,
                            status = ?,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            _format_datetime(now),
                            "monitoring",
                            _format_datetime(now),
                            int(target["id"]),
                        ),
                    )
                    _log_event(
                        connection,
                        target_race_id=int(target["id"]),
                        event_type="monitoring_started",
                        message=f"watch window {window_start_minutes}-{window_end_minutes} minutes before deadline",
                    )
                    target = connection.execute(
                        "SELECT * FROM target_races WHERE id = ?",
                        (int(target["id"]),),
                    ).fetchone()

                previous_status = str(target["status"])
                previous_row_status = str(target["row_status"] or "")
                try:
                    row = json.loads(target["payload_json"] or "{}")
                except json.JSONDecodeError:
                    row = {}

                result = _evaluate_runtime_row(
                    runtime_root=runtime_root,
                    row=row,
                    profile=profile,
                    client=client,
                )
                new_row_status = str(row.get("status", ""))
                new_reason = str(row.get("final_reason") or row.get("pre_reason") or "")

                target_status = "checked_waiting"
                go_decided_at = target["go_decided_at"]
                created = 0

                if result["ready"]:
                    target_status = "checked_go"
                    go_decided_at = target["go_decided_at"] or _format_datetime(now)
                    target = connection.execute(
                        "SELECT * FROM target_races WHERE id = ?",
                        (int(target["id"]),),
                    ).fetchone()
                    created = _ensure_intents(connection, target=target, settings=settings)
                    if created > 0 or _count_target_intents(connection, int(target["id"])) > 0:
                        target_status = "intent_created"
                    if previous_status != target_status or previous_row_status != new_row_status:
                        _log_event(
                            connection,
                            target_race_id=int(target["id"]),
                            event_type="go_decided",
                            message=new_reason,
                            details={
                                "created_intents": created,
                                "execution_mode": execution_mode(settings),
                            },
                        )
                    go_count += 1
                elif new_row_status == "filtered_out":
                    target_status = "checked_skip"
                    if previous_status != target_status or previous_row_status != new_row_status:
                        _log_event(
                            connection,
                            target_race_id=int(target["id"]),
                            event_type="target_skipped",
                            message=new_reason,
                        )
                    skip_count += 1
                else:
                    target_status = "checked_waiting"
                    if previous_status != target_status or previous_row_status != new_row_status:
                        _log_event(
                            connection,
                            target_race_id=int(target["id"]),
                            event_type="beforeinfo_waiting",
                            message=new_reason,
                        )
                    waiting_count += 1

                connection.execute(
                    """
                    UPDATE target_races
                    SET beforeinfo_checked_at = ?,
                        go_decided_at = ?,
                        updated_at = ?,
                        status = ?,
                        row_status = ?,
                        last_reason = ?,
                        payload_json = ?
                    WHERE id = ?
                    """,
                    (
                        _format_datetime(now),
                        go_decided_at,
                        _format_datetime(now),
                        target_status,
                        new_row_status,
                        new_reason,
                        _json_dumps(row),
                        int(target["id"]),
                    ),
                )
                checked += 1

        connection.commit()

    return {
        "race_date": target_race_date,
        "checked": checked,
        "go": go_count,
        "skip": skip_count,
        "waiting": waiting_count,
        "expired": expired_count,
    }


def _build_manual_target(payload: dict[str, Any], *, stadium_name_map: dict[str, str]) -> SimpleNamespace:
    stadium_code = str(payload["stadium_code"]).zfill(2)
    race_no = int(payload["race_no"])
    race_id = str(payload.get("race_id") or f"live_trigger_cli_{stadium_code}_{race_no:02d}")
    stadium_name = str(payload.get("stadium_name") or stadium_name_map.get(stadium_code, stadium_code))
    deadline_at = _normalize_datetime(payload.get("deadline_at"))
    return SimpleNamespace(
        stadium_code=stadium_code,
        stadium_name=stadium_name,
        race_no=race_no,
        race_id=race_id,
        deadline_at=deadline_at,
    )


def _build_manual_intents(payload: dict[str, Any]) -> list[SimpleNamespace]:
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


def _executor_settings_from_runtime(settings: dict[str, Any]) -> dict[str, Any]:
    payload = dict(settings)
    payload["headless"] = bool(settings.get("real_headless", False))
    return payload


def _fresh_executor_api() -> dict[str, Any]:
    module = _load_fresh_executor_module()
    legacy = _load_legacy_teleboat_module()
    return {
        "FreshTeleboatExecutor": module.FreshTeleboatExecutor,
        "STADIUM_CODE_TO_NAME": dict(getattr(module, "STADIUM_CODE_TO_NAME", {})),
        "TeleboatError": legacy.TeleboatError,
        "TeleboatConfigurationError": legacy.TeleboatConfigurationError,
        "TeleboatInsufficientFundsError": legacy.TeleboatInsufficientFundsError,
    }


def run_manual_test(
    payload: dict[str, Any],
    *,
    runtime_root: Path = RUNTIME_ROOT,
) -> dict[str, Any]:
    initialize_runtime(runtime_root)
    executor_api = _fresh_executor_api()
    FreshTeleboatExecutor = executor_api["FreshTeleboatExecutor"]
    stadium_name_map = executor_api["STADIUM_CODE_TO_NAME"]
    TeleboatError = executor_api["TeleboatError"]

    test_mode = str(payload.get("test_mode") or "login_only").strip().lower()
    settings = load_settings(runtime_root)
    settings.update(payload.get("settings") or {})
    effective_settings = _executor_settings_from_runtime(settings)

    target = None
    intents: list[SimpleNamespace] = []
    if test_mode != "login_only":
        target = _build_manual_target(payload, stadium_name_map=stadium_name_map)
        intents = _build_manual_intents(payload)
        if not intents:
            raise ValueError("manual-test requires at least one --bet unless test-mode is login_only")

    cleanup_after_test = _normalize_bool(payload.get("cleanup_after_test"), default=False)
    hold_open_seconds = max(0, int(payload.get("hold_open_seconds", 0)))
    next_real_target_in_seconds = payload.get("next_real_target_in_seconds")
    if next_real_target_in_seconds not in {None, ""}:
        next_real_target_in_seconds = int(next_real_target_in_seconds)
    else:
        next_real_target_in_seconds = None

    try:
        with FreshTeleboatExecutor(data_dir=data_dir(runtime_root), settings=effective_settings) as executor:
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
                raise ValueError(f"Unsupported test_mode: {test_mode}")

            details = dict(getattr(result, "details", {}) or {})
            details["planned_steps"] = list(getattr(executor.trace, "planned_steps", []))
            details["completed_steps"] = list(getattr(executor.trace, "completed_steps", []))
            details["warnings"] = list(getattr(executor.trace, "warnings", []))

            if cleanup_after_test and executor.has_active_session():
                try:
                    details["cleanup_logout"] = "completed" if executor.logout() else "skipped"
                except Exception as exc:  # noqa: BLE001
                    details["cleanup_logout"] = "failed"
                    details["cleanup_logout_error"] = str(exc)

            if hold_open_seconds > 0:
                details["hold_open_seconds"] = hold_open_seconds
                time.sleep(hold_open_seconds)

            return {
                "ok": True,
                "status": result.execution_status,
                "message": result.message,
                "contract_no": getattr(result, "contract_no", None),
                "screenshot_path": getattr(result, "screenshot_path", None),
                "html_path": getattr(result, "html_path", None),
                "details": details,
            }
    except TeleboatError as exc:
        return {
            "ok": False,
            "status": "error",
            "message": str(exc),
            "contract_no": None,
            "screenshot_path": getattr(exc, "screenshot_path", None),
            "html_path": getattr(exc, "html_path", None),
            "details": getattr(exc, "details", {}) or {},
        }


def _pending_intent_groups(
    connection: sqlite3.Connection,
    *,
    target_race_date: str,
) -> list[list[sqlite3.Row]]:
    rows = connection.execute(
        """
        SELECT
            bet_intents.*,
            target_races.target_key AS target_key,
            target_races.race_id AS target_race_id_value,
            target_races.race_date AS target_race_date,
            target_races.stadium_code AS target_stadium_code,
            target_races.stadium_name AS target_stadium_name,
            target_races.race_no AS target_race_no,
            target_races.profile_id AS target_profile_id,
            target_races.strategy_id AS target_strategy_id,
            target_races.source_watchlist_file AS target_source_watchlist_file,
            target_races.deadline_at AS target_deadline_at,
            target_races.last_reason AS target_last_reason,
            target_races.status AS target_status
        FROM bet_intents
        JOIN target_races ON target_races.id = bet_intents.target_race_id
        WHERE bet_intents.status = 'pending'
          AND target_races.race_date = ?
        ORDER BY target_races.deadline_at ASC,
                 target_races.race_id ASC,
                 bet_intents.execution_mode ASC,
                 bet_intents.created_at ASC,
                 bet_intents.id ASC
        """,
        (target_race_date,),
    ).fetchall()

    grouped: list[list[sqlite3.Row]] = []
    current_group_key: tuple[str, str] | None = None
    current_group: list[sqlite3.Row] = []
    for row in rows:
        group_key = (str(row["target_race_id_value"]), str(row["execution_mode"]))
        if current_group_key is None or group_key != current_group_key:
            if current_group:
                grouped.append(current_group)
            current_group = [row]
            current_group_key = group_key
        else:
            current_group.append(row)
    if current_group:
        grouped.append(current_group)
    return grouped


def _combine_execution_intents(intents: list[sqlite3.Row]) -> list[SimpleNamespace]:
    combined: dict[tuple[str, str], SimpleNamespace] = {}
    for intent in intents:
        key = (str(intent["bet_type"]), str(intent["combo"]))
        if key not in combined:
            combined[key] = SimpleNamespace(
                id=int(intent["id"]),
                bet_type=str(intent["bet_type"]),
                combo=str(intent["combo"]),
                amount=int(intent["amount"]),
                source_intent_ids=[int(intent["id"])],
            )
            continue
        combined[key].amount += int(intent["amount"])
        combined[key].source_intent_ids.append(int(intent["id"]))
    return list(combined.values())


def _set_target_statuses(
    connection: sqlite3.Connection,
    *,
    target_race_ids: list[int],
    status: str,
    reason: str,
    now: datetime,
    air_bet_executed_at: datetime | None = None,
) -> None:
    for target_race_id in target_race_ids:
        _set_target_status(
            connection,
            target_race_id=target_race_id,
            status=status,
            reason=reason,
            now=now,
            air_bet_executed_at=air_bet_executed_at,
        )


def _next_real_target_in_seconds(grouped_items: list[list[sqlite3.Row]], current_index: int) -> int | None:
    current_deadline = _normalize_datetime(grouped_items[current_index][0]["target_deadline_at"])
    if current_deadline is None:
        return None
    for next_index in range(current_index + 1, len(grouped_items)):
        next_group = grouped_items[next_index]
        if not next_group:
            continue
        next_mode = str(next_group[0]["execution_mode"])
        if next_mode == "air":
            continue
        next_deadline = _normalize_datetime(next_group[0]["target_deadline_at"])
        if next_deadline is None:
            continue
        return int((next_deadline - current_deadline).total_seconds())
    return None


def _record_execution_row(
    connection: sqlite3.Connection,
    *,
    intent_id: int,
    target_race_id: int,
    execution_mode: str,
    execution_status: str,
    executed_at: datetime,
    seconds_before_deadline: int | None,
    contract_no: str | None = None,
    screenshot_path: str | None = None,
    error_message: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO bet_executions (
            intent_id,
            target_race_id,
            execution_mode,
            execution_status,
            executed_at,
            seconds_before_deadline,
            contract_no,
            screenshot_path,
            error_message,
            details_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            intent_id,
            target_race_id,
            execution_mode,
            execution_status,
            _format_datetime(executed_at),
            seconds_before_deadline,
            contract_no,
            screenshot_path,
            error_message,
            _json_dumps(details),
        ),
    )


def _set_target_status(
    connection: sqlite3.Connection,
    *,
    target_race_id: int,
    status: str,
    reason: str,
    now: datetime,
    air_bet_executed_at: datetime | None = None,
) -> None:
    connection.execute(
        """
        UPDATE target_races
        SET status = ?,
            last_reason = ?,
            updated_at = ?,
            air_bet_executed_at = COALESCE(?, air_bet_executed_at)
        WHERE id = ?
        """,
        (
            status,
            reason,
            _format_datetime(now),
            _format_datetime(air_bet_executed_at),
            target_race_id,
        ),
    )


def _auto_stop_system(runtime_root: Path, settings: dict[str, Any]) -> bool:
    if not bool(settings.get("stop_on_insufficient_funds", True)):
        return False
    if not bool(settings.get("system_running", False)):
        return False
    settings["system_running"] = False
    save_settings(runtime_root, settings)
    return True


def execute_bets(
    runtime_root: Path = RUNTIME_ROOT,
    *,
    race_date: str | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    initialize_runtime(runtime_root)
    settings = load_settings(runtime_root)
    now = as_of or datetime.now()
    target_race_date = _normalize_race_date(race_date) if race_date else now.strftime("%Y-%m-%d")
    min_seconds = int(settings["check_window_end_minutes"]) * 60
    max_seconds = int(settings["check_window_start_minutes"]) * 60
    executor_api = _fresh_executor_api()
    FreshTeleboatExecutor = executor_api["FreshTeleboatExecutor"]
    TeleboatConfigurationError = executor_api["TeleboatConfigurationError"]
    TeleboatError = executor_api["TeleboatError"]
    TeleboatInsufficientFundsError = executor_api["TeleboatInsufficientFundsError"]

    processed = 0
    skipped = 0
    errors = 0
    halted = False

    with _connect_db(runtime_root) as connection:
        grouped_items = _pending_intent_groups(connection, target_race_date=target_race_date)
        if not grouped_items:
            return {
                "race_date": target_race_date,
                "processed": processed,
                "skipped": skipped,
                "errors": errors,
                "halted": halted,
            }

        needs_real = any(any(str(item["execution_mode"]) != "air" for item in group) for group in grouped_items)
        executor_context = (
            FreshTeleboatExecutor(data_dir=data_dir(runtime_root), settings=_executor_settings_from_runtime(settings))
            if needs_real
            else _NullContext()
        )

        with executor_context as executor:
            for index, intents in enumerate(grouped_items):
                target_ids = sorted({int(intent["target_race_id"]) for intent in intents})
                modes = {str(intent["execution_mode"]) for intent in intents}
                if len(modes) != 1:
                    message = f"execution mode conflict: {sorted(modes)}"
                    _set_target_statuses(connection, target_race_ids=target_ids, status="error", reason=message, now=now)
                    for intent in intents:
                        connection.execute("UPDATE bet_intents SET status = ? WHERE id = ?", ("error", int(intent["id"])))
                        _log_event(
                            connection,
                            target_race_id=int(intent["target_race_id"]),
                            intent_id=int(intent["id"]),
                            event_type="execution_mode_conflict",
                            message=message,
                        )
                    errors += len(intents)
                    connection.commit()
                    continue

                mode = next(iter(modes))
                deadline_at = _normalize_datetime(intents[0]["target_deadline_at"])
                if deadline_at is None:
                    continue
                seconds_before_deadline = int((deadline_at - now).total_seconds())

                if seconds_before_deadline < min_seconds or seconds_before_deadline > max_seconds:
                    message = (
                        f"timing window miss ({seconds_before_deadline}s before deadline / "
                        f"expected {min_seconds}-{max_seconds}s)"
                    )
                    _set_target_statuses(connection, target_race_ids=target_ids, status="expired", reason=message, now=now)
                    for intent in intents:
                        connection.execute(
                            "UPDATE bet_intents SET status = ? WHERE id = ?",
                            ("expired", int(intent["id"])),
                        )
                        _log_event(
                            connection,
                            target_race_id=int(intent["target_race_id"]),
                            intent_id=int(intent["id"]),
                            event_type="intent_expired",
                            message=message,
                        )
                    skipped += len(intents)
                    connection.commit()
                    continue

                if mode == "air":
                    reason = f"Air bet logged at {now:%H:%M:%S} ({seconds_before_deadline}s)"
                    _set_target_statuses(
                        connection,
                        target_race_ids=target_ids,
                        status="air_bet_logged",
                        reason=reason,
                        now=now,
                        air_bet_executed_at=now,
                    )
                    for intent in intents:
                        connection.execute(
                            "UPDATE bet_intents SET status = ? WHERE id = ?",
                            ("executed", int(intent["id"])),
                        )
                        _record_execution_row(
                            connection,
                            intent_id=int(intent["id"]),
                            target_race_id=int(intent["target_race_id"]),
                            execution_mode="air",
                            execution_status="logged",
                            executed_at=now,
                            seconds_before_deadline=seconds_before_deadline,
                            details={
                                "profile_id": intent["target_profile_id"],
                                "race_id": intents[0]["target_race_id_value"],
                                "deadline_at": intents[0]["target_deadline_at"],
                            },
                        )
                        _log_event(
                            connection,
                            target_race_id=int(intent["target_race_id"]),
                            intent_id=int(intent["id"]),
                            event_type="air_bet_logged",
                            message=reason,
                            details={
                                "bet_type": intent["bet_type"],
                                "combo": intent["combo"],
                                "amount": intent["amount"],
                                "seconds_before_deadline": seconds_before_deadline,
                            },
                        )
                        processed += 1
                    connection.commit()
                    continue

                next_real_target_in_seconds = _next_real_target_in_seconds(grouped_items, index)
                target = SimpleNamespace(
                    stadium_code=str(intents[0]["target_stadium_code"]),
                    stadium_name=str(intents[0]["target_stadium_name"] or ""),
                    race_no=int(intents[0]["target_race_no"]),
                    race_id=str(intents[0]["target_race_id_value"]),
                    deadline_at=deadline_at,
                )
                runtime_intents = _combine_execution_intents(intents)

                try:
                    result = executor.execute_target(
                        target=target,
                        intents=runtime_intents,
                        mode=mode,
                        next_real_target_in_seconds=next_real_target_in_seconds,
                    )
                    _log_session_event(
                        connection,
                        event_type="fresh_execution",
                        message=result.message,
                        details={
                            "race_id": target.race_id,
                            "mode": mode,
                            "contract_no": result.contract_no,
                            "execution_status": result.execution_status,
                            **dict(result.details),
                        },
                    )

                    if result.execution_status == "submitted":
                        target_status = "real_bet_placed"
                        intent_status = "executed"
                        event_type = "real_bet_placed"
                    elif result.execution_status in {"assist_timeout", "assist_window_closed"}:
                        target_status = result.execution_status
                        intent_status = result.execution_status
                        event_type = result.execution_status
                    else:
                        target_status = "error"
                        intent_status = "error"
                        event_type = "real_bet_error"

                    _set_target_statuses(
                        connection,
                        target_race_ids=target_ids,
                        status=target_status,
                        reason=result.message,
                        now=now,
                    )
                    for intent in intents:
                        connection.execute(
                            "UPDATE bet_intents SET status = ? WHERE id = ?",
                            (intent_status, int(intent["id"])),
                        )
                        _record_execution_row(
                            connection,
                            intent_id=int(intent["id"]),
                            target_race_id=int(intent["target_race_id"]),
                            execution_mode=mode,
                            execution_status=result.execution_status,
                            executed_at=getattr(result, "submitted_at", now),
                            seconds_before_deadline=seconds_before_deadline,
                            contract_no=getattr(result, "contract_no", None),
                            screenshot_path=getattr(result, "screenshot_path", None),
                            error_message=None if result.execution_status == "submitted" else result.message,
                            details={"html_path": getattr(result, "html_path", None), **dict(result.details)},
                        )
                        _log_event(
                            connection,
                            target_race_id=int(intent["target_race_id"]),
                            intent_id=int(intent["id"]),
                            event_type=event_type,
                            message=result.message,
                            details={
                                "contract_no": result.contract_no,
                                "screenshot_path": result.screenshot_path,
                                "html_path": result.html_path,
                                "execution_status": result.execution_status,
                            },
                        )
                    processed += len(intents)
                except TeleboatConfigurationError as exc:
                    _set_target_statuses(connection, target_race_ids=target_ids, status="error", reason=str(exc), now=now)
                    for intent in intents:
                        connection.execute("UPDATE bet_intents SET status = ? WHERE id = ?", ("error", int(intent["id"])))
                        _record_execution_row(
                            connection,
                            intent_id=int(intent["id"]),
                            target_race_id=int(intent["target_race_id"]),
                            execution_mode=mode,
                            execution_status="error",
                            executed_at=now,
                            seconds_before_deadline=seconds_before_deadline,
                            error_message=str(exc),
                        )
                        _log_event(
                            connection,
                            target_race_id=int(intent["target_race_id"]),
                            intent_id=int(intent["id"]),
                            event_type="credentials_missing",
                            message=str(exc),
                        )
                    _log_session_event(
                        connection,
                        event_type="credentials_missing",
                        message=str(exc),
                        details={"race_id": target.race_id, "mode": mode},
                    )
                    errors += len(intents)
                except TeleboatInsufficientFundsError as exc:
                    auto_stopped = _auto_stop_system(runtime_root, settings)
                    _set_target_statuses(
                        connection,
                        target_race_ids=target_ids,
                        status="insufficient_funds",
                        reason=str(exc),
                        now=now,
                    )
                    for intent in intents:
                        connection.execute(
                            "UPDATE bet_intents SET status = ? WHERE id = ?",
                            ("insufficient_funds", int(intent["id"])),
                        )
                        _record_execution_row(
                            connection,
                            intent_id=int(intent["id"]),
                            target_race_id=int(intent["target_race_id"]),
                            execution_mode=mode,
                            execution_status="insufficient_funds",
                            executed_at=now,
                            seconds_before_deadline=seconds_before_deadline,
                            screenshot_path=getattr(exc, "screenshot_path", None),
                            error_message=str(exc),
                            details={"html_path": getattr(exc, "html_path", None), **getattr(exc, "details", {})},
                        )
                        _log_event(
                            connection,
                            target_race_id=int(intent["target_race_id"]),
                            intent_id=int(intent["id"]),
                            event_type="insufficient_funds",
                            message=str(exc),
                            details={
                                "screenshot_path": getattr(exc, "screenshot_path", None),
                                "html_path": getattr(exc, "html_path", None),
                                "auto_stopped": auto_stopped,
                                **getattr(exc, "details", {}),
                            },
                        )
                    _log_session_event(
                        connection,
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
                        halted = True
                        _log_session_event(
                            connection,
                            event_type="system_auto_stopped",
                            message="live_trigger_cli loop stopped after insufficient funds",
                            details={"race_id": target.race_id, "mode": mode},
                    )
                    errors += len(intents)
                except TeleboatError as exc:
                    _set_target_statuses(connection, target_race_ids=target_ids, status="error", reason=str(exc), now=now)
                    for intent in intents:
                        connection.execute("UPDATE bet_intents SET status = ? WHERE id = ?", ("error", int(intent["id"])))
                        _record_execution_row(
                            connection,
                            intent_id=int(intent["id"]),
                            target_race_id=int(intent["target_race_id"]),
                            execution_mode=mode,
                            execution_status="error",
                            executed_at=now,
                            seconds_before_deadline=seconds_before_deadline,
                            screenshot_path=getattr(exc, "screenshot_path", None),
                            error_message=str(exc),
                            details={"html_path": getattr(exc, "html_path", None), **getattr(exc, "details", {})},
                        )
                        _log_event(
                            connection,
                            target_race_id=int(intent["target_race_id"]),
                            intent_id=int(intent["id"]),
                            event_type="real_bet_error",
                            message=str(exc),
                            details={
                                "screenshot_path": getattr(exc, "screenshot_path", None),
                                "html_path": getattr(exc, "html_path", None),
                                **getattr(exc, "details", {}),
                            },
                        )
                    _log_session_event(
                        connection,
                        event_type="teleboat_error",
                        message=str(exc),
                        details={"race_id": target.race_id, "mode": mode},
                    )
                    errors += len(intents)

                connection.commit()
                if halted:
                    break

    return {
        "race_date": target_race_date,
        "processed": processed,
        "skipped": skipped,
        "errors": errors,
        "halted": halted,
    }


def run_cycle(
    runtime_root: Path = RUNTIME_ROOT,
    *,
    race_date: str | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    sync_result = sync_watchlists(runtime_root, race_date=race_date)
    evaluate_result = evaluate_targets(runtime_root, race_date=race_date, as_of=as_of)
    execute_result = execute_bets(runtime_root, race_date=race_date, as_of=as_of)
    return {
        "sync": sync_result,
        "evaluate": evaluate_result,
        "execute": execute_result,
    }


def auto_loop(
    runtime_root: Path = RUNTIME_ROOT,
    *,
    max_cycles: int | None = None,
) -> dict[str, Any]:
    initialize_runtime(runtime_root)
    existing_pid = _claim_auto_loop_pid(runtime_root)
    if existing_pid is not None:
        _log(runtime_root, f"auto-loop already running on PID {existing_pid}; exiting duplicate process")
        return {"cycles": 0, "stopped": True, "already_running": True, "existing_pid": existing_pid}

    cycles = 0
    try:
        while True:
            settings = load_settings(runtime_root)
            if not settings.get("system_running", False):
                _log(runtime_root, "system_running=false, exiting loop")
                break

            cycle_result = run_cycle(runtime_root)
            cycles += 1
            _log(runtime_root, f"cycle completed: {json.dumps(cycle_result, ensure_ascii=False)}")
            if max_cycles is not None and cycles >= max_cycles:
                _log(runtime_root, f"max_cycles={max_cycles} reached")
                break

            poll_seconds = max(5, int(settings.get("poll_seconds", 30)))
            _log(runtime_root, f"sleeping {poll_seconds}s until next cycle")
            remaining = poll_seconds
            while remaining > 0:
                chunk = min(5, remaining)
                time.sleep(chunk)
                remaining -= chunk
                if not load_settings(runtime_root).get("system_running", False):
                    _log(runtime_root, "stop requested while sleeping")
                    return {"cycles": cycles, "stopped": True}
    finally:
        _release_auto_loop_pid(runtime_root)

    return {"cycles": cycles, "stopped": False}


def latest_summary(runtime_root: Path = RUNTIME_ROOT) -> dict[str, Any]:
    initialize_runtime(runtime_root)
    with _connect_db(runtime_root) as connection:
        summary: dict[str, Any] = {"targets_by_status": {}, "intents_by_status": {}}
        for table, key_name in (("target_races", "targets_by_status"), ("bet_intents", "intents_by_status")):
            rows = connection.execute(
                f"SELECT status, COUNT(*) AS count FROM {table} GROUP BY status ORDER BY status"
            ).fetchall()
            summary[key_name] = {str(row["status"]): int(row["count"]) for row in rows}
        latest_target = connection.execute(
            """
            SELECT race_id, profile_id, status, last_reason, updated_at
            FROM target_races
            ORDER BY updated_at DESC, id DESC
            LIMIT 1
            """
        ).fetchone()
        if latest_target is not None:
            summary["latest_target"] = dict(latest_target)
        return summary


class _NullContext:
    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False
