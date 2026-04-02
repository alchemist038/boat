# 3-of-4 Candidate C One-A Watch 2026-04-02

This note isolates the strongest current read from the `3-of-4` exploratory area and records it as a line-watch candidate rather than a closed exploratory branch.

Parent notes:

- [three_of_four_box_followup_20260402.md](./three_of_four_box_followup_20260402.md)
- [three_of_four_box_summary_2025h1.md](./three_of_four_box_2025h1_20260402/three_of_four_box_summary_2025h1.md)

## Candidate Shape

- core structure:
  - `lane3_slowest_exh`
  - `lane3_worst_st`
- ticket:
  - `1-2-4 BOX`
- refinement:
  - exactly one of `lane5` / `lane6` is `A-class`
  - here `A-class` means `A1` or `A2`

Interpretation:

- lane `3` looks weak enough to remove from the `1..4` top-3 frame
- the remaining path concentrates on `1,2,4`
- the branch becomes cleaner when `lane5` and `lane6` are not both strong and not both weak:
  - one side only carries `A-class` pressure

## Cross-Period Read

Base branch before the `one-A-only` refinement:

- `2025-01-01 .. 2025-06-30`
  - `sample 1647`
  - `hits 362`
  - `hit rate 21.98%`
  - `ROI 111.29%`
- `2025-07-01 .. 2025-12-31`
  - `sample 1610`
  - `hits 339`
  - `hit rate 21.06%`
  - `ROI 102.56%`
- `2026-01-01 .. 2026-04-01`
  - `sample 810`
  - `hits 165`
  - `hit rate 20.37%`
  - `ROI 98.37%`

Refined branch with `lane5/lane6 one-A-only`:

- `2025-07-01 .. 2025-12-31`
  - `sample 713`
  - `hits 137`
  - `hit rate 19.21%`
  - `ROI 116.57%`
- `2026-01-01 .. 2026-04-01`
  - `sample 368`
  - `hits 72`
  - `hit rate 19.57%`
  - `ROI 108.79%`

Comparison cut inside the same branch family:

- `2025_h2`
  - base branch: `ROI 102.56%`
  - exclude `lane5/lane6 = A1/A1` and `B2/B2`: `ROI 105.71%`
  - one-A-only: `ROI 116.57%`
- `2026_ytd`
  - base branch: `ROI 98.37%`
  - exclude `lane5/lane6 = A1/A1` and `B2/B2`: `ROI 105.57%`
  - one-A-only: `ROI 108.79%`

Working read:

- the light exclusion of `A1/A1` and `B2/B2` helps
- the stronger and cleaner version is:
  - keep only races where exactly one of `lane5` / `lane6` is `A-class`
- this keeps enough sample while improving the branch on both `2025_h2` and `2026_ytd`

## Lane 3 Class Slice

The refined `2025_h2` branch by `lane3_class`:

- `B1`
  - `sample 397`
  - `hits 91`
  - `hit rate 22.92%`
  - `ROI 129.38%`
- `A2`
  - `sample 206`
  - `hits 24`
  - `hit rate 11.65%`
  - `ROI 99.05%`
- `A1`
  - `sample 72`
  - `hits 14`
  - `hit rate 19.44%`
  - `ROI 109.03%`
- `B2`
  - `sample 38`
  - `hits 8`
  - `hit rate 21.05%`
  - `ROI 91.93%`

Interpretation:

- `lane3_class` is not the main driver
- `B1` looks best, but class itself does not explain the branch as cleanly as:
  - `lane3` exhibition weakness
  - `lane3` ST weakness
  - `lane5/lane6` one-side-only `A-class` pressure

## Current Status

Current recommendation:

- preserve this branch as the first `3-of-4` read that is worth line consideration
- do not auto-promote yet
- if the branch is reopened for live design, start from this exact version:
  - `lane3_slowest_exh`
  - `lane3_worst_st`
  - `lane5/lane6 one-A-only`
  - buy `1-2-4 BOX`

What still needs to be checked before runtime adoption:

1. odds shape and execution realism for a `6-ticket` box
2. stadium split and whether the branch is concentrated in a few venues
3. drawdown / flat-period shape, not only aggregate ROI
4. whether a lighter ticket expression exists inside the same structure
