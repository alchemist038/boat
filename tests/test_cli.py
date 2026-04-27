import boat_race_data.constants as constants
from boat_race_data.cli import MIN_RANGE_SLEEP_SECONDS, _normalize_sleep_seconds, build_parser
from boat_race_data.constants import (
    get_default_canonical_root,
    get_default_db_path,
    get_default_predict_script_path,
    get_default_raw_root,
    get_default_bronze_root,
    get_default_reports_root,
)


def test_normalize_sleep_seconds_keeps_safe_value() -> None:
    assert _normalize_sleep_seconds("collect-range", 0.75, MIN_RANGE_SLEEP_SECONDS) == 0.75


def test_normalize_sleep_seconds_clamps_collect_range_minimum() -> None:
    assert _normalize_sleep_seconds("collect-range", 0.1, MIN_RANGE_SLEEP_SECONDS) == MIN_RANGE_SLEEP_SECONDS


def test_collect_range_accepts_custom_worker_roots() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "collect-range",
            "--start-date",
            "20250401",
            "--end-date",
            "20250930",
            "--raw-root",
            "work/boat_a/raw",
            "--bronze-root",
            "work/boat_a/bronze",
            "--db-path",
            "work/boat_a/silver/boat_race.duckdb",
        ]
    )

    assert args.raw_root == "work/boat_a/raw"
    assert args.bronze_root == "work/boat_a/bronze"
    assert args.db_path == "work/boat_a/silver/boat_race.duckdb"


def test_parser_uses_boat_data_root_env_for_default_paths(monkeypatch) -> None:
    monkeypatch.setenv("BOAT_DATA_ROOT", r"\\038INS\boat\data")
    parser = build_parser()

    args = parser.parse_args(["refresh-silver"])

    assert args.bronze_root == r"\\038INS\boat\data\bronze"
    assert args.db_path == r"\\038INS\boat\data\silver\boat_race.duckdb"


def test_parser_prefers_explicit_db_path_env(monkeypatch) -> None:
    monkeypatch.setenv("BOAT_DATA_ROOT", r"\\038INS\boat\data")
    monkeypatch.setenv("BOAT_DB_PATH", r"\\038INS\boat\data\silver\boat_race_stage.duckdb")
    parser = build_parser()

    args = parser.parse_args(["collect-range", "--start-date", "20250401", "--end-date", "20250402"])

    assert args.raw_root == r"\\038INS\boat\data\raw"
    assert args.bronze_root == r"\\038INS\boat\data\bronze"
    assert args.db_path == r"\\038INS\boat\data\silver\boat_race_stage.duckdb"


def test_parser_uses_boat_live_trigger_root_env_for_trigger_paths(monkeypatch) -> None:
    monkeypatch.setenv("BOAT_LIVE_TRIGGER_ROOT", r"D:\portable\live_trigger")
    parser = build_parser()

    args = parser.parse_args(["build-watchlist", "--date", "20260319"])

    assert args.profile_path == r"D:\portable\live_trigger\boxes\125\profiles\suminoe_main.json"
    assert args.output_path == r"D:\portable\live_trigger\watchlists\latest.csv"
    assert args.raw_root == r"D:\portable\live_trigger\raw"


def test_canonical_root_defaults_from_boat_data_root(monkeypatch) -> None:
    monkeypatch.delenv("BOAT_CANONICAL_ROOT", raising=False)
    monkeypatch.delenv("BOAT_REPORTS_ROOT", raising=False)
    monkeypatch.delenv("BOAT_PREDICT_SCRIPT_PATH", raising=False)
    monkeypatch.setenv("BOAT_DATA_ROOT", r"C:\boat\data")

    assert get_default_canonical_root() == r"C:\boat"
    assert get_default_reports_root() == r"C:\boat\reports\strategies"
    assert get_default_predict_script_path() == r"C:\boat\workspace_codex\scripts\predict_racer_rank_live.py"


def test_canonical_root_helpers_prefer_explicit_overrides(monkeypatch) -> None:
    monkeypatch.setenv("BOAT_DATA_ROOT", r"C:\boat\data")
    monkeypatch.setenv("BOAT_CANONICAL_ROOT", r"D:\ops\boat")
    monkeypatch.setenv("BOAT_REPORTS_ROOT", r"D:\ops\reports\strategies")
    monkeypatch.setenv("BOAT_PREDICT_SCRIPT_PATH", r"D:\ops\scripts\predict_racer_rank_live.py")

    assert get_default_canonical_root() == r"D:\ops\boat"
    assert get_default_reports_root() == r"D:\ops\reports\strategies"
    assert get_default_predict_script_path() == r"D:\ops\scripts\predict_racer_rank_live.py"


def test_default_paths_prefer_local_canonical_root_when_available(monkeypatch, tmp_path) -> None:
    local_root = tmp_path / "boat"
    (local_root / "data" / "raw").mkdir(parents=True)
    (local_root / "data" / "bronze").mkdir(parents=True)
    (local_root / "data" / "silver").mkdir(parents=True)
    (local_root / "data" / "silver" / "boat_race.duckdb").write_text("", encoding="utf-8")
    monkeypatch.delenv("BOAT_CANONICAL_ROOT", raising=False)
    monkeypatch.delenv("BOAT_DATA_ROOT", raising=False)
    monkeypatch.delenv("BOAT_RAW_ROOT", raising=False)
    monkeypatch.delenv("BOAT_BRONZE_ROOT", raising=False)
    monkeypatch.delenv("BOAT_DB_PATH", raising=False)
    monkeypatch.setattr(constants, "LOCAL_CANONICAL_ROOT", local_root)
    monkeypatch.setattr(constants, "_package_canonical_root", lambda: None)

    assert get_default_canonical_root() == str(local_root)
    assert get_default_raw_root() == str(local_root / "data" / "raw")
    assert get_default_bronze_root() == str(local_root / "data" / "bronze")
    assert get_default_db_path() == str(local_root / "data" / "silver" / "boat_race.duckdb")
