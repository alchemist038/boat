import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from boat_race_data.live_trigger import (
    TriggerProfile,
    build_watchlist_row,
    compute_best_gap,
    compute_exhibition_rank,
    compute_lane_gap,
    compute_start_rank,
    compute_start_gap_over_rest,
    compute_watch_start_time,
    enrich_watchlist_row_with_beforeinfo,
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
        "stadium_name": "Suminoe",
        "meeting_title": "General",
        "race_title": "Preliminary",
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


def test_build_watchlist_row_applies_title_proxy_filters() -> None:
    profile = TriggerProfile.from_dict(
        {
            "box_id": "c2",
            "profile_id": "c2",
            "strategy_id": "c2",
            "pre_filters": {
                "meeting_title_keywords_any": ["女子", "レディース"],
            },
            "final_filters": {
                "lane1_start_gap_over_rest_min": 0.12,
            },
        }
    )
    race_row = {
        "race_id": "202603150201",
        "race_date": "2026-03-15",
        "stadium_code": "02",
        "stadium_name": "Toda",
        "meeting_title": "オールレディース",
        "race_title": "予選",
        "race_no": 1,
        "deadline_time": "10:55",
    }
    entry_rows = [
        {
            "lane": 1,
            "racer_id": 1001,
            "racer_name": "A",
            "racer_class": "B1",
            "motor_no": 12,
            "motor_place_rate": 0.0,
            "motor_top3_rate": 0.0,
        }
    ]

    row = build_watchlist_row(race_row, entry_rows, profile)

    assert row is not None
    assert row["pre_reason"].startswith("title_proxy")


def test_compute_best_gap_uses_fastest_exhibition_time() -> None:
    rows = [
        {"lane": 1, "exhibition_time": 6.79},
        {"lane": 2, "exhibition_time": 6.83},
        {"lane": 3, "exhibition_time": 6.77},
    ]

    assert round(compute_best_gap(rows, lane=1) or 0.0, 3) == 0.02


def test_c2_gap_helpers_compute_expected_values() -> None:
    rows = [
        {"lane": 1, "exhibition_time": 6.79, "start_exhibition_st": 0.21},
        {"lane": 2, "exhibition_time": 6.80, "start_exhibition_st": 0.05},
        {"lane": 3, "exhibition_time": 6.81, "start_exhibition_st": 0.07},
        {"lane": 4, "exhibition_time": 6.84, "start_exhibition_st": 0.09},
    ]

    assert round(compute_lane_gap(rows, 1, 2) or 0.0, 3) == -0.01
    assert round(compute_lane_gap(rows, 1, 3) or 0.0, 3) == -0.02
    assert round(compute_start_gap_over_rest(rows, 1) or 0.0, 3) == 0.16


def test_compute_start_rank_uses_fastest_start_exhibition_st() -> None:
    rows = [
        {"lane": 1, "start_exhibition_st": 0.16},
        {"lane": 2, "start_exhibition_st": 0.09},
        {"lane": 3, "start_exhibition_st": 0.11},
        {"lane": 4, "start_exhibition_st": 0.08},
    ]

    assert compute_start_rank(rows, lane=1) == 4
    assert compute_start_rank(rows, lane=4) == 1


def test_compute_exhibition_rank_can_scope_to_candidate_lanes() -> None:
    rows = [
        {"lane": 1, "exhibition_time": 6.78},
        {"lane": 2, "exhibition_time": 6.79},
        {"lane": 3, "exhibition_time": 6.83},
        {"lane": 4, "exhibition_time": 6.80},
        {"lane": 5, "exhibition_time": 6.76},
    ]

    assert compute_exhibition_rank(rows, lane=3, candidate_lanes=(1, 2, 3, 4)) == 4


def test_l3_124_watchlist_row_requires_exactly_one_outer_a_class() -> None:
    profile = next(
        profile
        for profile in load_trigger_profiles(ROOT / "live_trigger" / "boxes", include_disabled=True)
        if profile.profile_id == "l3_weak_124_box_one_a_ex241_v1"
    )
    race_row = {
        "race_id": "202604020901",
        "race_date": "2026-04-02",
        "stadium_code": "09",
        "stadium_name": "Test",
        "meeting_title": "General",
        "race_title": "Qualifying",
        "race_no": 1,
        "deadline_time": "12:30",
    }
    base_entries = [
        {"lane": 1, "racer_id": "1001", "racer_name": "L1", "racer_class": "B1", "motor_no": "11"},
        {"lane": 2, "racer_id": "1002", "racer_name": "L2", "racer_class": "A2"},
        {"lane": 3, "racer_id": "1003", "racer_name": "L3", "racer_class": "B1"},
        {"lane": 4, "racer_id": "1004", "racer_name": "L4", "racer_class": "A2"},
    ]

    accepted = build_watchlist_row(
        race_row,
        base_entries
        + [
            {"lane": 5, "racer_id": "1005", "racer_name": "L5", "racer_class": "A2"},
            {"lane": 6, "racer_id": "1006", "racer_name": "L6", "racer_class": "B1"},
        ],
        profile,
    )
    rejected = build_watchlist_row(
        race_row,
        base_entries
        + [
            {"lane": 5, "racer_id": "1005", "racer_name": "L5", "racer_class": "A1"},
            {"lane": 6, "racer_id": "1006", "racer_name": "L6", "racer_class": "A2"},
        ],
        profile,
    )

    assert accepted is not None
    assert accepted["pre_reason"] == "l3_weak_124_box_one_a_candidate"
    assert rejected is None


def test_l3_124_profile_becomes_trigger_ready_when_lane3_is_weakest_of_lanes_1_to_4(monkeypatch, tmp_path: Path) -> None:
    profile = next(
        profile
        for profile in load_trigger_profiles(ROOT / "live_trigger" / "boxes", include_disabled=True)
        if profile.profile_id == "l3_weak_124_box_one_a_ex241_v1"
    )

    monkeypatch.setattr(
        sys.modules["boat_race_data.live_trigger"],
        "_fetch_text_cached",
        lambda client, url, raw_path, refresh_after_seconds=None: type(
            "Fetch",
            (),
            {
                "text": "<html></html>",
                "url": url,
                "fetched_at": "2026-04-02T10:00:00",
            },
        )(),
    )
    monkeypatch.setattr(
        sys.modules["boat_race_data.live_trigger"],
        "parse_beforeinfo",
        lambda *args, **kwargs: [
            {"lane": 1, "start_exhibition_st": 0.13, "exhibition_time": 6.78},
            {"lane": 2, "start_exhibition_st": 0.11, "exhibition_time": 6.79},
            {"lane": 3, "start_exhibition_st": 0.22, "exhibition_time": 6.84},
            {"lane": 4, "start_exhibition_st": 0.15, "exhibition_time": 6.80},
            {"lane": 5, "start_exhibition_st": 0.09, "exhibition_time": 6.76},
            {"lane": 6, "start_exhibition_st": 0.17, "exhibition_time": 6.82},
        ],
    )

    row = {
        "race_id": "202604020901",
        "race_date": "2026-04-02",
        "stadium_code": "09",
        "race_no": 1,
        "status": "waiting_beforeinfo",
        "pre_reason": "l3_weak_124_box_one_a_candidate",
        "final_reason": "",
    }

    class FakeClient:
        def build_race_url(self, page: str, race_date: str, stadium_code: str, race_no: int) -> str:
            return f"{page}:{race_date}:{stadium_code}:{race_no}"

    result = enrich_watchlist_row_with_beforeinfo(
        row,
        profile,
        client=FakeClient(),
        raw_root=tmp_path,
    )

    assert result == {"changed": True, "ready": True}
    assert row["status"] == "trigger_ready"
    assert "lane3_exhibition_rank=4.000 == 4" in row["final_reason"]
    assert "lane3_start_rank=4.000 == 4" in row["final_reason"]


def test_h_a_profile_becomes_trigger_ready_with_start_rank_and_lane4_gap(monkeypatch, tmp_path: Path) -> None:
    profile = next(
        profile
        for profile in load_trigger_profiles(ROOT / "live_trigger" / "boxes", include_disabled=True)
        if profile.profile_id == "h_a_final_day_cut_v1"
    )

    monkeypatch.setattr(
        sys.modules["boat_race_data.live_trigger"],
        "_fetch_text_cached",
        lambda client, url, raw_path, refresh_after_seconds=None: type(
            "Fetch",
            (),
            {
                "text": "<html></html>",
                "url": url,
                "fetched_at": "2026-03-26T10:00:00",
            },
        )(),
    )
    monkeypatch.setattr(
        sys.modules["boat_race_data.live_trigger"],
        "parse_beforeinfo",
        lambda *args, **kwargs: [
            {"lane": 1, "start_exhibition_st": 0.12, "exhibition_time": 6.80},
            {"lane": 2, "start_exhibition_st": 0.18, "exhibition_time": 6.82},
            {"lane": 3, "start_exhibition_st": 0.14, "exhibition_time": 6.81},
            {"lane": 4, "start_exhibition_st": 0.05, "exhibition_time": 6.78},
            {"lane": 5, "start_exhibition_st": 0.19, "exhibition_time": 6.84},
            {"lane": 6, "start_exhibition_st": 0.20, "exhibition_time": 6.83},
        ],
    )

    row = {
        "race_id": "202603261204",
        "race_date": "2026-03-26",
        "stadium_code": "12",
        "race_no": 4,
        "status": "waiting_beforeinfo",
        "pre_reason": "broad_exacta_4_1_candidate",
        "final_reason": "",
    }

    class FakeClient:
        def build_race_url(self, page: str, race_date: str, stadium_code: str, race_no: int) -> str:
            return f"{page}:{race_date}:{stadium_code}:{race_no}"

    result = enrich_watchlist_row_with_beforeinfo(
        row,
        profile,
        client=FakeClient(),
        raw_root=tmp_path,
    )

    assert result == {"changed": True, "ready": True}
    assert row["status"] == "trigger_ready"
    assert "lane1_start_rank=2.000 <= 3" in row["final_reason"]
    assert "lane4_ahead_lane1_start_gap=0.070 >= 0.05" in row["final_reason"]


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
          "strategy_id": "c2",
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
