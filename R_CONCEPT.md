# R Concept

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

## Important Rules

- Always use the same aligned period when computing `R`
- Always use the current formal strategy definition
- Recompute `R` if the formal logic changes
- Recompute `R` if the main evaluation period changes materially
- `R` is a portfolio-risk tool first, not an ROI-optimization tool

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

## Reference Files

- `reports/strategies/combined/c2_125_4wind_2025-04-01_to_2026-03-09_20260322/`
- `projects/4wind/README.md`
- `projects/125/README.md`
- `projects/c2/README.md`
