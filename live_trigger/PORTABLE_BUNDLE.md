# Portable Live Trigger Bundle

`live_trigger/` is now the single portable folder for trigger planning and auto operation.
Move this folder as a unit and keep the internal relative layout unchanged.

## Folder map

- `app.py`
  - Main Streamlit UI for planning, watchlist creation, resolve, Air Bet, and stats
- `runtime/boat_race_data/`
  - Vendored trigger engine used by both the UI and the auto line
- `auto_system/`
  - Unattended automation UI and loop runner
- `boxes/`
  - Logic profiles
- `plans/`
  - Monthly and pre-day planning outputs
- `watchlists/`
  - Day-before target lists
- `ready/`
  - Day-of trigger resolution results
- `raw/`
  - Trigger-side cached HTML
- `air_bet_log.csv`
  - Air Bet execution history
- `auto_system/data/system.db`
  - Auto line state and execution history

## Unified flow

1. Monthly management
   - Run `app.py`
   - Build the logic board from the `board` tab
   - Outputs go to `plans/`
2. Previous-day management
   - Use the `watchlist` tab
   - Outputs go to `watchlists/`
3. Same-day management
   - Use the `resolve` tab
   - `beforeinfo` is checked and `trigger_ready` rows are written to `ready/`
4. Betting management
   - Manual Air Bet: `app.py`
   - Auto line UI: `auto_system/web_app.py`
   - Auto loop runner: `auto_system/auto_run.py`
5. Performance management
   - Manual side: `air_bet_log.csv`
   - Auto side: `auto_system/data/system.db`

## Launchers

- `run_app.cmd`
  - Starts the main Streamlit UI from this folder
- `run_auto_ui.cmd`
  - Starts the automation Streamlit UI
- `run_auto_cycle.cmd`
  - Starts the unattended 3-step loop

## Setup notes

- Python dependencies are listed in `requirements.txt`
- For real betting, create `auto_system/.env` from `auto_system/.env.example`
- If the shared data root changes, set `BOAT_DATA_ROOT`
- If this folder is moved, the vendored trigger engine keeps working with relative paths
