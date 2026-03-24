# I5 Start

This is the single-file bootstrap note for joining the project from `i5`.
Read this first when you want to restart work quickly without reconstructing the whole repo.

- updated_at: 2026-03-25 JST
- primary editing base: `C:\CODEX_WORK\boat_clone`
- operational share root: `\\038INS\boat\`

## 1. Non-Negotiables

Keep these fixed unless the project explicitly changes them.

- Canonical shared data root:
  - `\\038INS\boat\data`
- Canonical shared DB:
  - `\\038INS\boat\data\silver\boat_race.duckdb`
- Main bet line:
  - `live_trigger_cli`
- Logic source of truth:
  - `live_trigger/boxes/`
  - `live_trigger/shared_contract.py`
  - `live_trigger/auto_system/app/core/bets.py`
- Logic substrate:
  - `racer_index`

## 2. Machine Split

`i5` owns:

- historical DB recovery
- isolated odds-gap collection in local worker trees
- `live_trigger_cli` construction and forward operation
- execution-line UX and notification improvements

`ins14` owns:

- current and recent collection
- shared bronze import
- final shared `refresh-silver`
- shared DB integration
- logic scan
- racer-index work
- shared operational verification

Do not casually move work across this boundary.

## 3. Main Forward Set

Treat these three as the active forward logic set:

- `4wind_base_415`
- `c2_provisional_v1`
- `125_broad_four_stadium`

Shared owner locations:

- `live_trigger/boxes/4wind/`
- `live_trigger/boxes/c2/`
- `live_trigger/boxes/125/`

## 4. Main I5 Responsibilities Right Now

When starting on `i5`, the most likely work buckets are:

- historical odds-gap recovery
- local worker-tree collection and verification
- `live_trigger_cli` operation and improvement
- execution UX, Telegram flow, and operator assist
- packaging changes back into the canonical repo

If the task is about final shared DB integration, that usually belongs to `ins14`.

## 5. Read Order After This File

Read these next in this order:

1. [ROOT_DOC_MAP.md](./ROOT_DOC_MAP.md)
2. [OPERATING_MODEL.md](./OPERATING_MODEL.md)

Then open the matching status file for the task:

- DB / backfill / gap recovery:
  - [DB_STATUS.md](./DB_STATUS.md)
  - [FROM_INS14_TO_ME.md](./FROM_INS14_TO_ME.md)
- main bet line / UI / waiting / execution:
  - [BET_PROJECT_STATUS.md](./BET_PROJECT_STATUS.md)
  - [live_trigger_cli/README.md](./live_trigger_cli/README.md)
- logic and racer work:
  - [LOGIC_STATUS.md](./LOGIC_STATUS.md)
  - [RACER_INDEX_STATUS.md](./RACER_INDEX_STATUS.md)

If the task depends on machine-specific deltas, read these last:

- [TO_I5_FROM_ME.md](./TO_I5_FROM_ME.md)
- [FROM_I5_TO_ME.md](./FROM_I5_TO_ME.md)

## 6. Session Checklist

1. Start in `C:\CODEX_WORK\boat_clone`
2. Run `git pull --ff-only origin main`
3. Read this file
4. Read the matching status file for the current task
5. Confirm the task belongs to `i5`
6. Confirm you are not treating runtime state as source

## 7. Git Handling On I5

From `i5`, Git should be handled like this:

- use `C:\CODEX_WORK\boat_clone` as the canonical Git worktree
- commit code and docs there
- push to `origin/main` from there
- treat `\\038INS\boat\` as deployment copy and operational reference, not as the Git worktree
- if share-side docs or code diverge, merge them back into the local repo first, then push

Do not treat the share as the primary Git editing surface.

## 8. Runtime State Is Not Source

Do not treat these as owner docs or sync truth:

- local worker-tree `data/raw`, `data/bronze`, `data/silver`
- `live_trigger/raw/`
- `live_trigger/watchlists/`
- `live_trigger/ready/`
- `live_trigger/auto_system/data/`
- `live_trigger_cli/data/`
- `live_trigger_cli/raw/`
- `live_trigger_fresh_exec/auto_system/data/`
- `*.db`
- `*.log`
- `*.pid`
- screenshots
- HTML captures
- Telegram or session state files

## 9. Sync Rule

- edit code and docs primarily in `C:\CODEX_WORK\boat_clone`
- use allowlist sync from local repo to `\\038INS\boat\` when deployment or share reflection is needed
- never do a repo-wide mirror sync
- never mirror local worker-tree `data/` into `\\038INS\boat\data`
- for historical backfill, keep collection local first, verify, then hand off selected outputs

## 10. If You Remember Only Four Things

- protect the shared DB
- keep `live_trigger_cli` as the main operating line
- keep logic truth under shared `live_trigger/boxes`
- treat local worker trees as disposable collection environments, not as the project source
