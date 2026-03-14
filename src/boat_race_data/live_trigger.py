from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from pathlib import Path
import time
from typing import Any

from boat_race_data.client import BoatRaceClient, FetchResult
from boat_race_data.constants import STADIUMS
from boat_race_data.parsers import parse_beforeinfo, parse_racelist
from boat_race_data.utils import ensure_dir

WATCHLIST_COLUMNS = [
    "box_id",
    "profile_id",
    "strategy_id",
    "race_id",
    "race_date",
    "stadium_code",
    "stadium_name",
    "race_no",
    "deadline_time",
    "watch_start_time",
    "status",
    "pre_reason",
    "final_reason",
    "lane1_racer_id",
    "lane1_racer_name",
    "lane1_racer_class",
    "lane1_motor_no",
    "lane1_motor_place_rate",
    "lane1_motor_top3_rate",
    "lane1_exhibition_time",
    "lane1_exhibition_best_gap",
    "beforeinfo_fetched_at",
]


@dataclass(slots=True)
class TriggerProfile:
    box_id: str
    profile_id: str
    strategy_id: str
    display_name: str
    description: str
    accent_color: str
    enabled: bool
    stadiums: list[str]
    watch_minutes_before_deadline: int
    lane1_class_exclude: set[str]
    lane1_motor_place_rate_min: float | None
    lane1_motor_top3_rate_min: float | None
    lane1_exhibition_best_gap_max: float | None

    @classmethod
    def from_dict(cls, payload: dict[str, Any], *, box_id: str = "") -> "TriggerProfile":
        pre_filters = payload.get("pre_filters", {})
        final_filters = payload.get("final_filters", {})
        return cls(
            box_id=str(payload.get("box_id", box_id)),
            profile_id=str(payload["profile_id"]),
            strategy_id=str(payload["strategy_id"]),
            display_name=str(payload.get("display_name", payload["profile_id"])),
            description=str(payload.get("description", "")),
            accent_color=str(payload.get("accent_color", "#165d5b")),
            enabled=bool(payload.get("enabled", True)),
            stadiums=[str(code) for code in payload.get("stadiums", [])],
            watch_minutes_before_deadline=int(payload.get("watch_minutes_before_deadline", 25)),
            lane1_class_exclude={str(value) for value in pre_filters.get("lane1_class_exclude", [])},
            lane1_motor_place_rate_min=_maybe_float(pre_filters.get("lane1_motor_place_rate_min")),
            lane1_motor_top3_rate_min=_maybe_float(pre_filters.get("lane1_motor_top3_rate_min")),
            lane1_exhibition_best_gap_max=_maybe_float(final_filters.get("lane1_exhibition_best_gap_max")),
        )


def load_trigger_profile(path: Path) -> TriggerProfile:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return TriggerProfile.from_dict(payload, box_id=_box_id_from_path(path))


def load_trigger_profiles(root: Path, *, include_disabled: bool = False) -> list[TriggerProfile]:
    profiles: list[TriggerProfile] = []
    for path in sorted(root.rglob("*.json")):
        if path.name == "box.json":
            continue
        if _is_template_profile(path):
            continue
        profile = load_trigger_profile(path)
        if include_disabled or profile.enabled:
            profiles.append(profile)
    return profiles


def build_watchlist(
    *,
    race_date: str,
    profile: TriggerProfile,
    output_path: Path,
    raw_root: Path,
    max_race_no: int,
    sleep_seconds: float,
    timeout_seconds: int,
) -> tuple[int, Path]:
    ensure_dir(output_path.parent)
    ensure_dir(raw_root)
    rows: list[dict[str, object]] = []
    with BoatRaceClient(timeout_seconds=timeout_seconds) as client:
        stadium_codes = profile.stadiums or client.discover_active_stadiums(race_date)
        for stadium_code in stadium_codes:
            for race_no in range(1, max_race_no + 1):
                prefix = f"{stadium_code}_{race_no:02d}"
                fetch = _fetch_text_cached(
                    client,
                    client.build_race_url("racelist", race_date, stadium_code, race_no),
                    raw_root / "racelist" / race_date / f"{prefix}.html",
                )
                race_row, entry_rows = parse_racelist(
                    fetch.text or "",
                    race_date,
                    stadium_code,
                    STADIUMS.get(stadium_code, ""),
                    race_no,
                    fetch.url,
                    fetch.fetched_at,
                )
                if race_row is None or not entry_rows:
                    continue
                candidate = build_watchlist_row(race_row, entry_rows, profile)
                if candidate is not None:
                    rows.append(candidate)
                time.sleep(sleep_seconds)
    write_watchlist(output_path, rows)
    return len(rows), output_path


def build_watchlist_for_profiles(
    *,
    race_date: str,
    profiles: list[TriggerProfile],
    output_path: Path,
    raw_root: Path,
    max_race_no: int,
    sleep_seconds: float,
    timeout_seconds: int,
) -> tuple[int, Path]:
    ensure_dir(output_path.parent)
    ensure_dir(raw_root)
    rows: list[dict[str, object]] = []
    with BoatRaceClient(timeout_seconds=timeout_seconds) as client:
        for profile in profiles:
            stadium_codes = profile.stadiums or client.discover_active_stadiums(race_date)
            for stadium_code in stadium_codes:
                for race_no in range(1, max_race_no + 1):
                    prefix = f"{stadium_code}_{race_no:02d}"
                    fetch = _fetch_text_cached(
                        client,
                        client.build_race_url("racelist", race_date, stadium_code, race_no),
                        raw_root / "racelist" / race_date / f"{prefix}.html",
                    )
                    race_row, entry_rows = parse_racelist(
                        fetch.text or "",
                        race_date,
                        stadium_code,
                        STADIUMS.get(stadium_code, ""),
                        race_no,
                        fetch.url,
                        fetch.fetched_at,
                    )
                    if race_row is None or not entry_rows:
                        continue
                    candidate = build_watchlist_row(race_row, entry_rows, profile)
                    if candidate is not None:
                        rows.append(candidate)
                    time.sleep(sleep_seconds)
    write_watchlist(output_path, rows)
    return len(rows), output_path


def resolve_watchlist(
    *,
    watchlist_path: Path,
    profile: TriggerProfile,
    raw_root: Path,
    ready_output_path: Path | None,
    sleep_seconds: float,
    timeout_seconds: int,
) -> tuple[int, int]:
    rows = read_watchlist(watchlist_path)
    ready_rows: list[dict[str, object]] = []
    changed_rows = 0
    with BoatRaceClient(timeout_seconds=timeout_seconds) as client:
        for row in rows:
            if row["status"] == "trigger_ready":
                ready_rows.append(row)
                continue
            result = enrich_watchlist_row_with_beforeinfo(row, profile, client, raw_root)
            if result["changed"]:
                changed_rows += 1
            if result["ready"]:
                ready_rows.append(row)
            time.sleep(sleep_seconds)
    write_watchlist(watchlist_path, rows)
    if ready_output_path is not None:
        ensure_dir(ready_output_path.parent)
        write_watchlist(ready_output_path, ready_rows)
    return changed_rows, len(ready_rows)


def resolve_watchlist_for_profiles(
    *,
    watchlist_path: Path,
    profiles: list[TriggerProfile],
    raw_root: Path,
    ready_output_path: Path | None,
    sleep_seconds: float,
    timeout_seconds: int,
) -> tuple[int, int]:
    rows = read_watchlist(watchlist_path)
    ready_rows: list[dict[str, object]] = []
    changed_rows = 0
    profile_map = {profile.profile_id: profile for profile in profiles}
    with BoatRaceClient(timeout_seconds=timeout_seconds) as client:
        for row in rows:
            if row["status"] == "trigger_ready":
                ready_rows.append(row)
                continue
            profile = profile_map.get(str(row["profile_id"]))
            if profile is None:
                row["status"] = "profile_missing"
                row["final_reason"] = "profile not found"
                changed_rows += 1
                continue
            result = enrich_watchlist_row_with_beforeinfo(row, profile, client, raw_root)
            if result["changed"]:
                changed_rows += 1
            if result["ready"]:
                ready_rows.append(row)
            time.sleep(sleep_seconds)
    write_watchlist(watchlist_path, rows)
    if ready_output_path is not None:
        ensure_dir(ready_output_path.parent)
        write_watchlist(ready_output_path, ready_rows)
    return changed_rows, len(ready_rows)


def build_watchlist_row(
    race_row: dict[str, object],
    entry_rows: list[dict[str, object]],
    profile: TriggerProfile,
) -> dict[str, object] | None:
    lane1 = _entry_by_lane(entry_rows, 1)
    if lane1 is None:
        return None
    if lane1.get("racer_class", "") in profile.lane1_class_exclude:
        return None
    if not _passes_min_filter(lane1.get("motor_place_rate"), profile.lane1_motor_place_rate_min):
        return None
    if not _passes_min_filter(lane1.get("motor_top3_rate"), profile.lane1_motor_top3_rate_min):
        return None

    deadline_time = str(race_row.get("deadline_time", ""))
    return {
        "box_id": profile.box_id,
        "profile_id": profile.profile_id,
        "strategy_id": profile.strategy_id,
        "race_id": race_row.get("race_id", ""),
        "race_date": race_row.get("race_date", ""),
        "stadium_code": race_row.get("stadium_code", ""),
        "stadium_name": race_row.get("stadium_name", ""),
        "race_no": race_row.get("race_no", ""),
        "deadline_time": deadline_time,
        "watch_start_time": compute_watch_start_time(
            str(race_row.get("race_date", "")),
            deadline_time,
            profile.watch_minutes_before_deadline,
        ),
        "status": "waiting_beforeinfo",
        "pre_reason": build_pre_reason(lane1, profile),
        "final_reason": "",
        "lane1_racer_id": lane1.get("racer_id", ""),
        "lane1_racer_name": lane1.get("racer_name", ""),
        "lane1_racer_class": lane1.get("racer_class", ""),
        "lane1_motor_no": lane1.get("motor_no", ""),
        "lane1_motor_place_rate": lane1.get("motor_place_rate", ""),
        "lane1_motor_top3_rate": lane1.get("motor_top3_rate", ""),
        "lane1_exhibition_time": "",
        "lane1_exhibition_best_gap": "",
        "beforeinfo_fetched_at": "",
    }


def enrich_watchlist_row_with_beforeinfo(
    row: dict[str, object],
    profile: TriggerProfile,
    client: BoatRaceClient,
    raw_root: Path,
) -> dict[str, bool]:
    race_date = str(row["race_date"]).replace("-", "")
    stadium_code = str(row["stadium_code"])
    race_no = int(row["race_no"])
    prefix = f"{stadium_code}_{race_no:02d}"
    fetch = _fetch_text_cached(
        client,
        client.build_race_url("beforeinfo", race_date, stadium_code, race_no),
        raw_root / "beforeinfo" / race_date / f"{prefix}.html",
    )
    beforeinfo_rows = parse_beforeinfo(
        fetch.text or "",
        race_date,
        stadium_code,
        race_no,
        fetch.url,
        fetch.fetched_at,
    )
    row["beforeinfo_fetched_at"] = fetch.fetched_at
    lane1 = _entry_by_lane(beforeinfo_rows, 1)
    if lane1 is None or lane1.get("exhibition_time") in ("", None):
        row["status"] = "waiting_beforeinfo"
        row["final_reason"] = "beforeinfo not ready"
        return {"changed": True, "ready": False}

    best_gap = compute_best_gap(beforeinfo_rows, lane=1)
    row["lane1_exhibition_time"] = lane1.get("exhibition_time", "")
    row["lane1_exhibition_best_gap"] = "" if best_gap is None else f"{best_gap:.3f}"
    if _passes_max_filter(best_gap, profile.lane1_exhibition_best_gap_max):
        row["status"] = "trigger_ready"
        row["final_reason"] = build_final_reason(best_gap, profile)
        return {"changed": True, "ready": True}
    row["status"] = "filtered_out"
    row["final_reason"] = build_final_reason(best_gap, profile, matched=False)
    return {"changed": True, "ready": False}


def build_pre_reason(lane1: dict[str, object], profile: TriggerProfile) -> str:
    parts = [f"class={lane1.get('racer_class', '')}"]
    if profile.lane1_motor_place_rate_min is not None:
        parts.append(f"motor_place>={profile.lane1_motor_place_rate_min:g}")
    if profile.lane1_motor_top3_rate_min is not None:
        parts.append(f"motor_top3>={profile.lane1_motor_top3_rate_min:g}")
    return ", ".join(parts)


def build_final_reason(best_gap: float | None, profile: TriggerProfile, matched: bool = True) -> str:
    if best_gap is None:
        return "no exhibition_time"
    comparator = "<=" if matched else ">"
    threshold = "" if profile.lane1_exhibition_best_gap_max is None else f"{profile.lane1_exhibition_best_gap_max:g}"
    return f"lane1_best_gap={best_gap:.3f} {comparator} {threshold}".strip()


def compute_watch_start_time(race_date_iso: str, deadline_time: str, watch_minutes_before_deadline: int) -> str:
    if not race_date_iso or not deadline_time:
        return ""
    deadline = datetime.strptime(f"{race_date_iso} {deadline_time}", "%Y-%m-%d %H:%M")
    watch_start = deadline - timedelta(minutes=watch_minutes_before_deadline)
    return watch_start.strftime("%Y-%m-%d %H:%M")


def compute_best_gap(beforeinfo_rows: list[dict[str, object]], lane: int) -> float | None:
    lane_row = _entry_by_lane(beforeinfo_rows, lane)
    if lane_row is None:
        return None
    lane_time = _maybe_float(lane_row.get("exhibition_time"))
    if lane_time is None:
        return None
    times = [_maybe_float(item.get("exhibition_time")) for item in beforeinfo_rows]
    valid_times = [value for value in times if value is not None]
    if not valid_times:
        return None
    return lane_time - min(valid_times)


def read_watchlist(path: Path) -> list[dict[str, object]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def write_watchlist(path: Path, rows: list[dict[str, object]]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=WATCHLIST_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in WATCHLIST_COLUMNS})


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


def _passes_min_filter(value: object, minimum: float | None) -> bool:
    if minimum is None:
        return True
    number = _maybe_float(value)
    return number is not None and number >= minimum


def _passes_max_filter(value: float | None, maximum: float | None) -> bool:
    if maximum is None:
        return value is not None
    return value is not None and value <= maximum


def _maybe_float(value: object) -> float | None:
    if value in ("", None):
        return None
    return float(value)


def _box_id_from_path(path: Path) -> str:
    parts = list(path.parts)
    if "boxes" in parts:
        index = parts.index("boxes")
        if index + 1 < len(parts):
            return parts[index + 1]
    return ""


def _is_template_profile(path: Path) -> bool:
    return _box_id_from_path(path) == "template"
