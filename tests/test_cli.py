from boat_race_data.cli import MIN_RANGE_SLEEP_SECONDS, _normalize_sleep_seconds, build_parser


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
