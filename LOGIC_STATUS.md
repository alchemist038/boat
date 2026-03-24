# Logic Status

This file is the parent status doc for logic research, adopted forward logic, and logic-adjacent signal work.

## Companion Docs

- [PROJECT_STATUS.md](./PROJECT_STATUS.md)
- [BET_PROJECT_STATUS.md](./BET_PROJECT_STATUS.md)
- [RACER_INDEX_STATUS.md](./RACER_INDEX_STATUS.md)
- [projects/125/README.md](./projects/125/README.md)
- [projects/4wind/README.md](./projects/4wind/README.md)
- [live_trigger/PROJECT_RULES.md](./live_trigger/PROJECT_RULES.md)

- updated_at: 2026-03-24 JST

## 1. Logic Ownership

- runtime logic source of truth:
  - `live_trigger/boxes/`
- shared bet expansion source:
  - `live_trigger/auto_system/app/core/bets.py`
- local execution lines may consume this logic, but should not silently fork it

Current explicit exception:

- `live_trigger_cli/boxes/4wind/`
  - still exists as a line-local runtime profile
  - should be treated as a temporary ownership exception until the profile is promoted into shared `live_trigger/boxes`

## 2. Current Main Forward Set

These are the three active forward logic tracks.

### `4wind_base_415`

- current main project axis
- current runtime shape:
  - windy outside-head structure
  - partner focus `4-1 / 4-5`
  - `lane3_class in ('A1', 'A2')`
- current runtime profile lives in:
  - `live_trigger_cli/boxes/4wind/profiles/base_415.json`

### `c2_provisional_v1`

- target idea:
  - women-race structure with lane-1 weakness confirmation
- current watchlist entry path:
  - title proxy
  - or `women6_proxy`
- current execution refinement:
  - `B2 cut` in `2-ALL-ALL / 3-ALL-ALL`

### `125_broad_four_stadium`

- target idea:
  - fixed `1-2-5`
- scope:
  - `Suminoe / Naruto / Ashiya / Edogawa`
- current structural gate:
  - `lane1 = B1`
  - `lane5 != B2`
  - `lane6 = B2`

## 3. Common Adopted Filters

These should now be treated as adopted shared reads across the current forward set.

- exclude final meeting day
- keep logic point-in-time
- do not let execution-specific state redefine logic truth

## 4. Not Main But Still Present

- `125_suminoe_main`
  - valid profile
  - not part of the current main forward trio
- universal `pred6` overlay
  - not adopted yet
  - remains conditional / project-specific

## 5. Racer Index Position

`racer_index` is a logic substrate.

It is not:

- the main bet line
- the DB owner
- a standalone operational line

It is:

- a persistent racer-ability layer
- a source of candidate conditional filters and head signals
- an input into future logic refinement

Current racer-index status lives in:

- [RACER_INDEX_STATUS.md](./RACER_INDEX_STATUS.md)

## 6. Forward Discipline

For the current main trio:

- keep forward operation on `live_trigger_cli`
- keep logic ownership under the shared source
- record adopted filters and scope changes here
- keep strategy-specific backtest and refinement notes in the relevant project/readme files
