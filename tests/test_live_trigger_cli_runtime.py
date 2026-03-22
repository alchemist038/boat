from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

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
