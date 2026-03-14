from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
import subprocess
import time

from boat_race_data.client import BoatRaceClient, FetchResult
from boat_race_data.constants import (
    DEFAULT_BRONZE_ROOT,
    DEFAULT_DB_PATH,
    DEFAULT_RAW_ROOT,
    DEFAULT_SLEEP_SECONDS,
    STADIUMS,
    TERM_DOWNLOAD_URL,
)
from boat_race_data.backtest import run_backtest
from boat_race_data.correlation_study import export_correlation_study
from boat_race_data.gpt_export import export_gpt_package
from boat_race_data.live_trigger import (
    build_watchlist,
    build_watchlist_for_profiles,
    load_trigger_profile,
    load_trigger_profiles,
    resolve_watchlist,
    resolve_watchlist_for_profiles,
)
from boat_race_data.logic_board import build_logic_board
from boat_race_data.mbrace import (
    build_mbrace_lzh_url,
    ensure_mbrace_text,
    parse_mbrace_b_schedule,
    parse_mbrace_k_results,
)
from boat_race_data.parsers import (
    extract_term_urls,
    parse_beforeinfo,
    parse_odds_2t,
    parse_odds_3t,
    parse_race_meta,
    parse_racelist,
    parse_result,
    parse_term_stats_records,
)
from boat_race_data.schedule_planner import build_schedule_window
from boat_race_data.quality import generate_quality_report
from boat_race_data.storage import BRONZE_COLUMNS, refresh_duckdb, write_table_csv

LOGGER = logging.getLogger("boat_race_data")
MIN_RANGE_SLEEP_SECONDS = 0.5


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def _normalize_sleep_seconds(command_name: str, sleep_seconds: float, minimum: float = 0.0) -> float:
    normalized = max(sleep_seconds, minimum)
    if normalized != sleep_seconds:
        LOGGER.warning(
            "%s sleep_seconds=%.2f is below the safe minimum %.2f; using %.2f instead.",
            command_name,
            sleep_seconds,
            minimum,
            normalized,
        )
    return normalized


def _collect_term_stats(client: BoatRaceClient, raw_root: Path) -> tuple[str | None, list[dict[str, object]]]:
    download_page = client.fetch_text(TERM_DOWNLOAD_URL, raw_root / "term_stats" / "download.html")
    term_url, layout_url = extract_term_urls(download_page.text or "")
    if term_url is None:
        LOGGER.warning("No term stats LZH link found on %s", TERM_DOWNLOAD_URL)
        return None, []

    client.fetch_text(layout_url, raw_root / "term_stats" / "layout.html")
    term_filename = term_url.rsplit("/", 1)[-1]
    lzh_fetch = client.fetch_binary(term_url, raw_root / "term_stats" / term_filename)

    subprocess.run(["tar", "-xf", Path(term_filename).name], cwd=lzh_fetch.raw_path.parent, check=True, capture_output=True)
    txt_path = lzh_fetch.raw_path.parent / f"{Path(term_filename).stem}.txt"
    term_rows = parse_term_stats_records(
        txt_path.read_bytes(),
        term_file=Path(term_filename).stem,
        source_url=lzh_fetch.url,
        fetched_at=lzh_fetch.fetched_at,
    )
    return Path(term_filename).stem, term_rows


def _iter_dates(start_date: str, end_date: str) -> list[str]:
    start = datetime.strptime(start_date, "%Y%m%d").date()
    end = datetime.strptime(end_date, "%Y%m%d").date()
    if end < start:
        raise ValueError("end_date must be greater than or equal to start_date")
    dates: list[str] = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y%m%d"))
        current += timedelta(days=1)
    return dates


def _cached_fetch_result(raw_path: Path, url: str, is_text: bool) -> FetchResult:
    content = raw_path.read_bytes()
    fetched_at = datetime.fromtimestamp(raw_path.stat().st_mtime, tz=timezone.utc).isoformat()
    text = content.decode("utf-8", errors="replace") if is_text else None
    return FetchResult(url=url, fetched_at=fetched_at, raw_path=raw_path, content=content, text=text)


def _fetch_text_cached(client: BoatRaceClient, url: str, raw_path: Path) -> FetchResult:
    if raw_path.exists():
        return _cached_fetch_result(raw_path, url, is_text=True)
    return client.fetch_text(url, raw_path)


def _fetch_binary_cached(client: BoatRaceClient, url: str, raw_path: Path) -> FetchResult:
    if raw_path.exists():
        return _cached_fetch_result(raw_path, url, is_text=False)
    return client.fetch_binary(url, raw_path)


def _collect_day_tables(
    client: BoatRaceClient,
    race_date: str,
    stadium_codes: list[str],
    max_race_no: int,
    sleep_seconds: float,
    raw_root: Path,
    skip_odds_3t: bool,
) -> dict[str, list[dict[str, object]]]:
    tables: dict[str, list[dict[str, object]]] = {
        "races": [],
        "entries": [],
        "odds_2t": [],
        "odds_3t": [],
        "results": [],
        "beforeinfo_entries": [],
        "race_meta": [],
        "racer_stats_term": [],
    }

    LOGGER.info("Collecting %s for stadiums: %s", race_date, ", ".join(stadium_codes))
    for stadium_code in stadium_codes:
        stadium_name = STADIUMS[stadium_code]
        for race_no in range(1, max_race_no + 1):
            try:
                prefix = f"{stadium_code}_{race_no:02d}"

                racelist_fetch = _fetch_text_cached(
                    client,
                    client.build_race_url("racelist", race_date, stadium_code, race_no),
                    raw_root / "racelist" / race_date / f"{prefix}.html",
                )
                race_row, entry_rows = parse_racelist(
                    racelist_fetch.text or "",
                    race_date,
                    stadium_code,
                    stadium_name,
                    race_no,
                    racelist_fetch.url,
                    racelist_fetch.fetched_at,
                )
                if race_row is None:
                    LOGGER.debug("No racelist data for %s %sR", stadium_code, race_no)
                    continue
                tables["races"].append(race_row)
                tables["entries"].extend(entry_rows)
                race_meta_row = parse_race_meta(
                    racelist_fetch.text or "",
                    race_date,
                    stadium_code,
                    race_no,
                    racelist_fetch.url,
                    racelist_fetch.fetched_at,
                )
                if race_meta_row:
                    tables["race_meta"].append(race_meta_row)
                time.sleep(sleep_seconds)

                odds2_fetch = _fetch_text_cached(
                    client,
                    client.build_race_url("odds2t", race_date, stadium_code, race_no),
                    raw_root / "odds_2t" / race_date / f"{prefix}.html",
                )
                tables["odds_2t"].extend(
                    parse_odds_2t(
                        odds2_fetch.text or "",
                        race_date,
                        stadium_code,
                        race_no,
                        odds2_fetch.url,
                        odds2_fetch.fetched_at,
                    )
                )
                time.sleep(sleep_seconds)

                if not skip_odds_3t:
                    odds3_fetch = _fetch_text_cached(
                        client,
                        client.build_race_url("odds3t", race_date, stadium_code, race_no),
                        raw_root / "odds_3t" / race_date / f"{prefix}.html",
                    )
                    tables["odds_3t"].extend(
                        parse_odds_3t(
                            odds3_fetch.text or "",
                            race_date,
                            stadium_code,
                            race_no,
                            odds3_fetch.url,
                            odds3_fetch.fetched_at,
                        )
                    )
                    time.sleep(sleep_seconds)

                beforeinfo_fetch = _fetch_text_cached(
                    client,
                    client.build_race_url("beforeinfo", race_date, stadium_code, race_no),
                    raw_root / "beforeinfo" / race_date / f"{prefix}.html",
                )
                tables["beforeinfo_entries"].extend(
                    parse_beforeinfo(
                        beforeinfo_fetch.text or "",
                        race_date,
                        stadium_code,
                        race_no,
                        beforeinfo_fetch.url,
                        beforeinfo_fetch.fetched_at,
                    )
                )
                time.sleep(sleep_seconds)

                result_fetch = _fetch_text_cached(
                    client,
                    client.build_race_url("result", race_date, stadium_code, race_no),
                    raw_root / "results" / race_date / f"{prefix}.html",
                )
                result_row = parse_result(
                    result_fetch.text or "",
                    race_date,
                    stadium_code,
                    race_no,
                    result_fetch.url,
                    result_fetch.fetched_at,
                )
                if result_row:
                    tables["results"].append(result_row)
                time.sleep(sleep_seconds)
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Failed to collect %s %sR: %s", stadium_code, race_no, exc)
    return tables


def _write_day_tables(
    bronze_root: Path,
    race_date: str,
    tables: dict[str, list[dict[str, object]]],
    skip_term_stats: bool,
) -> None:
    for table_name, rows in tables.items():
        if table_name == "racer_stats_term" and skip_term_stats:
            continue
        file_name = f"{race_date}.csv" if table_name != "racer_stats_term" else "latest.csv"
        write_table_csv(bronze_root / table_name / file_name, BRONZE_COLUMNS[table_name], rows)


def _write_selected_tables(
    bronze_root: Path,
    race_date: str,
    table_rows: dict[str, list[dict[str, object]]],
) -> None:
    for table_name, rows in table_rows.items():
        file_name = f"{race_date}.csv" if table_name != "racer_stats_term" else "latest.csv"
        write_table_csv(bronze_root / table_name / file_name, BRONZE_COLUMNS[table_name], rows)


def _has_existing_day(bronze_root: Path, race_date: str) -> bool:
    required_files = [
        bronze_root / "races" / f"{race_date}.csv",
        bronze_root / "entries" / f"{race_date}.csv",
        bronze_root / "odds_2t" / f"{race_date}.csv",
        bronze_root / "results" / f"{race_date}.csv",
        bronze_root / "beforeinfo_entries" / f"{race_date}.csv",
        bronze_root / "race_meta" / f"{race_date}.csv",
    ]
    return all(path.exists() for path in required_files)


def _has_existing_bulk_day(bronze_root: Path, race_date: str) -> bool:
    required_files = [
        bronze_root / "races" / f"{race_date}.csv",
        bronze_root / "entries" / f"{race_date}.csv",
        bronze_root / "results" / f"{race_date}.csv",
        bronze_root / "beforeinfo_entries" / f"{race_date}.csv",
        bronze_root / "race_meta" / f"{race_date}.csv",
    ]
    return all(path.exists() for path in required_files)


def _collect_mbrace_day_tables(
    client: BoatRaceClient,
    race_date: str,
    sleep_seconds: float,
    raw_root: Path,
) -> dict[str, list[dict[str, object]]]:
    day_tables: dict[str, list[dict[str, object]]] = {
        "races": [],
        "entries": [],
        "results": [],
        "beforeinfo_entries": [],
        "race_meta": [],
    }
    race_date_iso = f"{race_date[:4]}-{race_date[4:6]}-{race_date[6:8]}"
    for kind in ["B", "K"]:
        url = build_mbrace_lzh_url(kind, race_date)
        raw_dir = raw_root / f"mbrace_{kind.lower()}" / race_date[:6]
        raw_path = raw_dir / f"{kind.lower()}{race_date[2:]}.lzh"
        fetch = _fetch_binary_cached(client, url, raw_path)
        txt_path = ensure_mbrace_text(fetch.raw_path)
        text = txt_path.read_text(encoding="cp932", errors="replace")
        if kind == "B":
            parsed = parse_mbrace_b_schedule(text, race_date, fetch.url, fetch.fetched_at)
        else:
            parsed = parse_mbrace_k_results(text, race_date, fetch.url, fetch.fetched_at)
        for table_name, rows in parsed.items():
            day_tables[table_name].extend(rows)
        time.sleep(sleep_seconds)

    LOGGER.info(
        "Collected mbrace %s: races=%s entries=%s results=%s beforeinfo_entries=%s race_meta=%s",
        race_date_iso,
        len(day_tables["races"]),
        len(day_tables["entries"]),
        len(day_tables["results"]),
        len(day_tables["beforeinfo_entries"]),
        len(day_tables["race_meta"]),
    )
    return day_tables


def collect_day(args: argparse.Namespace) -> int:
    race_date = args.date
    bronze_root = Path(args.bronze_root)
    raw_root = Path(args.raw_root)
    db_path = Path(args.db_path)
    report_root = Path("reports/data_quality")
    sleep_seconds = _normalize_sleep_seconds("collect-day", args.sleep_seconds)

    with BoatRaceClient() as client:
        stadium_codes = args.stadiums or client.discover_active_stadiums(race_date)
        if not stadium_codes:
            raise RuntimeError(f"No active stadiums found for {race_date}.")
        LOGGER.info(
            "collect-day %s with beforeinfo=%s odds_3t=%s sleep_seconds=%.2f stadiums=%s",
            race_date,
            True,
            not args.skip_odds_3t,
            sleep_seconds,
            ",".join(stadium_codes),
        )
        tables = _collect_day_tables(
            client=client,
            race_date=race_date,
            stadium_codes=stadium_codes,
            max_race_no=args.max_race_no,
            sleep_seconds=sleep_seconds,
            raw_root=raw_root,
            skip_odds_3t=args.skip_odds_3t,
        )

        if not args.skip_term_stats:
            try:
                download_page = _fetch_text_cached(client, TERM_DOWNLOAD_URL, raw_root / "term_stats" / "download.html")
                term_url, layout_url = extract_term_urls(download_page.text or "")
                if term_url is None:
                    LOGGER.warning("No term stats LZH link found on %s", TERM_DOWNLOAD_URL)
                    term_key, term_rows = None, []
                else:
                    _fetch_text_cached(client, layout_url, raw_root / "term_stats" / "layout.html")
                    term_filename = term_url.rsplit("/", 1)[-1]
                    lzh_fetch = _fetch_binary_cached(client, term_url, raw_root / "term_stats" / term_filename)
                    txt_path = lzh_fetch.raw_path.parent / f"{Path(term_filename).stem}.txt"
                    if not txt_path.exists():
                        subprocess.run(
                            ["tar", "-xf", Path(term_filename).name],
                            cwd=lzh_fetch.raw_path.parent,
                            check=True,
                            capture_output=True,
                        )
                    term_key = Path(term_filename).stem
                    term_rows = parse_term_stats_records(
                        txt_path.read_bytes(),
                        term_file=term_key,
                        source_url=lzh_fetch.url,
                        fetched_at=lzh_fetch.fetched_at,
                    )
                if term_key is not None:
                    tables["racer_stats_term"] = term_rows
                    LOGGER.info("Collected %s term stats rows for %s", len(term_rows), term_key)
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Failed to collect term stats: %s", exc)

    _write_day_tables(bronze_root, race_date, tables, args.skip_term_stats)

    refresh_duckdb(db_path, bronze_root)
    report_path = None
    if not args.skip_quality_report:
        report_path = generate_quality_report(db_path, race_date, report_root)

    LOGGER.info("Saved DuckDB to %s", db_path)
    if report_path is not None:
        LOGGER.info("Saved quality report to %s", report_path)
    LOGGER.info(
        "rows: races=%s entries=%s odds_2t=%s odds_3t=%s results=%s beforeinfo_entries=%s race_meta=%s racer_stats_term=%s",
        len(tables["races"]),
        len(tables["entries"]),
        len(tables["odds_2t"]),
        len(tables["odds_3t"]),
        len(tables["results"]),
        len(tables["beforeinfo_entries"]),
        len(tables["race_meta"]),
        len(tables["racer_stats_term"]),
    )
    return 0


def collect_range(args: argparse.Namespace) -> int:
    bronze_root = Path(args.bronze_root)
    raw_root = Path(args.raw_root)
    db_path = Path(args.db_path)
    report_root = Path("reports/data_quality")
    date_list = _iter_dates(args.start_date, args.end_date)
    sleep_seconds = _normalize_sleep_seconds("collect-range", args.sleep_seconds, MIN_RANGE_SLEEP_SECONDS)
    total_counts = {
        "races": 0,
        "entries": 0,
        "odds_2t": 0,
        "odds_3t": 0,
        "results": 0,
        "beforeinfo_entries": 0,
        "race_meta": 0,
    }
    term_rows: list[dict[str, object]] = []
    collected_days_since_refresh = 0

    with BoatRaceClient() as client:
        LOGGER.info(
            "collect-range %s..%s with beforeinfo=%s odds_3t=%s sleep_seconds=%.2f refresh_every_days=%s resume_existing_days=%s",
            args.start_date,
            args.end_date,
            True,
            not args.skip_odds_3t,
            sleep_seconds,
            args.refresh_every_days,
            args.resume_existing_days,
        )
        for race_date in date_list:
            try:
                if args.resume_existing_days and _has_existing_day(bronze_root, race_date):
                    LOGGER.info("Skipping %s because bronze files already exist.", race_date)
                    continue
                stadium_codes = args.stadiums or client.discover_active_stadiums(race_date)
                if not stadium_codes:
                    LOGGER.info("No active stadiums found for %s; skipping.", race_date)
                    continue
                tables = _collect_day_tables(
                    client=client,
                    race_date=race_date,
                    stadium_codes=stadium_codes,
                    max_race_no=args.max_race_no,
                    sleep_seconds=sleep_seconds,
                    raw_root=raw_root,
                    skip_odds_3t=args.skip_odds_3t,
                )
                _write_day_tables(bronze_root, race_date, tables, skip_term_stats=True)
                for key in total_counts:
                    total_counts[key] += len(tables[key])
                LOGGER.info(
                    "Completed %s: races=%s entries=%s odds_2t=%s odds_3t=%s results=%s beforeinfo_entries=%s race_meta=%s",
                    race_date,
                    len(tables["races"]),
                    len(tables["entries"]),
                    len(tables["odds_2t"]),
                    len(tables["odds_3t"]),
                    len(tables["results"]),
                    len(tables["beforeinfo_entries"]),
                    len(tables["race_meta"]),
                )
                collected_days_since_refresh += 1
                if args.refresh_every_days > 0 and collected_days_since_refresh >= args.refresh_every_days:
                    refresh_duckdb(db_path, bronze_root)
                    LOGGER.info("Refreshed DuckDB after %s collected day(s).", collected_days_since_refresh)
                    collected_days_since_refresh = 0
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Failed to collect %s: %s", race_date, exc)

        if not args.skip_term_stats:
            try:
                term_key, term_rows = _collect_term_stats(client, raw_root)
                if term_key is not None:
                    write_table_csv(
                        bronze_root / "racer_stats_term" / "latest.csv",
                        BRONZE_COLUMNS["racer_stats_term"],
                        term_rows,
                    )
                    LOGGER.info("Collected %s term stats rows for %s", len(term_rows), term_key)
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Failed to collect term stats: %s", exc)

    refresh_duckdb(db_path, bronze_root)
    report_path = None
    if not args.skip_quality_report:
        report_path = generate_quality_report(db_path, args.end_date, report_root)

    LOGGER.info(
        "range rows: races=%s entries=%s odds_2t=%s odds_3t=%s results=%s beforeinfo_entries=%s race_meta=%s racer_stats_term=%s",
        total_counts["races"],
        total_counts["entries"],
        total_counts["odds_2t"],
        total_counts["odds_3t"],
        total_counts["results"],
        total_counts["beforeinfo_entries"],
        total_counts["race_meta"],
        len(term_rows),
    )
    LOGGER.info("Saved DuckDB to %s", db_path)
    if report_path is not None:
        LOGGER.info("Saved quality report to %s", report_path)
    return 0


def collect_mbrace_range(args: argparse.Namespace) -> int:
    bronze_root = Path(args.bronze_root)
    raw_root = Path(args.raw_root)
    db_path = Path(args.db_path)
    report_root = Path("reports/data_quality")
    date_list = _iter_dates(args.start_date, args.end_date)
    sleep_seconds = _normalize_sleep_seconds("collect-mbrace-range", args.sleep_seconds, MIN_RANGE_SLEEP_SECONDS)
    total_counts = {
        "races": 0,
        "entries": 0,
        "results": 0,
        "beforeinfo_entries": 0,
        "race_meta": 0,
    }
    term_rows: list[dict[str, object]] = []
    collected_days_since_refresh = 0

    with BoatRaceClient() as client:
        LOGGER.info(
            "collect-mbrace-range %s..%s with sleep_seconds=%.2f refresh_every_days=%s resume_existing_days=%s",
            args.start_date,
            args.end_date,
            sleep_seconds,
            args.refresh_every_days,
            args.resume_existing_days,
        )
        for race_date in date_list:
            try:
                if args.resume_existing_days and _has_existing_bulk_day(bronze_root, race_date):
                    LOGGER.info("Skipping %s because bulk bronze files already exist.", race_date)
                    continue
                tables = _collect_mbrace_day_tables(
                    client=client,
                    race_date=race_date,
                    sleep_seconds=sleep_seconds,
                    raw_root=raw_root,
                )
                _write_selected_tables(bronze_root, race_date, tables)
                for key in total_counts:
                    total_counts[key] += len(tables[key])
                collected_days_since_refresh += 1
                if args.refresh_every_days > 0 and collected_days_since_refresh >= args.refresh_every_days:
                    refresh_duckdb(db_path, bronze_root)
                    LOGGER.info("Refreshed DuckDB after %s collected day(s).", collected_days_since_refresh)
                    collected_days_since_refresh = 0
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Failed to collect bulk %s: %s", race_date, exc)

        if not args.skip_term_stats:
            try:
                term_key, term_rows = _collect_term_stats(client, raw_root)
                if term_key is not None:
                    write_table_csv(
                        bronze_root / "racer_stats_term" / "latest.csv",
                        BRONZE_COLUMNS["racer_stats_term"],
                        term_rows,
                    )
                    LOGGER.info("Collected %s term stats rows for %s", len(term_rows), term_key)
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Failed to collect term stats: %s", exc)

    refresh_duckdb(db_path, bronze_root)
    report_path = None
    if not args.skip_quality_report:
        report_path = generate_quality_report(db_path, args.end_date, report_root)

    LOGGER.info(
        "bulk rows: races=%s entries=%s results=%s beforeinfo_entries=%s race_meta=%s racer_stats_term=%s",
        total_counts["races"],
        total_counts["entries"],
        total_counts["results"],
        total_counts["beforeinfo_entries"],
        total_counts["race_meta"],
        len(term_rows),
    )
    LOGGER.info("Saved DuckDB to %s", db_path)
    if report_path is not None:
        LOGGER.info("Saved quality report to %s", report_path)
    return 0


def export_gpt(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    counts = export_gpt_package(
        db_path=Path(args.db_path),
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=output_dir,
    )
    LOGGER.info("Exported GPT package to %s", output_dir)
    for filename, row_count in counts.items():
        LOGGER.info("%s rows=%s", filename, row_count)
    return 0


def export_correlation(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    counts = export_correlation_study(
        db_path=Path(args.db_path),
        discovery_start=args.discovery_start,
        discovery_end=args.discovery_end,
        validation_start=args.validation_start,
        validation_end=args.validation_end,
        output_dir=output_dir,
    )
    LOGGER.info("Exported correlation study package to %s", output_dir)
    for filename, row_count in counts.items():
        LOGGER.info("%s rows=%s", filename, row_count)
    return 0


def backtest_strategies(args: argparse.Namespace) -> int:
    counts = run_backtest(
        db_path=Path(args.db_path),
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=Path(args.output_dir),
    )
    LOGGER.info("Backtest outputs written to %s", args.output_dir)
    for filename, row_count in counts.items():
        LOGGER.info("%s rows=%s", filename, row_count)
    return 0


def build_next_day_watchlist(args: argparse.Namespace) -> int:
    profile = load_trigger_profile(Path(args.profile_path))
    count, output_path = build_watchlist(
        race_date=args.date,
        profile=profile,
        output_path=Path(args.output_path),
        raw_root=Path(args.raw_root),
        max_race_no=args.max_race_no,
        sleep_seconds=args.sleep_seconds,
        timeout_seconds=args.timeout_seconds,
    )
    LOGGER.info("Built watchlist rows=%s output=%s", count, output_path)
    return 0


def resolve_next_day_watchlist(args: argparse.Namespace) -> int:
    profile = load_trigger_profile(Path(args.profile_path))
    changed_rows, ready_rows = resolve_watchlist(
        watchlist_path=Path(args.watchlist_path),
        profile=profile,
        raw_root=Path(args.raw_root),
        ready_output_path=Path(args.ready_output_path) if args.ready_output_path else None,
        sleep_seconds=args.sleep_seconds,
        timeout_seconds=args.timeout_seconds,
    )
    LOGGER.info("Resolved watchlist changed_rows=%s ready_rows=%s", changed_rows, ready_rows)
    return 0


def build_batch_watchlist(args: argparse.Namespace) -> int:
    profiles = load_trigger_profiles(Path(args.profiles_dir))
    count, output_path = build_watchlist_for_profiles(
        race_date=args.date,
        profiles=profiles,
        output_path=Path(args.output_path),
        raw_root=Path(args.raw_root),
        max_race_no=args.max_race_no,
        sleep_seconds=args.sleep_seconds,
        timeout_seconds=args.timeout_seconds,
    )
    LOGGER.info("Built batch watchlist rows=%s output=%s profiles=%s", count, output_path, len(profiles))
    return 0


def resolve_batch_watchlist(args: argparse.Namespace) -> int:
    profiles = load_trigger_profiles(Path(args.profiles_dir))
    changed_rows, ready_rows = resolve_watchlist_for_profiles(
        watchlist_path=Path(args.watchlist_path),
        profiles=profiles,
        raw_root=Path(args.raw_root),
        ready_output_path=Path(args.ready_output_path) if args.ready_output_path else None,
        sleep_seconds=args.sleep_seconds,
        timeout_seconds=args.timeout_seconds,
    )
    LOGGER.info(
        "Resolved batch watchlist changed_rows=%s ready_rows=%s profiles=%s",
        changed_rows,
        ready_rows,
        len(profiles),
    )
    return 0


def build_schedule_window_command(args: argparse.Namespace) -> int:
    outputs = build_schedule_window(
        start_date=args.start_date,
        days=args.days,
        output_dir=Path(args.output_dir),
        raw_root=Path(args.raw_root),
        timeout_seconds=args.timeout_seconds,
    )
    for label, path in outputs.items():
        LOGGER.info("%s=%s", label, path)
    return 0


def build_logic_board_command(args: argparse.Namespace) -> int:
    profiles = load_trigger_profiles(Path(args.profiles_dir), include_disabled=True)
    outputs = build_logic_board(
        start_date=args.start_date,
        days=args.days,
        profiles=profiles,
        output_dir=Path(args.output_dir),
        raw_root=Path(args.raw_root),
        timeout_seconds=args.timeout_seconds,
    )
    for label, path in outputs.items():
        LOGGER.info("%s=%s", label, path)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect official BOAT RACE data into raw/bronze/silver layers.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect_parser = subparsers.add_parser("collect-day", help="Collect one day's data and refresh DuckDB.")
    collect_parser.add_argument("--date", required=True, help="Race date in YYYYMMDD format, for example 20260306.")
    collect_parser.add_argument(
        "--stadiums",
        nargs="*",
        choices=sorted(STADIUMS.keys()),
        help="Optional stadium codes. If omitted, active stadiums for the day are discovered automatically.",
    )
    collect_parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="DuckDB output path.")
    collect_parser.add_argument("--raw-root", default=DEFAULT_RAW_ROOT, help="Raw layer root directory.")
    collect_parser.add_argument("--bronze-root", default=DEFAULT_BRONZE_ROOT, help="Bronze layer root directory.")
    collect_parser.add_argument("--max-race-no", type=int, default=12, help="Max race number to fetch per stadium.")
    collect_parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=DEFAULT_SLEEP_SECONDS,
        help="Delay between requests to avoid aggressive access.",
    )
    collect_parser.add_argument(
        "--skip-term-stats",
        action="store_true",
        help="Skip the racer term stats download step.",
    )
    collect_parser.add_argument(
        "--skip-odds-3t",
        action="store_true",
        help="Skip 3連単 odds collection when only 2連単 backtests are needed.",
    )
    collect_parser.add_argument(
        "--skip-quality-report",
        action="store_true",
        help="Skip data quality report generation for this run.",
    )
    collect_parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    collect_parser.set_defaults(func=collect_day)

    collect_range_parser = subparsers.add_parser(
        "collect-range",
        help="Collect a date range into bronze/silver with raw cache reuse.",
    )
    collect_range_parser.add_argument("--start-date", required=True, help="Start date in YYYYMMDD format.")
    collect_range_parser.add_argument("--end-date", required=True, help="End date in YYYYMMDD format.")
    collect_range_parser.add_argument(
        "--stadiums",
        nargs="*",
        choices=sorted(STADIUMS.keys()),
        help="Optional stadium codes. If omitted, active stadiums for each day are discovered automatically.",
    )
    collect_range_parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="DuckDB output path.")
    collect_range_parser.add_argument("--raw-root", default=DEFAULT_RAW_ROOT, help="Raw layer root directory.")
    collect_range_parser.add_argument("--bronze-root", default=DEFAULT_BRONZE_ROOT, help="Bronze layer root directory.")
    collect_range_parser.add_argument("--max-race-no", type=int, default=12, help="Max race number to fetch per stadium.")
    collect_range_parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=DEFAULT_SLEEP_SECONDS,
        help="Delay between requests to avoid aggressive access. collect-range enforces a 0.5s minimum.",
    )
    collect_range_parser.add_argument(
        "--skip-term-stats",
        action="store_true",
        help="Skip the racer term stats download step.",
    )
    collect_range_parser.add_argument(
        "--skip-odds-3t",
        action="store_true",
        help="Skip 3連単 odds collection when only 2連単 backtests are needed.",
    )
    collect_range_parser.add_argument(
        "--skip-quality-report",
        action="store_true",
        help="Skip data quality report generation for this run.",
    )
    collect_range_parser.add_argument(
        "--resume-existing-days",
        action="store_true",
        help="Skip dates whose bronze day files already exist.",
    )
    collect_range_parser.add_argument(
        "--refresh-every-days",
        type=int,
        default=0,
        help="Refresh DuckDB every N collected days. Use 1 for safest resume behavior.",
    )
    collect_range_parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    collect_range_parser.set_defaults(func=collect_range)

    collect_mbrace_parser = subparsers.add_parser(
        "collect-mbrace-range",
        help="Collect a date range from official mbrace B/K daily downloads into bronze/silver.",
    )
    collect_mbrace_parser.add_argument("--start-date", required=True, help="Start date in YYYYMMDD format.")
    collect_mbrace_parser.add_argument("--end-date", required=True, help="End date in YYYYMMDD format.")
    collect_mbrace_parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="DuckDB output path.")
    collect_mbrace_parser.add_argument("--raw-root", default=DEFAULT_RAW_ROOT, help="Raw layer root directory.")
    collect_mbrace_parser.add_argument("--bronze-root", default=DEFAULT_BRONZE_ROOT, help="Bronze layer root directory.")
    collect_mbrace_parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=DEFAULT_SLEEP_SECONDS,
        help="Delay between daily B/K downloads. collect-mbrace-range enforces a 0.5s minimum.",
    )
    collect_mbrace_parser.add_argument(
        "--skip-term-stats",
        action="store_true",
        help="Skip the racer term stats download step.",
    )
    collect_mbrace_parser.add_argument(
        "--skip-quality-report",
        action="store_true",
        help="Skip data quality report generation for this run.",
    )
    collect_mbrace_parser.add_argument(
        "--resume-existing-days",
        action="store_true",
        help="Skip dates whose bulk bronze day files already exist.",
    )
    collect_mbrace_parser.add_argument(
        "--refresh-every-days",
        type=int,
        default=0,
        help="Refresh DuckDB every N collected days. Use 7 or 14 for long runs.",
    )
    collect_mbrace_parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    collect_mbrace_parser.set_defaults(func=collect_mbrace_range)

    export_parser = subparsers.add_parser("export-gpt", help="Export GPT-ready CSV and brief files from DuckDB.")
    export_parser.add_argument("--start-date", required=True, help="Start date in YYYY-MM-DD format.")
    export_parser.add_argument("--end-date", required=True, help="End date in YYYY-MM-DD format.")
    export_parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="DuckDB input path.")
    export_parser.add_argument(
        "--output-dir",
        default="GPT/output/latest",
        help="Directory where GPT-ready files will be written.",
    )
    export_parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    export_parser.set_defaults(func=export_gpt)

    correlation_parser = subparsers.add_parser(
        "export-correlation-study",
        help="Export discovery/validation packages for LLM-based correlation search.",
    )
    correlation_parser.add_argument("--discovery-start", required=True, help="Discovery start date in YYYY-MM-DD format.")
    correlation_parser.add_argument("--discovery-end", required=True, help="Discovery end date in YYYY-MM-DD format.")
    correlation_parser.add_argument("--validation-start", required=True, help="Validation start date in YYYY-MM-DD format.")
    correlation_parser.add_argument("--validation-end", required=True, help="Validation end date in YYYY-MM-DD format.")
    correlation_parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="DuckDB input path.")
    correlation_parser.add_argument(
        "--output-dir",
        default="GPT/output/correlation_study_latest",
        help="Directory where discovery/validation packages will be written.",
    )
    correlation_parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    correlation_parser.set_defaults(func=export_correlation)

    backtest_parser = subparsers.add_parser(
        "backtest-strategies",
        help="Backtest the current GPT-derived strategy hypotheses and write GPT-ready follow-up material.",
    )
    backtest_parser.add_argument("--start-date", required=True, help="Start date in YYYY-MM-DD format.")
    backtest_parser.add_argument("--end-date", required=True, help="End date in YYYY-MM-DD format.")
    backtest_parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="DuckDB input path.")
    backtest_parser.add_argument(
        "--output-dir",
        default="GPT/output/latest",
        help="Directory where backtest files will be written.",
    )
    backtest_parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    backtest_parser.set_defaults(func=backtest_strategies)

    build_watchlist_parser = subparsers.add_parser(
        "build-watchlist",
        help="Build a next-day watchlist from racelist pages and a trigger profile.",
    )
    build_watchlist_parser.add_argument("--date", required=True, help="Race date in YYYYMMDD format.")
    build_watchlist_parser.add_argument(
        "--profile-path",
        default="live_trigger/boxes/125/profiles/suminoe_main.json",
        help="JSON trigger profile path.",
    )
    build_watchlist_parser.add_argument(
        "--output-path",
        default="live_trigger/watchlists/latest.csv",
        help="CSV output path for the watchlist.",
    )
    build_watchlist_parser.add_argument(
        "--raw-root",
        default="live_trigger/raw",
        help="Raw cache root for trigger-side fetches.",
    )
    build_watchlist_parser.add_argument("--max-race-no", type=int, default=12, help="Max race number to fetch.")
    build_watchlist_parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=DEFAULT_SLEEP_SECONDS,
        help="Delay between requests.",
    )
    build_watchlist_parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=30,
        help="HTTP timeout seconds.",
    )
    build_watchlist_parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    build_watchlist_parser.set_defaults(func=build_next_day_watchlist)

    build_watchlist_batch_parser = subparsers.add_parser(
        "build-watchlist-batch",
        help="Build one combined watchlist from all enabled trigger profiles in a directory.",
    )
    build_watchlist_batch_parser.add_argument("--date", required=True, help="Race date in YYYYMMDD format.")
    build_watchlist_batch_parser.add_argument(
        "--profiles-dir",
        default="live_trigger/boxes",
        help="Directory containing trigger box folders and profile JSON files.",
    )
    build_watchlist_batch_parser.add_argument(
        "--output-path",
        default="live_trigger/watchlists/latest_batch.csv",
        help="CSV output path for the combined watchlist.",
    )
    build_watchlist_batch_parser.add_argument(
        "--raw-root",
        default="live_trigger/raw",
        help="Raw cache root for trigger-side fetches.",
    )
    build_watchlist_batch_parser.add_argument("--max-race-no", type=int, default=12, help="Max race number to fetch.")
    build_watchlist_batch_parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=DEFAULT_SLEEP_SECONDS,
        help="Delay between requests.",
    )
    build_watchlist_batch_parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=30,
        help="HTTP timeout seconds.",
    )
    build_watchlist_batch_parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    build_watchlist_batch_parser.set_defaults(func=build_batch_watchlist)

    resolve_watchlist_parser = subparsers.add_parser(
        "resolve-watchlist",
        help="Refresh beforeinfo for a watchlist and mark rows that are trigger-ready.",
    )
    resolve_watchlist_parser.add_argument(
        "--watchlist-path",
        required=True,
        help="Input watchlist CSV path.",
    )
    resolve_watchlist_parser.add_argument(
        "--profile-path",
        default="live_trigger/profiles/125_suminoe_non_a1.json",
        help="JSON trigger profile path.",
    )
    resolve_watchlist_parser.add_argument(
        "--ready-output-path",
        default="live_trigger/ready/latest.csv",
        help="Optional CSV output path for trigger-ready rows.",
    )
    resolve_watchlist_parser.add_argument(
        "--raw-root",
        default="live_trigger/raw",
        help="Raw cache root for trigger-side fetches.",
    )
    resolve_watchlist_parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=DEFAULT_SLEEP_SECONDS,
        help="Delay between requests.",
    )
    resolve_watchlist_parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=30,
        help="HTTP timeout seconds.",
    )
    resolve_watchlist_parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    resolve_watchlist_parser.set_defaults(func=resolve_next_day_watchlist)

    resolve_watchlist_batch_parser = subparsers.add_parser(
        "resolve-watchlist-batch",
        help="Resolve one combined watchlist using all enabled trigger profiles in a directory.",
    )
    resolve_watchlist_batch_parser.add_argument(
        "--watchlist-path",
        required=True,
        help="Input watchlist CSV path.",
    )
    resolve_watchlist_batch_parser.add_argument(
        "--profiles-dir",
        default="live_trigger/boxes",
        help="Directory containing trigger box folders and profile JSON files.",
    )
    resolve_watchlist_batch_parser.add_argument(
        "--ready-output-path",
        default="live_trigger/ready/latest_batch.csv",
        help="Optional CSV output path for trigger-ready rows.",
    )
    resolve_watchlist_batch_parser.add_argument(
        "--raw-root",
        default="live_trigger/raw",
        help="Raw cache root for trigger-side fetches.",
    )
    resolve_watchlist_batch_parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=DEFAULT_SLEEP_SECONDS,
        help="Delay between requests.",
    )
    resolve_watchlist_batch_parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=30,
        help="HTTP timeout seconds.",
    )
    resolve_watchlist_batch_parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    resolve_watchlist_batch_parser.set_defaults(func=resolve_batch_watchlist)

    schedule_window_parser = subparsers.add_parser(
        "build-schedule-window",
        help="Build a 2-week to 1-month planning window from official monthly schedules.",
    )
    schedule_window_parser.add_argument(
        "--start-date",
        required=True,
        help="Window start date in YYYY-MM-DD format.",
    )
    schedule_window_parser.add_argument(
        "--days",
        type=int,
        default=14,
        help="Number of days to include in the planning window.",
    )
    schedule_window_parser.add_argument(
        "--output-dir",
        default="live_trigger/plans",
        help="Directory for CSV/Markdown/HTML planning outputs.",
    )
    schedule_window_parser.add_argument(
        "--raw-root",
        default="live_trigger/raw",
        help="Raw cache root for schedule HTML.",
    )
    schedule_window_parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=30,
        help="HTTP timeout seconds.",
    )
    schedule_window_parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    schedule_window_parser.set_defaults(func=build_schedule_window_command)

    logic_board_parser = subparsers.add_parser(
        "build-logic-board",
        help="Build a planning board that auto-discovers logic boxes from trigger profiles.",
    )
    logic_board_parser.add_argument(
        "--start-date",
        required=True,
        help="Window start date in YYYY-MM-DD format.",
    )
    logic_board_parser.add_argument(
        "--days",
        type=int,
        default=14,
        help="Number of days to include in the board.",
    )
    logic_board_parser.add_argument(
        "--profiles-dir",
        default="live_trigger/boxes",
        help="Directory containing trigger box folders and profile JSON files.",
    )
    logic_board_parser.add_argument(
        "--output-dir",
        default="live_trigger/plans",
        help="Directory for board outputs.",
    )
    logic_board_parser.add_argument(
        "--raw-root",
        default="live_trigger/raw",
        help="Raw cache root for schedule HTML.",
    )
    logic_board_parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=30,
        help="HTTP timeout seconds.",
    )
    logic_board_parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    logic_board_parser.set_defaults(func=build_logic_board_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)
    return args.func(args)
