from datetime import date

from boat_race_data.live_trigger import TriggerProfile
from boat_race_data.logic_board import matching_profiles
from boat_race_data.schedule_planner import ScheduleEvent


def test_matching_profiles_filters_by_stadium() -> None:
    event = ScheduleEvent(
        stadium_code="12",
        stadium_name="住之江",
        title="Race",
        grade_code="Ippan",
        grade_label="General",
        start_date="2026-03-14",
        end_date="2026-03-19",
        days=6,
        detail_url="u",
        source_url="s",
        fetched_at="now",
    )
    profiles = [
        TriggerProfile.from_dict(
            {
                "profile_id": "p1",
                "strategy_id": "125",
                "display_name": "One",
                "enabled": True,
                "stadiums": ["12"],
                "pre_filters": {},
                "final_filters": {},
            }
        ),
        TriggerProfile.from_dict(
            {
                "profile_id": "p2",
                "strategy_id": "c2",
                "display_name": "Two",
                "enabled": True,
                "stadiums": ["13"],
                "pre_filters": {},
                "final_filters": {},
            }
        ),
    ]

    matched = matching_profiles(event, profiles)

    assert [profile.profile_id for profile in matched] == ["p1"]
