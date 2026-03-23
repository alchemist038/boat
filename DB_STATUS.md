# DB STATUS

## Companion Docs

- root index: [ROOT_DOC_MAP.md](./ROOT_DOC_MAP.md)
- repo overview: [README.md](./README.md)
- project summary: [PROJECT_STATUS.md](./PROJECT_STATUS.md)
- bet / trigger summary: [BET_PROJECT_STATUS.md](./BET_PROJECT_STATUS.md)

- updated_at: 2026-03-23 22:58 JST
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

## 9. Follow-up Measurement 2026-03-22

Direct re-check on the canonical shared DB:

- measured_at: `2026-03-22 23:54 JST`
- canonical_db: `\\038INS\boat\data\silver\boat_race.duckdb`
- canonical DB file timestamp: `2026-03-22 01:58 JST`

### Shared Silver Follow-up

- `races`: `169,596` rows, `2023-03-11..2026-03-20`, `1106` days
- `entries`: `1,017,576` rows, `2023-03-11..2026-03-20`, `1106` days
- `results`: `167,336` rows, `2023-03-11..2026-03-20`, `1106` days
- `beforeinfo_entries`: `991,417` rows, `2023-03-11..2026-03-20`, `1106` days
- `race_meta`: `169,596` rows, `2023-03-11..2026-03-20`, `1106` days
- `odds_2t`: `2,291,220` rows, `2025-04-01..2026-03-20`, `335` days
- `odds_3t`: `4,834,200` rows, `2025-04-01..2026-03-20`, `269` days

Distinct day ranges now present in silver:

- `odds_2t`: `2025-04-01..2025-08-20`, `2025-09-09..2026-03-20`
- `odds_3t`: `2025-04-01..2025-08-20`, `2025-09-09..2025-12-24`, `2026-03-01..2026-03-20`

Recent daily view from `collection_day_summary`:

- `2026-03-16`: `race_count=132`, `odds_2t_count=5940`, `odds_3t_count=15840`, `result_count=132`
- `2026-03-17`: `race_count=120`, `odds_2t_count=5400`, `odds_3t_count=14400`, `result_count=120`
- `2026-03-18`: `race_count=132`, `odds_2t_count=5940`, `odds_3t_count=15840`, `result_count=132`
- `2026-03-19`: `race_count=180`, `odds_2t_count=8100`, `odds_3t_count=21600`, `result_count=180`
- `2026-03-20`: `race_count=192`, `odds_2t_count=8640`, `odds_3t_count=23040`, `result_count=192`

### Shared Bronze Follow-up

Latest shared bronze files:

- `results`: latest file `20260320.csv`
- `beforeinfo_entries`: latest file `20260320.csv`
- `race_meta`: latest file `20260320.csv`
- `odds_2t`: latest file `20260320.csv`, files total `335`
- `odds_3t`: latest file `20260320.csv`, files total `335`, non-empty `269`, header-only `66`

Interpretation:

- shared bronze and shared silver now both reach `2026-03-20`
- as of this check, `2026-03-21` and `2026-03-22` are not yet present in canonical bronze/silver
- under the current daily task design, `2026-03-22` data is expected to appear on the morning run of `2026-03-23`

### Recent Missing-Race Follow-up

The previously observed partial/missing races in early March 2026 still remain as missing `results / odds_2t / odds_3t` while `beforeinfo_entries` exists:

- `2026-03-10` `常滑` `7R-12R`
- `2026-03-08` `桐生` `6R-12R`
- `2026-03-07` `桐生` `7R-12R`
- `2026-03-04` `平和島` `8R-12R`
- `2026-03-02` `若松` `6R-12R`

Current meaning:

- the recent supplement has advanced the canonical DB from `2026-03-18` to `2026-03-20`
- the main daily pipeline appears to be functioning through `2026-03-20`
- the next expected check point is the morning of `2026-03-23` for arrival of `2026-03-22` data

## 10. Local Re-check 2026-03-23

Direct re-check on the local working DB under `D:\boat\data`:

- measured_at: `2026-03-23 22:30 JST`
- local_db: `D:\boat\data\silver\boat_race.duckdb`
- local DB file timestamp: `2026-03-22 01:58 JST`

### Local Silver Re-check

- `races`: `169,596` rows, `2023-03-11..2026-03-20`, `1106` days
- `entries`: `1,017,576` rows, `2023-03-11..2026-03-20`, `1106` days
- `results`: `167,336` rows, `2023-03-11..2026-03-20`, `1106` days
- `beforeinfo_entries`: `991,417` rows, `2023-03-11..2026-03-20`, `1106` days
- `race_meta`: `169,596` rows, `2023-03-11..2026-03-20`, `1106` days
- `odds_2t`: `2,291,220` rows, `2025-04-01..2026-03-20`, `335` days
- `odds_3t`: `4,834,200` rows, `2025-04-01..2026-03-20`, `269` days

Recent daily view from `collection_day_summary` still ends at `2026-03-20`:

- `2026-03-20`: `race_count=192`, `result_count=192`, `beforeinfo_entry_count=1152`, `race_meta_count=192`, `odds_2t_count=8640`, `odds_3t_count=23040`
- `2026-03-19`: `race_count=180`, `result_count=180`, `beforeinfo_entry_count=1080`, `race_meta_count=180`, `odds_2t_count=8100`, `odds_3t_count=21600`
- `2026-03-18`: `race_count=132`, `result_count=132`, `beforeinfo_entry_count=792`, `race_meta_count=132`, `odds_2t_count=5940`, `odds_3t_count=15840`

### Local Bronze Re-check

Latest local bronze files are still `20260320.csv` for all recent validation inputs and odds:

- `results`: `20260320.csv`, timestamp `2026-03-22 01:50:51 JST`
- `beforeinfo_entries`: `20260320.csv`, timestamp `2026-03-22 01:50:51 JST`
- `race_meta`: `20260320.csv`, timestamp `2026-03-22 01:50:51 JST`
- `odds_2t`: `20260320.csv`, timestamp `2026-03-22 01:50:50 JST`
- `odds_3t`: `20260320.csv`, timestamp `2026-03-22 01:50:51 JST`

### Current Local Interpretation

- local `bronze` and local `silver` are **not** yet filled through `2026-03-21` or `2026-03-22`
- the current local working DB is still complete only through `2026-03-20`
- this means the expected morning refresh for `2026-03-23` had not appeared in the local DB at the time of this check
- for strategy / BT work, the latest trustworthy local cutoff remains `2026-03-20`

## 11. Manual One-Day Catch-up 2026-03-23

Follow-up after the local re-check:

- measured_at: `2026-03-23 22:58 JST`
- target day: `2026-03-21`
- scope: one-day manual collect against shared `\\038INS\boat\data`

### Bronze Result

The following shared bronze files now exist for `20260321`:

- `results/20260321.csv`
- `beforeinfo_entries/20260321.csv`
- `race_meta/20260321.csv`
- `odds_2t/20260321.csv`
- `odds_3t/20260321.csv`

Observed file timestamps:

- all core validation files and `odds_3t`: around `2026-03-23 22:08:57 JST`
- `odds_2t`: `2026-03-23 22:08:56 JST`

### Silver Result

Shared silver advanced to `2026-03-21`:

- `races`: `2026-03-21`, `1107` days
- `results`: `2026-03-21`, `1107` days
- `beforeinfo_entries`: `2026-03-21`, `1107` days
- `race_meta`: `2026-03-21`, `1107` days
- `odds_2t`: `2026-03-21`, `336` days
- `odds_3t`: `2026-03-21`, `270` days

Recent `collection_day_summary` view now includes:

- `2026-03-21`: `race_count=180`, `result_count=180`, `beforeinfo_entry_count=1080`, `race_meta_count=180`, `odds_2t_count=8100`, `odds_3t_count=21600`

### Current Interpretation

- shared `bronze` / `silver` are now confirmed through `2026-03-21`
- `2026-03-22` is still pending as of this note
- the practical latest trustworthy cutoff for current work is now `2026-03-21`
- scheduled-task behavior for the next day is intentionally left for natural observation rather than forcing another manual catch-up here
