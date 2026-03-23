from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
AUTO_SYSTEM_ROOT = ROOT / "live_trigger" / "auto_system"
SRC_ROOT = ROOT / "src"

for import_root in (AUTO_SYSTEM_ROOT, SRC_ROOT, ROOT):
    import_text = str(import_root)
    if import_text not in sys.path:
        sys.path.insert(0, import_text)

from app.core import bets
from live_trigger_cli import runtime


def test_build_bet_rows_keeps_legacy_c2_shape_without_context() -> None:
    rows = bets.build_bet_rows(
        strategy_id="c2",
        profile_id="c2_provisional_v1",
        amount=100,
    )

    assert rows == [
        {"bet_type": "trifecta", "combo": "2-ALL-ALL", "amount": 100},
        {"bet_type": "trifecta", "combo": "3-ALL-ALL", "amount": 100},
    ]


def test_build_bet_rows_expands_c2_b2_cut_with_context_lane_classes() -> None:
    rows = bets.build_bet_rows(
        strategy_id="c2",
        profile_id="c2_provisional_v1",
        amount=100,
        context={
            "race_id": "202603230801",
            "lane1_racer_class": "A2",
            "lane2_racer_class": "B1",
            "lane3_racer_class": "B2",
            "lane4_racer_class": "A2",
            "lane5_racer_class": "B2",
            "lane6_racer_class": "B1",
        },
    )

    combos = {str(row["combo"]) for row in rows}

    assert len(rows) == 18
    assert "2-1-4" in combos
    assert "2-3-1" not in combos
    assert "2-1-5" not in combos
    assert "3-1-2" in combos
    assert all(row["bet_type"] == "trifecta" for row in rows)
    assert all(int(row["amount"]) == 100 for row in rows)


def test_runtime_build_bet_rows_passes_context_to_shared_module(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_build_bet_rows(**kwargs):
        captured.update(kwargs)
        return [{"bet_type": "trifecta", "combo": "2-1-4", "amount": 100}]

    monkeypatch.setattr(
        runtime,
        "_load_shared_bets_module",
        lambda: SimpleNamespace(build_bet_rows=fake_build_bet_rows),
    )

    rows = runtime._build_bet_rows(
        strategy_id="c2",
        profile_id="c2_provisional_v1",
        amount=100,
        context={"race_id": "202603230801"},
    )

    assert rows == [{"bet_type": "trifecta", "combo": "2-1-4", "amount": 100}]
    assert captured == {
        "strategy_id": "c2",
        "profile_id": "c2_provisional_v1",
        "amount": 100,
        "context": {"race_id": "202603230801"},
    }
