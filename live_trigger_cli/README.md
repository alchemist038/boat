# Live Trigger CLI

`live_trigger_cli/` is the current main bet line.

It does not own strategy logic by itself.
It owns:

- CLI and UI entry points
- execution-line state
- runtime DB, logs, and operator flow
- Telegram-assisted approval flow

It consumes shared logic from:

- `live_trigger/boxes/125`
- `live_trigger/boxes/c2`
- `live_trigger/boxes/4wind`
- `live_trigger/auto_system/app/core/bets.py`

Its local runtime state lives under:

- `live_trigger_cli/data/settings.json`
- `live_trigger_cli/data/system.db`
- `live_trigger_cli/data/auto_run.log`
- `live_trigger_cli/raw/`

## Current Main Forward Set

- `125_broad_four_stadium`
- `c2_provisional_v1`
- `4wind_base_415`

All three are now owned under shared `live_trigger/boxes/`.

## Execution Modes

- `air`
  - no final submit
- `assist_real`
  - opens the submit path but waits for operator approval
- `armed_real`
  - submits automatically

## Assist Flow

`assist_real` now follows this path:

1. GO is detected
2. Telegram GO notification is sent
3. operator can press `approve` or `reject`
4. `approve` submits within the assist window
5. `reject` discards
6. no action until deadline means timeout discard
7. submitted bets send a completion notification

## UI

Start the UI with:

```powershell
live_trigger_cli\run_ui.cmd
```

Default browser URL:

```text
http://localhost:8502
```

## Ownership Rule

- main execution line: `live_trigger_cli`
- shared logic owner: `live_trigger/boxes`
- shared bet expansion owner: `live_trigger/auto_system/app/core/bets.py`
- canonical DB owner: `\\038INS\boat\data`

If a strategy changes, update the shared box first and let the CLI line consume it.
