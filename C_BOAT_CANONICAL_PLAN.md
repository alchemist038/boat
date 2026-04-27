# C:\boat Canonical Integration Plan

- updated_at: `2026-04-27 JST`
- current_shared_root: `\\038INS\boat`
- target_canonical_root: `C:\boat`
- workspace_root: `C:\CODEX_WORK\boat_clone`
- current_live_bet_line: `C:\CODEX_WORK\boat_clone\live_trigger_cli`
- current_state: `self-contained-runtime-active`

This file tracks the integration plan for moving the operational root from
`\\038INS\boat` onto this machine as `C:\boat` while keeping
`C:\CODEX_WORK\boat_clone` as the Git-managed workspace.

## Current State On 2026-04-27

The local self-contained runtime cutover is now active on `i5`.

- operational canonical data root:
  - `C:\boat\data`
- operational canonical DuckDB:
  - `C:\boat\data\silver\boat_race.duckdb`
- operational reports root:
  - `C:\boat\reports\strategies`
- Git editing / runtime workspace:
  - `C:\CODEX_WORK\boat_clone`
- rollback / fallback shared root:
  - `\\038INS\boat`

What is already switched:

- code defaults now prefer `C:\boat` when it exists
- daily DB refresh and racer-index scripts now prefer `C:\boat`
- `live_trigger_cli\run_ui.cmd` exports `C:\boat`-based env vars when possible
- `C:\boat\.venv` now exists and has the runtime dependencies plus Playwright
  Chromium
- the active `auto-loop` was restarted on `2026-04-27 22:24:22 JST`
  from `C:\boat`
- the UI server on port `8502` was restarted from `C:\boat`
- scheduler actions now point to:
  - `C:\boat\workspace_codex\scripts\run_shared_recent_collect_daily.ps1`
  - `C:\boat\workspace_codex\scripts\run_racer_rank_live_daily.ps1`
- runtime-hot state was copied and activated under:
  - `C:\boat\live_trigger_cli\data`
  - `C:\boat\live_trigger_cli\raw`
  - `C:\boat\live_trigger_fresh_exec\auto_system\data`
  - `C:\boat\live_trigger\auto_system\data`

What is intentionally still local to the workspace:

- Git history and editing workflow
- scratch analysis generation
- root markdown source editing

This means the active operating model is now:

- `C:\boat` is the system-of-record for `data/`, `reports/`, runtime state,
  and scheduler-owned execution
- `C:\CODEX_WORK\boat_clone` remains the Git / research / source-doc workspace
- `\\038INS\boat` is now treated as a rollback/fallback tree, not the primary
  writer root

## Target Model

- `C:\boat`
  - operational canonical root
  - canonical `data/`, `reports/`, and deployment-copy runtime tree
- `C:\CODEX_WORK\boat_clone`
  - Git workspace for edits, tests, research, and controlled promotion

Intended environment model after cutover:

- `BOAT_DATA_ROOT=C:\boat\data`
- optional `BOAT_CANONICAL_ROOT=C:\boat`
- optional `BOAT_REPORTS_ROOT=C:\boat\reports\strategies`
- optional `BOAT_PREDICT_SCRIPT_PATH=C:\boat\workspace_codex\scripts\predict_racer_rank_live.py`

Code-side preparation for this model was added on `2026-04-27` so the runtime
and daily scripts can derive their canonical DB/report/script roots from these
environment variables instead of assuming `\\038INS\boat`.

## Safe Initial Copy While Bet Line Is Active

Because the live bet line is currently running, the first copy should avoid the
runtime-hot state and bring over the stable tree first.

Conservative initial copy exclusions:

- `live_trigger\raw`
- `live_trigger\watchlists`
- `live_trigger\ready`
- `live_trigger\plans`
- `live_trigger\auto_system\data`
- `live_trigger_cli\data`
- `live_trigger_cli\raw`
- `live_trigger_fresh_exec\auto_system\data`
- `.venv`
- `.pytest_cache`
- `tmp_status`
- `logs`
- file exclusions for the initial pass:
  - `*.db`
  - `*.log`
  - `*.pid`
  - `air_bet_log.csv`

Reason:

- these locations contain live SQLite state, session/browser state, generated
  day files, screenshots, HTML captures, and append-only runtime logs
- they can be copied later during a short maintenance window or regenerated on
  the new canonical root

Recommended initial copy command:

```powershell
robocopy "\\038INS\boat" "C:\boat" /E /COPY:DAT /DCOPY:T /R:1 /W:1 /MT:8 `
  /XD ".venv" ".pytest_cache" "tmp_status" "logs" `
      "live_trigger\raw" "live_trigger\watchlists" "live_trigger\ready" "live_trigger\plans" `
      "live_trigger\auto_system\data" "live_trigger_cli\data" "live_trigger_cli\raw" `
      "live_trigger_fresh_exec\auto_system\data" `
  /XF "*.db" "*.log" "*.pid" "air_bet_log.csv"
```

Notes:

- use `/E` for the first pass, not `/MIR`
- the final cutover sync should be a shorter delta after the live line is paused
- do not copy onto `C:\CODEX_WORK\boat_clone`

## Cutover Sequence

1. Run the initial stable-tree copy from `\\038INS\boat` to `C:\boat`.
2. Keep the current live bet line running from `C:\CODEX_WORK\boat_clone`.
3. During a short maintenance window, stop or pause the active writer(s).
4. Sync the excluded runtime-hot locations that must be preserved if needed.
5. Set the canonical-root env vars to `C:\boat`.
6. Update scheduled tasks and launch wrappers to prefer `C:\boat`.
7. Restart the live line and confirm it reads `C:\boat\data` and
   `C:\boat\reports\strategies`.
8. Keep `\\038INS\boat` as rollback/fallback until several daily cycles pass.

Status against this sequence on `2026-04-27`:

- steps `1, 2, 3, 4, 5, 6, 7, 8`: complete
- step `3`: completed during the restart window
- runtime-hot state relocation is now complete for the current main line

## Validation After Cutover

- confirm `C:\boat\data\silver\boat_race.duckdb` exists and opens read-only
- confirm `C:\boat\reports\strategies\racer_rank_live_YYYYMMDD` is generated
- confirm the daily DB refresh task succeeds against `C:\boat\data`
- confirm the daily racer-index task succeeds against `C:\boat\data`
- confirm the live line imports the six active forward profiles normally
- confirm the loop log keeps advancing after the restart

## Current Cautions

- `auto-loop` and Streamlit can still appear as launcher + worker process under
  the venv launcher, so judge health from `auto_run.log` freshness and the
  worker PID log line
- the current portable root still assumes Python exists on the target machine
  if `setup_runtime.cmd` must be rerun there
