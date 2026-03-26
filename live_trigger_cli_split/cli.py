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


def _parse_datetime_or_none(value: str | None) -> Any:
    if value is None:
        return None
    normalized = runtime.base_runtime._normalize_datetime(value)  # type: ignore[attr-defined]
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


def _command_run_bet_cycle(args: argparse.Namespace) -> int:
    _print_payload(runtime.run_bet_cycle(race_date=args.race_date, as_of=args.as_of))
    return 0


def _command_sync_loop(args: argparse.Namespace) -> int:
    _print_payload(runtime.sync_loop(max_cycles=args.max_cycles))
    return 0


def _command_bet_loop(args: argparse.Namespace) -> int:
    _print_payload(runtime.bet_loop(max_cycles=args.max_cycles))
    return 0


def _command_summary(_: argparse.Namespace) -> int:
    _print_payload(runtime.latest_summary())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Experimental split runtime that separates sync-loop and bet-loop while reusing shared logic."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    show_settings_parser = subparsers.add_parser("show-settings", help="Print effective split-line settings.")
    show_settings_parser.set_defaults(func=_command_show_settings)

    configure_parser = subparsers.add_parser("configure", help="Update split-line settings.")
    configure_parser.add_argument(
        "--execution-mode",
        choices=runtime.base_runtime.VALID_EXECUTION_MODES,
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
        help="Explicitly enable a profile in this split line.",
    )
    configure_parser.add_argument(
        "--disable-profile",
        action="append",
        help="Explicitly disable a profile in this split line.",
    )
    configure_parser.set_defaults(func=_command_configure)

    sync_parser = subparsers.add_parser("sync-watchlists", help="Run one sync cycle.")
    sync_parser.add_argument("--race-date", help="Race date in YYYY-MM-DD or YYYYMMDD. Defaults to today.")
    sync_parser.set_defaults(func=_command_sync_watchlists)

    bet_cycle_parser = subparsers.add_parser("run-bet-cycle", help="Run evaluate + execute once.")
    bet_cycle_parser.add_argument("--race-date", help="Race date in YYYY-MM-DD or YYYYMMDD. Defaults to today.")
    bet_cycle_parser.add_argument(
        "--as-of",
        type=_parse_datetime_or_none,
        help="Override current time for window checks.",
    )
    bet_cycle_parser.set_defaults(func=_command_run_bet_cycle)

    sync_loop_parser = subparsers.add_parser("sync-loop", help="Run the low-frequency sync loop.")
    sync_loop_parser.add_argument("--max-cycles", type=int, help="Optional safety cap for loop iterations.")
    sync_loop_parser.set_defaults(func=_command_sync_loop)

    bet_loop_parser = subparsers.add_parser("bet-loop", help="Run the higher-frequency evaluate/execute loop.")
    bet_loop_parser.add_argument("--max-cycles", type=int, help="Optional safety cap for loop iterations.")
    bet_loop_parser.set_defaults(func=_command_bet_loop)

    summary_parser = subparsers.add_parser("summary", help="Show a small split-runtime DB summary.")
    summary_parser.set_defaults(func=_command_summary)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)

