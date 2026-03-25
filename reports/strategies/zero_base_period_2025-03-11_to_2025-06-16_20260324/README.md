# Zero-Base Period Discovery 2025-03-11 to 2025-06-16

## Purpose

- preserve the zero-base exacta hypotheses derived from the bounded period slice
- keep one canonical human-readable note under `reports/strategies/`
- point back to the local analysis artifacts used to generate the hypotheses

## Data Scope

- structural discovery slice:
  - `2025-03-11` to `2025-06-16`
- odds-backed evaluation slice:
  - `2025-04-01` to `2025-06-16`

Reason for the odds-backed start date:

- canonical shared `odds_2t` / `odds_3t` coverage in `\\038INS\boat\data\silver\boat_race.duckdb` begins on `2025-04-01`

## Data Source

- read-only shared DB:
  - `\\038INS\boat\data\silver\boat_race.duckdb`

## Local Analysis Artifacts

- `workspace_codex/analysis/discovery_20250311_20250616/race_wide_20250311_20250616.csv`
- `workspace_codex/analysis/discovery_20250311_20250616/lane_head_scan_20250401_20250616.csv`
- `workspace_codex/analysis/discovery_20250311_20250616/exacta_rule_scan_20250401_20250616.csv`
- `workspace_codex/analysis/discovery_20250311_20250616/zero_base_hypotheses_odds_20250311_20250616_20260324.md`

## Hypothesis Summary

### H-A

- exacta:
  - `4-1`
- condition:
  - `lane1_st_top3`
  - `lane4_ahead_lane1_005`
- interpretation:
  - lane 1 is still structurally alive
  - but lane 4 is clearly ahead of lane 1 on exhibition ST
  - read it as `lane4 steals head, lane1 survives second`
- odds-backed result:
  - bets: `253`
  - hits: `16`
  - avg quoted odds: `26.08`
  - ROI: `143.08%`

### H-B

- exacta:
  - `4-2`
- condition:
  - `wave_6p`
  - `lane4_ahead_lane1_005`
- interpretation:
  - rough water plus clear lane-4 ST edge over lane 1
  - lane 4 takes head, lane 2 survives second more often than the market prices
- odds-backed result:
  - bets: `181`
  - hits: `6`
  - avg quoted odds: `61.73`
  - ROI: `138.56%`

### H-C

- exacta:
  - `3-2`
- condition:
  - `lane3_a`
  - `lane4_b2`
- interpretation:
  - lane 3 has real class strength
  - lane 4 is too weak to apply normal outside pressure
  - shorthand: `strong 3, dead 4, sticky 2`
- odds-backed result:
  - odds window: `15-60`
  - bets: `153`
  - hits: `7`
  - avg quoted odds: `31.07`
  - ROI: `122.29%`

### H-D

- exacta:
  - `5-2`
- condition:
  - `lane5_exgap_le_002`
  - `wind_4_6`
- interpretation:
  - lane 5 is truly live on exhibition
  - wind weakens pure inside persistence
  - lane 2 survives second more often than the market prices
- odds-backed result:
  - odds window: `20-80`
  - bets: `306`
  - hits: `7`
  - avg quoted odds: `47.74`
  - ROI: `104.15%`

## Current Priority

If only two branches are carried forward first:

1. `H-A`
2. `H-C`

Reason:

- both clear the `100+` sample requirement comfortably
- both have cleaner structural explanations than a pure payout accident
- both look less period-fragile than `H-B`

## Current Interpretation

This slice suggests a temporary structural shift away from pure inside-preservation thinking.

The strongest read is:

- a middle / outer boat takes the head
- one specific inside partner remains sticky enough for exacta

So the practical question becomes:

- not only `which fixed trifecta survives`
- but also `which outside head becomes real and which inside partner stays alive`

## Suggested Next Step

1. Re-test `H-A` and `H-C` first on the period after `2025-06-16`.
2. Keep `H-B` as a rough-water branch to verify by stadium.
3. Keep `H-D` as a lower-priority follow-up unless it survives the next period.
