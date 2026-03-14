from __future__ import annotations

import re
import subprocess
from pathlib import Path

from boat_race_data.constants import STADIUMS
from boat_race_data.utils import clean_text, make_race_id, maybe_float, maybe_int, to_json_text

MBRACE_BASE_URL = "https://www1.mbrace.or.jp/od2"

_STADIUM_CODE_BY_NAME = {clean_text(name).replace(" ", ""): code for code, name in STADIUMS.items()}

_B_SECTION_RE = re.compile(
    r"^\u30dc\u30fc\u30c8\u30ec\u30fc\u30b9(?P<stadium_name>.+?) \d+\u6708 ?\d+\u65e5 "
    r"(?P<meeting_title>.+?) \u7b2c ?(?P<meeting_day_no>\d+)\u65e5$"
)
_B_RACE_RE = re.compile(
    r"^(?P<race_no>\d{1,2})R (?P<race_title>.+?) H(?P<distance_m>\d+)m "
    r"\u96fb\u8a71\u6295\u7968\u7de0\u5207\u4e88\u5b9a(?P<deadline_time>\d{2}:\d{2})$"
)
_K_SECTION_RE = re.compile(
    r"^\u7b2c ?(?P<meeting_day_no>\d+)\u65e5 \d{4}/ ?\d+/ ?\d+ \u30dc\u30fc\u30c8\u30ec\u30fc\u30b9(?P<stadium_name>.+)$"
)
_K_PAYOUT_RE = re.compile(
    r"^(?P<race_no>\d{1,2})R "
    r"(?P<trifecta_combo>\d-\d-\d)\s+(?P<trifecta_payout>\d+)\s+"
    r"(?P<trio_combo>\d-\d-\d)\s+(?P<trio_payout>\d+)\s+"
    r"(?P<exacta_combo>\d-\d)\s+(?P<exacta_payout>\d+)\s+"
    r"(?P<quinella_combo>\d-\d)\s+(?P<quinella_payout>\d+)$"
)
_K_RACE_RE = re.compile(
    r"^(?P<race_no>\d{1,2})R (?P<race_title>.+?) H(?P<distance_m>\d+)m "
    r"(?P<weather_condition>\S+) \u98a8 (?P<wind_direction>\S+) "
    r"(?P<wind_speed_m>\d+)m \u6ce2 (?P<wave_height_cm>\d+)cm$"
)
_RACE_TIME_RE = re.compile(r"^\d+\.\d+\.\d+$")
_START_VALUE_RE = re.compile(r"^(?P<status>[FL])?(?P<value>\d+\.\d+)$")
_K_SPECIAL_FINISH_CODES = {"F", "K0", "K1", "L0", "L1", "S0", "S1", "S2"}


def build_mbrace_lzh_url(kind: str, race_date: str) -> str:
    lower_kind = kind.lower()
    yyyymm = race_date[:6]
    yymmdd = race_date[2:]
    return f"{MBRACE_BASE_URL}/{kind.upper()}/{yyyymm}/{lower_kind}{yymmdd}.lzh"


def ensure_mbrace_text(lzh_path: Path) -> Path:
    txt_path = lzh_path.with_suffix(".TXT")
    if txt_path.exists():
        return txt_path
    subprocess.run(["tar", "-xf", lzh_path.name], cwd=lzh_path.parent, check=True, capture_output=True)
    return txt_path


def _normalize_grade_from_title(meeting_title: str) -> tuple[str, str]:
    title = clean_text(meeting_title)
    upper_title = title.upper()
    if "PG1" in upper_title or re.search(r"(^|[^A-Z])SG([^A-Z]|$)", upper_title):
        return "SG", "title"
    if any(keyword in title for keyword in ["クイーンズクライマックス", "グランプリ", "チャレンジカップ"]):
        return "SG", "title_heuristic"
    if "G2" in upper_title:
        return "G2", "title"
    if "G1" in upper_title:
        return "G1", "title"
    if "G3" in upper_title:
        return "G3", "title"
    if any(keyword in title for keyword in ["周年記念", "地区選手権"]):
        return "G1", "title_heuristic"
    return "一般", "title"


def _section_starts(lines: list[str], pattern: re.Pattern[str]) -> list[int]:
    return [index for index, line in enumerate(lines) if pattern.match(clean_text(line))]


def _race_date_iso(race_date: str) -> str:
    return f"{race_date[:4]}-{race_date[4:6]}-{race_date[6:8]}"


def _stadium_code(stadium_name: str) -> str | None:
    return _STADIUM_CODE_BY_NAME.get(clean_text(stadium_name).replace(" ", ""))


def _extract_meeting_title(section: list[str], fallback: str) -> str:
    best = clean_text(fallback)
    for line in section[:10]:
        cleaned = clean_text(line)
        if not cleaned:
            continue
        if cleaned.startswith("***") or "番組表" in cleaned:
            continue
        if cleaned.startswith("第 ") and "年" in cleaned:
            continue
        if cleaned.startswith("ボートレース"):
            continue
        if len(cleaned) > len(best):
            best = cleaned
    return best


def _parse_b_entry_line(line: str) -> dict[str, object] | None:
    if not line or not line[0].isdigit() or len(line) < 58:
        return None
    lane = maybe_int(line[0:1])
    racer_id = maybe_int(line[2:6])
    racer_name = clean_text(line[6:10]).replace(" ", "")
    age = maybe_int(line[10:12])
    branch = clean_text(line[12:14])
    weight_kg = maybe_float(line[14:16])
    racer_class = clean_text(line[16:18])
    national_win_rate = maybe_float(line[19:23])
    national_place_rate = maybe_float(line[24:29])
    local_win_rate = maybe_float(line[30:34])
    local_place_rate = maybe_float(line[35:40])
    motor_no = maybe_int(line[41:44])
    motor_place_rate = maybe_float(line[44:49])
    boat_no = maybe_int(line[49:52])
    boat_place_rate = maybe_float(line[53:58])
    suffix = clean_text(line[58:])
    quick_view_race_no = None
    if suffix:
        tail = suffix.split(" ")[-1]
        tail_value = maybe_int(tail)
        if tail_value is not None and 1 <= tail_value <= 12:
            quick_view_race_no = tail_value
    if lane is None or racer_id is None or not racer_name:
        return None
    return {
        "lane": lane,
        "racer_id": racer_id,
        "racer_name": racer_name,
        "racer_class": racer_class,
        "branch": branch,
        "age": age,
        "weight_kg": weight_kg,
        "national_win_rate": national_win_rate,
        "national_place_rate": national_place_rate,
        "local_win_rate": local_win_rate,
        "local_place_rate": local_place_rate,
        "motor_no": motor_no,
        "motor_place_rate": motor_place_rate,
        "boat_no": boat_no,
        "boat_place_rate": boat_place_rate,
        "quick_view_race_no": quick_view_race_no,
    }


def parse_mbrace_b_schedule(
    text: str,
    race_date: str,
    source_url: str,
    fetched_at: str,
) -> dict[str, list[dict[str, object]]]:
    race_date_iso = _race_date_iso(race_date)
    lines = text.splitlines()
    starts = _section_starts(lines, _B_SECTION_RE)

    races: list[dict[str, object]] = []
    entries: list[dict[str, object]] = []
    race_meta: list[dict[str, object]] = []

    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(lines)
        section = lines[start:end]
        header_match = _B_SECTION_RE.match(clean_text(section[0]))
        if header_match is None:
            continue

        stadium_name = clean_text(header_match.group("stadium_name")).replace(" ", "")
        stadium_code = _stadium_code(stadium_name)
        if stadium_code is None:
            continue
        meeting_title = _extract_meeting_title(section, header_match.group("meeting_title"))
        meeting_day_no = maybe_int(header_match.group("meeting_day_no"))
        meeting_day_label = f"第{meeting_day_no}日" if meeting_day_no is not None else ""
        grade, grade_raw = _normalize_grade_from_title(meeting_title)

        row_index = 0
        while row_index < len(section):
            race_match = _B_RACE_RE.match(clean_text(section[row_index]))
            if race_match is None:
                row_index += 1
                continue

            race_no = int(race_match.group("race_no"))
            race_id = make_race_id(race_date, stadium_code, race_no)
            race_title = clean_text(race_match.group("race_title"))
            distance_m = maybe_int(race_match.group("distance_m"))
            deadline_time = clean_text(race_match.group("deadline_time"))

            races.append(
                {
                    "race_id": race_id,
                    "race_date": race_date_iso,
                    "stadium_code": stadium_code,
                    "stadium_name": stadium_name,
                    "race_no": race_no,
                    "meeting_title": meeting_title,
                    "race_title": race_title,
                    "distance_m": distance_m,
                    "deadline_time": deadline_time,
                    "source_url": source_url,
                    "fetched_at": fetched_at,
                }
            )
            race_meta.append(
                {
                    "race_id": race_id,
                    "race_date": race_date_iso,
                    "stadium_code": stadium_code,
                    "meeting_title": meeting_title,
                    "grade": grade,
                    "grade_raw": grade_raw,
                    "meeting_day_no": meeting_day_no,
                    "meeting_day_label": meeting_day_label,
                    "is_final_day": 0,
                    "source_url": source_url,
                    "fetched_at": fetched_at,
                }
            )

            entry_index = row_index + 1
            while entry_index < len(section):
                cleaned = clean_text(section[entry_index])
                if not cleaned:
                    if entries and entries[-1]["race_id"] == race_id:
                        break
                    entry_index += 1
                    continue
                if _B_RACE_RE.match(cleaned):
                    break
                entry_values = _parse_b_entry_line(section[entry_index])
                if entry_values is not None:
                    entries.append(
                        {
                            "race_id": race_id,
                            "race_date": race_date_iso,
                            "stadium_code": stadium_code,
                            "race_no": race_no,
                            "lane": entry_values["lane"],
                            "racer_id": entry_values["racer_id"],
                            "racer_name": entry_values["racer_name"],
                            "racer_class": entry_values["racer_class"],
                            "branch": entry_values["branch"],
                            "hometown": "",
                            "age": entry_values["age"],
                            "weight_kg": entry_values["weight_kg"],
                            "photo_url": "",
                            "f_count": None,
                            "l_count": None,
                            "avg_start_timing": None,
                            "national_win_rate": entry_values["national_win_rate"],
                            "national_place_rate": entry_values["national_place_rate"],
                            "national_top3_rate": None,
                            "local_win_rate": entry_values["local_win_rate"],
                            "local_place_rate": entry_values["local_place_rate"],
                            "local_top3_rate": None,
                            "motor_no": entry_values["motor_no"],
                            "motor_place_rate": entry_values["motor_place_rate"],
                            "motor_top3_rate": None,
                            "boat_no": entry_values["boat_no"],
                            "boat_place_rate": entry_values["boat_place_rate"],
                            "boat_top3_rate": None,
                            "quick_view_race_no": entry_values["quick_view_race_no"],
                            "source_url": source_url,
                            "fetched_at": fetched_at,
                        }
                    )
                entry_index += 1
            row_index = entry_index

    return {
        "races": races,
        "entries": entries,
        "race_meta": race_meta,
    }


def _parse_start_value(value: str) -> tuple[float | None, str]:
    match = _START_VALUE_RE.match(value)
    if match is None:
        return maybe_float(value), ""
    return maybe_float(match.group("value")), clean_text(match.group("status"))


def _parse_k_lane_row_tokens(tokens: list[str]) -> dict[str, object]:
    race_time = ""
    tail_offset = 0

    if tokens and _RACE_TIME_RE.match(tokens[-1]):
        race_time = tokens[-1]
        tail_offset = 1
    elif len(tokens) >= 2 and tokens[-2:] == [".", "."]:
        # 5着/6着行では race_time 自体は空でも、末尾プレースホルダの列は残っている。
        tail_offset = 2

    start_token = tokens[-1 - tail_offset]
    course_entry = tokens[-2 - tail_offset]
    exhibition_time = tokens[-3 - tail_offset]
    boat_no = tokens[-4 - tail_offset]
    motor_no = tokens[-5 - tail_offset]
    racer_name = "".join(tokens[3 : len(tokens) - (5 + tail_offset)])

    return {
        "race_time": race_time,
        "start_token": start_token,
        "course_entry": course_entry,
        "exhibition_time": exhibition_time,
        "boat_no": boat_no,
        "motor_no": motor_no,
        "racer_name": racer_name,
    }


def _is_k_lane_row_tokens(tokens: list[str]) -> bool:
    if len(tokens) < 9:
        return False
    if not tokens[1].isdigit() or not tokens[2].isdigit():
        return False
    finish_token = clean_text(tokens[0]).upper()
    return finish_token.isdigit() or finish_token in _K_SPECIAL_FINISH_CODES


def _parse_k_finish_token(value: str) -> int | None:
    finish_token = clean_text(value)
    if finish_token.isdigit():
        return int(finish_token)
    return None


def parse_mbrace_k_results(
    text: str,
    race_date: str,
    source_url: str,
    fetched_at: str,
) -> dict[str, list[dict[str, object]]]:
    race_date_iso = _race_date_iso(race_date)
    lines = text.splitlines()
    starts = _section_starts(lines, _K_SECTION_RE)

    results: list[dict[str, object]] = []
    beforeinfo_entries: list[dict[str, object]] = []

    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(lines)
        section = lines[start:end]
        section_match = _K_SECTION_RE.match(clean_text(section[0]))
        if section_match is None:
            continue

        stadium_name = clean_text(section_match.group("stadium_name")).replace(" ", "")
        stadium_code = _stadium_code(stadium_name)
        if stadium_code is None:
            continue

        payout_map: dict[int, dict[str, object]] = {}
        for line in section:
            payout_match = _K_PAYOUT_RE.match(clean_text(line))
            if payout_match is None:
                continue
            values = payout_match.groupdict()
            payout_map[int(values["race_no"])] = {
                "exacta_combo": values["exacta_combo"],
                "exacta_payout": maybe_int(values["exacta_payout"]),
                "quinella_combo": values["quinella_combo"],
                "quinella_payout": maybe_int(values["quinella_payout"]),
                "trifecta_combo": values["trifecta_combo"],
                "trifecta_payout": maybe_int(values["trifecta_payout"]),
                "trio_combo": values["trio_combo"],
                "trio_payout": maybe_int(values["trio_payout"]),
            }

        row_index = 0
        while row_index < len(section):
            race_match = _K_RACE_RE.match(clean_text(section[row_index]))
            if race_match is None:
                row_index += 1
                continue

            race_no = int(race_match.group("race_no"))
            race_id = make_race_id(race_date, stadium_code, race_no)
            weather_condition = clean_text(race_match.group("weather_condition"))
            wind_speed_m = maybe_int(race_match.group("wind_speed_m"))
            wave_height_cm = maybe_int(race_match.group("wave_height_cm"))
            winning_technique = ""
            if row_index + 1 < len(section):
                header_tokens = clean_text(section[row_index + 1]).split(" ")
                winning_technique = header_tokens[-1] if header_tokens else ""

            lane_rows: list[dict[str, object]] = []
            entry_index = row_index + 2
            while entry_index < len(section):
                cleaned = clean_text(section[entry_index])
                if not cleaned:
                    if lane_rows:
                        break
                    entry_index += 1
                    continue
                if _K_RACE_RE.match(cleaned):
                    break
                tokens = cleaned.split(" ")
                # Some lower-order rows use non-numeric finish codes like F/S0/K1.
                # Those rows still carry valid lane/beforeinfo columns and should not be skipped.
                if _is_k_lane_row_tokens(tokens):
                    parsed_row = _parse_k_lane_row_tokens(tokens)
                    race_time = parsed_row["race_time"]
                    start_token = parsed_row["start_token"]
                    course_entry = parsed_row["course_entry"]
                    exhibition_time = parsed_row["exhibition_time"]
                    boat_no = parsed_row["boat_no"]
                    motor_no = parsed_row["motor_no"]
                    racer_name = parsed_row["racer_name"]
                    start_value, start_status = _parse_start_value(start_token)
                    lane_rows.append(
                        {
                            "finish": _parse_k_finish_token(tokens[0]),
                            "lane": maybe_int(tokens[1]),
                            "racer_id": maybe_int(tokens[2]),
                            "racer_name": racer_name,
                            "motor_no": maybe_int(motor_no),
                            "boat_no": maybe_int(boat_no),
                            "exhibition_time": maybe_float(exhibition_time),
                            "course_entry": maybe_int(course_entry),
                            "start_timing": start_value,
                            "start_status": start_status,
                            "race_time": race_time,
                        }
                    )
                entry_index += 1

            if len(lane_rows) < 3:
                row_index = entry_index
                continue

            ordered = sorted(lane_rows, key=lambda item: item["finish"] or 999)
            finish_lanes = [item["lane"] for item in ordered]
            while len(finish_lanes) < 6:
                finish_lanes.append(None)
            payout = payout_map.get(race_no, {})
            start_timing_json = {
                str(item["lane"]): {"value": item["start_timing"], "status": item["start_status"]} for item in lane_rows
            }
            finish_order_json = [{"finish": item["finish"], "lane": item["lane"]} for item in ordered]
            payouts_json = {
                "exacta": {"combo": payout.get("exacta_combo"), "payout": payout.get("exacta_payout")},
                "quinella": {"combo": payout.get("quinella_combo"), "payout": payout.get("quinella_payout")},
                "trifecta": {"combo": payout.get("trifecta_combo"), "payout": payout.get("trifecta_payout")},
                "trio": {"combo": payout.get("trio_combo"), "payout": payout.get("trio_payout")},
            }

            results.append(
                {
                    "race_id": race_id,
                    "race_date": race_date_iso,
                    "stadium_code": stadium_code,
                    "race_no": race_no,
                    "first_place_lane": finish_lanes[0],
                    "second_place_lane": finish_lanes[1],
                    "third_place_lane": finish_lanes[2],
                    "fourth_place_lane": finish_lanes[3],
                    "fifth_place_lane": finish_lanes[4],
                    "sixth_place_lane": finish_lanes[5],
                    "finish_order_json": to_json_text(finish_order_json),
                    "start_timing_json": to_json_text(start_timing_json),
                    "payouts_json": to_json_text(payouts_json),
                    "refund_info": "",
                    "winning_technique": winning_technique,
                    "note": "",
                    "weather_condition": weather_condition,
                    "weather_temp_c": None,
                    "wind_speed_m": wind_speed_m,
                    "wind_direction_code": None,
                    "water_temp_c": None,
                    "wave_height_cm": wave_height_cm,
                    "exacta_combo": payout.get("exacta_combo"),
                    "exacta_payout": payout.get("exacta_payout"),
                    "quinella_combo": payout.get("quinella_combo"),
                    "quinella_payout": payout.get("quinella_payout"),
                    "trifecta_combo": payout.get("trifecta_combo"),
                    "trifecta_payout": payout.get("trifecta_payout"),
                    "trio_combo": payout.get("trio_combo"),
                    "trio_payout": payout.get("trio_payout"),
                    "source_url": source_url,
                    "fetched_at": fetched_at,
                }
            )

            for item in lane_rows:
                beforeinfo_entries.append(
                    {
                        "race_id": race_id,
                        "race_date": race_date_iso,
                        "stadium_code": stadium_code,
                        "race_no": race_no,
                        "lane": item["lane"],
                        "racer_id": item["racer_id"],
                        "racer_name": item["racer_name"],
                        "weight_kg_before": None,
                        "adjust_weight_kg": None,
                        "exhibition_time": item["exhibition_time"],
                        "tilt": None,
                        "course_entry": item["course_entry"],
                        "start_exhibition_st": item["start_timing"],
                        "start_exhibition_status": item["start_status"],
                        "weather_condition": weather_condition,
                        "weather_temp_c": None,
                        "wind_speed_m": wind_speed_m,
                        "wind_direction_code": None,
                        "water_temp_c": None,
                        "wave_height_cm": wave_height_cm,
                        "source_url": source_url,
                        "fetched_at": fetched_at,
                    }
                )

            row_index = entry_index

    return {
        "results": results,
        "beforeinfo_entries": beforeinfo_entries,
    }
