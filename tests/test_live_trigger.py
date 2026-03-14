from pathlib import Path

from boat_race_data.live_trigger import (
    TriggerProfile,
    build_watchlist_row,
    compute_best_gap,
    compute_watch_start_time,
    load_trigger_profiles,
)


def test_compute_watch_start_time_subtracts_minutes() -> None:
    assert compute_watch_start_time("2026-03-15", "14:25", 25) == "2026-03-15 14:00"


def test_build_watchlist_row_applies_pre_filters() -> None:
    profile = TriggerProfile.from_dict(
        {
            "box_id": "125",
            "profile_id": "test",
            "strategy_id": "125",
            "stadiums": ["12"],
            "watch_minutes_before_deadline": 25,
            "pre_filters": {
                "lane1_class_exclude": ["A1"],
                "lane1_motor_place_rate_min": 35.0,
                "lane1_motor_top3_rate_min": 45.0,
            },
            "final_filters": {
                "lane1_exhibition_best_gap_max": 0.02,
            },
        }
    )
    race_row = {
        "race_id": "202603151201",
        "race_date": "2026-03-15",
        "stadium_code": "12",
        "stadium_name": "住之江",
        "race_no": 1,
        "deadline_time": "14:25",
    }
    entry_rows = [
        {
            "lane": 1,
            "racer_id": 1001,
            "racer_name": "A",
            "racer_class": "B1",
            "motor_no": 12,
            "motor_place_rate": 38.2,
            "motor_top3_rate": 47.1,
        }
    ]

    row = build_watchlist_row(race_row, entry_rows, profile)

    assert row is not None
    assert row["box_id"] == "125"
    assert row["status"] == "waiting_beforeinfo"
    assert row["watch_start_time"] == "2026-03-15 14:00"


def test_compute_best_gap_uses_fastest_exhibition_time() -> None:
    rows = [
        {"lane": 1, "exhibition_time": 6.79},
        {"lane": 2, "exhibition_time": 6.83},
        {"lane": 3, "exhibition_time": 6.77},
    ]

    assert round(compute_best_gap(rows, lane=1) or 0.0, 3) == 0.02


def test_load_trigger_profiles_reads_enabled_json_files(tmp_path: Path) -> None:
    (tmp_path / "boxes" / "125" / "profiles").mkdir(parents=True)
    (tmp_path / "boxes" / "c2" / "profiles").mkdir(parents=True)
    (tmp_path / "boxes" / "template" / "profiles").mkdir(parents=True)
    (tmp_path / "boxes" / "125" / "profiles" / "enabled.json").write_text(
        """
        {
          "box_id": "125",
          "profile_id": "p1",
          "strategy_id": "125",
          "display_name": "One",
          "enabled": true,
          "stadiums": ["12"],
          "pre_filters": {},
          "final_filters": {}
        }
        """,
        encoding="utf-8",
    )
    (tmp_path / "boxes" / "c2" / "profiles" / "disabled.json").write_text(
        """
        {
          "box_id": "c2",
          "profile_id": "p2",
          "strategy_id": "125",
          "display_name": "Two",
          "enabled": false,
          "stadiums": ["13"],
          "pre_filters": {},
          "final_filters": {}
        }
        """,
        encoding="utf-8",
    )
    (tmp_path / "boxes" / "template" / "profiles" / "logic_profile_template.json").write_text(
        """
        {
          "box_id": "template",
          "profile_id": "template_profile",
          "strategy_id": "template",
          "display_name": "Template",
          "enabled": true,
          "stadiums": ["12"],
          "pre_filters": {},
          "final_filters": {}
        }
        """,
        encoding="utf-8",
    )

    profiles = load_trigger_profiles(tmp_path / "boxes")

    assert [profile.profile_id for profile in profiles] == ["p1"]
    assert profiles[0].box_id == "125"
