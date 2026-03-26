# DB STATUS

## Companion Docs

- root index: [ROOT_DOC_MAP.md](./ROOT_DOC_MAP.md)
- repo overview: [README.md](./README.md)
- project summary: [PROJECT_STATUS.md](./PROJECT_STATUS.md)
- bet / trigger summary: [BET_PROJECT_STATUS.md](./BET_PROJECT_STATUS.md)

- updated_at: 2026-03-27 08:05 JST
- doc_owner_repo_root: `C:\CODEX_WORK\boat_clone`
- canonical_data_root: `\\038INS\boat\data`
- canonical_db: `\\038INS\boat\data\silver\boat_race.duckdb`
- basis:
  - root markdown reviewed:
    - `README.md`
    - `CODEX_START_HERE.md`
    - `PROJECT_STATUS.md`
    - `BET_PROJECT_STATUS.md`
    - `TO_I5_FROM_ME.md`
    - `TO_INS14_FROM_ME.md`
    - `FROM_I5_TO_ME.md`
    - `FROM_INS14_TO_ME.md`
  - live measurement on shared `bronze/`, `silver/`, and `copy_inbox/`

## 0. 2026-03-27 Overnight Gap Recovery Refresh

Shared canonical DB and shared bronze were rechecked again on `2026-03-27` after the overnight apply job on `2026-03-26`.

Current read:

- recent collection is now reflected through `2026-03-25`
- validation inputs are continuous through `2026-03-25`
- `odds_2t` and `odds_3t` now both span `2025-04-01..2026-03-25`
- the large historical gap blocks have been filled:
  - `odds_2t`: `2025-08-21..2025-09-08` recovered
  - `odds_3t`: `2025-08-21..2025-09-08` recovered
  - `odds_3t`: `2025-12-25..2026-02-28` recovered
- shared `bronze` no longer contains header-only `odds_3t` files
- the remaining odds issue is no longer a contiguous gap block
- the remaining odds issue is a set of `53` partial-mismatch days between `2025-04-08` and `2026-03-10`
- from `2026-03-11` through `2026-03-25`, odds daily counts match expected full-card counts for both `2t` and `3t`

## 1. DB_STATUS Rule

From this point forward, every `DB_STATUS.md` update should record both `bronze` and `silver` status for:

- `odds_2t`
- `odds_3t`
- `results`
- `beforeinfo_entries`
- `race_meta`

Reason:

- `odds` alone is not enough to judge BT readiness
- strategy validation also depends on `results`, `beforeinfo_entries`, and `race_meta`
- when something is missing, we need to know whether the gap is at the `bronze` layer, the `silver` layer, or both

The same principle applies to scheduled collection:

- if a periodic DB collection task is discussed or changed, record its implementation state in this file
- for the scheduler notes here, focus on boat/DB tasks only

## 2. Current Shared Silver Status

Actual measurement from `\\038INS\boat\data\silver\boat_race.duckdb`:

- `races`: `170,388` rows, `2023-03-11..2026-03-25`, `1111` distinct race days
- `entries`: `1,022,328` rows, `2023-03-11..2026-03-25`, `1111` days
- `results`: `168,124` rows, `2023-03-11..2026-03-25`, `1111` days
- `beforeinfo_entries`: `996,169` rows, `2023-03-11..2026-03-25`, `1111` days
- `race_meta`: `170,388` rows, `2023-03-11..2026-03-25`, `1111` days
- `racer_stats_term`: `1,625` rows
- `odds_2t`: `2,446,605` rows, `2025-04-01..2026-03-25`, `359` distinct days
- `odds_3t`: `6,524,280` rows, `2025-04-01..2026-03-25`, `359` distinct days

Distinct day ranges actually present in silver:

- `odds_2t`: `2025-04-01..2026-03-25`
- `odds_3t`: `2025-04-01..2026-03-25`

Recent daily view from `collection_day_summary`:

- `2026-03-21`: `race_count=180`, `odds_2t_count=8100`, `odds_3t_count=21600`
- `2026-03-22`: `race_count=180`, `odds_2t_count=8100`, `odds_3t_count=21600`
- `2026-03-23`: `race_count=156`, `odds_2t_count=7020`, `odds_3t_count=18720`
- `2026-03-24`: `race_count=144`, `odds_2t_count=6480`, `odds_3t_count=17280`
- `2026-03-25`: `race_count=132`, `odds_2t_count=5940`, `odds_3t_count=15840`

## 3. Current Shared Bronze Odds Status

Actual non-empty file coverage under `\\038INS\boat\data\bronze`:

- `odds_2t`
  - files total: `359`
  - non-empty files: `359`
  - ranges: `2025-04-01..2026-03-25`
- `odds_3t`
  - files total: `359`
  - non-empty files: `359`
  - header-only files: `0`
  - non-empty ranges: `2025-04-01..2026-03-25`

Important observation:

- shared `silver` has now been rebuilt again from the corrected shared `bronze`
- the previous `header-only` `odds_3t` winter block has been replaced with real bronze data
- bronze-level contiguous gaps are no longer the main issue
- the remaining issue is silver-level partial mismatch on a subset of days, not total file absence

## 4. Validation Inputs Status

These are the main non-odds tables used in validation and strategy research.

### Shared Bronze

- `results`
  - files total: `1109`
  - non-empty files: `1109`
  - ranges: `2023-03-11..2026-03-23`
- `beforeinfo_entries`
  - files total: `1109`
  - non-empty files: `1109`
  - ranges: `2023-03-11..2026-03-23`
- `race_meta`
  - files total: `1109`
  - non-empty files: `1109`
  - ranges: `2023-03-11..2026-03-23`

### Shared Silver

- `results`: `167,852` rows, `2023-03-11..2026-03-23`, `1109` days
- `beforeinfo_entries`: `994,513` rows, `2023-03-11..2026-03-23`, `1109` days
- `race_meta`: `170,112` rows, `2023-03-11..2026-03-23`, `1109` days

Recent daily view from `collection_day_summary`:

- `2026-03-19`: `result_count=180`, `beforeinfo_entry_count=1080`, `race_meta_count=180`
- `2026-03-20`: `result_count=192`, `beforeinfo_entry_count=1152`, `race_meta_count=192`
- `2026-03-21`: `result_count=180`, `beforeinfo_entry_count=1080`, `race_meta_count=180`
- `2026-03-22`: `result_count=180`, `beforeinfo_entry_count=1080`, `race_meta_count=180`
- `2026-03-23`: `result_count=156`, `beforeinfo_entry_count=936`, `race_meta_count=156`

Interpretation:

- the validation inputs are continuous through `2026-03-23`
- current gaps are concentrated in the odds layer, not in `results / beforeinfo_entries / race_meta`
- this means fixed-rule BT and context analysis have a much better base than odds-based EV analysis

## 5. i5 Handoff Bundles In Copy Inbox

Confirmed under `\\038INS\boat\copy_inbox\from_i5`:

### `20260319_odds_backfill`

- `odds_2t`: `160` non-empty files
- `odds_3t`: `160` non-empty files
- ranges: `2025-04-01..2025-06-14`, `2025-10-01..2025-12-24`

### `20260321_odds_backfill_delta_stop`

- `odds_2t`: `89` non-empty files
- `odds_3t`: `89` non-empty files
- ranges: `2025-06-15..2025-08-20`, `2025-09-09..2025-09-30`

There are no additional odds backfill bundles beyond these two in `copy_inbox\from_i5`.

## 6. Rebuild Result

Completed on `2026-03-21`.

What was done:

1. Copied both i5 odds bundles into shared bronze with overwrite allowed.
2. Rebuilt a temporary clean DB, verified it, and then promoted it to canonical.
3. Backed up the previous canonical DB at:
   - `\\038INS\boat\data\silver\boat_race_pre_clean_promote_20260321.duckdb`
4. Promoted the clean rebuild to the canonical path:
   - `\\038INS\boat\data\silver\boat_race.duckdb`
5. Removed the temporary rebuild artifact after promotion.

Result:

- canonical DB is now the clean rebuild
- `odds_2t` improved from `166` days to `333` days
- `odds_3t` improved from `86` days to `267` days

## 7. Remaining Gaps

After the overnight `2026-03-26` apply job, the remaining missing coverage is no longer a contiguous block. The current residual issue is:

### partial mismatch days after `2025-04-01`

- mismatch day count: `53`
- first mismatch day: `2025-04-08`
- last mismatch day: `2026-03-10`

Interpretation:

- these are not zero-coverage day blocks
- these are days where `odds_2t` and/or `odds_3t` counts are below full-card expectation
- from `2026-03-11..2026-03-25`, odds counts are now fully aligned with expected daily totals

Interpretation:

- the large summer and winter gap blocks are closed
- the next odds task is a forensic cleanup of the `53` partial-mismatch days
- this is a lower-severity cleanup task than the former contiguous gap recovery

## 8. Current Working Interpretation

The project documents and the live measurements now line up to the following interpretation:

- the canonical operational truth remains the shared root `\\038INS\boat\data`
- shared bronze has now been updated with the overnight summer/winter odds recovery payloads
- canonical silver has been rebuilt from that corrected bronze
- the main DB is now materially cleaner and more complete than before
- recent-day collection is working through `2026-03-25`
- the next data task is no longer "fix recent extension"
- the next data task is specifically "analyze and close the 53 partial-mismatch odds days"

This file should be updated again when the remaining partial-mismatch days are explained or closed.

## 9. Scheduled Task Status

As of `2026-03-21`, the boat/DB periodic scheduler is **implemented** as a regular daily task.

Current state:

- active daily task:
  - task name: `\BoatDailyRecentCollect`
  - start time: `04:30`
  - target window: `last 2 days`
  - task command:
    - `powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File D:\boat\run_daily_recent_collect.ps1`
- old one-time task `BoatQ2TrifectaResume20260313` is no longer present and is not part of the current design

Implemented collection flow:

- target root: `\\038INS\boat\data`
- execution script: [run_daily_recent_collect.ps1](/d:/boat/run_daily_recent_collect.ps1)
- log root: `D:\boat\reports\logs`
- flow:
  - collect recent `raw/bronze`
  - final `collect-range` rebuild refreshes canonical `silver`
  - leave logs for morning verification

Operational intent:

- finish around `06:00` under the current rough estimate
- keep enough margin before morning use
- use the 2-day overlap to make the daily collection self-healing when one day is partially missed

Observed result in the canonical DB on `2026-03-24`:

- `collection_day_summary` now includes `2026-03-21`
- `collection_day_summary` now includes `2026-03-22`
- `collection_day_summary` now includes `2026-03-23`

Current scheduler settings for the boat task:

- daily at `04:30`
- `MultipleInstances = IgnoreNew`
- `ExecutionTimeLimit = PT4H`
- `StartWhenAvailable = True`

This section should be updated again when the task timing or command is changed.

## 10. Active Gap Recovery Jobs

As of `2026-03-22 00:12 JST`, two i5-local long-run collection jobs are active to fill the remaining odds gaps without writing directly into the shared canonical tree during collection.

Current active jobs:

- `boat_a`
  - clone root: `C:\CODEX_WORK\boat_a`
  - target gap: `2025-08-21..2025-09-08`
  - goal: fill the remaining `19` summer gap days for both `odds_2t` and `odds_3t`
  - log files:
    - `C:\CODEX_WORK\boat_a\reports\logs\collect_gap_a_20250821_20250908_20260322_001255.out.log`
    - `C:\CODEX_WORK\boat_a\reports\logs\collect_gap_a_20250821_20250908_20260322_001255.err.log`
- `boat_b`
  - clone root: `C:\CODEX_WORK\boat_b`
  - target gap: `2025-12-25..2026-02-28`
  - goal: recover the winter `odds_3t` block currently left as header-only bronze files in the shared tree
  - log files:
    - `C:\CODEX_WORK\boat_b\reports\logs\collect_gap_b_20251225_20260228_20260322_001255.out.log`
    - `C:\CODEX_WORK\boat_b\reports\logs\collect_gap_b_20251225_20260228_20260322_001255.err.log`

Operational rules for this recovery run:

- collection stays in machine-local `data/raw`, `data/bronze`, and `data/silver`
- shared `\\038INS\boat\data` is not the write target during the collection phase
- after local verification, the needed `raw/` and `bronze/` odds files should be copied into `copy_inbox`, then imported into shared bronze, then followed by one final shared `refresh-silver`
- active job detail is tracked in:
  - `workspace_codex/coordination/jobs/active/20260322_boat_a_odds_gap_20250821_20250908.md`
  - `workspace_codex/coordination/jobs/active/20260322_boat_b_odds_gap_20251225_20260228.md`

Current interpretation on `2026-03-24`:

- the canonical DB still shows the same remaining gap structure
- so these jobs should not yet be treated as fully merged into shared bronze/silver
