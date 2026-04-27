# Operating Model

This file defines the current ownership model for code, docs, data, logic, and runtime state.

## Companion Docs

- [ROOT_DOC_MAP.md](./ROOT_DOC_MAP.md)
- [PROJECT_STATUS.md](./PROJECT_STATUS.md)
- [DB_STATUS.md](./DB_STATUS.md)
- [BET_PROJECT_STATUS.md](./BET_PROJECT_STATUS.md)
- [LOGIC_STATUS.md](./LOGIC_STATUS.md)
- [RACER_INDEX_STATUS.md](./RACER_INDEX_STATUS.md)
- [live_trigger/PROJECT_RULES.md](./live_trigger/PROJECT_RULES.md)

- updated_at: 2026-04-27 JST

## 1. Non-Negotiable Owners

- Canonical operational data root on this machine:
  - `C:\boat\data`
- Canonical operational DuckDB on this machine:
  - `C:\boat\data\silver\boat_race.duckdb`
- Legacy rollback / fallback share:
  - `\\038INS\boat`
  - optional rollback copy only, no longer an intended code default
- Main bet line:
  - `live_trigger_cli`
- Logic source of truth:
  - `live_trigger/boxes/`
  - `live_trigger/shared_contract.py`
  - `live_trigger/auto_system/app/core/bets.py`
- Logic substrate:
  - `racer_index`

## 2. Machine Roles

### `i5`

- operational canonical `data/` and `reports/` root
- main daily DB refresh and racer-index generation
- current and recent collection
- historical DB recovery when needed
- odds gap collection in isolated local worker trees when needed
- `live_trigger_cli` construction and forward operation
- execution-line UX and notification improvements

### `ins14`

- legacy shared-root host while rollback remains available
- optional backup / reference copy
- no longer the intended primary writer for the main daily path after the
  `2026-04-27` `C:\boat` cutover

## 3. Ownership Boundaries

### Code And Docs

- Primary editing base:
  - `C:\CODEX_WORK\boat_clone`
- Archived local cleanup bundles:
  - `C:\CODEX_WORK\archive\boat_clone_workspace_cleanup_20260427`
- Archived historical worker trees:
  - `C:\CODEX_WORK\archive\worker_trees_20260427\boat_a`
  - `C:\CODEX_WORK\archive\worker_trees_20260427\boat_b`
- Share role:
  - deployment copy and rollback reference under `\\038INS\boat\`
- Active execution copy:
  - `C:\boat`

### Shared Data

- Treat `C:\boat\data` as the operational system of record on this machine.
- Treat `\\038INS\boat\data` as fallback / rollback data only while the
  optional rollback copy is retained.
- Do not rely on `\\038INS\boat` as an implicit runtime default anymore.
- Do not casually mirror workspace-local experimental `data/` into either root.

### Runtime State

These are not source and should not be merged blindly across machines:

- `live_trigger/raw/`
- `live_trigger/watchlists/`
- `live_trigger/ready/`
- `live_trigger/plans/`
- `live_trigger/auto_system/data/`
- `live_trigger_cli/data/`
- `live_trigger_cli/raw/`
- `live_trigger_fresh_exec/auto_system/data/`
- `*.db`
- `*.log`
- `*.pid`
- screenshots / HTML captures / session-state files

Current main-line runtime state owner on this machine:

- `C:\boat\live_trigger_cli\data`
- `C:\boat\live_trigger_cli\raw`
- `C:\boat\live_trigger_fresh_exec\auto_system\data`
- optional legacy fallback runtime under `C:\boat\live_trigger\auto_system\data`

## 4. Bet Line Structure

- `live_trigger_cli`
  - main forward operating line
  - main UI and loop owner
  - main notification owner
- `live_trigger_fresh_exec`
  - fresh execution engine
  - reusable real-execution component
- `live_trigger`
  - shared logic owner
  - shared bet expansion owner
  - portable / backup line

## 5. Waiting Logic Policy

Current assist policy for the main line:

- `assist_real`
  - detect `GO`
  - send Telegram alert
  - open fresh confirmation flow
  - wait for operator approval
  - if approved in time, submit
  - if rejected, discard
  - if untouched until deadline, discard
- `armed_real`
  - submit automatically after `GO`
- `air`
  - evaluate and log only

This waiting logic belongs to the bet line, not to the logic source of truth.

## 6. Sync Policy

- Prefer allowlist-based sync from `boat_clone` to `C:\boat`.
- If the legacy share still needs a reference copy, sync selected files from the
  repo or from `C:\boat` outward deliberately.
- Never do a repo-wide mirror sync.
- Always exclude runtime-generated state when syncing back into the Git
  workspace.
- When docs disagree between local and share, reconcile them in the local repo first, then promote the merged version outward.

## 7. Current Main Direction

- Keep the DB safe by using `C:\boat\data` as the local canonical root on `i5`.
- Keep the CLI line safe by treating `live_trigger_cli` as the main operating line.
- Keep logic safe by preserving the shared source-of-truth boundaries.
- Keep racer-index under logic, not as a separate top-level operating line.

## 8. Next Runtime Direction

- `live_trigger_cli` remains the current protected main line.
- The next runtime experiment should not fork shared logic truth.
- Instead, prepare a separate runtime box that reuses shared logic and bet expansion while splitting loop responsibilities:
  - `live_trigger_cli_split/`
  - `sync_loop`
    - low-frequency watchlist rebuild
  - `bet_loop`
    - higher-frequency `evaluate + execute`
- This split is meant to absorb future broad-scan logic additions without destabilizing the current main line.
