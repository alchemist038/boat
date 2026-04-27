# I5 Start

This is the single-file bootstrap note for joining the project from `i5`.
Read this first when you want to restart work quickly without reconstructing the whole repo.

- updated_at: 2026-04-27 JST
- primary editing base: `C:\CODEX_WORK\boat_clone`
- operational canonical root: `C:\boat`
- legacy rollback share root: `\\038INS\boat\`
  - optional only while rollback is still retained

## 1. Non-Negotiables

Keep these fixed unless the project explicitly changes them.

- Canonical operational data root:
  - `C:\boat\data`
- Canonical operational DB:
  - `C:\boat\data\silver\boat_race.duckdb`
- Legacy rollback / fallback share:
  - `\\038INS\boat`
  - do not assume this exists as a runtime default anymore
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

- operational canonical `data/` and `reports/` root
- current and recent collection
- main daily DB refresh and racer-index generation
- historical DB recovery
- isolated odds-gap collection in local worker trees
- `live_trigger_cli` construction and forward operation
- execution-line UX and notification improvements

`ins14` owns:

- legacy share hosting while rollback remains available
- optional backup / reference copy
- no longer the intended primary writer for the main daily path after the
  `2026-04-27` `C:\boat` cutover

Do not casually move work across this boundary.

## 3. Main Forward Set

Treat these six as the active forward logic set:

- `125_broad_four_stadium`
- `4wind_base_415`
- `c2_provisional_v1`
- `h_a_final_day_cut_v1`
- `l3_weak_124_box_one_a_ex241_v1`
- `l1_weak_234_box_v1`

Shared owner locations:

- `live_trigger/boxes/125/`
- `live_trigger/boxes/4wind/`
- `live_trigger/boxes/c2/`
- `live_trigger/boxes/h_a/`
- `live_trigger/boxes/l3_124/`
- `live_trigger/boxes/l1_234/`

Daily point-in-time forward report:

- [README.md](./reports/live_trade/live_trigger_cli_forward_logic_performance_latest/README.md)

## 4. Main I5 Responsibilities Right Now

When starting on `i5`, the most likely work buckets are:

- historical odds-gap recovery
- local worker-tree collection and verification
- `live_trigger_cli` operation and improvement
- execution UX, Telegram flow, and operator assist
- packaging changes back into the canonical repo

If the task is about the active canonical DB/report path, start from `C:\boat`
and only use `\\038INS\boat` as fallback / rollback context if that copy is
still being retained.

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
- treat `C:\boat` as the operational canonical root, not as the Git worktree
- treat `\\038INS\boat\` as rollback / reference copy while it still exists
- retired temporary bundles now live under:
  - `C:\CODEX_WORK\archive\boat_clone_workspace_cleanup_20260427`
- retired historical worker trees now live under:
  - `C:\CODEX_WORK\archive\worker_trees_20260427\boat_a`
  - `C:\CODEX_WORK\archive\worker_trees_20260427\boat_b`
- if share-side docs or code diverge, merge them back into the local repo first, then push

Do not treat either `C:\boat` or the share as the primary Git editing surface.

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
- use allowlist sync from local repo to `C:\boat` for the active operational copy
- if the legacy share still needs reflection, sync to `\\038INS\boat\`
  separately and deliberately
- never do a repo-wide mirror sync
- never mirror local worker-tree `data/` into canonical `C:\boat\data`
- for historical backfill, keep collection local first, verify, then hand off selected outputs
- current live runtime state is expected under `C:\boat`, not under the Git
  worktree

## 10. If You Remember Only Four Things

- protect the canonical DB
- keep `live_trigger_cli` as the main operating line
- keep logic truth under shared `live_trigger/boxes`
- treat local worker trees as disposable collection environments, not as the project source
