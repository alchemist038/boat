from pathlib import Path

from boat_race_data.mbrace import (
    _normalize_grade_from_title,
    _parse_k_finish_token,
    parse_mbrace_b_schedule,
    parse_mbrace_k_results,
)


ROOT = Path(__file__).resolve().parents[1]
DEBUG_SAMPLE_ROOT = ROOT / "docs" / "manual_debug_samples" / "20260313_root_cleanup"
CANONICAL_DATA_ROOT = Path(r"C:\boat\data")


def _first_existing_path(*candidates: Path) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("sample file not found: " + ", ".join(str(path) for path in candidates))


def _read_sample_text(*candidates: Path) -> str:
    return _first_existing_path(*candidates).read_text(encoding="cp932", errors="replace")


def test_parse_mbrace_b_schedule_sample_day() -> None:
    text = _read_sample_text(ROOT / "B260306.TXT", DEBUG_SAMPLE_ROOT / "B260306.TXT")
    tables = parse_mbrace_b_schedule(text, "20260306", "test://b", "2026-03-11T00:00:00+00:00")

    assert len(tables["races"]) > 100
    assert len(tables["entries"]) == len(tables["races"]) * 6
    assert len(tables["race_meta"]) == len(tables["races"])

    race = next(row for row in tables["races"] if row["race_id"] == "202603062301")
    assert race["stadium_code"] == "23"
    assert race["race_no"] == 1
    assert race["deadline_time"] == "08:47"

    entry = next(
        row for row in tables["entries"] if row["race_id"] == "202603062301" and row["lane"] == 1
    )
    assert entry["racer_id"] == 5129
    assert entry["racer_class"] == "A2"
    assert entry["motor_place_rate"] == 29.79

    meta = next(row for row in tables["race_meta"] if row["race_id"] == "202603062301")
    assert meta["meeting_day_no"] == 1


def test_parse_mbrace_k_results_sample_day() -> None:
    text = _read_sample_text(ROOT / "K260306.TXT", DEBUG_SAMPLE_ROOT / "K260306.TXT")
    tables = parse_mbrace_k_results(text, "20260306", "test://k", "2026-03-11T00:00:00+00:00")

    assert len(tables["results"]) > 100
    assert len(tables["beforeinfo_entries"]) >= len(tables["results"]) * 5

    result = next(row for row in tables["results"] if row["race_id"] == "202603062301")
    assert result["first_place_lane"] == 1
    assert result["second_place_lane"] == 6
    assert result["third_place_lane"] == 2
    assert result["exacta_combo"] == "1-6"
    assert result["trifecta_combo"] == "1-6-2"
    assert result["wind_speed_m"] == 1

    beforeinfo = next(
        row for row in tables["beforeinfo_entries"] if row["race_id"] == "202603062301" and row["lane"] == 1
    )
    assert beforeinfo["exhibition_time"] == 6.71
    assert beforeinfo["course_entry"] == 1
    assert beforeinfo["start_exhibition_st"] == 0.16


def test_parse_mbrace_k_results_preserves_placeholder_columns_for_lower_finishers() -> None:
    text = _read_sample_text(
        ROOT / "data" / "raw" / "mbrace_k" / "202512" / "K251208.TXT",
        CANONICAL_DATA_ROOT / "raw" / "mbrace_k" / "202512" / "K251208.TXT",
    )
    tables = parse_mbrace_k_results(text, "20251208", "test://k", "2026-03-12T00:00:00+00:00")

    lane6 = next(
        row for row in tables["beforeinfo_entries"] if row["race_id"] == "202512082201" and row["lane"] == 6
    )
    lane4 = next(
        row for row in tables["beforeinfo_entries"] if row["race_id"] == "202512082201" and row["lane"] == 4
    )

    assert lane6["racer_id"] == 5200
    assert lane6["exhibition_time"] == 6.83
    assert lane6["course_entry"] == 6
    assert lane6["start_exhibition_st"] == 0.18

    assert lane4["racer_id"] == 5389
    assert lane4["exhibition_time"] == 6.81
    assert lane4["course_entry"] == 5
    assert lane4["start_exhibition_st"] == 0.22


def test_parse_k_finish_token_ignores_special_result_codes() -> None:
    assert _parse_k_finish_token("01") == 1
    assert _parse_k_finish_token("6") == 6
    assert _parse_k_finish_token("S1") is None
    assert _parse_k_finish_token("K0") is None
    assert _parse_k_finish_token("F") is None


def test_parse_mbrace_k_results_keeps_beforeinfo_rows_with_special_finish_codes() -> None:
    text = _read_sample_text(
        ROOT / "data" / "raw" / "mbrace_k" / "202303" / "K230311.TXT",
        CANONICAL_DATA_ROOT / "raw" / "mbrace_k" / "202303" / "K230311.TXT",
    )
    tables = parse_mbrace_k_results(text, "20230311", "test://k", "2026-03-13T00:00:00+00:00")

    special_row = next(
        row for row in tables["beforeinfo_entries"] if row["race_id"] == "202303112005" and row["lane"] == 3
    )

    assert special_row["racer_id"] == 5054
    assert special_row["exhibition_time"] == 6.78
    assert special_row["course_entry"] == 3
    assert special_row["start_exhibition_st"] == 0.01
    assert special_row["start_exhibition_status"] == "F"


def test_normalize_grade_from_title_heuristics() -> None:
    assert _normalize_grade_from_title("第14回クイーンズクライマックス/G3QCシリーズ")[0] == "SG"
    assert _normalize_grade_from_title("開設73周年記念 海の王者決定戦")[0] == "G1"
