from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from boat_race_data.live_trigger import build_watchlist_row, load_trigger_profiles


def test_c2_all_women_proxy_accepts_tokoname_20260323_r1(monkeypatch) -> None:
    profile = next(
        profile
        for profile in load_trigger_profiles(ROOT / "live_trigger" / "boxes", include_disabled=True)
        if profile.profile_id == "c2_provisional_v1"
    )
    import boat_race_data.live_trigger as live_trigger

    monkeypatch.setattr(
        live_trigger,
        "_latest_racer_sex_index",
        lambda: {
            "4501": "2",
            "4909": "2",
            "5324": "2",
            "4478": "2",
            "5389": "2",
            "5173": "2",
        },
    )

    race_row = {
        "race_id": "202603230801",
        "race_date": "2026-03-23",
        "stadium_code": "08",
        "stadium_name": "常滑",
        "race_no": 1,
        "meeting_title": "第28回日本財団会長杯争奪戦競走",
        "race_title": "朝トコ小判R",
        "deadline_time": "10:18",
    }
    entry_rows = [
        {"lane": 1, "racer_id": 4501, "racer_name": "樋口 由加里", "racer_class": "A2", "motor_no": 43, "motor_place_rate": 32.47, "motor_top3_rate": 45.45},
        {"lane": 2, "racer_id": 4909, "racer_name": "薮内 瑞希", "racer_class": "B1"},
        {"lane": 3, "racer_id": 5324, "racer_name": "畑田 希咲", "racer_class": "B2"},
        {"lane": 4, "racer_id": 4478, "racer_name": "櫻本 あゆみ", "racer_class": "A2"},
        {"lane": 5, "racer_id": 5389, "racer_name": "恵良 琴美", "racer_class": "B2"},
        {"lane": 6, "racer_id": 5173, "racer_name": "谷口 佳蓮", "racer_class": "B1"},
    ]

    row = build_watchlist_row(race_row, entry_rows, profile)

    assert row is not None
    assert row["profile_id"] == "c2_provisional_v1"
    assert row["race_id"] == "202603230801"
    assert row["pre_reason"] == "women6_proxy, class=A2"


def test_build_watchlist_row_excludes_final_day(monkeypatch) -> None:
    profile = next(
        profile
        for profile in load_trigger_profiles(ROOT / "live_trigger" / "boxes", include_disabled=True)
        if profile.profile_id == "c2_provisional_v1"
    )
    import boat_race_data.live_trigger as live_trigger

    monkeypatch.setattr(
        live_trigger,
        "_latest_racer_sex_index",
        lambda: {
            "4501": "2",
            "4909": "2",
            "5324": "2",
            "4478": "2",
            "5389": "2",
            "5173": "2",
        },
    )

    race_row = {
        "race_id": "202603230801",
        "race_date": "2026-03-23",
        "stadium_code": "08",
        "stadium_name": "常滑",
        "race_no": 1,
        "meeting_title": "第28回日本財団会長杯争奪戦",
        "race_title": "予選",
        "deadline_time": "10:18",
        "is_final_day": 1,
    }
    entry_rows = [
        {"lane": 1, "racer_id": 4501, "racer_name": "Lane1", "racer_class": "A2", "motor_no": 43, "motor_place_rate": 32.47, "motor_top3_rate": 45.45},
        {"lane": 2, "racer_id": 4909, "racer_name": "Lane2", "racer_class": "B1"},
        {"lane": 3, "racer_id": 5324, "racer_name": "Lane3", "racer_class": "B2"},
        {"lane": 4, "racer_id": 4478, "racer_name": "Lane4", "racer_class": "A2"},
        {"lane": 5, "racer_id": 5389, "racer_name": "Lane5", "racer_class": "B2"},
        {"lane": 6, "racer_id": 5173, "racer_name": "Lane6", "racer_class": "B1"},
    ]

    row = build_watchlist_row(race_row, entry_rows, profile)

    assert row is None
