from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import duckdb


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = REPO_ROOT / "data" / "silver" / "boat_race.duckdb"
DEFAULT_RAW_ROOT = REPO_ROOT / "data" / "raw"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "workspace_codex" / "reports" / "data_quality" / "allowed_missing_latest"

RACE_CANCELLED_TEXT = "".join(map(chr, [0x30EC, 0x30FC, 0x30B9, 0x4E2D, 0x6B62]))
STADIUM_NAMES = {
    "01": "\u6850\u751f",
    "02": "\u6238\u7530",
    "03": "\u6c5f\u6238\u5ddd",
    "04": "\u5e73\u548c\u5cf6",
    "05": "\u591a\u6469\u5ddd",
    "06": "\u6d5c\u540d\u6e56",
    "07": "\u84b2\u90e1",
    "08": "\u5e38\u6ed1",
    "09": "\u6d25",
    "10": "\u4e09\u56fd",
    "11": "\u3073\u308f\u3053",
    "12": "\u4f4f\u4e4b\u6c5f",
    "13": "\u5c3c\u5d0e",
    "14": "\u9cf4\u9580",
    "15": "\u4e38\u4e80",
    "16": "\u5150\u5cf6",
    "17": "\u5bae\u5cf6",
    "18": "\u5fb3\u5c71",
    "19": "\u4e0b\u95a2",
    "20": "\u82e5\u677e",
    "21": "\u82a6\u5c4b",
    "22": "\u798f\u5ca1",
    "23": "\u5510\u6d25",
    "24": "\u5927\u6751",
}


@dataclass(frozen=True)
class MissingRace:
    race_date: str
    stadium_code: str
    stadium_name: str
    race_no: int
    race_id: str
    result_missing: bool
    odds2_rows: int
    odds3_rows: int
    beforeinfo_rows: int

    @property
    def missing_tables(self) -> list[str]:
        tables: list[str] = []
        if self.result_missing:
            tables.append("results")
        if self.odds2_rows < 45:
            tables.append("odds_2t")
        if self.odds3_rows < 120:
            tables.append("odds_3t")
        if self.beforeinfo_rows < 6:
            tables.append("beforeinfo_entries")
        return tables


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split DB missing settlement/odds rows into official cancellations and true missing rows."
    )
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--start-date", required=True, help="Inclusive YYYY-MM-DD date.")
    parser.add_argument("--end-date", required=True, help="Inclusive YYYY-MM-DD date.")
    return parser.parse_args()


def fetch_missing_rows(db_path: Path, start_date: str, end_date: str) -> list[MissingRace]:
    con = duckdb.connect(str(db_path), read_only=True)
    rows = con.sql(
        """
        SELECT
            CAST(r.race_date AS VARCHAR) AS race_date,
            r.stadium_code,
            r.stadium_name,
            r.race_no,
            r.race_id,
            res.race_id IS NULL AS result_missing,
            COALESCE(o2.c, 0) AS odds2_rows,
            COALESCE(o3.c, 0) AS odds3_rows,
            COALESCE(b.c, 0) AS beforeinfo_rows
        FROM races r
        LEFT JOIN results res ON res.race_id = r.race_id
        LEFT JOIN (
            SELECT race_id, COUNT(*) AS c
            FROM odds_2t
            GROUP BY race_id
        ) o2 ON o2.race_id = r.race_id
        LEFT JOIN (
            SELECT race_id, COUNT(*) AS c
            FROM odds_3t
            GROUP BY race_id
        ) o3 ON o3.race_id = r.race_id
        LEFT JOIN (
            SELECT race_id, COUNT(*) AS c
            FROM beforeinfo_entries
            GROUP BY race_id
        ) b ON b.race_id = r.race_id
        WHERE r.race_date BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
          AND (
            res.race_id IS NULL
            OR COALESCE(o2.c, 0) < 45
            OR COALESCE(o3.c, 0) < 120
            OR COALESCE(b.c, 0) < 6
          )
        ORDER BY r.race_date, r.stadium_code, r.race_no
        """,
        params=[start_date, end_date],
    ).fetchall()
    con.close()
    return [
        MissingRace(
            race_date=str(row[0]).split(" ")[0],
            stadium_code=str(row[1]),
            stadium_name=STADIUM_NAMES.get(str(row[1]), str(row[2])),
            race_no=int(row[3]),
            race_id=str(row[4]),
            result_missing=bool(row[5]),
            odds2_rows=int(row[6] or 0),
            odds3_rows=int(row[7] or 0),
            beforeinfo_rows=int(row[8] or 0),
        )
        for row in rows
    ]


def result_raw_path(raw_root: Path, race: MissingRace) -> Path:
    compact = race.race_date.replace("-", "")
    return raw_root / "results" / compact / f"{race.stadium_code}_{race.race_no:02d}.html"


def is_official_cancelled(raw_root: Path, race: MissingRace) -> tuple[bool, str]:
    path = result_raw_path(raw_root, race)
    if not path.exists():
        return False, "result raw page missing"
    text = path.read_text(encoding="utf-8", errors="replace")
    if RACE_CANCELLED_TEXT in text:
        return True, "official result page says race cancelled"
    return False, "missing rows not explained by official cancellation page"


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_reports(
    missing_rows: list[MissingRace],
    raw_root: Path,
    verified_at: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    exceptions: list[dict[str, object]] = []
    true_missing: list[dict[str, object]] = []
    summary: dict[tuple[str, str, str], dict[str, object]] = {}

    for race in missing_rows:
        cancelled, reason = is_official_cancelled(raw_root, race)
        key = (race.race_date, race.stadium_code, race.stadium_name)
        item = summary.setdefault(
            key,
            {
                "race_date": race.race_date,
                "stadium_code": race.stadium_code,
                "stadium_name": race.stadium_name,
                "missing_rows": 0,
                "allowed_missing_rows": 0,
                "true_missing_rows": 0,
                "min_race_no": race.race_no,
                "max_race_no": race.race_no,
            },
        )
        item["missing_rows"] = int(item["missing_rows"]) + 1
        item["min_race_no"] = min(int(item["min_race_no"]), race.race_no)
        item["max_race_no"] = max(int(item["max_race_no"]), race.race_no)

        base = {
            "race_date": race.race_date,
            "stadium_code": race.stadium_code,
            "stadium_name": race.stadium_name,
            "race_no": race.race_no,
            "race_id": race.race_id,
            "missing_tables": "|".join(race.missing_tables),
            "result_missing": int(race.result_missing),
            "odds2_rows": race.odds2_rows,
            "odds3_rows": race.odds3_rows,
            "beforeinfo_rows": race.beforeinfo_rows,
            "source_path": str(result_raw_path(raw_root, race)),
        }
        if cancelled:
            item["allowed_missing_rows"] = int(item["allowed_missing_rows"]) + 1
            exceptions.append(
                {
                    "race_date": race.race_date,
                    "stadium_code": race.stadium_code,
                    "stadium_name": race.stadium_name,
                    "race_no": race.race_no,
                    "race_id": race.race_id,
                    "exception_type": "cancelled",
                    "reason": reason,
                    "source": "official_result_page",
                    "verified_at": verified_at,
                    "allowed_missing_tables": "|".join(race.missing_tables),
                }
            )
        else:
            item["true_missing_rows"] = int(item["true_missing_rows"]) + 1
            true_missing.append({**base, "reason": reason})

    return exceptions, true_missing, list(summary.values())


def race_range_text(min_race_no: object, max_race_no: object) -> str:
    if int(min_race_no) == int(max_race_no):
        return f"{min_race_no}R"
    return f"{min_race_no}R-{max_race_no}R"


def write_readme(
    output_dir: Path,
    start_date: str,
    end_date: str,
    exceptions: list[dict[str, object]],
    true_missing: list[dict[str, object]],
    summary: list[dict[str, object]],
) -> None:
    lines = [
        "# DB Allowed Missing Audit",
        "",
        f"- period: `{start_date}` to `{end_date}`",
        f"- allowed missing races: `{len(exceptions)}`",
        f"- true missing races: `{len(true_missing)}`",
        "",
        "## By Date And Stadium",
        "",
        "| Date | Stadium | Races | Missing | Allowed | True Missing |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in sorted(summary, key=lambda item: (str(item["race_date"]), str(item["stadium_code"]))):
        lines.append(
            "| {race_date} | {stadium_name} | {races} | {missing_rows} | {allowed_missing_rows} | {true_missing_rows} |".format(
                race_date=row["race_date"],
                stadium_name=row["stadium_name"],
                races=race_range_text(row["min_race_no"], row["max_race_no"]),
                missing_rows=row["missing_rows"],
                allowed_missing_rows=row["allowed_missing_rows"],
                true_missing_rows=row["true_missing_rows"],
            )
        )
    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `race_exceptions.csv`: official cancellations that are allowed to remain missing from settlement/odds tables",
            "- `true_missing.csv`: rows that still need repair",
            "- `summary.csv`: grouped audit counts",
            "",
        ]
    )
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    verified_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    missing_rows = fetch_missing_rows(args.db_path, args.start_date, args.end_date)
    exceptions, true_missing, summary = build_reports(missing_rows, args.raw_root, verified_at)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(
        args.output_dir / "race_exceptions.csv",
        exceptions,
        [
            "race_date",
            "stadium_code",
            "stadium_name",
            "race_no",
            "race_id",
            "exception_type",
            "reason",
            "source",
            "verified_at",
            "allowed_missing_tables",
        ],
    )
    write_csv(
        args.output_dir / "true_missing.csv",
        true_missing,
        [
            "race_date",
            "stadium_code",
            "stadium_name",
            "race_no",
            "race_id",
            "missing_tables",
            "result_missing",
            "odds2_rows",
            "odds3_rows",
            "beforeinfo_rows",
            "source_path",
            "reason",
        ],
    )
    write_csv(
        args.output_dir / "summary.csv",
        summary,
        [
            "race_date",
            "stadium_code",
            "stadium_name",
            "missing_rows",
            "allowed_missing_rows",
            "true_missing_rows",
            "min_race_no",
            "max_race_no",
        ],
    )
    write_readme(args.output_dir, args.start_date, args.end_date, exceptions, true_missing, summary)

    print(f"missing_rows={len(missing_rows)}")
    print(f"allowed_missing={len(exceptions)}")
    print(f"true_missing={len(true_missing)}")
    print(f"output_dir={args.output_dir}")
    return 1 if true_missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
