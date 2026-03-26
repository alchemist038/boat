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

- updated_at: 2026-03-24 JST

## 1. Non-Negotiable Owners

- Canonical shared data root:
  - `\\038INS\boat\data`
- Canonical shared DuckDB:
  - `\\038INS\boat\data\silver\boat_race.duckdb`
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

- historical DB recovery
- odds gap collection in isolated local worker trees
- `live_trigger_cli` construction and forward operation
- execution-line UX and notification improvements

### `ins14`

- current and recent collection
- final shared DB integration
- shared bronze import and final `refresh-silver`
- logic scan and racer-index work
- shared operational docs and runtime verification

## 3. Ownership Boundaries

### Code And Docs

- Primary editing base:
  - `C:\CODEX_WORK\boat_clone`
- Share role:
  - deployment copy and operational reference under `\\038INS\boat\`

### Shared Data

- Always treat `\\038INS\boat\data` as the operational system of record.
- Do not try to mirror local `data/` into the shared root.

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

- Prefer allowlist-based sync from `boat_clone` to `\\038INS\boat`.
- Never do a repo-wide mirror sync.
- Always exclude runtime-generated state and shared canonical data.
- When docs disagree between local and share, reconcile them in the local repo first, then promote the merged version outward.

## 7. Current Main Direction

- Keep the DB safe by preserving the shared canonical root.
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
