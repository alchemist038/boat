from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path
import re
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from boat_race_data.client import BoatRaceClient, FetchResult
from boat_race_data.constants import BASE_URL, STADIUMS
from boat_race_data.utils import ensure_dir

MONTHLY_SCHEDULE_PATH = "/owpc/pc/race/monthlyschedule?ym={ym}"
SCHEDULE_EVENT_COLUMNS = [
    "stadium_code",
    "stadium_name",
    "title",
    "grade_code",
    "grade_label",
    "start_date",
    "end_date",
    "days",
    "detail_url",
    "source_url",
    "fetched_at",
]

GRADE_LABELS = {
    "SG": "SG",
    "G1": "G1",
    "G2": "G2",
    "G3": "G3",
    "Lady": "Lady",
    "Venus": "Venus",
    "Rookie": "Rookie",
    "Masters": "Masters",
    "Ippan": "General",
}


@dataclass(slots=True)
class ScheduleEvent:
    stadium_code: str
    stadium_name: str
    title: str
    grade_code: str
    grade_label: str
    start_date: str
    end_date: str
    days: int
    detail_url: str
    source_url: str
    fetched_at: str

    def as_row(self) -> dict[str, object]:
        return {
            "stadium_code": self.stadium_code,
            "stadium_name": self.stadium_name,
            "title": self.title,
            "grade_code": self.grade_code,
            "grade_label": self.grade_label,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "days": self.days,
            "detail_url": self.detail_url,
            "source_url": self.source_url,
            "fetched_at": self.fetched_at,
        }


def build_schedule_window(
    *,
    start_date: str,
    days: int,
    output_dir: Path,
    raw_root: Path,
    timeout_seconds: int,
) -> dict[str, Path]:
    start, end, events = collect_schedule_events(
        start_date=start_date,
        days=days,
        raw_root=raw_root,
        timeout_seconds=timeout_seconds,
    )
    calendar_rows = build_calendar_rows(start, end, events)

    events_csv = output_dir / f"schedule_events_{start:%Y%m%d}_{end:%Y%m%d}.csv"
    calendar_md = output_dir / f"schedule_window_{start:%Y%m%d}_{end:%Y%m%d}.md"
    calendar_html = output_dir / f"schedule_window_{start:%Y%m%d}_{end:%Y%m%d}.html"

    write_schedule_events(events_csv, events)
    write_schedule_markdown(calendar_md, start, end, events, calendar_rows)
    write_schedule_html(calendar_html, start, end, calendar_rows)

    return {
        "events_csv": events_csv,
        "calendar_md": calendar_md,
        "calendar_html": calendar_html,
    }


def collect_schedule_events(
    *,
    start_date: str,
    days: int,
    raw_root: Path,
    timeout_seconds: int,
) -> tuple[date, date, list[ScheduleEvent]]:
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = start + timedelta(days=days - 1)
    months = _month_keys_between(start, end)
    ensure_dir(raw_root)

    events_by_key: dict[tuple[str, str, str], ScheduleEvent] = {}
    with BoatRaceClient(timeout_seconds=timeout_seconds) as client:
        for ym in months:
            fetch = _fetch_monthly_schedule(client, ym, raw_root)
            for event in parse_monthly_schedule(fetch.text or "", fetch.url, fetch.fetched_at):
                if _overlaps_window(event, start, end):
                    key = (event.stadium_code, event.start_date, event.title)
                    events_by_key[key] = event

    events = sorted(events_by_key.values(), key=lambda item: (item.start_date, item.stadium_code, item.title))
    return start, end, events


def parse_monthly_schedule(html: str, source_url: str, fetched_at: str) -> list[ScheduleEvent]:
    soup = BeautifulSoup(html, "html.parser")
    events: list[ScheduleEvent] = []
    for table in soup.select("div.table1 table"):
        for body in table.find_all("tbody"):
            row = body.find("tr")
            if row is None:
                continue
            header = row.find("th")
            if header is None:
                continue
            stadium_code = _stadium_code_from_header(header)
            if stadium_code is None:
                continue
            stadium_name = STADIUMS.get(stadium_code, stadium_code)
            for cell in row.find_all("td"):
                anchor = cell.find("a")
                if anchor is None:
                    continue
                detail_url = _absolute_url(anchor.get("href", ""))
                if not detail_url:
                    continue
                start_date = _hd_param(detail_url)
                if start_date is None:
                    continue
                colspan = int(cell.get("colspan", "1") or "1")
                end_date = (
                    datetime.strptime(start_date, "%Y-%m-%d").date() + timedelta(days=colspan - 1)
                ).strftime("%Y-%m-%d")
                grade_code = _grade_code_from_classes(cell.get("class", []))
                events.append(
                    ScheduleEvent(
                        stadium_code=stadium_code,
                        stadium_name=stadium_name,
                        title=_clean(anchor.get_text(" ", strip=True)),
                        grade_code=grade_code,
                        grade_label=GRADE_LABELS.get(grade_code, grade_code or ""),
                        start_date=start_date,
                        end_date=end_date,
                        days=colspan,
                        detail_url=detail_url,
                        source_url=source_url,
                        fetched_at=fetched_at,
                    )
                )
    return events


def build_calendar_rows(
    start: date,
    end: date,
    events: list[ScheduleEvent],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    current = start
    while current <= end:
        current_iso = current.strftime("%Y-%m-%d")
        day_events = [
            event
            for event in events
            if event.start_date <= current_iso <= event.end_date
        ]
        rows.append(
            {
                "date": current_iso,
                "weekday": current.strftime("%a"),
                "active_stadiums": len(day_events),
                "events": day_events,
            }
        )
        current += timedelta(days=1)
    return rows


def write_schedule_events(path: Path, events: list[ScheduleEvent]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SCHEDULE_EVENT_COLUMNS)
        writer.writeheader()
        for event in events:
            writer.writerow(event.as_row())


def write_schedule_markdown(
    path: Path,
    start: date,
    end: date,
    events: list[ScheduleEvent],
    calendar_rows: list[dict[str, object]],
) -> None:
    lines = [
        f"# Schedule Window {start:%Y-%m-%d} to {end:%Y-%m-%d}",
        "",
        f"- days: {(end - start).days + 1}",
        f"- unique_events: {len(events)}",
        "",
        "## Daily View",
        "",
    ]
    for row in calendar_rows:
        lines.append(f"### {row['date']} ({row['weekday']})")
        lines.append(f"- active_stadiums: {row['active_stadiums']}")
        day_events: list[ScheduleEvent] = row["events"]  # type: ignore[assignment]
        if not day_events:
            lines.append("- none")
            lines.append("")
            continue
        for event in day_events:
            lines.append(
                f"- {event.stadium_name}({event.stadium_code}) {event.grade_label} "
                f"{event.title} [{event.start_date}..{event.end_date}]"
            )
        lines.append("")

    lines.extend(["## Event List", ""])
    for event in events:
        lines.append(
            f"- {event.start_date}..{event.end_date} {event.stadium_name}({event.stadium_code}) "
            f"{event.grade_label} {event.title}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_schedule_html(path: Path, start: date, end: date, calendar_rows: list[dict[str, object]]) -> None:
    ensure_dir(path.parent)
    cards: list[str] = []
    for row in calendar_rows:
        events: list[ScheduleEvent] = row["events"]  # type: ignore[assignment]
        items = "".join(
            (
                "<li>"
                f"<span class='grade'>{escape(event.grade_label)}</span> "
                f"<span class='stadium'>{escape(event.stadium_name)}({escape(event.stadium_code)})</span> "
                f"<span class='title'>{escape(event.title)}</span>"
                "</li>"
            )
            for event in events
        ) or "<li class='empty'>none</li>"
        cards.append(
            "<section class='day-card'>"
            f"<h2>{escape(str(row['date']))} <span>{escape(str(row['weekday']))}</span></h2>"
            f"<p class='count'>active stadiums: {row['active_stadiums']}</p>"
            f"<ul>{items}</ul>"
            "</section>"
        )
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Schedule Window {start:%Y-%m-%d} to {end:%Y-%m-%d}</title>
  <style>
    :root {{
      --bg: #f3efe4;
      --panel: #fffdf8;
      --ink: #1f2a30;
      --muted: #6a7479;
      --accent: #165d5b;
      --line: #d8d0c2;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Yu Gothic UI", "Segoe UI", sans-serif;
      background: linear-gradient(180deg, #e7ecdf 0%, var(--bg) 100%);
      color: var(--ink);
    }}
    main {{
      max-width: 1320px;
      margin: 0 auto;
      padding: 24px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 32px;
    }}
    p.meta {{
      margin: 0 0 24px;
      color: var(--muted);
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 16px;
    }}
    .day-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px;
      box-shadow: 0 10px 30px rgba(31, 42, 48, 0.06);
    }}
    .day-card h2 {{
      margin: 0 0 6px;
      font-size: 20px;
    }}
    .day-card h2 span {{
      color: var(--muted);
      font-size: 14px;
      margin-left: 8px;
    }}
    .count {{
      margin: 0 0 12px;
      color: var(--accent);
      font-weight: 700;
    }}
    ul {{
      margin: 0;
      padding-left: 18px;
    }}
    li {{
      margin-bottom: 8px;
      line-height: 1.4;
    }}
    .grade {{
      display: inline-block;
      min-width: 54px;
      color: var(--accent);
      font-weight: 700;
    }}
    .stadium {{
      font-weight: 700;
    }}
    .empty {{
      color: var(--muted);
      list-style: none;
      margin-left: -18px;
    }}
  </style>
</head>
<body>
  <main>
    <h1>Upcoming Schedule Window</h1>
    <p class="meta">{start:%Y-%m-%d} to {end:%Y-%m-%d}</p>
    <div class="grid">
      {''.join(cards)}
    </div>
  </main>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


def _fetch_monthly_schedule(client: BoatRaceClient, ym: str, raw_root: Path) -> FetchResult:
    url = f"{BASE_URL}{MONTHLY_SCHEDULE_PATH.format(ym=ym)}"
    raw_path = raw_root / "monthlyschedule" / f"{ym}.html"
    if raw_path.exists():
        content = raw_path.read_bytes()
        return FetchResult(
            url=url,
            fetched_at=datetime.fromtimestamp(raw_path.stat().st_mtime).isoformat(),
            raw_path=raw_path,
            content=content,
            text=content.decode("utf-8", errors="replace"),
        )
    return client.fetch_text(url, raw_path)


def _month_keys_between(start: date, end: date) -> list[str]:
    keys: list[str] = []
    current = date(start.year, start.month, 1)
    while current <= end:
        keys.append(current.strftime("%Y%m"))
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return keys


def _overlaps_window(event: ScheduleEvent, start: date, end: date) -> bool:
    event_start = datetime.strptime(event.start_date, "%Y-%m-%d").date()
    event_end = datetime.strptime(event.end_date, "%Y-%m-%d").date()
    return event_start <= end and event_end >= start


def _stadium_code_from_header(header: object) -> str | None:
    header_html = str(header)
    match = re.search(r"jcd=(\d{2})", header_html)
    if match:
        return match.group(1)
    match = re.search(r"text_place1_(\d{2})", header_html)
    return match.group(1) if match else None


def _grade_code_from_classes(classes: list[str]) -> str:
    for class_name in classes:
        match = re.match(r"is-gradeColor(.+)", class_name)
        if match:
            return match.group(1)
    return ""


def _hd_param(url: str) -> str | None:
    parsed = urlparse(url)
    value = parse_qs(parsed.query).get("hd", [""])
    if not value or not value[0]:
        return None
    raw = value[0]
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"


def _absolute_url(path_or_url: str) -> str:
    text = _clean(path_or_url)
    if not text:
        return ""
    if text.startswith("http://") or text.startswith("https://"):
        return text
    return f"{BASE_URL}{text}"


def _clean(value: str) -> str:
    return " ".join(value.replace("\u3000", " ").split())
