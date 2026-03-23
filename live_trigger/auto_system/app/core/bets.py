from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

LANES = ("1", "2", "3", "4", "5", "6")
ALL_TOKENS = {"ALL", "*", "全", "全通り"}
CANONICAL_DUCKDB_PATH = Path(r"\\038INS\boat\data\silver\boat_race.duckdb")


def _combo_parts(combo: str) -> list[str]:
    return [part.strip().upper() for part in str(combo).split("-") if part.strip()]


def _candidates(token: str, used: set[str]) -> list[str]:
    if token in ALL_TOKENS:
        return [lane for lane in LANES if lane not in used]
    if token not in LANES or token in used:
        return []
    return [token]


def _normalize_race_id(context: Mapping[str, Any] | None) -> str | None:
    if not context:
        return None
    value = context.get("race_id")
    if value in {None, ""}:
        return None
    text = str(value).strip()
    return text or None


def _lane_class_map_from_context(context: Mapping[str, Any] | None) -> dict[str, str]:
    if not context:
        return {}

    lane_class_map: dict[str, str] = {}
    for lane in LANES:
        key = f"lane{lane}_racer_class"
        value = context.get(key)
        if value in {None, ""}:
            continue
        lane_class_map[lane] = str(value).strip().upper()
    return lane_class_map


@lru_cache(maxsize=4096)
def _lane_class_map_for_race(race_id: str) -> dict[str, str]:
    if not race_id or not CANONICAL_DUCKDB_PATH.exists():
        return {}

    try:
        import duckdb
    except ImportError:
        return {}

    connection = duckdb.connect(str(CANONICAL_DUCKDB_PATH), read_only=True)
    try:
        rows = connection.execute(
            """
            WITH ranked AS (
              SELECT
                lane,
                racer_class,
                ROW_NUMBER() OVER (
                  PARTITION BY lane
                  ORDER BY fetched_at DESC NULLS LAST
                ) AS row_no
              FROM entries
              WHERE race_id = ?
            )
            SELECT lane, racer_class
            FROM ranked
            WHERE row_no = 1
            """,
            [race_id],
        ).fetchall()
    finally:
        connection.close()

    return {
        str(int(lane)): str(racer_class).strip().upper()
        for lane, racer_class in rows
        if lane is not None and racer_class not in {None, ""}
    }


def _expand_trifecta_combo(combo: str, *, excluded_lanes: set[str]) -> list[str]:
    parts = _combo_parts(combo)
    if len(parts) != 3:
        return []

    expanded: list[str] = []
    for first in _candidates(parts[0], set()):
        used_first = {first}
        second_candidates = _candidates(parts[1], used_first)
        if parts[1] in ALL_TOKENS:
            second_candidates = [lane for lane in second_candidates if lane not in excluded_lanes]
        for second in second_candidates:
            used_second = {first, second}
            third_candidates = _candidates(parts[2], used_second)
            if parts[2] in ALL_TOKENS:
                third_candidates = [lane for lane in third_candidates if lane not in excluded_lanes]
            for third in third_candidates:
                expanded.append(f"{first}-{second}-{third}")
    return expanded


def _build_c2_b2_cut_rows(*, amount: int, context: Mapping[str, Any] | None) -> list[dict[str, Any]] | None:
    lane_class_map = _lane_class_map_from_context(context)
    if not lane_class_map:
        race_id = _normalize_race_id(context)
        if race_id is None:
            return None
        lane_class_map = _lane_class_map_for_race(race_id)
    if not lane_class_map:
        return None

    excluded_lanes = {
        lane
        for lane, racer_class in lane_class_map.items()
        if str(racer_class).upper() == "B2"
    }
    rows: list[dict[str, Any]] = []
    for combo in ("2-ALL-ALL", "3-ALL-ALL"):
        for resolved_combo in _expand_trifecta_combo(combo, excluded_lanes=excluded_lanes):
            rows.append(
                {
                    "bet_type": "trifecta",
                    "combo": resolved_combo,
                    "amount": amount,
                }
            )
    return rows


def bet_point_count(*, bet_type: str, combo: str) -> int:
    normalized_bet_type = str(bet_type).lower()
    parts = _combo_parts(combo)
    if not parts:
        return 0

    if normalized_bet_type != "trifecta" or len(parts) != 3:
        return 1

    count = 0
    for first in _candidates(parts[0], set()):
        for second in _candidates(parts[1], {first}):
            for third in _candidates(parts[2], {first, second}):
                count += 1
    return count


def bet_total_amount(*, bet_type: str, combo: str, unit_amount: int) -> int:
    if int(unit_amount) <= 0:
        return 0
    return bet_point_count(bet_type=bet_type, combo=combo) * int(unit_amount)


def build_bet_rows(
    *,
    strategy_id: str,
    profile_id: str,
    amount: int,
    context: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    normalized_strategy = str(strategy_id).lower()
    normalized_profile = str(profile_id).lower()

    if amount <= 0:
        return []

    if normalized_strategy == "125" or "125" in normalized_profile:
        return [
            {
                "bet_type": "trifecta",
                "combo": "1-2-5",
                "amount": amount,
            }
        ]

    if normalized_strategy == "c2" or "c2" in normalized_profile:
        expanded_rows = _build_c2_b2_cut_rows(amount=amount, context=context)
        if expanded_rows:
            return expanded_rows
        return [
            {
                "bet_type": "trifecta",
                "combo": "2-ALL-ALL",
                "amount": amount,
            },
            {
                "bet_type": "trifecta",
                "combo": "3-ALL-ALL",
                "amount": amount,
            },
        ]

    return []
