from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Callable

from bs4 import BeautifulSoup

from boat_race_data.client import absolute_url
from boat_race_data.constants import TERM_LAYOUT_URL
from boat_race_data.utils import (
    clean_text,
    era_date_to_iso,
    has_no_data,
    make_race_id,
    maybe_float,
    maybe_int,
    parse_age_weight,
    parse_f_l_st,
    parse_race_title,
    parse_three_rates,
    parse_two_rates_with_number,
    scaled_int,
    to_json_text,
)


def _deadline_for_race(soup: BeautifulSoup, race_no: int) -> str:
    tables = soup.find_all("table")
    if not tables:
        return ""
    rows = tables[0].find_all("tr")
    if len(rows) < 2:
        return ""
    cells = [clean_text(cell.get_text(" ", strip=True)) for cell in rows[1].find_all(["th", "td"])]
    if len(cells) <= race_no:
        return ""
    return cells[race_no]


def _parse_weather_fields(soup: BeautifulSoup) -> dict[str, object]:
    weather_condition = ""
    weather_temp_c = None
    wind_speed_m = None
    wind_direction_code = None
    water_temp_c = None
    wave_height_cm = None
    weather_root = soup.select_one("div.weather1")
    if weather_root:
        condition_node = weather_root.select_one("div.weather1_bodyUnit.is-weather div.weather1_bodyUnitLabel")
        weather_condition = clean_text(condition_node.get_text(" ", strip=True)) if condition_node else ""

        temp_node = weather_root.select_one("div.weather1_bodyUnit.is-direction span.weather1_bodyUnitLabelData")
        wind_node = weather_root.select_one("div.weather1_bodyUnit.is-wind span.weather1_bodyUnitLabelData")
        water_node = weather_root.select_one(
            "div.weather1_bodyUnit.is-waterTemperature span.weather1_bodyUnitLabelData"
        )
        wave_node = weather_root.select_one("div.weather1_bodyUnit.is-wave span.weather1_bodyUnitLabelData")
        weather_temp_c = maybe_float(temp_node.get_text(" ", strip=True)) if temp_node else None
        wind_speed_m = maybe_int(wind_node.get_text(" ", strip=True)) if wind_node else None
        water_temp_c = maybe_float(water_node.get_text(" ", strip=True)) if water_node else None
        wave_height_cm = maybe_int(wave_node.get_text(" ", strip=True)) if wave_node else None

        wind_dir_image = weather_root.select_one("div.weather1_bodyUnit.is-windDirection p")
        if wind_dir_image:
            for class_name in wind_dir_image.get("class", []):
                match = re.fullmatch(r"is-wind(\d+)", class_name)
                if match:
                    wind_direction_code = int(match.group(1))
                    break

    return {
        "weather_condition": weather_condition,
        "weather_temp_c": weather_temp_c,
        "wind_speed_m": wind_speed_m,
        "wind_direction_code": wind_direction_code,
        "water_temp_c": water_temp_c,
        "wave_height_cm": wave_height_cm,
    }


def _normalize_grade(meeting_title: str, heading_classes: list[str]) -> tuple[str, str]:
    title = clean_text(meeting_title)
    upper_title = title.upper()
    grade_raw = ""
    for class_name in heading_classes:
        if class_name.startswith("is-"):
            grade_raw = class_name
            break

    if "PG1" in upper_title or re.search(r"(^|[^A-Z])SG([^A-Z]|$)", upper_title):
        return "SG", grade_raw
    if "G2" in upper_title:
        return "G2", grade_raw
    if "G1" in upper_title:
        return "G1", grade_raw
    if "G3" in upper_title:
        return "G3", grade_raw

    if any(class_name.startswith("is-SG") for class_name in heading_classes):
        return "SG", grade_raw
    if any(class_name.startswith("is-G1") for class_name in heading_classes):
        return "G1", grade_raw
    if any(class_name.startswith("is-G3") for class_name in heading_classes):
        return "G3", grade_raw
    return "一般", grade_raw


def _parse_meeting_day_info(soup: BeautifulSoup) -> tuple[int | None, str, int]:
    tab_items = soup.select("div.tab2 ul.tab2_tabs li")
    active_item = soup.select_one("div.tab2 ul.tab2_tabs li.is-active2")
    labels: list[str] = []
    active_index = -1
    for index, item in enumerate(tab_items):
        label_node = item.select_one(".tab2_inner span")
        label = clean_text(label_node.get_text(" ", strip=True)) if label_node else ""
        labels.append(label)
        if item is active_item:
            active_index = index

    active_label = labels[active_index] if 0 <= active_index < len(labels) else ""
    numbered_labels = [label for label in labels if label and label != "順延"]

    if active_label == "初日":
        return 1, active_label, 0
    if active_label == "最終日":
        return len(numbered_labels) or None, active_label, 1

    label_day = maybe_int(active_label)
    if label_day is not None and "日目" in active_label:
        return label_day, active_label, 0

    if active_index >= 0:
        day_no = 0
        for index, label in enumerate(labels):
            if label and label != "順延":
                day_no += 1
            if index == active_index:
                return (day_no or None), active_label, 0
    return None, active_label, 0


def parse_race_meta(
    html: str,
    race_date: str,
    stadium_code: str,
    race_no: int,
    source_url: str,
    fetched_at: str,
) -> dict[str, object] | None:
    if has_no_data(html):
        return None

    soup = BeautifulSoup(html, "html.parser")
    race_id = make_race_id(race_date, stadium_code, race_no)
    race_date_iso = f"{race_date[:4]}-{race_date[4:6]}-{race_date[6:8]}"
    title_node = soup.select_one("h2.heading2_titleName")
    meeting_title = clean_text(title_node.get_text(" ", strip=True)) if title_node else ""
    heading_node = soup.select_one("div.heading2_title")
    heading_classes = heading_node.get("class", []) if heading_node else []
    grade, grade_raw = _normalize_grade(meeting_title, heading_classes)
    meeting_day_no, meeting_day_label, is_final_day = _parse_meeting_day_info(soup)
    return {
        "race_id": race_id,
        "race_date": race_date_iso,
        "stadium_code": stadium_code,
        "meeting_title": meeting_title,
        "grade": grade,
        "grade_raw": grade_raw,
        "meeting_day_no": meeting_day_no,
        "meeting_day_label": meeting_day_label,
        "is_final_day": is_final_day,
        "source_url": source_url,
        "fetched_at": fetched_at,
    }


def parse_racelist(
    html: str,
    race_date: str,
    stadium_code: str,
    stadium_name: str,
    race_no: int,
    source_url: str,
    fetched_at: str,
) -> tuple[dict[str, object] | None, list[dict[str, object]]]:
    if has_no_data(html):
        return None, []

    soup = BeautifulSoup(html, "html.parser")
    race_id = make_race_id(race_date, stadium_code, race_no)
    meeting_title = clean_text(soup.select_one("h2.heading2_titleName").get_text(" ", strip=True))
    race_title_text = clean_text(soup.select_one("h3.title16_titleDetail__add2020").get_text(" ", strip=True))
    race_title, distance_m = parse_race_title(race_title_text)
    race_date_iso = f"{race_date[:4]}-{race_date[4:6]}-{race_date[6:8]}"
    meeting_day_no, meeting_day_label, is_final_day = _parse_meeting_day_info(soup)

    race = {
        "race_id": race_id,
        "race_date": race_date_iso,
        "stadium_code": stadium_code,
        "stadium_name": stadium_name,
        "race_no": race_no,
        "meeting_title": meeting_title,
        "race_title": race_title,
        "distance_m": distance_m,
        "meeting_day_no": meeting_day_no,
        "meeting_day_label": meeting_day_label,
        "is_final_day": is_final_day,
        "deadline_time": _deadline_for_race(soup, race_no),
        "source_url": source_url,
        "fetched_at": fetched_at,
    }

    tables = soup.find_all("table")
    if len(tables) < 2:
        return race, []

    entries: list[dict[str, object]] = []
    for tbody in tables[1].find_all("tbody"):
        rows = tbody.find_all("tr")
        if not rows:
            continue
        cells = rows[0].find_all("td")
        if len(cells) < 9:
            continue

        lane = maybe_int(cells[0].get_text(" ", strip=True))
        photo = cells[1].find("img")
        photo_url = absolute_url(photo["src"]) if photo and photo.get("src") else ""

        info_divs = cells[2].find_all("div")
        basic_text = clean_text(info_divs[0].get_text(" ", strip=True)) if len(info_divs) > 0 else ""
        name_text = clean_text(info_divs[1].get_text(" ", strip=True)) if len(info_divs) > 1 else ""
        detail_lines = list(info_divs[2].stripped_strings) if len(info_divs) > 2 else []
        branch_hometown = clean_text(detail_lines[0]) if detail_lines else ""
        age_weight = clean_text(detail_lines[1]) if len(detail_lines) > 1 else ""

        basic_parts = [clean_text(part) for part in basic_text.split("/") if clean_text(part)]
        racer_id = maybe_int(basic_parts[0]) if basic_parts else None
        racer_class = basic_parts[1] if len(basic_parts) > 1 else ""

        branch, hometown = ("", "")
        if "/" in branch_hometown:
            branch, hometown = [clean_text(part) for part in branch_hometown.split("/", 1)]

        age, weight = parse_age_weight(age_weight)
        f_count, l_count, avg_start_timing = parse_f_l_st(cells[3].get_text("\n", strip=True))
        national_win_rate, national_place_rate, national_top3_rate = parse_three_rates(
            cells[4].get_text("\n", strip=True)
        )
        local_win_rate, local_place_rate, local_top3_rate = parse_three_rates(
            cells[5].get_text("\n", strip=True)
        )
        motor_no, motor_place_rate, motor_top3_rate = parse_two_rates_with_number(
            cells[6].get_text("\n", strip=True)
        )
        boat_no, boat_place_rate, boat_top3_rate = parse_two_rates_with_number(
            cells[7].get_text("\n", strip=True)
        )
        quick_view_race_no = maybe_int(clean_text(cells[-1].get_text(" ", strip=True)).replace("R", ""))

        entries.append(
            {
                "race_id": race_id,
                "race_date": race_date_iso,
                "stadium_code": stadium_code,
                "race_no": race_no,
                "lane": lane,
                "racer_id": racer_id,
                "racer_name": name_text,
                "racer_class": racer_class,
                "branch": branch,
                "hometown": hometown,
                "age": age,
                "weight_kg": weight,
                "photo_url": photo_url,
                "f_count": f_count,
                "l_count": l_count,
                "avg_start_timing": avg_start_timing,
                "national_win_rate": national_win_rate,
                "national_place_rate": national_place_rate,
                "national_top3_rate": national_top3_rate,
                "local_win_rate": local_win_rate,
                "local_place_rate": local_place_rate,
                "local_top3_rate": local_top3_rate,
                "motor_no": motor_no,
                "motor_place_rate": motor_place_rate,
                "motor_top3_rate": motor_top3_rate,
                "boat_no": boat_no,
                "boat_place_rate": boat_place_rate,
                "boat_top3_rate": boat_top3_rate,
                "quick_view_race_no": quick_view_race_no,
                "source_url": source_url,
                "fetched_at": fetched_at,
            }
        )

    return race, entries


def _find_beforeinfo_tables(soup: BeautifulSoup) -> tuple[object | None, object | None]:
    entry_table = None
    start_table = None
    for table in soup.find_all("table"):
        header_texts = [clean_text(cell.get_text(" ", strip=True)) for cell in table.find_all("th")]
        if not header_texts:
            continue
        if "展示 タイム" in header_texts and entry_table is None:
            entry_table = table
        if header_texts[0] == "スタート展示" and start_table is None:
            start_table = table
    return entry_table, start_table


def _extract_racer_id_from_href(href: str) -> int | None:
    match = re.search(r"toban=(\d+)", href)
    return int(match.group(1)) if match else None


def _parse_start_exhibition_value(value: str) -> tuple[float | None, str]:
    text = clean_text(value).upper()
    if not text:
        return None, ""
    status = ""
    if text[0] in {"F", "L"}:
        status = text[0]
        text = text[1:]
    if text.startswith("."):
        text = f"0{text}"
    return maybe_float(text), status


def parse_beforeinfo(
    html: str,
    race_date: str,
    stadium_code: str,
    race_no: int,
    source_url: str,
    fetched_at: str,
) -> list[dict[str, object]]:
    if has_no_data(html):
        return []

    soup = BeautifulSoup(html, "html.parser")
    entry_table, start_table = _find_beforeinfo_tables(soup)
    if entry_table is None:
        return []

    weather = _parse_weather_fields(soup)
    race_id = make_race_id(race_date, stadium_code, race_no)
    race_date_iso = f"{race_date[:4]}-{race_date[4:6]}-{race_date[6:8]}"

    start_map: dict[int, dict[str, object]] = {}
    if start_table is not None:
        for course_entry, tr in enumerate(start_table.select("tbody tr"), start=1):
            lane_node = tr.select_one("span.table1_boatImage1Number")
            start_node = tr.select_one("span.table1_boatImage1Time")
            lane = maybe_int(lane_node.get_text(" ", strip=True)) if lane_node else None
            start_value, start_status = _parse_start_exhibition_value(
                start_node.get_text(" ", strip=True) if start_node else ""
            )
            if lane is not None:
                start_map[lane] = {
                    "course_entry": course_entry,
                    "start_exhibition_st": start_value,
                    "start_exhibition_status": start_status,
                }

    rows: list[dict[str, object]] = []
    for tbody in entry_table.find_all("tbody"):
        tr_list = tbody.find_all("tr")
        if len(tr_list) < 4:
            continue
        first_cells = tr_list[0].find_all("td")
        third_cells = tr_list[2].find_all("td")
        if len(first_cells) < 8:
            continue

        lane = maybe_int(first_cells[0].get_text(" ", strip=True))
        profile_link = first_cells[2].find("a", href=True)
        racer_id = _extract_racer_id_from_href(profile_link["href"]) if profile_link else None
        racer_name = clean_text(first_cells[2].get_text(" ", strip=True))
        weight_kg_before = maybe_float(first_cells[3].get_text(" ", strip=True))
        exhibition_time = maybe_float(first_cells[4].get_text(" ", strip=True))
        tilt = maybe_float(first_cells[5].get_text(" ", strip=True))
        adjust_weight_kg = maybe_float(third_cells[0].get_text(" ", strip=True)) if third_cells else None
        start_info = start_map.get(lane or 0, {})

        rows.append(
            {
                "race_id": race_id,
                "race_date": race_date_iso,
                "stadium_code": stadium_code,
                "race_no": race_no,
                "lane": lane,
                "racer_id": racer_id,
                "racer_name": racer_name,
                "weight_kg_before": weight_kg_before,
                "adjust_weight_kg": adjust_weight_kg,
                "exhibition_time": exhibition_time,
                "tilt": tilt,
                "course_entry": start_info.get("course_entry"),
                "start_exhibition_st": start_info.get("start_exhibition_st"),
                "start_exhibition_status": start_info.get("start_exhibition_status", ""),
                "weather_condition": weather["weather_condition"],
                "weather_temp_c": weather["weather_temp_c"],
                "wind_speed_m": weather["wind_speed_m"],
                "wind_direction_code": weather["wind_direction_code"],
                "water_temp_c": weather["water_temp_c"],
                "wave_height_cm": weather["wave_height_cm"],
                "source_url": source_url,
                "fetched_at": fetched_at,
            }
        )
    return rows


def _parse_odds_2way_table(
    table,
    bet_type: str,
    race_date: str,
    stadium_code: str,
    race_no: int,
    source_url: str,
    fetched_at: str,
) -> list[dict[str, object]]:
    header_row = table.find("tr")
    if header_row is None:
        return []
    header_cells = [clean_text(cell.get_text(" ", strip=True)) for cell in header_row.find_all(["th", "td"])]
    first_lanes = [maybe_int(header_cells[index]) for index in range(0, len(header_cells), 2)]
    race_id = make_race_id(race_date, stadium_code, race_no)
    race_date_iso = f"{race_date[:4]}-{race_date[4:6]}-{race_date[6:8]}"

    odds_rows: list[dict[str, object]] = []
    for tr in table.find_all("tr")[1:]:
        cells = tr.find_all("td")
        if not cells:
            continue
        for idx, first_lane in enumerate(first_lanes):
            if first_lane is None:
                continue
            cell_index = idx * 2
            if cell_index + 1 >= len(cells):
                continue
            second_lane = maybe_int(cells[cell_index].get_text(" ", strip=True))
            odds_text = clean_text(cells[cell_index + 1].get_text(" ", strip=True))
            odds = maybe_float(odds_text)
            odds_status = "" if odds is not None else odds_text
            if second_lane is None or (odds is None and not odds_status):
                continue
            odds_rows.append(
                {
                    "race_id": race_id,
                    "race_date": race_date_iso,
                    "stadium_code": stadium_code,
                    "race_no": race_no,
                    "bet_type": bet_type,
                    "first_lane": first_lane,
                    "second_lane": second_lane,
                    "odds": odds,
                    "odds_status": odds_status,
                    "source_url": source_url,
                    "fetched_at": fetched_at,
                }
            )
    return odds_rows


def parse_odds_2t(
    html: str,
    race_date: str,
    stadium_code: str,
    race_no: int,
    source_url: str,
    fetched_at: str,
) -> list[dict[str, object]]:
    if has_no_data(html):
        return []
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    if len(tables) < 3:
        return []
    rows = _parse_odds_2way_table(tables[1], "2連単", race_date, stadium_code, race_no, source_url, fetched_at)
    rows.extend(_parse_odds_2way_table(tables[2], "2連複", race_date, stadium_code, race_no, source_url, fetched_at))
    return rows


def parse_odds_3t(
    html: str,
    race_date: str,
    stadium_code: str,
    race_no: int,
    source_url: str,
    fetched_at: str,
) -> list[dict[str, object]]:
    if has_no_data(html):
        return []

    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    if len(tables) < 2:
        return []

    table = tables[1]
    header_cells = [clean_text(cell.get_text(" ", strip=True)) for cell in table.find("tr").find_all("th")]
    first_lanes = [maybe_int(header_cells[index]) for index in range(0, len(header_cells), 2)]
    active_second = [None] * len(first_lanes)
    remaining = [0] * len(first_lanes)
    race_id = make_race_id(race_date, stadium_code, race_no)
    race_date_iso = f"{race_date[:4]}-{race_date[4:6]}-{race_date[6:8]}"

    rows: list[dict[str, object]] = []
    for tr in table.find_all("tr")[1:]:
        cells = tr.find_all("td")
        if not cells:
            continue
        pointer = 0
        for group_idx, first_lane in enumerate(first_lanes):
            if first_lane is None:
                continue
            if remaining[group_idx] == 0:
                if pointer >= len(cells):
                    break
                second_cell = cells[pointer]
                pointer += 1
                active_second[group_idx] = maybe_int(second_cell.get_text(" ", strip=True))
                remaining[group_idx] = int(second_cell.get("rowspan", "1"))

            if pointer + 1 >= len(cells):
                break

            third_lane = maybe_int(cells[pointer].get_text(" ", strip=True))
            odds_text = clean_text(cells[pointer + 1].get_text(" ", strip=True))
            odds = maybe_float(odds_text)
            odds_status = "" if odds is not None else odds_text
            pointer += 2
            second_lane = active_second[group_idx]

            if second_lane is not None and third_lane is not None and (odds is not None or odds_status):
                rows.append(
                    {
                        "race_id": race_id,
                        "race_date": race_date_iso,
                        "stadium_code": stadium_code,
                        "race_no": race_no,
                        "bet_type": "3連単",
                        "first_lane": first_lane,
                        "second_lane": second_lane,
                        "third_lane": third_lane,
                        "odds": odds,
                        "odds_status": odds_status,
                        "source_url": source_url,
                        "fetched_at": fetched_at,
                    }
                )
            remaining[group_idx] -= 1

    return rows


def parse_result(
    html: str,
    race_date: str,
    stadium_code: str,
    race_no: int,
    source_url: str,
    fetched_at: str,
) -> dict[str, object] | None:
    if has_no_data(html):
        return None

    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    if len(tables) < 7:
        return None

    finish_rows: list[dict[str, object]] = []
    for tr in tables[1].find_all("tr")[1:]:
        cells = [clean_text(cell.get_text(" ", strip=True)) for cell in tr.find_all(["th", "td"])]
        if len(cells) < 4:
            continue
        racer_tokens = cells[2].split(" ", 1)
        finish_rows.append(
            {
                "position": maybe_int(cells[0]),
                "lane": maybe_int(cells[1]),
                "racer_id": maybe_int(racer_tokens[0]) if racer_tokens else None,
                "racer_name": clean_text(racer_tokens[1]) if len(racer_tokens) > 1 else "",
                "race_time": cells[3],
            }
        )

    start_rows: list[dict[str, object]] = []
    for tr in tables[2].find_all("tr")[1:]:
        text = clean_text(tr.get_text(" ", strip=True))
        if not text:
            continue
        parts = text.split(" ")
        start_rows.append(
            {
                "lane": maybe_int(parts[0]) if parts else None,
                "timing": parts[1] if len(parts) > 1 else "",
            }
        )

    payout_rows: list[dict[str, object]] = []
    payout_map: dict[str, list[dict[str, object]]] = {}
    for tr in tables[3].find_all("tr")[1:]:
        cells = [clean_text(cell.get_text(" ", strip=True)) for cell in tr.find_all(["th", "td"])]
        if len(cells) < 4 or not cells[0]:
            continue
        row = {
            "bet_type": cells[0],
            "combo": cells[1],
            "payout": maybe_int(cells[2]),
            "popularity": maybe_int(cells[3]),
        }
        payout_rows.append(row)
        payout_map.setdefault(cells[0], []).append(row)

    refund_info = ""
    refund_cells = tables[4].find_all("td")
    if refund_cells:
        refund_info = clean_text(refund_cells[0].get_text(" ", strip=True))

    winning_technique = ""
    technique_cells = tables[5].find_all("td")
    if technique_cells:
        winning_technique = clean_text(technique_cells[0].get_text(" ", strip=True))

    note = ""
    note_cells = tables[6].find_all("td")
    if note_cells:
        note = clean_text(note_cells[0].get_text(" ", strip=True))

    weather = _parse_weather_fields(soup)

    def payout_first(bet_type: str, key: str):
        rows = payout_map.get(bet_type, [])
        if not rows:
            return None
        return rows[0].get(key)

    finish_by_position = {row["position"]: row for row in finish_rows if row.get("position") is not None}
    race_id = make_race_id(race_date, stadium_code, race_no)
    race_date_iso = f"{race_date[:4]}-{race_date[4:6]}-{race_date[6:8]}"
    return {
        "race_id": race_id,
        "race_date": race_date_iso,
        "stadium_code": stadium_code,
        "race_no": race_no,
        "first_place_lane": finish_by_position.get(1, {}).get("lane"),
        "second_place_lane": finish_by_position.get(2, {}).get("lane"),
        "third_place_lane": finish_by_position.get(3, {}).get("lane"),
        "fourth_place_lane": finish_by_position.get(4, {}).get("lane"),
        "fifth_place_lane": finish_by_position.get(5, {}).get("lane"),
        "sixth_place_lane": finish_by_position.get(6, {}).get("lane"),
        "finish_order_json": to_json_text(finish_rows),
        "start_timing_json": to_json_text(start_rows),
        "payouts_json": to_json_text(payout_rows),
        "refund_info": refund_info,
        "winning_technique": winning_technique,
        "note": note,
        "weather_condition": weather["weather_condition"],
        "weather_temp_c": weather["weather_temp_c"],
        "wind_speed_m": weather["wind_speed_m"],
        "wind_direction_code": weather["wind_direction_code"],
        "water_temp_c": weather["water_temp_c"],
        "wave_height_cm": weather["wave_height_cm"],
        "exacta_combo": payout_first("2連単", "combo"),
        "exacta_payout": payout_first("2連単", "payout"),
        "quinella_combo": payout_first("2連複", "combo"),
        "quinella_payout": payout_first("2連複", "payout"),
        "trifecta_combo": payout_first("3連単", "combo"),
        "trifecta_payout": payout_first("3連単", "payout"),
        "trio_combo": payout_first("3連複", "combo"),
        "trio_payout": payout_first("3連複", "payout"),
        "source_url": source_url,
        "fetched_at": fetched_at,
    }


def extract_term_urls(download_html: str) -> tuple[str | None, str]:
    soup = BeautifulSoup(download_html, "html.parser")
    for anchor in soup.find_all("a", href=True):
        href = clean_text(anchor["href"])
        if href.lower().endswith(".lzh") and "kibetsu" in href:
            return absolute_url(href), TERM_LAYOUT_URL
    return None, TERM_LAYOUT_URL


@dataclass(frozen=True, slots=True)
class TermField:
    name: str
    width: int
    parser: Callable[[bytes], object]


def _decode_term_text(raw: bytes) -> str:
    return raw.decode("cp932", errors="replace").strip()


def _term_text(width: int, name: str) -> TermField:
    return TermField(name=name, width=width, parser=_decode_term_text)


def _term_int(width: int, name: str) -> TermField:
    return TermField(name=name, width=width, parser=lambda raw: maybe_int(_decode_term_text(raw)))


def _term_scaled(width: int, name: str, decimals: int) -> TermField:
    return TermField(name=name, width=width, parser=lambda raw: scaled_int(_decode_term_text(raw), decimals))


TERM_FIELDS: list[TermField] = [
    _term_int(4, "racer_id"),
    _term_text(16, "racer_name_kanji"),
    _term_text(15, "racer_name_kana"),
    _term_text(4, "branch"),
    _term_text(2, "current_class"),
    _term_text(1, "birth_era"),
    _term_text(6, "birth_yymmdd"),
    _term_text(1, "sex"),
    _term_int(2, "age"),
    _term_int(3, "height_cm"),
    _term_int(2, "weight_kg"),
    _term_text(2, "blood_type"),
    _term_scaled(4, "win_rate", 2),
    _term_scaled(4, "place_rate", 1),
    _term_int(3, "first_place_count"),
    _term_int(3, "second_place_count"),
    _term_int(3, "starts"),
    _term_int(2, "finals"),
    _term_int(2, "wins"),
    _term_scaled(3, "average_start_timing", 2),
]

for course in range(1, 7):
    TERM_FIELDS.extend(
        [
            _term_int(3, f"course_{course}_entry_count"),
            _term_scaled(4, f"course_{course}_place_rate", 1),
            _term_scaled(3, f"course_{course}_average_start_timing", 2),
            _term_scaled(3, f"course_{course}_average_start_rank", 2),
        ]
    )

TERM_FIELDS.extend(
    [
        _term_text(2, "previous_class_1"),
        _term_text(2, "previous_class_2"),
        _term_text(2, "previous_class_3"),
        _term_scaled(4, "previous_term_ability_index", 2),
        _term_scaled(4, "current_term_ability_index", 2),
        _term_int(4, "term_year"),
        _term_int(1, "term_half"),
        _term_text(8, "term_start_date_raw"),
        _term_text(8, "term_end_date_raw"),
        _term_int(3, "training_term"),
    ]
)

for course in range(1, 7):
    for placing in range(1, 7):
        TERM_FIELDS.append(_term_int(3, f"course_{course}_finish_{placing}_count"))
    TERM_FIELDS.extend(
        [
            _term_int(2, f"course_{course}_f_count"),
            _term_int(2, f"course_{course}_l0_count"),
            _term_int(2, f"course_{course}_l1_count"),
            _term_int(2, f"course_{course}_k0_count"),
            _term_int(2, f"course_{course}_k1_count"),
            _term_int(2, f"course_{course}_s0_count"),
            _term_int(2, f"course_{course}_s1_count"),
            _term_int(2, f"course_{course}_s2_count"),
        ]
    )

TERM_FIELDS.extend(
    [
        _term_int(2, "no_course_l0_count"),
        _term_int(2, "no_course_l1_count"),
        _term_int(2, "no_course_k0_count"),
        _term_int(2, "no_course_k1_count"),
        _term_text(6, "hometown"),
    ]
)

TERM_STAT_COLUMNS = [field.name for field in TERM_FIELDS] + [
    "birth_date",
    "term_start_date",
    "term_end_date",
    "term_file",
    "source_url",
    "fetched_at",
]


def parse_term_stats_records(
    raw_bytes: bytes,
    term_file: str,
    source_url: str,
    fetched_at: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for raw_line in raw_bytes.splitlines():
        line = raw_line.rstrip(b"\r\n")
        if not line:
            continue
        offset = 0
        record: dict[str, object] = {}
        for field in TERM_FIELDS:
            chunk = line[offset : offset + field.width]
            record[field.name] = field.parser(chunk)
            offset += field.width

        birth_era = clean_text(str(record.get("birth_era") or ""))
        birth_yymmdd = clean_text(str(record.get("birth_yymmdd") or ""))
        term_start_raw = clean_text(str(record.get("term_start_date_raw") or ""))
        term_end_raw = clean_text(str(record.get("term_end_date_raw") or ""))

        record["birth_date"] = era_date_to_iso(birth_era, birth_yymmdd)
        record["term_start_date"] = (
            date(int(term_start_raw[:4]), int(term_start_raw[4:6]), int(term_start_raw[6:8])).isoformat()
            if len(term_start_raw) == 8 and term_start_raw.isdigit()
            else None
        )
        record["term_end_date"] = (
            date(int(term_end_raw[:4]), int(term_end_raw[4:6]), int(term_end_raw[6:8])).isoformat()
            if len(term_end_raw) == 8 and term_end_raw.isdigit()
            else None
        )
        record["term_file"] = term_file
        record["source_url"] = source_url
        record["fetched_at"] = fetched_at
        rows.append(record)
    return rows
