# Copy Staging

Local staging area for handing collected files from `i5` to `ins14`.

## Layout

- `collect/`
  - source-separated staging copied from local workers such as `boat_a` and `boat_b`
- `move/`
  - final handoff bundle that can be copied to `ins14`

## Current Bundle

- final bundle:
  - `copy/move/20260319_odds_backfill/`
- contents:
  - `bronze/odds_2t/`
  - `bronze/odds_3t/`
  - `raw/odds_2t/` (empty on `i5`)
  - `raw/odds_3t/` (empty on `i5`)

## Recommended Target On ins14

Copy the final bundle to a staging inbox first:

- `Z:\\boat\\copy_inbox\\from_i5\\20260319_odds_backfill\\`

After verification on `ins14`, move the day files into the main `data/` tree.

## Rule

- staged data must not be committed to Git
- use `collect/` for source grouping and `move/` for the final bundle
- record first date, last date, table counts, and target path after copy
