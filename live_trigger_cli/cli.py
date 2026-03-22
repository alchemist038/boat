from __future__ import annotations

import argparse
import json
from typing import Any

from . import runtime


def _parse_key_value(raw: str) -> tuple[str, str]:
    if "=" not in raw:
        raise argparse.ArgumentTypeError(f"Expected KEY=VALUE, got: {raw}")
    key, value = raw.split("=", 1)
    key = key.strip()
    if not key:
        raise argparse.ArgumentTypeError(f"Empty key is not allowed: {raw}")
    return key, value.strip()


def _parse_profile_amount(raw: str) -> tuple[str, int]:
    key, value = _parse_key_value(raw)
    try:
        amount = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Amount must be an integer: {raw}") from exc
    return key, amount


def _parse_scalar(value: str) -> Any:
    lowered = value.strip().lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def _parse_bet(raw: str) -> dict[str, Any]:
    parts = raw.split(":", 2)
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("Bet must be BET_TYPE:COMBO:AMOUNT")
    bet_type, combo, amount_text = parts
    try:
        amount = int(amount_text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Amount must be an integer: {raw}") from exc
    return {
        "bet_type": bet_type.strip(),
        "combo": combo.strip(),
        "amount": amount,
    }


def _parse_datetime_or_none(value: str | None) -> Any:
    if value is None:
        return None
    normalized = runtime._normalize_datetime(value)  # type: ignore[attr-defined]
    if normalized is None:
        raise argparse.ArgumentTypeError(f"Unsupported datetime format: {value}")
    return normalized


def _print_payload(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _command_show_settings(_: argparse.Namespace) -> int:
    _print_payload(runtime.load_settings())
    return 0


def _command_configure(args: argparse.Namespace) -> int:
    overrides = {}
    for key, value in args.setting or []:
        overrides[key] = _parse_scalar(value)
    profile_amount_updates = {key: amount for key, amount in args.profile_amount or []}
    result = runtime.configure_runtime(
        execution_mode=args.execution_mode,
        setting_overrides=overrides,
        profile_amount_updates=profile_amount_updates,
        enabled_profiles=args.enable_profile or [],
        disabled_profiles=args.disable_profile or [],
    )
    _print_payload(result)
    return 0


def _command_sync_watchlists(args: argparse.Namespace) -> int:
    _print_payload(runtime.sync_watchlists(race_date=args.race_date))
    return 0


def _command_evaluate_targets(args: argparse.Namespace) -> int:
    _print_payload(runtime.evaluate_targets(race_date=args.race_date, as_of=args.as_of))
    return 0


def _command_execute_bets(args: argparse.Namespace) -> int:
    _print_payload(runtime.execute_bets(race_date=args.race_date, as_of=args.as_of))
    return 0


def _command_run_cycle(args: argparse.Namespace) -> int:
    _print_payload(runtime.run_cycle(race_date=args.race_date, as_of=args.as_of))
    return 0


def _command_auto_loop(args: argparse.Namespace) -> int:
    _print_payload(runtime.auto_loop(max_cycles=args.max_cycles))
    return 0


def _command_manual_test(args: argparse.Namespace) -> int:
    settings_override = {}
    for key, value in args.setting or []:
        settings_override[key] = _parse_scalar(value)

    payload: dict[str, Any] = {
        "test_mode": args.test_mode,
        "settings": settings_override,
    }
    if args.test_mode != "login_only":
        if args.stadium_code is None or args.race_no is None:
            raise SystemExit("manual-test requires --stadium-code and --race-no unless --test-mode login_only")
        payload["stadium_code"] = args.stadium_code
        payload["race_no"] = args.race_no
        payload["bets"] = args.bet or []
        if not payload["bets"]:
            raise SystemExit("manual-test requires at least one --bet unless --test-mode login_only")
        if args.deadline_at is not None:
            payload["deadline_at"] = args.deadline_at.strftime("%Y-%m-%d %H:%M:%S")
    if args.cleanup_after_test:
        payload["cleanup_after_test"] = True
    if args.hold_open_seconds is not None:
        payload["hold_open_seconds"] = args.hold_open_seconds
    if args.next_real_target_in_seconds is not None:
        payload["next_real_target_in_seconds"] = args.next_real_target_in_seconds

    _print_payload(runtime.run_manual_test(payload))
    return 0


def _command_summary(_: argparse.Namespace) -> int:
    _print_payload(runtime.latest_summary())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CLI-first isolated bet runtime that leaves current live_trigger lines untouched."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    show_settings_parser = subparsers.add_parser("show-settings", help="Print effective CLI-line settings.")
    show_settings_parser.set_defaults(func=_command_show_settings)

    configure_parser = subparsers.add_parser("configure", help="Update CLI-line settings.")
    configure_parser.add_argument(
        "--execution-mode",
        choices=runtime.VALID_EXECUTION_MODES,
        help="Execution mode for future intent creation.",
    )
    configure_parser.add_argument(
        "--setting",
        action="append",
        type=_parse_key_value,
        help="Generic setting override in KEY=VALUE form.",
    )
    configure_parser.add_argument(
        "--profile-amount",
        action="append",
        type=_parse_profile_amount,
        help="Profile amount override in PROFILE_ID=AMOUNT form.",
    )
    configure_parser.add_argument(
        "--enable-profile",
        action="append",
        help="Explicitly enable a profile in this CLI line.",
    )
    configure_parser.add_argument(
        "--disable-profile",
        action="append",
        help="Explicitly disable a profile in this CLI line.",
    )
    configure_parser.set_defaults(func=_command_configure)

    sync_parser = subparsers.add_parser("sync-watchlists", help="Import today's shared watchlists into CLI-line DB.")
    sync_parser.add_argument("--race-date", help="Race date in YYYY-MM-DD or YYYYMMDD. Defaults to today.")
    sync_parser.set_defaults(func=_command_sync_watchlists)

    evaluate_parser = subparsers.add_parser("evaluate-targets", help="Fetch beforeinfo and create intents.")
    evaluate_parser.add_argument("--race-date", help="Race date in YYYY-MM-DD or YYYYMMDD. Defaults to today.")
    evaluate_parser.add_argument(
        "--as-of",
        type=_parse_datetime_or_none,
        help="Override current time for window checks.",
    )
    evaluate_parser.set_defaults(func=_command_evaluate_targets)

    execute_parser = subparsers.add_parser("execute-bets", help="Consume pending intents and execute them.")
    execute_parser.add_argument("--race-date", help="Race date in YYYY-MM-DD or YYYYMMDD. Defaults to today.")
    execute_parser.add_argument(
        "--as-of",
        type=_parse_datetime_or_none,
        help="Override current time for window checks.",
    )
    execute_parser.set_defaults(func=_command_execute_bets)

    cycle_parser = subparsers.add_parser("run-cycle", help="Run sync -> evaluate -> execute once.")
    cycle_parser.add_argument("--race-date", help="Race date in YYYY-MM-DD or YYYYMMDD. Defaults to today.")
    cycle_parser.add_argument(
        "--as-of",
        type=_parse_datetime_or_none,
        help="Override current time for window checks.",
    )
    cycle_parser.set_defaults(func=_command_run_cycle)

    loop_parser = subparsers.add_parser("auto-loop", help="Run the CLI-line loop while system_running=true.")
    loop_parser.add_argument(
        "--max-cycles",
        type=int,
        help="Optional safety cap for loop iterations.",
    )
    loop_parser.set_defaults(func=_command_auto_loop)

    manual_test_parser = subparsers.add_parser("manual-test", help="Run direct Teleboat manual/real test via reused executor.")
    manual_test_parser.add_argument(
        "--test-mode",
        default="login_only",
        choices=("login_only", "confirm_only", "confirm_prefill", "assist_real", "armed_real"),
        help="Manual test mode.",
    )
    manual_test_parser.add_argument("--stadium-code", help="Stadium code such as 01.")
    manual_test_parser.add_argument("--race-no", type=int, help="Race number.")
    manual_test_parser.add_argument(
        "--bet",
        action="append",
        type=_parse_bet,
        help="Bet row in BET_TYPE:COMBO:AMOUNT form.",
    )
    manual_test_parser.add_argument(
        "--deadline-at",
        type=_parse_datetime_or_none,
        help="Optional deadline timestamp for the test target.",
    )
    manual_test_parser.add_argument(
        "--cleanup-after-test",
        action="store_true",
        help="Log out after the test when a session remains active.",
    )
    manual_test_parser.add_argument(
        "--hold-open-seconds",
        type=int,
        help="Keep the browser open briefly after success.",
    )
    manual_test_parser.add_argument(
        "--next-real-target-in-seconds",
        type=int,
        help="Hint for burst_reuse policy.",
    )
    manual_test_parser.add_argument(
        "--setting",
        action="append",
        type=_parse_key_value,
        help="Temporary executor setting override in KEY=VALUE form.",
    )
    manual_test_parser.set_defaults(func=_command_manual_test)

    summary_parser = subparsers.add_parser("summary", help="Show a small runtime DB summary.")
    summary_parser.set_defaults(func=_command_summary)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
