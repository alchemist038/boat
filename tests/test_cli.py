from boat_race_data.cli import MIN_RANGE_SLEEP_SECONDS, _normalize_sleep_seconds


def test_normalize_sleep_seconds_keeps_safe_value() -> None:
    assert _normalize_sleep_seconds("collect-range", 0.75, MIN_RANGE_SLEEP_SECONDS) == 0.75


def test_normalize_sleep_seconds_clamps_collect_range_minimum() -> None:
    assert _normalize_sleep_seconds("collect-range", 0.1, MIN_RANGE_SLEEP_SECONDS) == MIN_RANGE_SLEEP_SECONDS
