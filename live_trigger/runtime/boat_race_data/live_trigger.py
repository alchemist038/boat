from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache
import json
from pathlib import Path
import time
from typing import Any

from boat_race_data.client import BoatRaceClient, FetchResult
from boat_race_data.constants import STADIUMS
from boat_race_data.parsers import parse_beforeinfo, parse_racelist, parse_result
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
    "meeting_title",
    "race_title",
    "deadline_time",
    "watch_start_time",
    "status",
    "pre_reason",
    "final_reason",
    "lane1_racer_id",
    "lane1_racer_name",
    "lane1_racer_class",
    "lane2_racer_class",
    "lane3_racer_class",
    "lane4_racer_class",
    "lane5_racer_class",
    "lane6_racer_class",
    "lane1_motor_no",
    "lane1_motor_place_rate",
    "lane1_motor_top3_rate",
    "lane1_exhibition_time",
    "lane1_exhibition_best_gap",
    "lane2_exhibition_time",
    "lane3_exhibition_time",
    "lane1_start_exhibition_st",
    "min_other_start_exhibition_st",
    "lane1_start_gap_over_rest",
    "beforeinfo_fetched_at",
]

CANONICAL_DUCKDB_PATH = Path(r"\\038INS\boat\data\silver\boat_race.duckdb")


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
    meeting_title_keywords_any: list[str]
    race_title_keywords_any: list[str]
    lane1_class_exclude: set[str]
    lane1_class_include: set[str]
    lane5_class_exclude: set[str]
    lane6_class_include: set[str]
    lane1_motor_place_rate_min: float | None
    lane1_motor_top3_rate_min: float | None
    lane1_exhibition_best_gap_max: float | None
    lane1_start_gap_over_rest_min: float | None
    lane1_exhibition_vs_lane2_max_gap: float | None
    lane1_exhibition_vs_lane3_max_gap: float | None

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
            meeting_title_keywords_any=[str(value) for value in pre_filters.get("meeting_title_keywords_any", [])],
            race_title_keywords_any=[str(value) for value in pre_filters.get("race_title_keywords_any", [])],
            lane1_class_exclude={str(value) for value in pre_filters.get("lane1_class_exclude", [])},
            lane1_class_include={str(value) for value in pre_filters.get("lane1_class_include", [])},
            lane5_class_exclude={str(value) for value in pre_filters.get("lane5_class_exclude", [])},
            lane6_class_include={str(value) for value in pre_filters.get("lane6_class_include", [])},
            lane1_motor_place_rate_min=_maybe_float(pre_filters.get("lane1_motor_place_rate_min")),
            lane1_motor_top3_rate_min=_maybe_float(pre_filters.get("lane1_motor_top3_rate_min")),
            lane1_exhibition_best_gap_max=_maybe_float(final_filters.get("lane1_exhibition_best_gap_max")),
            lane1_start_gap_over_rest_min=_maybe_float(final_filters.get("lane1_start_gap_over_rest_min")),
            lane1_exhibition_vs_lane2_max_gap=_maybe_float(final_filters.get("lane1_exhibition_vs_lane2_max_gap")),
            lane1_exhibition_vs_lane3_max_gap=_maybe_float(final_filters.get("lane1_exhibition_vs_lane3_max_gap")),
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
    if int(race_row.get("is_final_day", 0) or 0) == 1:
        return None
    lane1 = _entry_by_lane(entry_rows, 1)
    if lane1 is None:
        return None
    lane2 = _entry_by_lane(entry_rows, 2)
    lane3 = _entry_by_lane(entry_rows, 3)
    lane4 = _entry_by_lane(entry_rows, 4)
    proxy_reason = None
    if not _matches_title_filters(race_row, profile):
        proxy_reason = _c2_all_women_reason(entry_rows, profile)
        if proxy_reason is None:
            return None
    if lane1.get("racer_class", "") in profile.lane1_class_exclude:
        return None
    if profile.lane1_class_include and lane1.get("racer_class", "") not in profile.lane1_class_include:
        return None

    # lane5, lane6 check
    lane5 = _entry_by_lane(entry_rows, 5)
    lane6 = _entry_by_lane(entry_rows, 6)
    if lane5 and (lane5.get("racer_class", "") in profile.lane5_class_exclude):
        return None
    if lane6 and profile.lane6_class_include and (lane6.get("racer_class", "") not in profile.lane6_class_include):
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
        "meeting_title": race_row.get("meeting_title", ""),
        "race_title": race_row.get("race_title", ""),
        "deadline_time": deadline_time,
        "watch_start_time": compute_watch_start_time(
            str(race_row.get("race_date", "")),
            deadline_time,
            profile.watch_minutes_before_deadline,
        ),
        "status": "waiting_beforeinfo",
        "pre_reason": build_pre_reason(lane1, profile, proxy_reason=proxy_reason),
        "final_reason": "",
        "lane1_racer_id": lane1.get("racer_id", ""),
        "lane1_racer_name": lane1.get("racer_name", ""),
        "lane1_racer_class": lane1.get("racer_class", ""),
        "lane2_racer_class": "" if lane2 is None else lane2.get("racer_class", ""),
        "lane3_racer_class": "" if lane3 is None else lane3.get("racer_class", ""),
        "lane4_racer_class": "" if lane4 is None else lane4.get("racer_class", ""),
        "lane5_racer_class": "" if lane5 is None else lane5.get("racer_class", ""),
        "lane6_racer_class": "" if lane6 is None else lane6.get("racer_class", ""),
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
        refresh_after_seconds=20,
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
    row["min_other_start_exhibition_st"] = (
        "" if start_gap is None else _min_other_start_value(beforeinfo_rows, lane=1)
    )
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
        return {"changed": True, "ready": True}
    row["status"] = "filtered_out"
    row["final_reason"] = build_final_reason(best_gap, lane2_gap, lane3_gap, start_gap, profile, matched=False)
    return {"changed": True, "ready": False}


def build_pre_reason(
    lane1: dict[str, object],
    profile: TriggerProfile,
    *,
    proxy_reason: str | None = None,
) -> str:
    parts: list[str] = []
    if proxy_reason:
        parts.append(proxy_reason)
    elif profile.meeting_title_keywords_any or profile.race_title_keywords_any:
        parts.append("title_proxy")
    parts.append(f"class={lane1.get('racer_class', '')}")
    if profile.lane1_motor_place_rate_min is not None:
        parts.append(f"motor_place>={profile.lane1_motor_place_rate_min:g}")
    if profile.lane1_motor_top3_rate_min is not None:
        parts.append(f"motor_top3>={profile.lane1_motor_top3_rate_min:g}")
    return ", ".join(parts)


def build_final_reason(
    best_gap: float | None,
    lane2_gap: float | None,
    lane3_gap: float | None,
    start_gap: float | None,
    profile: TriggerProfile,
    matched: bool = True,
) -> str:
    parts: list[str] = []
    if profile.lane1_exhibition_best_gap_max is not None:
        parts.append(
            _format_comparison(
                "lane1_best_gap",
                best_gap,
                profile.lane1_exhibition_best_gap_max,
                "<=" if matched else ">",
            )
        )
    if profile.lane1_exhibition_vs_lane2_max_gap is not None:
        parts.append(
            _format_comparison(
                "lane1_vs_lane2_gap",
                lane2_gap,
                profile.lane1_exhibition_vs_lane2_max_gap,
                "<=" if matched else ">",
            )
        )
    if profile.lane1_exhibition_vs_lane3_max_gap is not None:
        parts.append(
            _format_comparison(
                "lane1_vs_lane3_gap",
                lane3_gap,
                profile.lane1_exhibition_vs_lane3_max_gap,
                "<=" if matched else ">",
            )
        )
    if profile.lane1_start_gap_over_rest_min is not None:
        parts.append(
            _format_comparison(
                "lane1_start_gap_over_rest",
                start_gap,
                profile.lane1_start_gap_over_rest_min,
                ">=" if matched else "<",
            )
        )
    return ", ".join(part for part in parts if part) or "beforeinfo ready"


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


def compute_lane_gap(beforeinfo_rows: list[dict[str, object]], lane: int, reference_lane: int) -> float | None:
    lane_row = _entry_by_lane(beforeinfo_rows, lane)
    ref_row = _entry_by_lane(beforeinfo_rows, reference_lane)
    if lane_row is None or ref_row is None:
        return None
    lane_time = _maybe_float(lane_row.get("exhibition_time"))
    ref_time = _maybe_float(ref_row.get("exhibition_time"))
    if lane_time is None or ref_time is None:
        return None
    return lane_time - ref_time


def compute_start_gap_over_rest(beforeinfo_rows: list[dict[str, object]], lane: int) -> float | None:
    lane_row = _entry_by_lane(beforeinfo_rows, lane)
    if lane_row is None:
        return None
    lane_start = _maybe_float(lane_row.get("start_exhibition_st"))
    other_start = _min_other_start_value(beforeinfo_rows, lane=lane)
    if lane_start is None or other_start is None:
        return None
    return lane_start - other_start


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


def record_air_bets(ready_path: Path, log_path: Path, rows_with_results: list[dict[str, object]] = None) -> int:
    """ready.csv または引数から trigger_ready 行を抽出し、ログに追記する。"""
    target_rows = []
    if rows_with_results is not None:
        target_rows = [r for r in rows_with_results if r.get("status") == "trigger_ready"]
    elif ready_path.exists():
        ready_rows = read_watchlist(ready_path)
        target_rows = [r for r in ready_rows if r.get("status") == "trigger_ready"]
    
    if not target_rows:
        return 0

    log_fields = ["race_id", "race_date", "stadium_code", "race_no", "profile_id", "strategy_id", "result", "payout", "timestamp"]
    existing_keys = set()
    if log_path.exists():
        with log_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_keys.add((row["race_id"], row["profile_id"]))

    new_count = 0
    now_str = datetime.now().isoformat()
    ensure_dir(log_path.parent)
    is_new_file = not log_path.exists()
    
    with log_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=log_fields, extrasaction="ignore")
        if is_new_file:
            writer.writeheader()
        for r in target_rows:
            key = (str(r["race_id"]), str(r["profile_id"]))
            if key not in existing_keys:
                r["timestamp"] = now_str
                # Ensure result and payout exist
                r.setdefault("result", "")
                r.setdefault("payout", 0)
                writer.writerow(r)
                existing_keys.add(key)
                new_count += 1
    return new_count


def judge_air_bet(row: dict[str, object], client: BoatRaceClient, raw_root: Path) -> tuple[str, int]:
    """実際のレース結果を取得し、プロファイルに応じた勝敗 (win/lose) と払戻を返す。"""
    race_date = str(row.get("race_date", "")).replace("-", "")
    stadium_code = str(row.get("stadium_code", ""))
    race_no = int(row.get("race_no", 0))
    if not (race_date and stadium_code and race_no):
        return "lose", 0

    prefix = f"{stadium_code}_{race_no:02d}"
    raw_path = raw_root / "result" / race_date / f"{prefix}.html"
    result_url = client.build_race_url("result", race_date, stadium_code, race_no)
    fetch = _fetch_text_cached(
        client,
        result_url,
        raw_path,
    )
    result = parse_result(fetch.text or "", race_date, stadium_code, race_no, fetch.url, fetch.fetched_at)
    if result is None:
        # 結果ページの取得失敗やトップページ混入時は、キャッシュを信用せず一度だけ再取得する。
        fetch = client.fetch_text(result_url, raw_path)
        result = parse_result(fetch.text or "", race_date, stadium_code, race_no, fetch.url, fetch.fetched_at)
    if result is None:
        return "lose", 0

    profile_id = str(row.get("profile_id", "")).lower()
    is_win = False
    payout = 0

    if "125" in profile_id:
        # 1-2-5 判定
        if (result.get("first_place_lane") == 1 and 
            result.get("second_place_lane") == 2 and 
            result.get("third_place_lane") == 5):
            is_win = True
            payout = int(result.get("trifecta_payout") or 0)
    elif "c2" in profile_id:
        # 1着が 2 または 3 判定
        if result.get("first_place_lane") in (2, 3):
            is_win = True
            # C2 の払戻詳細は未定義だが、一旦 3連単全体払戻を使用
            payout = int(result.get("trifecta_payout") or 0)

    return ("win" if is_win else "lose"), payout


def _fetch_text_cached(
    client: BoatRaceClient,
    url: str,
    raw_path: Path,
    *,
    refresh_after_seconds: int | None = None,
) -> FetchResult:
    if raw_path.exists():
        if refresh_after_seconds is not None:
            age_seconds = time.time() - raw_path.stat().st_mtime
            if age_seconds > max(0, int(refresh_after_seconds)):
                return client.fetch_text(url, raw_path)
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


def _normalize_racer_id(value: object) -> str | None:
    if value in {"", None}:
        return None
    text = str(value).strip()
    return text or None


def _c2_all_women_reason(entry_rows: list[dict[str, object]], profile: TriggerProfile) -> str | None:
    if profile.strategy_id != "c2":
        return None

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


def _passes_min_filter(value: object, minimum: float | None) -> bool:
    if minimum is None:
        return True
    number = _maybe_float(value)
    return number is not None and number >= minimum


def _passes_max_filter(value: float | None, maximum: float | None) -> bool:
    if maximum is None:
        return True
    return value is not None and value <= maximum


def _passes_title_keyword_filter(text: object, keywords: list[str]) -> bool:
    if not keywords:
        return True
    haystack = str(text or "").lower()
    return any(keyword.lower() in haystack for keyword in keywords)


def _matches_title_filters(race_row: dict[str, object], profile: TriggerProfile) -> bool:
    meeting_ok = _passes_title_keyword_filter(race_row.get("meeting_title", ""), profile.meeting_title_keywords_any)
    race_ok = _passes_title_keyword_filter(race_row.get("race_title", ""), profile.race_title_keywords_any)
    return meeting_ok and race_ok


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


def _format_comparison(label: str, value: float | None, threshold: float, operator: str) -> str:
    if value is None:
        return f"{label}=NA"
    return f"{label}={value:.3f} {operator} {threshold:g}"


def _min_other_start_value(beforeinfo_rows: list[dict[str, object]], lane: int) -> float | None:
    values: list[float] = []
    for row in beforeinfo_rows:
        if int(row.get("lane", 0) or 0) == lane:
            continue
        number = _maybe_float(row.get("start_exhibition_st"))
        if number is not None:
            values.append(number)
    if not values:
        return None
    return min(values)


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


def get_air_bet_stats(log_path: Path) -> dict[str, dict[str, object]]:
    """Air Bet ログを集計し、全体および profile_id ごとの統計を返す。"""
    if not log_path.exists():
        return {}

    stats = {}
    
    def init_stat():
        return {
            "race_count": 0,
            "win_count": 0,
            "investment": 0,
            "payout": 0,
            "balance": 0,
            "win_rate": 0.0,
            "recovery_rate": 0.0
        }

    stats["TOTAL"] = init_stat()

    with log_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            res = row.get("result")
            if res not in ("win", "lose"):
                continue
            
            pid = row.get("profile_id", "unknown")
            if pid not in stats:
                stats[pid] = init_stat()
            
            payout_val = int(row.get("payout", 0) or 0)
            is_win = row.get("result") == "win"
            
            for key in ["TOTAL", pid]:
                stats[key]["race_count"] += 1
                stats[key]["investment"] += 100  # 固定100円
                stats[key]["payout"] += payout_val
                if is_win:
                    stats[key]["win_count"] += 1

    for key in stats:
        s = stats[key]
        if s["race_count"] > 0:
            s["win_rate"] = round(s["win_count"] / s["race_count"] * 100, 1)
            s["recovery_rate"] = round(s["payout"] / s["investment"] * 100, 1)
            s["balance"] = s["payout"] - s["investment"]

    return stats


def print_air_bet_stats(stats: dict[str, dict[str, object]]) -> None:
    """集計された成績をコンソールに表示する。"""
    if not stats:
        print("集計データがありません。")
        return

    # TOTAL を最初に表示
    if "TOTAL" in stats:
        s = stats["TOTAL"]
        print("■ TOTAL")
        print(f"・レース数: {s['race_count']}")
        print(f"・勝率: {s['win_rate']}%")
        print(f"・回収率: {s['recovery_rate']}%")
        print(f"・収支: {s['balance']}円")
        print()

    # 各プロファイルを順に表示
    for pid, s in stats.items():
        if pid == "TOTAL":
            continue
        print(f"■ {pid}")
        print(f"・レース数: {s['race_count']}")
        print(f"・勝率: {s['win_rate']}%")
        print(f"・回収率: {s['recovery_rate']}%")
        print(f"・収支: {s['balance']}円")
        print()


def process_air_bets_full_flow(
    ready_path: Path, 
    log_path: Path, 
    client: BoatRaceClient, 
    raw_root: Path
) -> None:
    """判定から表示までの一連の Air Bet 処理を一括実行する。"""
    if not ready_path.exists():
        return

    # 1. データの読み込み
    rows = read_watchlist(ready_path)
    ready_rows = [r for r in rows if r.get("status") == "trigger_ready"]
    if not ready_rows:
        return

    # 2. 的中判定の実行
    for r in ready_rows:
        try:
            res, payout = judge_air_bet(r, client, raw_root)
            r["result"] = res
            r["payout"] = payout
        except Exception as e:
            r["result"] = "skip"
            r["payout"] = 0
            print(f"Error judging {r.get('race_id')}: {e}")

    # 3. ログへの記録
    record_air_bets(ready_path, log_path, rows_with_results=ready_rows)

    # 4. 集計の実行
    stats = get_air_bet_stats(log_path)

    # 5. 結果の表示
    print_air_bet_stats(stats)


def run_air_bet_flow_cli(
    ready_path: Path, 
    log_path: Path, 
    raw_root: Path
) -> None:
    """BoatRaceClient を内部で生成し、Air Bet フローを一括実行する。"""
    from boat_race_data.constants import DEFAULT_TIMEOUT_SECONDS
    with BoatRaceClient(timeout_seconds=DEFAULT_TIMEOUT_SECONDS) as client:
        process_air_bets_full_flow(ready_path, log_path, client, raw_root)
