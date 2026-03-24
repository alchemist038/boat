# R Concept

## Position In Project

`R` should now be read as a logic-side portfolio sizing concept.

Companion docs:

- [LOGIC_STATUS.md](./LOGIC_STATUS.md)
- [BET_PROJECT_STATUS.md](./BET_PROJECT_STATUS.md)
- [ROOT_DOC_MAP.md](./ROOT_DOC_MAP.md)

It is:

- part of logic and portfolio design
- an input into runtime stake sizing

It is not:

- a DB concept
- a race-selection rule by itself
- a waiting/execution control concept

This file defines the project-level meaning of `R`.

## Core Meaning

In this project, `R` means:

- a risk-scaling multiplier
- used to roughly equalize `MAX DD` contribution across strategies

It is **not** being used here as a generic betting term or a profit unit.

The working idea is:

- each strategy has its own natural stake and natural `MAX DD`
- if strategies are combined as-is, one of them may dominate portfolio risk
- so a multiplier is applied to each strategy so that drawdown contribution is brought closer to the same level

## Basic Formula

For a chosen aligned test period:

`strategy_R ≈ target_max_dd / strategy_natural_max_dd`

Where:

- `target_max_dd` is usually taken from the anchor strategy
- `strategy_natural_max_dd` is the natural `MAX DD` of the strategy in the same period

Rounded practical values are allowed.

## Target Choice Modes

There are two acceptable ways to choose `target_max_dd`.

### 1. Anchor Mode

Use one strategy as the anchor.

- example:
  - `C2 = 1R`
  - other strategies are scaled toward `C2` drawdown

This is useful when one strategy is already the practical portfolio baseline.

### 2. Average Mode

Use the average natural `MAX DD` of the active strategy set.

`target_max_dd = average(strategy_natural_max_dd)`

This is useful when:

- no single strategy should be the anchor
- the goal is to average drawdown contribution across the active set
- the runtime wants a neutral portfolio baseline

In this mode, `R` is still computed per strategy, but the common target comes from the active portfolio average instead of one anchor line.

## Important Rules

- Always use the same aligned period when computing `R`
- Always use the current formal strategy definition
- Recompute `R` if the formal logic changes
- Recompute `R` if the main evaluation period changes materially
- `R` is a portfolio-risk tool first, not an ROI-optimization tool
- The chosen target mode (`anchor` or `average`) must be recorded with the `R` values
- Runtime bet sizing should consume precomputed `R`; it should not estimate `MAX DD` on the fly

## Current Example

Aligned period used in the current combined note:

- `2025-04-01` to `2026-03-09`

Natural `MAX DD` values:

- `C2`: `149,590 yen`
- `125 x1`: `4,200 yen`
- `4wind x1`: `27,600 yen`

If `C2` is treated as the anchor:

- `C2 = 1R`
- `125 ≈ 149,590 / 4,200 ≈ 35.6R`
- `4wind ≈ 149,590 / 27,600 ≈ 5.4R`

Practical rounded version:

- `125 = 36R`
- `4wind = 5R`

## Current Interpretation

When someone says:

- `125 = 20R`
- `4wind = 5R`

that should be read as a portfolio choice, not as exact DD parity.

If strict DD parity is the goal, the current closer approximation is:

- `C2 = 1R`
- `125 = 36R`
- `4wind = 5R`

## Runtime Use

`R` should feed bet sizing, not race selection.

Recommended runtime interpretation:

- BOX decides whether a race is structurally actionable
- market check decides whether the live price is acceptable
- `R` decides how large the final bet should be

Recommended formula shape:

`final_bet_amount = round_to_ticket_unit(base_r_yen * strategy_R * profile_multiplier)`

Where:

- `base_r_yen` is the common yen value of `1R`
- `strategy_R` is precomputed from aligned backtest `MAX DD`
- `profile_multiplier` is an optional operational override such as `0.5x`, `1.0x`, `1.5x`

So `R` belongs to stake sizing, not to GO / NO_GO judgment.

## Current Placement

Within the current doc structure:

- `LOGIC_STATUS.md`
  - owns the current logic set and logic-adjacent research context
- `R_CONCEPT.md`
  - defines the shared portfolio-risk sizing language used by that logic
- `BET_PROJECT_STATUS.md`
  - describes how execution lines consume precomputed sizing

## Reference Files

- `reports/strategies/combined/c2_125_4wind_2025-04-01_to_2026-03-09_20260322/`
- `projects/4wind/README.md`
- `projects/125/README.md`
- `projects/c2/README.md`
