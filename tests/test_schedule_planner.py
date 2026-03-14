from datetime import date

from boat_race_data.schedule_planner import build_calendar_rows, parse_monthly_schedule


def test_parse_monthly_schedule_extracts_event_range() -> None:
    html = """
    <div class="table1">
      <table>
        <tbody>
          <tr class="is-fs12">
            <th><a href="/owpc/pc/data/stadium?jcd=12">x</a></th>
            <td colspan="4" class="is-gradeColorIppan">
              <a href="/owpc/pc/race/raceindex?jcd=12&hd=20260314">Sample Title</a>
            </td>
            <td>&nbsp;</td>
          </tr>
        </tbody>
      </table>
    </div>
    """

    events = parse_monthly_schedule(html, "https://www.boatrace.jp/owpc/pc/race/monthlyschedule?ym=202603", "now")

    assert len(events) == 1
    assert events[0].stadium_code == "12"
    assert events[0].start_date == "2026-03-14"
    assert events[0].end_date == "2026-03-17"
    assert events[0].days == 4


def test_build_calendar_rows_marks_overlapping_days() -> None:
    html = """
    <div class="table1">
      <table>
        <tbody>
          <tr class="is-fs12">
            <th><a href="/owpc/pc/data/stadium?jcd=12">x</a></th>
            <td colspan="3" class="is-gradeColorIppan">
              <a href="/owpc/pc/race/raceindex?jcd=12&hd=20260314">Sample Title</a>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    """
    events = parse_monthly_schedule(html, "src", "now")

    rows = build_calendar_rows(date(2026, 3, 14), date(2026, 3, 17), events)

    assert rows[0]["active_stadiums"] == 1
    assert rows[1]["active_stadiums"] == 1
    assert rows[2]["active_stadiums"] == 1
    assert rows[3]["active_stadiums"] == 0
