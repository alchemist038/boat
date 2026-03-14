from boat_race_data.utils import clean_text, era_date_to_iso, make_race_id, scaled_int


def test_make_race_id_preserves_stadium_code_padding() -> None:
    assert make_race_id("20260306", "01", 1) == "202603060101"


def test_clean_text_normalizes_full_width_digits() -> None:
    assert clean_text("　３連単　") == "3連単"


def test_scaled_int_handles_decimal_conversion() -> None:
    assert scaled_int("0739", 1) == 73.9
    assert scaled_int("015", 2) == 0.15


def test_era_date_to_iso() -> None:
    assert era_date_to_iso("S", "240426") == "1949-04-26"
