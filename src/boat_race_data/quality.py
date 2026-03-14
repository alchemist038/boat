from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import duckdb

from boat_race_data.utils import ensure_dir


def _rows_to_markdown(headers: list[str], rows: list[tuple[object, ...]]) -> str:
    if not rows:
        return "_none_"
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows[:20]:
        lines.append("| " + " | ".join("" if item is None else str(item) for item in row) + " |")
    return "\n".join(lines)


def generate_quality_report(db_path: Path, report_date: str, output_dir: Path) -> Path:
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        duplicate_race_ids = con.execute(
            """
            SELECT race_id, COUNT(*) AS duplicate_count
            FROM races
            GROUP BY 1
            HAVING COUNT(*) > 1
            ORDER BY duplicate_count DESC, race_id
            """
        ).fetchall()
        invalid_entry_counts = con.execute(
            """
            SELECT race_id, COUNT(*) AS entry_count
            FROM entries
            GROUP BY 1
            HAVING COUNT(*) <> 6
            ORDER BY race_id
            """
        ).fetchall()
        results_without_entries = con.execute(
            """
            SELECT r.race_id
            FROM results r
            LEFT JOIN (SELECT DISTINCT race_id FROM entries) e USING (race_id)
            WHERE e.race_id IS NULL
            ORDER BY r.race_id
            """
        ).fetchall()
        odds_2t_missing = con.execute(
            """
            SELECT race_id, bet_type, COUNT(*) AS available_rows
            FROM odds_2t
            GROUP BY 1, 2
            HAVING
              (bet_type = '2連単' AND COUNT(*) <> 30)
              OR (bet_type = '2連複' AND COUNT(*) <> 15)
            ORDER BY race_id, bet_type
            """
        ).fetchall()
        odds_3t_missing = con.execute(
            """
            SELECT race_id, COUNT(*) AS available_rows
            FROM odds_3t
            GROUP BY 1
            HAVING COUNT(*) <> 120
            ORDER BY race_id
            """
        ).fetchall()
        counts = con.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM races) AS races,
              (SELECT COUNT(*) FROM entries) AS entries,
              (SELECT COUNT(*) FROM odds_2t) AS odds_2t,
              (SELECT COUNT(*) FROM odds_3t) AS odds_3t,
              (SELECT COUNT(*) FROM results) AS results,
              (SELECT COUNT(*) FROM beforeinfo_entries) AS beforeinfo_entries,
              (SELECT COUNT(*) FROM race_meta) AS race_meta,
              (SELECT COUNT(*) FROM racer_stats_term) AS racer_stats_term
            """
        ).fetchone()
    finally:
        con.close()

    ensure_dir(output_dir)
    report_path = output_dir / f"{report_date}.md"
    report = "\n".join(
        [
            f"# Data Quality Report {report_date}",
            "",
            f"- generated_at_utc: {datetime.now(timezone.utc).isoformat()}",
            f"- races: {counts[0]}",
            f"- entries: {counts[1]}",
            f"- odds_2t: {counts[2]}",
            f"- odds_3t: {counts[3]}",
            f"- results: {counts[4]}",
            f"- beforeinfo_entries: {counts[5]}",
            f"- race_meta: {counts[6]}",
            f"- racer_stats_term: {counts[7]}",
            "",
            "## Duplicate race_id in races",
            _rows_to_markdown(["race_id", "duplicate_count"], duplicate_race_ids),
            "",
            "## Non-6 entry counts",
            _rows_to_markdown(["race_id", "entry_count"], invalid_entry_counts),
            "",
            "## Results without entries",
            _rows_to_markdown(["race_id"], results_without_entries),
            "",
            "## odds_2t missing counts",
            _rows_to_markdown(["race_id", "bet_type", "available_rows"], odds_2t_missing),
            "",
            "## odds_3t missing counts",
            _rows_to_markdown(["race_id", "available_rows"], odds_3t_missing),
            "",
        ]
    )
    report_path.write_text(report, encoding="utf-8")
    return report_path
