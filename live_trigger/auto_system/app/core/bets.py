from __future__ import annotations

from typing import Any


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
