from __future__ import annotations

from datetime import date
from html import escape
from pathlib import Path

from boat_race_data.live_trigger import TriggerProfile
from boat_race_data.schedule_planner import ScheduleEvent, build_calendar_rows, collect_schedule_events
from boat_race_data.utils import ensure_dir


def build_logic_board(
    *,
    start_date: str,
    days: int,
    profiles: list[TriggerProfile],
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
    rows = build_calendar_rows(start, end, events)
    md_path = output_dir / f"logic_board_{start:%Y%m%d}_{end:%Y%m%d}.md"
    html_path = output_dir / f"logic_board_{start:%Y%m%d}_{end:%Y%m%d}.html"
    write_logic_board_markdown(md_path, start, end, profiles, rows)
    write_logic_board_html(html_path, start, end, profiles, rows)
    return {"logic_board_md": md_path, "logic_board_html": html_path}


def matching_profiles(event: ScheduleEvent, profiles: list[TriggerProfile]) -> list[TriggerProfile]:
    matched: list[TriggerProfile] = []
    for profile in profiles:
        if profile.enabled and (not profile.stadiums or event.stadium_code in profile.stadiums):
            matched.append(profile)
    return matched


def group_profiles_by_box(profiles: list[TriggerProfile]) -> dict[str, list[TriggerProfile]]:
    grouped: dict[str, list[TriggerProfile]] = {}
    for profile in profiles:
        grouped.setdefault(profile.box_id or "unassigned", []).append(profile)
    return grouped


def write_logic_board_markdown(
    path: Path,
    start: date,
    end: date,
    profiles: list[TriggerProfile],
    calendar_rows: list[dict[str, object]],
) -> None:
    ensure_dir(path.parent)
    lines = [
        f"# Logic Board {start:%Y-%m-%d} to {end:%Y-%m-%d}",
        "",
        "## Logic Boxes",
        "",
    ]
    for box_id, items in group_profiles_by_box(profiles).items():
        lines.append(f"### BOX {box_id}")
        for profile in items:
            stadium_text = ",".join(profile.stadiums) if profile.stadiums else "all"
            lines.append(f"- {profile.display_name} ({profile.profile_id})")
            lines.append(f"  stadiums: {stadium_text}")
            if profile.description:
                lines.append(f"  note: {profile.description}")
        lines.append("")
    lines.append("## Calendar")
    lines.append("")
    for row in calendar_rows:
        lines.append(f"### {row['date']} ({row['weekday']})")
        events: list[ScheduleEvent] = row["events"]  # type: ignore[assignment]
        if not events:
            lines.append("- none")
            lines.append("")
            continue
        for event in events:
            matched = matching_profiles(event, profiles)
            profile_text = ", ".join(profile.display_name for profile in matched) or "none"
            lines.append(
                f"- {event.stadium_name}({event.stadium_code}) {event.grade_label} {event.title} | logic={profile_text}"
            )
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_logic_board_html(
    path: Path,
    start: date,
    end: date,
    profiles: list[TriggerProfile],
    calendar_rows: list[dict[str, object]],
) -> None:
    ensure_dir(path.parent)
    profile_cards = "".join(
        (
            "<section class='box-card'>"
            f"<h2>BOX {escape(box_id)}</h2>"
            + "".join(
                "<article class='logic-card'>"
                f"<div class='swatch' style='background:{escape(profile.accent_color)}'></div>"
                f"<h3>{escape(profile.display_name)}</h3>"
                f"<p class='meta'>{escape(profile.profile_id)} / {escape(profile.strategy_id)}</p>"
                f"<p>{escape(profile.description or 'No description')}</p>"
                f"<p class='meta'>status: {escape('enabled' if profile.enabled else 'disabled')}</p>"
                f"<p class='meta'>stadiums: {escape(','.join(profile.stadiums) if profile.stadiums else 'all')}</p>"
                "</article>"
                for profile in items
            )
            + "</section>"
        )
        for box_id, items in group_profiles_by_box(profiles).items()
    )
    day_cards: list[str] = []
    for row in calendar_rows:
        events: list[ScheduleEvent] = row["events"]  # type: ignore[assignment]
        items = []
        for event in events:
            matched = matching_profiles(event, profiles)
            badges = "".join(
                f"<span class='badge' style='border-color:{escape(profile.accent_color)};color:{escape(profile.accent_color)}'>{escape(profile.display_name)}</span>"
                for profile in matched
            ) or "<span class='badge muted'>none</span>"
            items.append(
                "<li>"
                f"<div class='event-head'><span class='stadium'>{escape(event.stadium_name)}({escape(event.stadium_code)})</span>"
                f"<span class='grade'>{escape(event.grade_label)}</span></div>"
                f"<div class='event-title'>{escape(event.title)}</div>"
                f"<div class='badges'>{badges}</div>"
                "</li>"
            )
        item_html = "".join(items) or "<li class='empty'>none</li>"
        day_cards.append(
            "<section class='day-card'>"
            f"<h3>{escape(str(row['date']))} <span>{escape(str(row['weekday']))}</span></h3>"
            f"<p class='count'>active stadiums: {row['active_stadiums']}</p>"
            f"<ul>{item_html}</ul>"
            "</section>"
        )
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Logic Board {start:%Y-%m-%d} to {end:%Y-%m-%d}</title>
  <style>
    :root {{
      --bg: #f4efe2;
      --panel: #fffdf8;
      --ink: #1f2a30;
      --muted: #6a7479;
      --line: #d8d0c2;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Yu Gothic UI", "Segoe UI", sans-serif;
      background: radial-gradient(circle at top left, #e8f1e5, var(--bg));
      color: var(--ink);
    }}
    main {{ max-width: 1400px; margin: 0 auto; padding: 24px; }}
    h1 {{ margin: 0 0 8px; font-size: 34px; }}
    p.meta {{ margin: 0 0 22px; color: var(--muted); }}
    .logic-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
      margin-bottom: 28px;
    }}
    .box-card, .logic-card, .day-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px;
      box-shadow: 0 10px 26px rgba(31, 42, 48, 0.06);
    }}
    .box-card > h2 {{
      margin: 0 0 12px;
      font-size: 22px;
    }}
    .box-card .logic-card {{
      margin-top: 12px;
      box-shadow: none;
      background: rgba(255,255,255,0.6);
    }}
    .swatch {{
      width: 52px;
      height: 6px;
      border-radius: 999px;
      margin-bottom: 12px;
    }}
    .logic-card h3, .day-card h3 {{ margin: 0 0 6px; }}
    .calendar-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
    }}
    .count, .meta {{ color: var(--muted); }}
    ul {{ margin: 0; padding-left: 18px; }}
    li {{ margin-bottom: 10px; }}
    .event-head {{
      display: flex;
      justify-content: space-between;
      gap: 8px;
      font-weight: 700;
    }}
    .event-title {{ margin: 4px 0 6px; }}
    .badges {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .badge {{
      display: inline-block;
      border: 1px solid currentColor;
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 12px;
      font-weight: 700;
      background: rgba(255,255,255,0.7);
    }}
    .badge.muted {{ color: var(--muted); border-color: var(--muted); }}
    .empty {{ color: var(--muted); list-style: none; margin-left: -18px; }}
  </style>
</head>
<body>
  <main>
    <h1>Logic Board</h1>
    <p class="meta">{start:%Y-%m-%d} to {end:%Y-%m-%d}</p>
    <section class="logic-grid">
      {profile_cards}
    </section>
    <section class="calendar-grid">
      {''.join(day_cards)}
    </section>
  </main>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
