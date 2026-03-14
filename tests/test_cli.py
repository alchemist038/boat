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
