# Live Trigger

This folder contains the alert-trigger foundation for adopted and candidate logic boxes.

## Purpose

- Build next-day watchlists from official race list pages.
- Re-check `beforeinfo` close to the race and mark `trigger_ready` rows.
- Keep the logic definition separate by box, such as `125` and `c2`.

## Layout

- `boxes/`
  - one folder per logic box
  - each box stores `profiles/*.json`
- `watchlists/`
  - CSV output from next-day candidate extraction
- `ready/`
  - CSV output from final trigger resolution
- `plans/`
  - schedule and logic-board HTML / Markdown outputs
- `app.py`
  - Streamlit app for schedule, watchlist, and final-resolution checks

## Run The App

From the repo root:

```powershell
cd C:\CODEX_WORK\boat_clone
& .\.venv\Scripts\streamlit.exe run live_trigger\app.py
```

Or run this launcher:

```powershell
live_trigger\run_app.cmd
```

If the app dependency is not installed yet:

```powershell
& .\.venv\Scripts\python.exe -m pip install -e .[app]
```

## Current Rule

- `125` and `c2` are managed as separate boxes.
- Batch watchlist generation uses only `enabled: true` profiles by default.
- The app can still inspect disabled profiles and run them manually for validation.
