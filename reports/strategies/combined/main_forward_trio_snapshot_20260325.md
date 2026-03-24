# Main Forward Trio Snapshot 2026-03-25

This note is the single-page risk and performance snapshot for the current main forward trio:

- `4wind_base_415`
- `c2_provisional_v1`
- `125_broad_four_stadium`

Use this note when you want a quick current read on:

- what each active logic is
- where its current runtime definition lives
- what the latest available DD / ROI evidence is
- what caveats still exist between runtime shape and evidence shape

## 1. Current Runtime Ownership

Shared logic owner:

- `live_trigger/boxes/125/`
- `live_trigger/boxes/c2/`
- `live_trigger/boxes/4wind/`

Main operating line:

- `live_trigger_cli`

Common adopted filter across the trio:

- exclude final meeting day

## 2. Current Runtime Shapes

### `125_broad_four_stadium`

Current runtime shape:

- stadiums:
  - `Suminoe`
  - `Naruto`
  - `Ashiya`
  - `Edogawa`
- `lane1 = B1`
- `lane5 != B2`
- `lane6 = B2`
- `lane1_exhibition_best_gap <= 0.02`
- fixed bet:
  - `1-2-5`

Owner file:

- [broad_four_stadium.json](/c:/CODEX_WORK/boat_clone/live_trigger/boxes/125/profiles/broad_four_stadium.json)

### `c2_provisional_v1`

Current runtime shape:

- women-race title proxy
- or `women6_proxy`
- beforeinfo lane-1 weakness confirmation
- bet expansion:
  - `2-ALL-ALL`
  - `3-ALL-ALL`
- current runtime refinement:
  - `B2 cut`

Owner file:

- [provisional_v1.json](/c:/CODEX_WORK/boat_clone/live_trigger/boxes/c2/profiles/provisional_v1.json)

### `4wind_base_415`

Current runtime shape:

- `wind 5-6m`
- `lane4_st_diff_from_inside <= -0.05`
- `lane4_exhibition_time_rank <= 3`
- `lane3_class in ('A1', 'A2')`
- partner focus:
  - `4-1`
  - `4-5`
- quoted odds zone:
  - `10 <= min_odds < 50`

Owner file:

- [base_415.json](/c:/CODEX_WORK/boat_clone/live_trigger/boxes/4wind/profiles/base_415.json)

## 3. Best Available DD / ROI Evidence

The most comparable aligned evidence across the trio is:

- period:
  - `2025-04-01 .. 2026-03-09`
- source:
  - [README.md](/c:/CODEX_WORK/boat_clone/reports/strategies/combined/c2_125_4wind_2025-04-01_to_2026-03-09_20260322/README.md)
  - [summary.csv](/c:/CODEX_WORK/boat_clone/reports/strategies/combined/c2_125_4wind_2025-04-01_to_2026-03-09_20260322/summary.csv)

| logic | source variant | races | source stake | ROI | max DD | max losing streak | note |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `125_broad_four_stadium` | `125_four_stadium_x1` | 224 | 100 yen / race | 223.04% | 4,200 yen | 42 | closest aligned natural-stake evidence |
| `c2_provisional_v1` | `C2_provisional_v1` | 288 | 4,000 yen / race | 163.89% | 149,590 yen | 13 | evidence predates current `B2 cut` and final-day exclusion |
| `4wind_base_415` | `4wind_only_wind_5_6_415` | 597 | 200 yen / race | 154.39% | 27,600 yen | 138 | closest aligned evidence for current `4-1 / 4-5` shape |

## 4. Strategy-Specific Reading Notes

### `125_broad_four_stadium`

Main detailed read:

- [summary_20260314.md](/c:/CODEX_WORK/boat_clone/reports/strategies/125/summary_20260314.md)

Important interpretation:

- this is the cleanest current trio member from a DD perspective
- the broad 4-stadium package remained shallow on DD even before final-day exclusion
- `125` should be read as a low-class lane-1 inside-preservation logic, not a generic weak-lane1 fade

### `c2_provisional_v1`

Main detailed reads:

- [README.md](/c:/CODEX_WORK/boat_clone/reports/strategies/c2/README.md)
- [status_notebooklm_20260313.txt](/c:/CODEX_WORK/boat_clone/projects/c2/status_notebooklm_20260313.txt)

Important interpretation:

- this is still the heaviest DD member of the trio
- the best available aligned DD evidence comes from the pre-`B2 cut` portfolio
- current runtime is safer than that old evidence because:
  - `B2 cut` is now adopted
  - final meeting day is now excluded
  - `women6_proxy` is now allowed in runtime

So the old DD number should be treated as an upper-risk reference, not as the final current-state DD.

### `4wind_base_415`

Main detailed reads:

- [README.md](/c:/CODEX_WORK/boat_clone/reports/strategies/gemini_registry/4wind/README.md)
- [logic_considerations.md](/c:/CODEX_WORK/boat_clone/projects/4wind/logic_considerations.md)

Important interpretation:

- current `4wind` is no longer the broad original Gemini branch
- the active runtime shape is the narrowed `4-1 / 4-5` structure with `lane3_class in ('A1', 'A2')`
- DD is materially lower than the old wide 2025 branch because partner spread and wind zone were narrowed

## 5. Current Practical Read

As of this note:

- `125_broad_four_stadium`
  - best current balance of DD and simplicity
- `4wind_base_415`
  - acceptable DD shape with a clearer structural story after refinement
- `c2_provisional_v1`
  - still valuable, but risk control is the main issue

So the trio should be read roughly as:

1. `125` = safest current practical shape
2. `4wind` = refined structural shape with manageable DD
3. `c2` = highest-risk member, still under refinement pressure

## 6. Update Rule

When a newer aligned trio backtest is produced, update this file first if any of the following change:

- max drawdown
- max losing streak
- stake-normalized ROI read
- runtime-vs-evidence caveat

If only one strategy changes, still update this snapshot so the trio remains comparable in one place.
