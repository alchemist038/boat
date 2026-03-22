from live_trigger_cli.cli import build_parser


def test_configure_accepts_profile_updates() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "configure",
            "--execution-mode",
            "assist_real",
            "--setting",
            "poll_seconds=15",
            "--profile-amount",
            "c2=300",
            "--disable-profile",
            "c2_provisional_v1",
        ]
    )

    assert args.execution_mode == "assist_real"
    assert args.setting == [("poll_seconds", "15")]
    assert args.profile_amount == [("c2", 300)]
    assert args.disable_profile == ["c2_provisional_v1"]


def test_manual_test_accepts_direct_bets() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "manual-test",
            "--test-mode",
            "confirm_only",
            "--stadium-code",
            "01",
            "--race-no",
            "12",
            "--bet",
            "trifecta:1-2-5:100",
            "--bet",
            "trifecta:2-ALL-ALL:100",
        ]
    )

    assert args.test_mode == "confirm_only"
    assert args.stadium_code == "01"
    assert args.race_no == 12
    assert args.bet == [
        {"bet_type": "trifecta", "combo": "1-2-5", "amount": 100},
        {"bet_type": "trifecta", "combo": "2-ALL-ALL", "amount": 100},
    ]


def test_run_cycle_accepts_as_of_override() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "run-cycle",
            "--race-date",
            "20260322",
            "--as-of",
            "2026-03-22 13:55:00",
        ]
    )

    assert args.race_date == "20260322"
    assert args.as_of.strftime("%Y-%m-%d %H:%M:%S") == "2026-03-22 13:55:00"
