# Root Doc Map

This file is the root-level document index for the repo.
Use it when you want to understand what to open next without guessing.

## Recommended Read Order

1. [CODEX_START_HERE.md](./CODEX_START_HERE.md)
   - startup checklist for coordination and Git sync
2. [ROOT_DOC_MAP.md](./ROOT_DOC_MAP.md)
   - this routing map
3. Open the operating-model doc when ownership or sync boundaries matter:
   - [OPERATING_MODEL.md](./OPERATING_MODEL.md)
4. Open the current status file that matches your task:
   - [PROJECT_STATUS.md](./PROJECT_STATUS.md)
   - [BET_PROJECT_STATUS.md](./BET_PROJECT_STATUS.md)
   - [DB_STATUS.md](./DB_STATUS.md)
   - [LOGIC_STATUS.md](./LOGIC_STATUS.md)
   - [RACER_INDEX_STATUS.md](./RACER_INDEX_STATUS.md)
5. If machine coordination matters, read:
   - [TO_I5_FROM_ME.md](./TO_I5_FROM_ME.md)
   - [FROM_I5_TO_ME.md](./FROM_I5_TO_ME.md)
   - [TO_INS14_FROM_ME.md](./TO_INS14_FROM_ME.md)
   - [FROM_INS14_TO_ME.md](./FROM_INS14_TO_ME.md)

## Which Root File Owns What

- [README.md](./README.md)
  - repository overview, CLI entry points, storage model, and canonical shared data root
- [R_CONCEPT.md](./R_CONCEPT.md)
  - project-level definition of `R` as max-drawdown-based risk scaling
- [CODEX_START_HERE.md](./CODEX_START_HERE.md)
  - startup procedure for a new session
- [PROJECT_STATUS.md](./PROJECT_STATUS.md)
  - high-level project state across data, strategy research, and incoming work
- [BET_PROJECT_STATUS.md](./BET_PROJECT_STATUS.md)
  - trigger, auto-bet, Teleboat, and execution-line status
- [DB_STATUS.md](./DB_STATUS.md)
  - current shared bronze/silver coverage, remaining gaps, rebuild status, and scheduler status
- [OPERATING_MODEL.md](./OPERATING_MODEL.md)
  - machine roles, sync boundaries, and non-negotiable owners
- [PROJECT_TIMELINE.md](./PROJECT_TIMELINE.md)
  - major steps in the recent project evolution
- [LOGIC_STATUS.md](./LOGIC_STATUS.md)
  - parent status for the current logic set and logic-adjacent tracks
- [RACER_INDEX_STATUS.md](./RACER_INDEX_STATUS.md)
  - racer-index status as a logic substrate, not a separate operating line

## Data / DB Route

Open these when the task is about collection, missing dates, shared data, or refresh rules.

- [README.md](./README.md)
- [DB_STATUS.md](./DB_STATUS.md)
- [FROM_I5_TO_ME.md](./FROM_I5_TO_ME.md)
- [run_daily_recent_collect.ps1](./run_daily_recent_collect.ps1)

## Logic Research Route

Open these when the task is about logic evaluation, adopted filters, forward candidates, and racer-index work.

- [LOGIC_STATUS.md](./LOGIC_STATUS.md)
- [RACER_INDEX_STATUS.md](./RACER_INDEX_STATUS.md)
- [racer_index/README.md](./racer_index/README.md)
- [racer_index/OPERATIONS.md](./racer_index/OPERATIONS.md)
- [racer_index/SCHEMA.md](./racer_index/SCHEMA.md)
- [PROJECT_STATUS.md](./PROJECT_STATUS.md)
- [projects/125/README.md](./projects/125/README.md)
- [projects/c2/status_notebooklm_20260313.txt](./projects/c2/status_notebooklm_20260313.txt)
- [projects/4wind/README.md](./projects/4wind/README.md)
- [R_CONCEPT.md](./R_CONCEPT.md)
- [reports/strategies/gemini_registry/README.md](./reports/strategies/gemini_registry/README.md)
- [reports/strategies/gemini_registry/4wind/README.md](./reports/strategies/gemini_registry/4wind/README.md)

## CLI Bet Line Route

Open these when the task is about the current main bet line.

- [BET_PROJECT_STATUS.md](./BET_PROJECT_STATUS.md)
- [OPERATING_MODEL.md](./OPERATING_MODEL.md)
- [live_trigger_cli/README.md](./live_trigger_cli/README.md)
- [live_trigger/PROJECT_RULES.md](./live_trigger/PROJECT_RULES.md)
- [live_trigger_fresh_exec/FRESH_EXECUTION_FLOW.md](./live_trigger_fresh_exec/FRESH_EXECUTION_FLOW.md)

## Shared Logic / Portable Route

Open these when the task is about the shared logic owner or the backup portable bundle.

- [BET_PROJECT_STATUS.md](./BET_PROJECT_STATUS.md)
- [live_trigger/README.md](./live_trigger/README.md)
- [live_trigger/PORTABLE_BUNDLE.md](./live_trigger/PORTABLE_BUNDLE.md)
- [live_trigger/BOX_GO_RUNTIME_CONCEPT.md](./live_trigger/BOX_GO_RUNTIME_CONCEPT.md)
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
    - [live_trigger/BOX_GO_RUNTIME_CONCEPT.md](./live_trigger/BOX_GO_RUNTIME_CONCEPT.md)
    - [live_trigger_fresh_exec/FRESH_EXECUTION_FLOW.md](./live_trigger_fresh_exec/FRESH_EXECUTION_FLOW.md)
- Cross-machine handoff changes:
  - update the relevant `TO_*` or `FROM_*` file
- Strategy adoption or research conclusion changes:
  - update [PROJECT_STATUS.md](./PROJECT_STATUS.md)
  - update [LOGIC_STATUS.md](./LOGIC_STATUS.md)
  - update the relevant project or report README
- Racer-index / logic substrate changes:
  - update [RACER_INDEX_STATUS.md](./RACER_INDEX_STATUS.md)
  - update the relevant file under [racer_index/](./racer_index/README.md)
- Ownership / sync-rule changes:
  - update [OPERATING_MODEL.md](./OPERATING_MODEL.md)
- Timeline-worthy milestones:
  - update [PROJECT_TIMELINE.md](./PROJECT_TIMELINE.md)
