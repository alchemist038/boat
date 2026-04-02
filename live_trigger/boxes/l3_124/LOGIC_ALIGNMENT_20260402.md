# L3_124 Logic Alignment 2026-04-02

This memo aligns the research shape with the forward runtime candidate.

Canonical research shape:

- `lane3_slowest_exh`
- `lane3_worst_st`
- exactly one of `lane5` / `lane6` is A-class
- `1-2-4 BOX`
- six-ticket research view includes `2-4-1`

Forward runtime candidate:

- profile id: `l3_weak_124_box_one_a_ex241_v1`
- disabled by default
- five-ticket trifecta slice
- excludes `2-4-1`

Alignment notes:

- the core race read is unchanged
- the runtime slice is narrower only because `2-4-1` was the weakest ticket in the ticket-level breakdown
- this is a deliberate runtime refinement, not a change to the research hypothesis

Promotion guardrail:

- keep the profile disabled until the shared runtime implementation and forward test both stay stable
- existing promoted lines must remain untouched while this branch is evaluated
