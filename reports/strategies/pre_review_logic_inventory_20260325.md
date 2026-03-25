# Pre-Review Logic Inventory 2026-03-25

This note is the holding inventory for logic branches that are not part of the current main forward trio, but should still remain reachable from the parent logic status.

Use this file as the entry point for:

- branches that are still `検討前`
- dormant hypotheses that may deserve a next review pass
- branches that are preserved but not promoted

## 1. Current Status Label

For this note, `検討前` means:

- not part of the current forward trio
- not adopted into the shared live runtime
- still preserved because the branch may contain reusable structure or context

Current main forward trio remains:

- `125_broad_four_stadium`
- `c2_provisional_v1`
- `4wind_base_415`

See:

- [LOGIC_STATUS.md](/c:/CODEX_WORK/boat_clone/LOGIC_STATUS.md)
- [main_forward_trio_snapshot_20260325.md](/c:/CODEX_WORK/boat_clone/reports/strategies/combined/main_forward_trio_snapshot_20260325.md)

## 2. Priority Order

### Priority 1: `2025-04-01..2025-06-16` bounded discovery slice

Current status:

- `検討前`
- highest dormant-review priority

Canonical note:

- [README.md](/c:/CODEX_WORK/boat_clone/reports/strategies/zero_base_period_2025-03-11_to_2025-06-16_20260324/README.md)

Contained branches:

- `H-A`
  - `4-1`
- `H-C`
  - `3-2`
- `H-B`
  - `4-2`
- `H-D`
  - `5-2`

Current review order inside this slice:

1. `H-A`
2. `H-C`
3. `H-B`
4. `H-D`

Reason for top priority:

- current trio DD / ROI comparison is anchored on the aligned period `2025-04-01 .. 2026-03-09`
- [main_forward_trio_snapshot_20260325.md](/c:/CODEX_WORK/boat_clone/reports/strategies/combined/main_forward_trio_snapshot_20260325.md) is the current cross-trio reference
- `125` has an explicitly recorded BT max-DD interval of `2025-03-11 -> 2025-06-16`
- [summary_20260314.md](/c:/CODEX_WORK/boat_clone/reports/strategies/125/summary_20260314.md) identifies that interval directly
- this means the bounded exacta discovery slice `2025-04-01 .. 2025-06-16` sits inside the early stress zone that already matters for the current main logic set
- therefore this slice is the most natural place to look for the next branch before expanding into broader dormant inventory

Working interpretation:

- this slice should be treated as the first dormant branch review area because it may explain, complement, or hedge the trio's early drawdown regime
- it is not yet a promoted runtime candidate, but it is the best current `検討前` source

### Priority 2: `2press`

Current status:

- `検討前`
- alive, but not promoted

Canonical note:

- [README.md](/c:/CODEX_WORK/boat_clone/reports/strategies/gemini_registry/2press/README.md)

Reason:

- still alive in `2025`, but weakened materially
- current read is that it needs context slicing before any promotion
- this makes it weaker than the bounded `2025-04-01..2025-06-16` slice, but still stronger than fully rejected Gemini branches

### Priority 3: `H-003 / H-004 / H-005`

Current status:

- `検討前`
- preserved, but not current promotion targets

Canonical note:

- [non_selected_hypotheses.md](/c:/CODEX_WORK/boat_clone/reports/strategies/gemini_registry/non_selected_hypotheses.md)

Reason:

- these are useful as preserved zero-base exploration history
- but they are already negative or clearly weak in the retained cross-year read
- they should remain reachable, but not consume review priority ahead of the two groups above

## 3. Practical Reading Rule

If a new review thread wants to inspect dormant logic, use this order:

1. read this file
2. read the bounded slice note for `H-A / H-C / H-B / H-D`
3. only then move to `2press`
4. look at `H-003 / H-004 / H-005` last unless a very specific structural question requires them

## 4. Update Rule

Update this note when any of the following happens:

- one of these branches is promoted into project-level logic
- one of these branches is explicitly rejected and archived
- a newer dormant-review priority is chosen from a more relevant trio-DD period
