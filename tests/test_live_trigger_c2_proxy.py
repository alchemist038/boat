from __future__ import annotations

import sys
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from boat_race_data.live_trigger import (
    build_watchlist_row,
    enrich_watchlist_row_with_beforeinfo,
    load_trigger_profiles,
)


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
    monkeypatch.setattr(
        live_trigger,
        "_daily_pred1_lane_index",
        lambda race_date_iso: {"202603230801": 2},
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


def test_c2_racer_index_overlay_filters_when_pred1_is_lane1(monkeypatch, tmp_path: Path) -> None:
    profile = next(
        profile
        for profile in load_trigger_profiles(ROOT / "live_trigger" / "boxes", include_disabled=True)
        if profile.profile_id == "c2_provisional_v1"
    )
    import boat_race_data.live_trigger as live_trigger

    monkeypatch.setattr(
        live_trigger,
        "_daily_pred1_lane_index",
        lambda race_date_iso: {"202603230801": 1},
    )

    row = {
        "race_id": "202603230801",
        "race_date": "2026-03-23",
        "stadium_code": "08",
        "race_no": 1,
        "status": "waiting_beforeinfo",
        "pre_reason": "women6_proxy, class=A2",
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

    assert result == {"changed": True, "ready": False}
    assert row["status"] == "filtered_out"
    assert row["final_reason"] == "racer_index_pred1_lane=1 excluded"
    assert row["racer_index_pred1_lane"] == 1
    assert row["racer_index_signal_date"] == "2026-03-23"


def test_c2_racer_index_overlay_filters_at_watchlist_build_stage(monkeypatch) -> None:
    profile = next(
        profile
        for profile in load_trigger_profiles(ROOT / "live_trigger" / "boxes", include_disabled=True)
        if profile.profile_id == "c2_provisional_v1"
    )
    import boat_race_data.live_trigger as live_trigger

    monkeypatch.setattr(
        live_trigger,
        "_daily_pred1_lane_index",
        lambda race_date_iso: {"202603230801": 1},
    )

    race_row = {
        "race_id": "202603230801",
        "race_date": "2026-03-23",
        "stadium_code": "08",
        "stadium_name": "Tokoname",
        "race_no": 1,
        "meeting_title": "Lady Cup",
        "race_title": "1R",
        "deadline_time": "10:18",
    }
    entry_rows = [
        {"lane": 1, "racer_id": 4501, "racer_name": "Lane1", "racer_class": "A2", "motor_no": 43, "motor_place_rate": 32.47, "motor_top3_rate": 45.45},
        {"lane": 2, "racer_id": 4909, "racer_name": "Lane2", "racer_class": "B1"},
        {"lane": 3, "racer_id": 5324, "racer_name": "Lane3", "racer_class": "B2"},
        {"lane": 4, "racer_id": 4478, "racer_name": "Lane4", "racer_class": "A2"},
        {"lane": 5, "racer_id": 5389, "racer_name": "Lane5", "racer_class": "B1"},
        {"lane": 6, "racer_id": 5173, "racer_name": "Lane6", "racer_class": "B1"},
    ]

    row = build_watchlist_row(race_row, entry_rows, profile)

    assert row is None


def test_c2_racer_index_overlay_defaults_missing_pred1_to_lane1_at_watchlist_build_stage(monkeypatch) -> None:
    profile = next(
        profile
        for profile in load_trigger_profiles(ROOT / "live_trigger" / "boxes", include_disabled=True)
        if profile.profile_id == "c2_provisional_v1"
    )
    import boat_race_data.live_trigger as live_trigger

    monkeypatch.setattr(
        live_trigger,
        "_daily_pred1_lane_index",
        lambda race_date_iso: {},
    )

    race_row = {
        "race_id": "202603230801",
        "race_date": "2026-03-23",
        "stadium_code": "08",
        "stadium_name": "Tokoname",
        "race_no": 1,
        "meeting_title": "Lady Cup",
        "race_title": "1R",
        "deadline_time": "10:18",
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


def test_c2_racer_index_overlay_keeps_row_when_pred1_is_not_lane1(monkeypatch, tmp_path: Path) -> None:
    profile = next(
        profile
        for profile in load_trigger_profiles(ROOT / "live_trigger" / "boxes", include_disabled=True)
        if profile.profile_id == "c2_provisional_v1"
    )
    import boat_race_data.live_trigger as live_trigger

    monkeypatch.setattr(
        live_trigger,
        "_daily_pred1_lane_index",
        lambda race_date_iso: {"202603230801": 2},
    )
    monkeypatch.setattr(
        live_trigger,
        "_fetch_text_cached",
        lambda client, url, raw_path, refresh_after_seconds=None: type(
            "Fetch",
            (),
            {
                "text": "<html></html>",
                "url": url,
                "fetched_at": "2026-03-23T10:00:00",
            },
        )(),
    )
    monkeypatch.setattr(
        live_trigger,
        "parse_beforeinfo",
        lambda *args, **kwargs: [],
    )

    row = {
        "race_id": "202603230801",
        "race_date": "2026-03-23",
        "stadium_code": "08",
        "race_no": 1,
        "status": "waiting_beforeinfo",
        "pre_reason": "women6_proxy, class=A2",
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

    assert result == {"changed": True, "ready": False}
    assert row["status"] == "waiting_beforeinfo"
    assert row["final_reason"] == "beforeinfo not ready"
    assert row["racer_index_pred1_lane"] == 2
    assert row["racer_index_signal_date"] == "2026-03-23"


def test_c2_racer_index_overlay_defaults_missing_pred1_to_lane1_beforeinfo(monkeypatch, tmp_path: Path) -> None:
    profile = next(
        profile
        for profile in load_trigger_profiles(ROOT / "live_trigger" / "boxes", include_disabled=True)
        if profile.profile_id == "c2_provisional_v1"
    )
    import boat_race_data.live_trigger as live_trigger

    monkeypatch.setattr(
        live_trigger,
        "_daily_pred1_lane_index",
        lambda race_date_iso: {},
    )

    row = {
        "race_id": "202603230801",
        "race_date": "2026-03-23",
        "stadium_code": "08",
        "race_no": 1,
        "status": "waiting_beforeinfo",
        "pre_reason": "women6_proxy, class=A2",
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

    assert result == {"changed": True, "ready": False}
    assert row["status"] == "filtered_out"
    assert row["final_reason"] == "racer_index_pred1_lane=1 excluded (defaulted_missing_index)"
    assert row["racer_index_pred1_lane"] == 1
    assert row["racer_index_signal_date"] == "2026-03-23"


def test_daily_pred1_lane_index_reloads_when_csv_appears(monkeypatch, tmp_path: Path) -> None:
    import boat_race_data.live_trigger as live_trigger

    shared_root = tmp_path / "shared_reports"
    local_root = tmp_path / "local_reports"
    monkeypatch.setattr(live_trigger, "SHARED_REPORTS_STRATEGY_ROOT", shared_root)
    monkeypatch.setattr(live_trigger, "LOCAL_REPORTS_STRATEGY_ROOT", local_root)
    live_trigger._load_daily_pred1_lane_index_csv.cache_clear()

    assert live_trigger._daily_pred1_lane_index("2026-03-28") == {}

    report_dir = shared_root / "racer_rank_live_20260328"
    report_dir.mkdir(parents=True)
    csv_path = report_dir / "race_summary.csv"
    csv_path.write_text("race_id,pred1_lane\n202603280101,1\n", encoding="utf-8")
    time.sleep(0.01)

    assert live_trigger._daily_pred1_lane_index("2026-03-28") == {"202603280101": 1}
