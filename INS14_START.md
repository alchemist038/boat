# INS14 Start

This is the single-file bootstrap note for joining the project from `ins14`.
Read this first when you want to rejoin quickly without reconstructing the whole repo.

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

`ins14` owns:

- current and recent collection
- shared bronze import
- final shared `refresh-silver`
- shared DB integration
- logic scan
- racer-index work
- shared operational verification

`i5` owns:

- historical gap recovery
- isolated odds-gap collection
- `live_trigger_cli` construction
- execution-line UX and notification improvements

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

## 4. Bet-Line Structure

- `live_trigger_cli`
  - main operating line
  - main UI, loop, and notification owner
- `live_trigger_fresh_exec`
  - fresh execution engine
  - reusable real-execution component
- `live_trigger`
  - shared logic owner
  - shared bet expansion owner
  - portable and backup line

The current waiting policy belongs to the bet line, not to the logic owner.

## 5. Current Waiting Policy

- `assist_real`
  - detect `GO`
  - send Telegram alert
  - open fresh confirmation flow
  - wait for Telegram approval or reject
  - submit only if approved in time
  - reject or timeout discards
- `armed_real`
  - submit automatically
- `air`
  - evaluate and notify only

## 6. Read Order After This File

Read these next in this order:

1. [ROOT_DOC_MAP.md](./ROOT_DOC_MAP.md)
2. [OPERATING_MODEL.md](./OPERATING_MODEL.md)

Then open the matching status file for the task:

- DB:
  - [DB_STATUS.md](./DB_STATUS.md)
- bet line, UI, waiting, execution:
  - [BET_PROJECT_STATUS.md](./BET_PROJECT_STATUS.md)
  - [live_trigger_cli/README.md](./live_trigger_cli/README.md)
- logic and racer work:
  - [LOGIC_STATUS.md](./LOGIC_STATUS.md)
  - [RACER_INDEX_STATUS.md](./RACER_INDEX_STATUS.md)

If the task depends on machine-specific deltas, read these last:

- [TO_INS14_FROM_ME.md](./TO_INS14_FROM_ME.md)
- [FROM_INS14_TO_ME.md](./FROM_INS14_TO_ME.md)

## 7. Session Checklist

1. Start in `C:\CODEX_WORK\boat_clone`
2. Run `git pull --ff-only origin main`
3. Read this file
4. Read the matching status file for the current task
5. Confirm the task belongs to `ins14`
6. Confirm you are not treating runtime state as source

## 8. Git Handling On Ins14

From `ins14`, Git should be handled like this:

- use `C:\CODEX_WORK\boat_clone` as the canonical Git worktree
- run `git pull --ff-only origin main` before starting a new task
- make code and doc changes in the local repo first
- commit and push from the local repo
- only after that, reflect selected code/docs to `\\038INS\boat\` by allowlist sync when needed
- if you discover newer share-side docs or code, merge them back into the local repo first instead of editing only on share

In short:

- Git truth lives in the local repo
- operational truth for data lives in `\\038INS\boat\data`
- the share root is not the primary Git editing surface

## 9. Runtime State Is Not Source

Do not treat these as owner docs or sync truth:

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

## 10. Sync Rule

- Edit code and docs primarily in `C:\CODEX_WORK\boat_clone`
- Treat `\\038INS\boat\` as deployment copy and operational reference
- Prefer allowlist sync from local repo to share
- Never do a repo-wide mirror sync
- Never mirror local `data/` into `\\038INS\boat\data`

## 11. If You Remember Only Four Things

- protect the shared DB
- keep `live_trigger_cli` as the main operating line
- keep logic truth under shared `live_trigger/boxes`
- keep `racer_index` under logic
