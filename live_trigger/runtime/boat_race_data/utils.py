from __future__ import annotations

import json
import re
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

SPACE_RE = re.compile(r"\s+")
NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def clean_text(value: str | None) -> str:
    if value is None:
        return ""
    normalized = unicodedata.normalize("NFKC", value.replace("\xa0", " "))
    return SPACE_RE.sub(" ", normalized).strip()


def maybe_int(value: str | None) -> int | None:
    text = clean_text(value)
    if not text:
        return None
    text = text.replace(",", "").replace("¥", "")
    try:
        return int(text)
    except ValueError:
        match = NUMBER_RE.search(text)
        if match:
            return int(float(match.group(0)))
        return None


def maybe_float(value: str | None) -> float | None:
    text = clean_text(value)
    if not text:
        return None
    text = text.replace(",", "").replace("¥", "")
    try:
        return float(text)
    except ValueError:
        match = NUMBER_RE.search(text)
        if match:
            return float(match.group(0))
        return None


def scaled_int(value: str | None, decimal_places: int) -> float | None:
    text = clean_text(value)
    if not text:
        return None
    if set(text) == {"0"}:
        return 0.0
    number = maybe_int(text)
    if number is None:
        return None
    return number / (10**decimal_places)


def parse_age_weight(value: str) -> tuple[int | None, float | None]:
    text = clean_text(value)
    if not text:
        return None, None
    age_match = re.search(r"(\d+)歳", text)
    weight_match = re.search(r"(\d+(?:\.\d+)?)kg", text)
    age = int(age_match.group(1)) if age_match else None
    weight = float(weight_match.group(1)) if weight_match else None
    return age, weight


def parse_f_l_st(value: str) -> tuple[int | None, int | None, float | None]:
    text = clean_text(value)
    if not text:
        return None, None, None
    f_match = re.search(r"F(\d+)", text)
    l_match = re.search(r"L(\d+)", text)
    float_match = re.search(r"(\d+\.\d+)$", text)
    return (
        int(f_match.group(1)) if f_match else None,
        int(l_match.group(1)) if l_match else None,
        float(float_match.group(1)) if float_match else None,
    )


def parse_three_rates(value: str) -> tuple[float | None, float | None, float | None]:
    parts = clean_text(value).split(" ")
    if len(parts) < 3:
        return None, None, None
    return maybe_float(parts[0]), maybe_float(parts[1]), maybe_float(parts[2])


def parse_two_rates_with_number(value: str) -> tuple[int | None, float | None, float | None]:
    parts = clean_text(value).split(" ")
    if len(parts) < 3:
        return None, None, None
    return maybe_int(parts[0]), maybe_float(parts[1]), maybe_float(parts[2])


def make_race_id(race_date: str, stadium_code: str, race_no: int) -> str:
    return f"{race_date}{stadium_code}{race_no:02d}"


def parse_race_title(value: str) -> tuple[str, int | None]:
    text = clean_text(value)
    match = re.search(r"(.+?)\s+(\d+)m$", text)
    if not match:
        return text, None
    return clean_text(match.group(1)), int(match.group(2))


def has_no_data(html: str) -> bool:
    return "データがありません" in html


def to_json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def era_date_to_iso(era_code: str, yymmdd: str) -> str | None:
    text = clean_text(yymmdd)
    if not era_code or len(text) != 6 or not text.isdigit():
        return None
    yy = int(text[:2])
    mm = int(text[2:4])
    dd = int(text[4:6])
    base_year = {
        "M": 1867,
        "T": 1911,
        "S": 1925,
        "H": 1988,
        "R": 2018,
    }.get(era_code)
    if base_year is None:
        return None
    try:
        converted = date(base_year + yy, mm, dd)
    except ValueError:
        return None
    return converted.isoformat()
