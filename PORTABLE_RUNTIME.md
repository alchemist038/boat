# Portable Runtime

This note describes the target operating model where the runtime can be carried
by moving the root folder itself.

## Target

The practical target is:

- `C:\boat`
  - execution line
  - canonical `data/`
  - canonical `reports/`
  - runtime state
  - launchers
  - local `.venv`
- `C:\CODEX_WORK\boat_clone`
  - Git worktree
  - logic research
  - scratch analysis
  - source markdown and controlled promotion

## What Must Exist Under The Portable Root

For `C:\boat` to be close to self-contained, keep these inside it:

- `data/`
- `reports/`
- `live_trigger_cli/data/`
- `live_trigger_cli/raw/`
- `live_trigger_fresh_exec/auto_system/data/`
- optional legacy runtime state under `live_trigger/auto_system/data/`
- `workspace_codex/scripts/`
- root `.venv`

## Bootstrap

Run:

```bat
setup_runtime.cmd
```

This creates `.\.venv`, installs the project dependencies, and installs the
Playwright Chromium browser used by the execution line.

## Main Launchers

- UI:
  - `run_live_trigger_cli_ui.cmd`
- loop only:
  - `run_live_trigger_cli_loop.cmd`

UI から `auto-loop` を起動する場合も、hidden background ではなく
表示コンソール付きで起動する前提です。

## Scheduler Registration

To repoint or create the two daily operational tasks for the current root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\workspace_codex\scripts\register_operational_tasks.ps1
```

If the tasks do not exist yet:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\workspace_codex\scripts\register_operational_tasks.ps1 -CreateIfMissing
```

## Important Boundary

This model aims to make the runtime portable by carrying one root folder.

It does not make the Git worktree portable by itself. The Git / research source
of truth remains under `C:\CODEX_WORK\boat_clone`.
