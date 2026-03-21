# DB STATUS

## Companion Docs

- root index: [ROOT_DOC_MAP.md](./ROOT_DOC_MAP.md)
- repo overview: [README.md](./README.md)
- project summary: [PROJECT_STATUS.md](./PROJECT_STATUS.md)
- bet / trigger summary: [BET_PROJECT_STATUS.md](./BET_PROJECT_STATUS.md)

- updated_at: 2026-03-21 19:56 JST
- repo_root: `D:\boat`
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

## 0. DB_STATUS Rule

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

## 1. Current Shared Silver Status

Actual measurement from `\\038INS\boat\data\silver\boat_race.duckdb`:

- `races`: `169,224` rows, `2023-03-11..2026-03-18`, `1104` distinct race days
- `entries`: `1,015,344` rows, `2023-03-11..2026-03-18`, `1104` days
- `results`: `166,964` rows, `2023-03-11..2026-03-18`, `1104` days
- `beforeinfo_entries`: `989,185` rows, `2023-03-11..2026-03-18`, `1104` days
- `race_meta`: `169,224` rows, `2023-03-11..2026-03-18`, `1104` days
- `racer_stats_term`: `1,625` rows
- `odds_2t`: `2,274,480` rows, `2025-04-01..2026-03-18`, `333` distinct days
- `odds_3t`: `4,789,560` rows, `2025-04-01..2026-03-18`, `267` distinct days

Distinct day ranges actually present in silver:

- `odds_2t`: `2025-04-01..2025-08-20`, `2025-09-09..2026-03-18`
- `odds_3t`: `2025-04-01..2025-08-20`, `2025-09-09..2025-12-24`, `2026-03-01..2026-03-18`

Recent daily view from `collection_day_summary`:

- `2026-03-14`: `race_count=156`, `odds_2t_count=7020`, `odds_3t_count=18720`
- `2026-03-15`: `race_count=156`, `odds_2t_count=7020`, `odds_3t_count=18720`
- `2026-03-16`: `race_count=132`, `odds_2t_count=5940`, `odds_3t_count=15840`
- `2026-03-17`: `race_count=120`, `odds_2t_count=5400`, `odds_3t_count=14400`
- `2026-03-18`: `race_count=132`, `odds_2t_count=5940`, `odds_3t_count=15840`

## 2. Current Shared Bronze Odds Status

Actual non-empty file coverage under `\\038INS\boat\data\bronze`:

- `odds_2t`
  - files total: `333`
  - non-empty files: `333`
  - ranges: `2025-04-01..2025-08-20`, `2025-09-09..2026-03-18`
- `odds_3t`
  - files total: `333`
  - non-empty files: `267`
  - header-only files: `66`
  - non-empty ranges: `2025-04-01..2025-08-20`, `2025-09-09..2025-12-24`, `2026-03-01..2026-03-18`
  - header-only range: `2025-12-25..2026-02-28`

Important observation:

- shared `silver` is now rebuilt from the corrected shared `bronze`
- the main remaining issue is `header-only` `odds_3t` bronze files for `2025-12-25..2026-02-28`
- `refresh-silver` is now complete, but missing `3t` data still cannot appear where bronze CSVs are empty

## 3. Validation Inputs Status

These are the main non-odds tables used in validation and strategy research.

### Shared Bronze

- `results`
  - files total: `1104`
  - non-empty files: `1104`
  - ranges: `2023-03-11..2026-03-18`
- `beforeinfo_entries`
  - files total: `1104`
  - non-empty files: `1104`
  - ranges: `2023-03-11..2026-03-18`
- `race_meta`
  - files total: `1104`
  - non-empty files: `1104`
  - ranges: `2023-03-11..2026-03-18`

### Shared Silver

- `results`: `166,964` rows, `2023-03-11..2026-03-18`, `1104` days
- `beforeinfo_entries`: `989,185` rows, `2023-03-11..2026-03-18`, `1104` days
- `race_meta`: `169,224` rows, `2023-03-11..2026-03-18`, `1104` days

Recent daily view from `collection_day_summary`:

- `2026-03-14`: `result_count=156`, `beforeinfo_entry_count=936`, `race_meta_count=156`
- `2026-03-15`: `result_count=156`, `beforeinfo_entry_count=936`, `race_meta_count=156`
- `2026-03-16`: `result_count=132`, `beforeinfo_entry_count=792`, `race_meta_count=132`
- `2026-03-17`: `result_count=120`, `beforeinfo_entry_count=720`, `race_meta_count=120`
- `2026-03-18`: `result_count=132`, `beforeinfo_entry_count=792`, `race_meta_count=132`

Interpretation:

- the validation inputs are continuous through `2026-03-18`
- current gaps are concentrated in the odds layer, not in `results / beforeinfo_entries / race_meta`
- this means fixed-rule BT and context analysis have a much better base than odds-based EV analysis

## 4. i5 Handoff Bundles In Copy Inbox

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

## 5. Rebuild Result

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

## 6. Remaining Gaps

After the clean rebuild, the remaining missing coverage is:

### `odds_2t`

- `2025-08-21..2025-09-08` (`19` days)

### `odds_3t`

- `2025-08-21..2025-09-08` (`19` days)
- `2025-12-25..2026-02-28` (`66` days)

Interpretation:

- the late-summer `19`-day gap remains for both `2t` and `3t`
- the winter `66`-day gap remains only for `3t`
- this winter `3t` block is still empty at the bronze level, so it cannot be recovered by another rebuild alone

## 7. Current Working Interpretation

The project documents and the live measurements now line up to the following interpretation:

- the canonical operational truth remains the shared root `\\038INS\boat\data`
- shared bronze has been updated with the available i5 handoff bundles
- canonical silver has been rebuilt from that corrected bronze
- the main DB is now materially cleaner and more complete than before
- the next data task is no longer "rebuild the DB"
- the next data task is specifically "collect or source the remaining missing odds days"

This file should be updated again when the remaining `2t / 3t` gaps are filled.

## 8. Scheduled Task Status

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

Current scheduler settings for the boat task:

- daily at `04:30`
- `MultipleInstances = IgnoreNew`
- `ExecutionTimeLimit = PT4H`
- `StartWhenAvailable = True`

This section should be updated again when the task timing or command is changed.
