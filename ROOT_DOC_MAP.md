# Root Doc Map

This file is the root-level document index for the repo.
Use it when you want to understand what to open next without guessing.

## Recommended Read Order

1. [CODEX_START_HERE.md](./CODEX_START_HERE.md)
   - startup checklist for coordination and Git sync
2. [ROOT_DOC_MAP.md](./ROOT_DOC_MAP.md)
   - this routing map
3. Open the current status file that matches your task:
   - [PROJECT_STATUS.md](./PROJECT_STATUS.md)
   - [BET_PROJECT_STATUS.md](./BET_PROJECT_STATUS.md)
   - [DB_STATUS.md](./DB_STATUS.md)
4. If machine coordination matters, read:
   - [TO_I5_FROM_ME.md](./TO_I5_FROM_ME.md)
   - [FROM_I5_TO_ME.md](./FROM_I5_TO_ME.md)
   - [TO_INS14_FROM_ME.md](./TO_INS14_FROM_ME.md)
   - [FROM_INS14_TO_ME.md](./FROM_INS14_TO_ME.md)

## Which Root File Owns What

- [README.md](./README.md)
  - repository overview, CLI entry points, storage model, and canonical shared data root
- [CODEX_START_HERE.md](./CODEX_START_HERE.md)
  - startup procedure for a new session
- [PROJECT_STATUS.md](./PROJECT_STATUS.md)
  - high-level project state across data, strategy research, and incoming work
- [BET_PROJECT_STATUS.md](./BET_PROJECT_STATUS.md)
  - trigger, auto-bet, Teleboat, and execution-line status
- [DB_STATUS.md](./DB_STATUS.md)
  - current shared bronze/silver coverage, remaining gaps, rebuild status, and scheduler status

## Data / DB Route

Open these when the task is about collection, missing dates, shared data, or refresh rules.

- [README.md](./README.md)
- [DB_STATUS.md](./DB_STATUS.md)
- [FROM_I5_TO_ME.md](./FROM_I5_TO_ME.md)
- [run_daily_recent_collect.ps1](./run_daily_recent_collect.ps1)

## Strategy Research Route

Open these when the task is about logic evaluation, backtests, and adopted vs candidate rules.

- [PROJECT_STATUS.md](./PROJECT_STATUS.md)
- [projects/125/README.md](./projects/125/README.md)
- [projects/c2/status_notebooklm_20260313.txt](./projects/c2/status_notebooklm_20260313.txt)
- [reports/strategies/gemini_registry/README.md](./reports/strategies/gemini_registry/README.md)
- [reports/strategies/gemini_registry/4wind/README.md](./reports/strategies/gemini_registry/4wind/README.md)

## Live Trigger Portable Route

Open these when the task is about the main portable trigger bundle.

- [BET_PROJECT_STATUS.md](./BET_PROJECT_STATUS.md)
- [live_trigger/README.md](./live_trigger/README.md)
- [live_trigger/PORTABLE_BUNDLE.md](./live_trigger/PORTABLE_BUNDLE.md)
- [live_trigger/PROJECT_RULES.md](./live_trigger/PROJECT_RULES.md)

## Fresh Execution Route

Open these when the task is about the separate fresh real-execution line.

- [BET_PROJECT_STATUS.md](./BET_PROJECT_STATUS.md)
- [live_trigger_fresh_exec/README.md](./live_trigger_fresh_exec/README.md)
- [live_trigger_fresh_exec/FRESH_EXECUTION_FLOW.md](./live_trigger_fresh_exec/FRESH_EXECUTION_FLOW.md)
- [live_trigger/PROJECT_RULES.md](./live_trigger/PROJECT_RULES.md)

## Coordination Route

Open these when the task depends on another machine, handoff, or shared ownership.

- [TO_I5_FROM_ME.md](./TO_I5_FROM_ME.md)
- [FROM_I5_TO_ME.md](./FROM_I5_TO_ME.md)
- [TO_INS14_FROM_ME.md](./TO_INS14_FROM_ME.md)
- [FROM_INS14_TO_ME.md](./FROM_INS14_TO_ME.md)

## Update Rules

When work changes, update the root-level document that owns the summary, then update the detailed sub-doc if needed.

- Data or scheduler changes:
  - update [DB_STATUS.md](./DB_STATUS.md)
  - update [PROJECT_STATUS.md](./PROJECT_STATUS.md) if the high-level interpretation changed
- Trigger / auto-bet / execution-line changes:
  - update [BET_PROJECT_STATUS.md](./BET_PROJECT_STATUS.md)
  - update the detailed trigger doc:
    - [live_trigger/PORTABLE_BUNDLE.md](./live_trigger/PORTABLE_BUNDLE.md)
    - [live_trigger_fresh_exec/FRESH_EXECUTION_FLOW.md](./live_trigger_fresh_exec/FRESH_EXECUTION_FLOW.md)
- Cross-machine handoff changes:
  - update the relevant `TO_*` or `FROM_*` file
- Strategy adoption or research conclusion changes:
  - update [PROJECT_STATUS.md](./PROJECT_STATUS.md)
  - update the relevant project or report README
