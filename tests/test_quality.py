from pathlib import Path

import duckdb

from boat_race_data.quality import generate_quality_report


def test_generate_quality_report_lists_possible_canceled_races(tmp_path: Path) -> None:
    db_path = tmp_path / "boat_race.duckdb"
    report_dir = tmp_path / "reports"
    con = duckdb.connect(str(db_path))
    try:
        con.execute(
            """
            CREATE TABLE races (
              race_id VARCHAR,
              race_date DATE,
              stadium_code VARCHAR,
              stadium_name VARCHAR,
              race_no INTEGER
            )
            """
        )
        con.execute("CREATE TABLE entries (race_id VARCHAR)")
        con.execute("CREATE TABLE odds_2t (race_id VARCHAR, bet_type VARCHAR)")
        con.execute("CREATE TABLE odds_3t (race_id VARCHAR)")
        con.execute("CREATE TABLE results (race_id VARCHAR)")
        con.execute("CREATE TABLE beforeinfo_entries (race_id VARCHAR)")
        con.execute("CREATE TABLE race_meta (race_id VARCHAR)")
        con.execute("CREATE TABLE racer_stats_term (racer_id INTEGER)")

        con.execute(
            """
            INSERT INTO races VALUES
              ('20260310_08_07', '2026-03-10', '08', '常滑', 7),
              ('20260310_08_06', '2026-03-10', '08', '常滑', 6)
            """
        )
        con.execute(
            """
            INSERT INTO entries VALUES
              ('20260310_08_07'),
              ('20260310_08_06')
            """
        )
        con.execute("INSERT INTO beforeinfo_entries VALUES ('20260310_08_07')")
        con.execute("INSERT INTO results VALUES ('20260310_08_06')")
        con.execute(
            """
            INSERT INTO odds_2t VALUES
              ('20260310_08_06', '2連単'),
              ('20260310_08_06', '2連複')
            """
        )
        con.execute("INSERT INTO odds_3t VALUES ('20260310_08_06')")
    finally:
        con.close()

    report_path = generate_quality_report(db_path, "20260310", report_dir)
    report = report_path.read_text(encoding="utf-8")

    assert "## Races without results" in report
    assert "## Races without odds_2t" in report
    assert "## Races without odds_3t" in report
    assert "## Possible canceled or aborted races" in report
    assert "20260310_08_07" in report
    assert "常滑" in report
    assert "yes" in report
