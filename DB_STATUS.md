# DB STATUS

## Companion Docs

- root index: [ROOT_DOC_MAP.md](./ROOT_DOC_MAP.md)
- repo overview: [README.md](./README.md)
- project summary: [PROJECT_STATUS.md](./PROJECT_STATUS.md)
- bet / trigger summary: [BET_PROJECT_STATUS.md](./BET_PROJECT_STATUS.md)

- updated_at: 2026-04-15 05:56 JST
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

## 0. 2026-04-14 Shared Repair And Current State

Shared canonical DB was rechecked and repaired again on `2026-04-14` and `2026-04-15`.

Key outcome:

- canonical shared DB is now current through:
  - `races / entries / beforeinfo_entries / race_meta`: `2026-04-15`
  - `results / odds_2t / odds_3t`: `2026-04-14`
- `2026-04-12` was successfully repaired end-to-end after a stale cached raw-page issue
- `2026-04-13` is now complete in `collection_day_summary`
- `2026-03-27` `odds_3t` has now been repaired
- `2026-04-15` has same-day `races / entries / beforeinfo_entries`, while `results / odds` are still naturally zero

Root cause of the `2026-04-12` repair:

- cached raw `results` pages for `20260412` had been fetched too early and later reused
- cached raw `odds_3t` pages could also remain stale when the cached page parsed to zero rows
- `collect-day` therefore needed one-time forced re-fetch protection when cached `result` or `odds_3t` parsed empty

Code-side mitigation now in place:

- `src/boat_race_data/cli.py`
  - refetch `result` once when cached raw parses to no `result_row`
  - refetch `odds_3t` once when cached raw parses to zero rows

Current live interpretation:

- shared canonical DB is operationally healthy for current-day and prior-day work
- the biggest recent repairs are complete:
  - `2026-04-12`
  - `2026-03-27 odds_3t`
- the prior headline issue `2026-03-27 odds_3t = 0` is no longer open

## 0A. 2026-03-27 Overnight Gap Recovery Refresh

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

- `races`: `173,220` rows, `2023-03-11..2026-04-15`, `1132` distinct race days
- `entries`: `1,039,320` rows, `2023-03-11..2026-04-15`, `1132` days
- `results`: `170,772` rows, `2023-03-11..2026-04-14`, `1131` days
- `beforeinfo_entries`: `1,013,161` rows, `2023-03-11..2026-04-15`, `1132` days
- `race_meta`: `173,220` rows, `2023-03-11..2026-04-15`, `1132` days
- `racer_stats_term`: `1,625` rows
- `odds_2t`: `2,563,875` rows, `2025-04-01..2026-04-14`, `379` distinct days
- `odds_3t`: `6,828,000` rows, `2025-04-01..2026-04-14`, `378` distinct days

Distinct day ranges actually present in silver:

- `odds_2t`: `2025-04-01..2026-04-14`
- `odds_3t`: `2025-04-01..2026-04-14`

Recent daily view from `collection_day_summary`:

- `2026-04-12`: `race_count=132`, `odds_2t_count=5940`, `odds_3t_count=15840`
- `2026-04-13`: `race_count=132`, `odds_2t_count=5940`, `odds_3t_count=15840`
- `2026-04-14`: `race_count=144`, `odds_2t_count=6480`, `odds_3t_count=17280`
- `2026-04-15`: `race_count=132`, `odds_2t_count=0`, `odds_3t_count=0`

## 3. Current Shared Bronze Odds Status

Actual non-empty file coverage under `\\038INS\boat\data\bronze`:

- `odds_2t`
  - files total: `380`
  - non-empty files: `379`
  - header-only files: `1`
  - non-empty ranges: `2025-04-01..2026-04-14`
- `odds_3t`
  - files total: `380`
  - non-empty files: `378`
  - header-only files: `2`
  - non-empty ranges: `2025-04-01..2026-04-14`

Important observation:

- shared `silver` has now been rebuilt again from the corrected shared `bronze`
- the previous `header-only` `odds_3t` winter block has been replaced with real bronze data
- bronze-level contiguous gaps are no longer the main issue
- current header-only files are:
  - `odds_2t/20260415.csv` (same-day natural placeholder)
  - `odds_3t/20260415.csv` (same-day natural placeholder)
  - `odds_3t/20260327.csv` is no longer header-only

## 4. Validation Inputs Status

These are the main non-odds tables used in validation and strategy research.

### Shared Bronze

- `results`
  - files total: `1131`
  - non-empty files: `1131`
  - ranges: `2023-03-11..2026-04-14`
- `beforeinfo_entries`
  - files total: `1131`
  - non-empty files: `1131`
  - ranges: `2023-03-11..2026-04-14`
- `race_meta`
  - files total: `1131`
  - non-empty files: `1131`
  - ranges: `2023-03-11..2026-04-14`

### Shared Silver

- `results`: `170,772` rows, `2023-03-11..2026-04-14`, `1131` days
- `beforeinfo_entries`: `1,013,161` rows, `2023-03-11..2026-04-15`, `1132` days
- `race_meta`: `173,220` rows, `2023-03-11..2026-04-15`, `1132` days

Recent daily view from `collection_day_summary`:

- `2026-04-12`: `result_count=132`, `beforeinfo_entry_count=792`, `race_meta_count=132`
- `2026-04-13`: `result_count=132`, `beforeinfo_entry_count=792`, `race_meta_count=132`
- `2026-04-14`: `result_count=144`, `beforeinfo_entry_count=864`, `race_meta_count=144`
- `2026-04-15`: `result_count=0`, `beforeinfo_entry_count=792`, `race_meta_count=132`

Interpretation:

- the validation inputs are continuous through `2026-04-15` at bronze level
- silver `results` are continuous through `2026-04-14`
- current gaps are concentrated in the odds layer, not in `beforeinfo_entries / race_meta`
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

## 9A. Daily Racer-Index Live CSV Task

As of `2026-03-27`, a separate derived-data task is now implemented for the daily racer-index live CSV bundle.

Purpose:

- this task is not the canonical DB builder
- it sits after the shared DB / raw pipeline
- it generates the daily `racer_rank_live_YYYYMMDD` files used by the current live racer-index overlay

Current state confirmed on `MASAO_N8N`:

- shared DB recent refresh task:
  - task name: `\BoatSharedRecentCollectDaily`
  - start time: `01:00`
  - logon mode: `Interactive only`
  - task command:
    - `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\CODEX_WORK\boat_clone\workspace_codex\scripts\run_shared_recent_collect_daily.ps1"`
- derived racer-index task:
  - task name: `\BoatRacerIndexLiveCsvDaily`
  - start time: `03:00`
  - logon mode: `Interactive only`
  - task command:
    - `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\CODEX_WORK\boat_clone\workspace_codex\scripts\run_racer_rank_live_daily.ps1"`

Implementation files:

- shared recent refresh:
  - `C:\CODEX_WORK\boat_clone\workspace_codex\scripts\run_shared_recent_collect_daily.ps1`
- daily wrapper:
  - `C:\CODEX_WORK\boat_clone\workspace_codex\scripts\run_racer_rank_live_daily.ps1`
- CLI launcher:
  - `C:\CODEX_WORK\boat_clone\workspace_codex\scripts\run_boat_race_cli.py`
- live predictor:
  - `\\038INS\boat\workspace_codex\scripts\predict_racer_rank_live.py`

Current flow:

1. `01:00` task refreshes shared DB recent overlap (`target-2 .. target-1`) against:
   - raw root: `\\038INS\boat\data\raw`
   - bronze root: `\\038INS\boat\data\bronze`
   - DB path: `\\038INS\boat\data\silver\boat_race.duckdb`
2. racer-index task checks shared DuckDB `results` for at least the prior-day `race_date`
3. if prior-day `results` are still missing, it backfills the prior day locally on this machine
4. run `collect-day` against the shared roots for the target day:
   - raw root: `\\038INS\boat\data\raw`
   - bronze root: `\\038INS\boat\data\bronze`
   - DB path: `\\038INS\boat\data\silver\boat_race.duckdb`
5. run `predict_racer_rank_live.py` for the target day
6. write outputs under:
   - `\\038INS\boat\reports\strategies\racer_rank_live_YYYYMMDD`

Important operating note:

- the current live overlay consumes `race_summary.csv`
- it does not read `daily_pred1_signal` or `daily_pred6` from DuckDB yet
- so the current operational chain is:
  - shared DB/raw -> daily prediction script -> CSV bundle -> live filter

Current ownership note:

- `MASAO_N8N` is now capable of producing both the recent shared DB refresh and the daily racer-index CSV without waiting on the older INS14 morning schedule
- if the legacy INS14 scheduler is still active, disable it there manually to avoid duplicate writers
- operational stance:
  - `MASAO_N8N` is the active morning writer for both the recent shared DB refresh and the derived racer-index CSV
  - legacy INS14 boat tasks should be kept `disabled`, not deleted, so they can be re-enabled quickly if this machine or the network path becomes unavailable
- local DB note:
  - keep `\\038INS\boat\data\silver\boat_race.duckdb` as the canonical DB
  - a second full local mirror DB on `MASAO_N8N` is not required for normal daily operation and would mostly duplicate storage and refresh time
  - if a local DB is ever introduced here, treat it as a temporary fallback or debug cache rather than a second canonical source

Confirmed output for `2026-03-27`:

- output dir:
  - `\\038INS\boat\reports\strategies\racer_rank_live_20260327`
- files:
  - `predictions.csv`
  - `race_summary.csv`
  - `confidence_tier_stats.csv`
  - `summary.md`
- total bundle size:
  - about `376,584 bytes` (`~368 KB`)

Current interpretation:

- this derived task is light enough to keep daily output history for BT checks and traceability
- keeping one date folder per day is operationally reasonable
- if the canonical DB collection timing moves again, adjust this task start time and keep the prior-day results wait gate
- morning recovery hardening:
  - `run_shared_recent_collect_daily.ps1` now clears stale `raw/results/YYYYMMDD` and `bronze/results/YYYYMMDD.csv` before recent overlap refresh
  - the same script also widens the overlap window backward to `max(results.race_date) + 1` when shared `results` are lagging, so a missed day is pulled back in automatically instead of being skipped
  - `run_racer_rank_live_daily.ps1` now clears stale prior-day results artifacts before its local backfill `collect-day`, then predicts with the newest available cutoff
  - `run_racer_rank_live_daily.ps1` now anchors `tune_start` and `profile_start` to the `cutoff` month instead of the `target` month, so month-boundary mornings such as `2026-04-01` do not produce an empty tuning window
  - `src/boat_race_data/cli.py` now refetches an `odds_2t` page once when the cached raw page parses to zero rows, which protects against the thin/header-only page variant that appeared on `2026-03-31`

Current shared DB check on `2026-04-01` after repair:

- max dates:
  - `races / entries / beforeinfo_entries / race_meta`: `2026-04-01`
  - `results / odds_2t / odds_3t`: `2026-03-31`
- `collection_day_summary`:
  - `2026-03-30`: `races 168 / entries 1008 / odds_2t 7560 / odds_3t 19680 / results 164`
  - `2026-03-31`: `races 156 / entries 936 / odds_2t 6885 / odds_3t 18360 / results 153`
  - `2026-04-01`: `races 108 / entries 648 / beforeinfo 648 / results 0 / odds 0`

`2026-03-31` odds_2t repair note:

- symptom:
  - shared DB showed `odds_2t max(race_date) = 2026-03-30` while `results` and `odds_3t` had already advanced to `2026-03-31`
  - `\\038INS\boat\data\bronze\odds_2t\20260331.csv` was header-only
- root cause:
  - cached `raw/odds_2t/20260331/*.html` pages included a thin page variant with only the deadline table and no odds matrix
  - parser therefore returned zero rows and bronze remained empty
- recovery:
  - forced fresh re-fetch of all `156` raw `odds_2t` pages for `20260331`
  - rewrote `\\038INS\boat\data\bronze\odds_2t\20260331.csv`
  - refreshed shared DuckDB
- result:
  - `odds_2t_count = 6885` for `2026-03-31`
  - this matches `153 races x 45 combinations`, so the 2T layer is back in sync with the available race/results coverage

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
