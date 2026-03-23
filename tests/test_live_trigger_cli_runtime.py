from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from live_trigger_cli import runtime


def test_load_runtime_profiles_includes_local_4wind() -> None:
    profiles = runtime.load_runtime_profiles(include_disabled=True)
    profile_ids = {profile.profile_id for profile in profiles}

    assert "4wind_base_415" in profile_ids


def test_build_bet_rows_supports_4wind_exacta() -> None:
    rows = runtime._build_bet_rows(strategy_id="4wind", profile_id="4wind_base_415", amount=100)

    assert rows == [
        {"bet_type": "exacta", "combo": "4-1", "amount": 100},
        {"bet_type": "exacta", "combo": "4-5", "amount": 100},
    ]


def test_decide_4wind_evaluation_ready() -> None:
    profile = next(
        profile
        for profile in runtime.load_runtime_profiles(include_disabled=True)
        if profile.profile_id == "4wind_base_415"
    )
    row = {"lane3_racer_class": "A1"}
    beforeinfo_rows = [
        {"lane": 1, "exhibition_time": 6.79, "start_exhibition_st": 0.18, "wind_speed_m": 5.0},
        {"lane": 2, "exhibition_time": 6.81, "start_exhibition_st": 0.21, "wind_speed_m": 5.0},
        {"lane": 3, "exhibition_time": 6.80, "start_exhibition_st": 0.19, "wind_speed_m": 5.0},
        {"lane": 4, "exhibition_time": 6.77, "start_exhibition_st": 0.12, "wind_speed_m": 5.0},
    ]
    odds_map = {"4-1": 12.4, "4-5": 24.8}

    decision = runtime._decide_4wind_evaluation(
        row=row,
        profile=profile,
        beforeinfo_rows=beforeinfo_rows,
        odds_map=odds_map,
    )

    assert decision["ready"] is True
    assert decision["status"] == "trigger_ready"
    assert "min_odds=12.40" in decision["reason"]


def test_pending_intent_groups_merge_same_race_and_combine_duplicates(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    runtime.initialize_runtime(runtime_root)

    connection = sqlite3.connect(runtime.db_path(runtime_root))
    connection.row_factory = sqlite3.Row
    try:
        now = datetime(2026, 3, 22, 12, 0, 0)
        deadline = "2026-03-22 12:10:00"

        connection.execute(
            """
            INSERT INTO target_races (
                target_key, race_id, race_date, stadium_code, stadium_name, race_no,
                profile_id, strategy_id, source_watchlist_file, deadline_at, watch_start_at,
                imported_at, updated_at, status, row_status, last_reason, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "202603220101::c2_provisional_v1",
                "202603220101",
                "2026-03-22",
                "01",
                "桐生",
                1,
                "c2_provisional_v1",
                "c2",
                "shared.csv",
                deadline,
                "2026-03-22 11:45:00",
                runtime._format_datetime(now),
                runtime._format_datetime(now),
                "intent_created",
                "trigger_ready",
                "go",
                "{}",
            ),
        )
        connection.execute(
            """
            INSERT INTO target_races (
                target_key, race_id, race_date, stadium_code, stadium_name, race_no,
                profile_id, strategy_id, source_watchlist_file, deadline_at, watch_start_at,
                imported_at, updated_at, status, row_status, last_reason, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "202603220101::4wind_base_415",
                "202603220101",
                "2026-03-22",
                "01",
                "桐生",
                1,
                "4wind_base_415",
                "4wind",
                "local::4wind_base_415",
                deadline,
                "2026-03-22 11:45:00",
                runtime._format_datetime(now),
                runtime._format_datetime(now),
                "intent_created",
                "trigger_ready",
                "go",
                "{}",
            ),
        )
        connection.execute(
            """
            INSERT INTO bet_intents (
                target_race_id, intent_key, execution_mode, status, bet_type, combo, amount, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (1, "a", "assist_real", "pending", "exacta", "4-1", 100, runtime._format_datetime(now)),
        )
        connection.execute(
            """
            INSERT INTO bet_intents (
                target_race_id, intent_key, execution_mode, status, bet_type, combo, amount, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (2, "b", "assist_real", "pending", "exacta", "4-1", 200, runtime._format_datetime(now)),
        )
        connection.commit()

        groups = runtime._pending_intent_groups(connection, target_race_date="2026-03-22")

        assert len(groups) == 1
        assert len(groups[0]) == 2

        combined = runtime._combine_execution_intents(groups[0])

        assert len(combined) == 1
        assert combined[0].bet_type == "exacta"
        assert combined[0].combo == "4-1"
        assert combined[0].amount == 300
    finally:
        connection.close()


def test_build_runtime_watchlist_row_supports_shared_profile() -> None:
    profile = next(
        profile
        for profile in runtime.load_runtime_profiles(include_disabled=True)
        if profile.profile_id == "125_broad_four_stadium"
    )
    race_row = {
        "race_id": "202603230112",
        "race_date": "2026-03-23",
        "stadium_code": "12",
        "stadium_name": "住之江",
        "race_no": 12,
        "meeting_title": "一般",
        "race_title": "予選",
        "deadline_time": "15:20",
    }
    entry_rows = [
        {
            "lane": 1,
            "racer_id": "1001",
            "racer_name": "Lane1",
            "racer_class": "B1",
            "motor_no": "11",
            "motor_place_rate": "34.5",
            "motor_top3_rate": "52.1",
        },
        {"lane": 2, "racer_id": "1002", "racer_name": "Lane2", "racer_class": "A2"},
        {"lane": 3, "racer_id": "1003", "racer_name": "Lane3", "racer_class": "A1"},
        {"lane": 4, "racer_id": "1004", "racer_name": "Lane4", "racer_class": "A2"},
        {"lane": 5, "racer_id": "1005", "racer_name": "Lane5", "racer_class": "B1"},
        {"lane": 6, "racer_id": "1006", "racer_name": "Lane6", "racer_class": "B2"},
    ]

    row = runtime._build_runtime_watchlist_row(race_row, entry_rows, profile)

    assert row is not None
    assert row["profile_id"] == "125_broad_four_stadium"
    assert row["strategy_id"] == "125"
    assert row["race_id"] == "202603230112"
    assert row["status"] == "waiting_beforeinfo"


def test_build_runtime_watchlist_row_excludes_final_day_for_local_profile() -> None:
    profile = next(
        profile
        for profile in runtime.load_runtime_profiles(include_disabled=True)
        if profile.profile_id == "4wind_base_415"
    )
    race_row = {
        "race_id": "202603230112",
        "race_date": "2026-03-23",
        "stadium_code": "24",
        "stadium_name": "大村",
        "race_no": 12,
        "meeting_title": "一般",
        "race_title": "予選",
        "deadline_time": "15:20",
        "is_final_day": 1,
    }
    entry_rows = [
        {"lane": 1, "racer_id": "1001", "racer_name": "Lane1", "racer_class": "B1"},
        {"lane": 2, "racer_id": "1002", "racer_name": "Lane2", "racer_class": "A2"},
        {"lane": 3, "racer_id": "1003", "racer_name": "Lane3", "racer_class": "A1"},
        {"lane": 4, "racer_id": "1004", "racer_name": "Lane4", "racer_class": "A2"},
        {"lane": 5, "racer_id": "1005", "racer_name": "Lane5", "racer_class": "B1"},
        {"lane": 6, "racer_id": "1006", "racer_name": "Lane6", "racer_class": "B2"},
    ]

    row = runtime._build_runtime_watchlist_row(race_row, entry_rows, profile)

    assert row is None


def test_build_runtime_watchlist_row_supports_c2_all_women_proxy(monkeypatch) -> None:
    profile = next(
        profile
        for profile in runtime.load_runtime_profiles(include_disabled=True)
        if profile.profile_id == "c2_provisional_v1"
    )
    monkeypatch.setattr(
        runtime,
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

    row = runtime._build_runtime_watchlist_row(race_row, entry_rows, profile)

    assert row is not None
    assert row["profile_id"] == "c2_provisional_v1"
    assert row["race_id"] == "202603230801"
    assert row["pre_reason"] == "women6_proxy, class=A2"
    assert row["lane3_racer_class"] == "B2"
    assert row["lane5_racer_class"] == "B2"


def test_build_runtime_watchlist_sources_collects_shared_and_local_profiles(
    monkeypatch,
    tmp_path: Path,
) -> None:
    profiles = runtime.load_runtime_profiles(include_disabled=True)
    selected_profiles = [
        profile
        for profile in profiles
        if profile.profile_id in {"125_broad_four_stadium", "c2_provisional_v1", "4wind_base_415"}
    ]
    c2_profile = next(profile for profile in selected_profiles if profile.profile_id == "c2_provisional_v1")
    meeting_title = c2_profile.shared_profile.meeting_title_keywords_any[0]

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def discover_active_stadiums(self, race_date: str) -> list[str]:
            return ["24"]

        def build_race_url(self, page: str, race_date: str, stadium_code: str, race_no: int) -> str:
            return f"{page}:{race_date}:{stadium_code}:{race_no}"

    def fake_fetch_text_cached(client, url: str, raw_path: Path) -> SimpleNamespace:
        return SimpleNamespace(
            url=url,
            fetched_at="2026-03-22T10:00:00",
            raw_path=raw_path,
            content=b"",
            text="<html></html>",
        )

    def fake_parse_racelist(
        text: str,
        race_date: str,
        stadium_code: str,
        stadium_name: str,
        race_no: int,
        url: str,
        fetched_at: str,
    ) -> tuple[dict[str, object], list[dict[str, object]]]:
        race_row = {
            "race_id": f"{race_date}{stadium_code}{race_no:02d}",
            "race_date": datetime.strptime(race_date, "%Y%m%d").strftime("%Y-%m-%d"),
            "stadium_code": stadium_code,
            "stadium_name": stadium_name,
            "race_no": race_no,
            "meeting_title": meeting_title,
            "race_title": "予選",
            "deadline_time": "15:20",
        }
        entry_rows = [
            {
                "lane": 1,
                "racer_id": "1001",
                "racer_name": "Lane1",
                "racer_class": "B1",
                "motor_no": "11",
                "motor_place_rate": "34.5",
                "motor_top3_rate": "52.1",
            },
            {"lane": 2, "racer_id": "1002", "racer_name": "Lane2", "racer_class": "A2"},
            {"lane": 3, "racer_id": "1003", "racer_name": "Lane3", "racer_class": "A1"},
            {"lane": 4, "racer_id": "1004", "racer_name": "Lane4", "racer_class": "A2"},
            {"lane": 5, "racer_id": "1005", "racer_name": "Lane5", "racer_class": "B1"},
            {"lane": 6, "racer_id": "1006", "racer_name": "Lane6", "racer_class": "B2"},
        ]
        return race_row, entry_rows

    monkeypatch.setattr(runtime, "load_runtime_profiles", lambda *args, **kwargs: selected_profiles)
    monkeypatch.setattr(runtime, "BoatRaceClient", FakeClient)
    monkeypatch.setattr(runtime, "_fetch_text_cached", fake_fetch_text_cached)
    monkeypatch.setattr(runtime, "parse_racelist", fake_parse_racelist)

    source_rows, source_names = runtime._build_runtime_watchlist_sources(
        runtime_root=tmp_path / "runtime",
        race_date="2026-03-23",
    )

    assert set(source_names) == {
        "shared::125_broad_four_stadium",
        "shared::c2_provisional_v1",
        "local::4wind_base_415",
    }
    assert {name for name, _ in source_rows} == set(source_names)


def test_normalize_settings_accepts_telegram_fields() -> None:
    settings = runtime._normalize_settings(
        {
            "telegram_enabled": "true",
            "telegram_go_notifications": "1",
            "telegram_bot_token": "token-123",
            "telegram_chat_id": "456",
        }
    )

    assert settings["telegram_enabled"] is True
    assert settings["telegram_go_notifications"] is True
    assert settings["telegram_bot_token"] == "token-123"
    assert settings["telegram_chat_id"] == "456"


def test_notify_telegram_go_logs_once(monkeypatch, tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    runtime.initialize_runtime(runtime_root)
    connection = sqlite3.connect(runtime.db_path(runtime_root))
    connection.row_factory = sqlite3.Row
    try:
        now = runtime._format_datetime(datetime(2026, 3, 23, 10, 0, 0))
        connection.execute(
            """
            INSERT INTO target_races (
                target_key, race_id, race_date, stadium_code, stadium_name, race_no,
                profile_id, strategy_id, source_watchlist_file, deadline_at, watch_start_at,
                imported_at, updated_at, status, row_status, last_reason, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "202603230101::4wind_base_415",
                "202603230101",
                "2026-03-23",
                "01",
                "桐生",
                1,
                "4wind_base_415",
                "4wind",
                "local::4wind_base_415",
                "2026-03-23 10:10:00",
                "2026-03-23 09:55:00",
                now,
                now,
                "intent_created",
                "trigger_ready",
                "go",
                "{}",
            ),
        )
        connection.execute(
            """
            INSERT INTO bet_intents (
                target_race_id, intent_key, execution_mode, status, bet_type, combo, amount, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (1, "intent-a", "assist_real", "pending", "exacta", "4-1", 100, now),
        )
        settings = runtime._normalize_settings(
            {
                "telegram_enabled": True,
                "telegram_go_notifications": True,
                "telegram_bot_token": "token-123",
                "telegram_chat_id": "999",
            }
        )
        sent_payloads: list[tuple[str, str, str]] = []

        def fake_send_message(*, token: str, chat_id: str, text: str) -> dict[str, object]:
            sent_payloads.append((token, chat_id, text))
            return {"ok": True, "result": {"message_id": 321}}

        monkeypatch.setattr(runtime, "_telegram_send_message", fake_send_message)
        target = connection.execute("SELECT * FROM target_races WHERE id = 1").fetchone()

        sent = runtime._notify_telegram_go(
            connection,
            target=target,
            settings=settings,
            reason="min_odds=12.40",
            mode="assist_real",
        )
        sent_again = runtime._notify_telegram_go(
            connection,
            target=target,
            settings=settings,
            reason="min_odds=12.40",
            mode="assist_real",
        )

        logged = connection.execute(
            "SELECT event_type, message FROM execution_events WHERE event_type = 'telegram_go_notified'"
        ).fetchall()

        assert sent is True
        assert sent_again is False
        assert len(sent_payloads) == 1
        assert sent_payloads[0][0] == "token-123"
        assert sent_payloads[0][1] == "999"
        assert "GO" in sent_payloads[0][2]
        assert "4wind_base_415" in sent_payloads[0][2]
        assert len(logged) == 1
    finally:
        connection.close()


def test_evaluate_runtime_row_for_shared_profile_uses_runtime_raw_root(monkeypatch, tmp_path: Path) -> None:
    profile = next(
        profile
        for profile in runtime.load_runtime_profiles(include_disabled=True)
        if profile.profile_id == "125_broad_four_stadium"
    )
    captured: dict[str, object] = {}

    def fake_enrich(row, shared_profile, client, raw_root: Path) -> dict[str, bool]:
        captured["row"] = row
        captured["shared_profile_id"] = shared_profile.profile_id
        captured["raw_root"] = raw_root
        return {"changed": True, "ready": False}

    monkeypatch.setattr(runtime, "enrich_watchlist_row_with_beforeinfo", fake_enrich)

    row = {
        "race_date": "2026-03-23",
        "stadium_code": "24",
        "race_no": 12,
    }
    runtime_root = tmp_path / "runtime"

    result = runtime._evaluate_runtime_row(
        runtime_root=runtime_root,
        row=row,
        profile=profile,
        client=object(),
    )

    assert result == {"changed": True, "ready": False}
    assert captured["shared_profile_id"] == "125_broad_four_stadium"
    assert captured["raw_root"] == runtime.raw_root(runtime_root)


def test_sync_watchlists_withdraws_disabled_profile_targets(monkeypatch, tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    runtime.initialize_runtime(runtime_root)
    runtime.save_settings(
        runtime_root,
        {
            "active_profiles": {
                "4wind_base_415": True,
                "c2_provisional_v1": False,
            }
        },
    )

    profiles = runtime.load_runtime_profiles(include_disabled=True)
    selected_profiles = [
        profile
        for profile in profiles
        if profile.profile_id in {"c2_provisional_v1", "4wind_base_415"}
    ]
    c2_profile = next(profile for profile in selected_profiles if profile.profile_id == "c2_provisional_v1")
    meeting_title = c2_profile.shared_profile.meeting_title_keywords_any[0]

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def discover_active_stadiums(self, race_date: str) -> list[str]:
            return ["24"]

        def build_race_url(self, page: str, race_date: str, stadium_code: str, race_no: int) -> str:
            return f"{page}:{race_date}:{stadium_code}:{race_no}"

    def fake_fetch_text_cached(client, url: str, raw_path: Path) -> SimpleNamespace:
        return SimpleNamespace(
            url=url,
            fetched_at="2026-03-23T06:00:00",
            raw_path=raw_path,
            content=b"",
            text="<html></html>",
        )

    def fake_parse_racelist(
        text: str,
        race_date: str,
        stadium_code: str,
        stadium_name: str,
        race_no: int,
        url: str,
        fetched_at: str,
    ) -> tuple[dict[str, object], list[dict[str, object]]]:
        race_row = {
            "race_id": f"{race_date}{stadium_code}{race_no:02d}",
            "race_date": datetime.strptime(race_date, "%Y%m%d").strftime("%Y-%m-%d"),
            "stadium_code": stadium_code,
            "stadium_name": stadium_name,
            "race_no": race_no,
            "meeting_title": meeting_title,
            "race_title": "Test Race",
            "deadline_time": "15:20",
        }
        entry_rows = [
            {
                "lane": 1,
                "racer_id": "1001",
                "racer_name": "Lane1",
                "racer_class": "B1",
                "motor_no": "11",
                "motor_place_rate": "34.5",
                "motor_top3_rate": "52.1",
            },
            {"lane": 2, "racer_id": "1002", "racer_name": "Lane2", "racer_class": "A2"},
            {"lane": 3, "racer_id": "1003", "racer_name": "Lane3", "racer_class": "A1"},
            {"lane": 4, "racer_id": "1004", "racer_name": "Lane4", "racer_class": "A2"},
            {"lane": 5, "racer_id": "1005", "racer_name": "Lane5", "racer_class": "B1"},
            {"lane": 6, "racer_id": "1006", "racer_name": "Lane6", "racer_class": "B2"},
        ]
        return race_row, entry_rows

    monkeypatch.setattr(runtime, "load_runtime_profiles", lambda *args, **kwargs: selected_profiles)
    monkeypatch.setattr(runtime, "BoatRaceClient", FakeClient)
    monkeypatch.setattr(runtime, "_fetch_text_cached", fake_fetch_text_cached)
    monkeypatch.setattr(runtime, "parse_racelist", fake_parse_racelist)

    with runtime._connect_db(runtime_root) as connection:
        now = datetime(2026, 3, 23, 6, 0, 0)
        connection.execute(
            """
            INSERT INTO target_races (
                target_key, race_id, race_date, stadium_code, stadium_name, race_no,
                profile_id, strategy_id, source_watchlist_file, deadline_at, watch_start_at,
                imported_at, updated_at, status, row_status, last_reason, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "202603232401::c2_provisional_v1",
                "202603232401",
                "2026-03-23",
                "24",
                "Dummy",
                1,
                "c2_provisional_v1",
                "c2",
                "shared::c2_provisional_v1",
                "2026-03-23 15:20:00",
                "2026-03-23 14:55:00",
                runtime._format_datetime(now),
                runtime._format_datetime(now),
                "imported",
                "waiting_beforeinfo",
                "existing c2 row",
                "{}",
            ),
        )
        connection.commit()

    result = runtime.sync_watchlists(runtime_root=runtime_root, race_date="2026-03-23")

    assert result["shared_profiles"] == 0
    assert result["local_profiles"] == 1
    assert result["withdrawn"] == 1

    with runtime._connect_db(runtime_root) as connection:
        rows = connection.execute(
            """
            SELECT profile_id, status
            FROM target_races
            WHERE race_date = '2026-03-23'
            ORDER BY profile_id
            """
        ).fetchall()

    assert [tuple(row) for row in rows] == [
        ("4wind_base_415", "imported"),
        ("4wind_base_415", "imported"),
        ("4wind_base_415", "imported"),
        ("4wind_base_415", "imported"),
        ("4wind_base_415", "imported"),
        ("4wind_base_415", "imported"),
        ("4wind_base_415", "imported"),
        ("4wind_base_415", "imported"),
        ("4wind_base_415", "imported"),
        ("4wind_base_415", "imported"),
        ("4wind_base_415", "imported"),
        ("4wind_base_415", "imported"),
        ("c2_provisional_v1", "withdrawn"),
    ]


def test_auto_loop_refuses_duplicate_process(monkeypatch, tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    runtime.initialize_runtime(runtime_root)
    runtime.save_settings(runtime_root, {"system_running": True})

    called = {"run_cycle": 0}

    def fake_claim(runtime_root_arg: Path) -> int | None:
        assert runtime_root_arg == runtime_root
        return 4242

    def fake_run_cycle(runtime_root_arg: Path) -> dict[str, object]:
        called["run_cycle"] += 1
        return {}

    monkeypatch.setattr(runtime, "_claim_auto_loop_pid", fake_claim)
    monkeypatch.setattr(runtime, "run_cycle", fake_run_cycle)

    result = runtime.auto_loop(runtime_root=runtime_root, max_cycles=1)

    assert result == {
        "cycles": 0,
        "stopped": True,
        "already_running": True,
        "existing_pid": 4242,
    }
    assert called["run_cycle"] == 0
