# Live Trigger CLI Split

`live_trigger_cli_split/` is the experimental next box for future broad-scan logic additions.

It does **not** replace the current main line yet.

- current protected main line:
  - `live_trigger_cli`
- this split box:
  - separate `sync_loop`
  - separate `bet_loop`
  - shared logic truth stays in `live_trigger/boxes/`
  - shared bet expansion stays in `live_trigger/auto_system/app/core/bets.py`

## Purpose

The goal is to keep the current main line stable while preparing a structure that can absorb more broad-scan logic without putting all work into one combined loop.

This box reuses:

- shared logic from `src/boat_race_data/live_trigger.py`
- shared bet expansion from `live_trigger/auto_system/app/core/bets.py`
- current runtime functions from `live_trigger_cli/runtime.py`

It keeps its own runtime state under this folder:

- `live_trigger_cli_split/data/settings.json`
- `live_trigger_cli_split/data/system.db`
- `live_trigger_cli_split/data/auto_run.log`
- `live_trigger_cli_split/data/sync_loop.log`
- `live_trigger_cli_split/data/bet_loop.log`
- `live_trigger_cli_split/raw/`

## Loop Split

- `sync_loop`
  - low-frequency watchlist rebuild
  - interval comes from `sync_interval_seconds`
- `bet_loop`
  - higher-frequency `evaluate + execute`
  - interval comes from `poll_seconds`

## Commands

```powershell
python -m live_trigger_cli_split show-settings
python -m live_trigger_cli_split configure --setting system_running=true
python -m live_trigger_cli_split sync-loop
python -m live_trigger_cli_split bet-loop
python -m live_trigger_cli_split run-bet-cycle
```

## Front-Facing Launchers

```powershell
live_trigger_cli_split\run_sync_loop.cmd
live_trigger_cli_split\run_bet_loop.cmd
```

Both launch visible consoles on purpose.

## Current Status

- minimal scaffold only
- no dedicated UI yet
- safe to use for structural experimentation
- not yet promoted as the main operating line

