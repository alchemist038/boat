from __future__ import annotations

from typing import Any

LANES = ("1", "2", "3", "4", "5", "6")
ALL_TOKENS = {"ALL", "*", "全", "全通り"}


def _combo_parts(combo: str) -> list[str]:
    return [part.strip().upper() for part in str(combo).split("-") if part.strip()]


def _candidates(token: str, used: set[str]) -> list[str]:
    if token in ALL_TOKENS:
        return [lane for lane in LANES if lane not in used]
    if token not in LANES or token in used:
        return []
    return [token]


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


def build_bet_rows(*, strategy_id: str, profile_id: str, amount: int) -> list[dict[str, Any]]:
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
