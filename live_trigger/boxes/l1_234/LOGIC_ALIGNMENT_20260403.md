# L1_234 Logic Alignment 2026-04-03

This memo aligns the research shape with the forward runtime candidate.

Canonical research shape:

- `lane1_slowest_exh`
- `lane1_worst_st`
- `2-3-4 BOX`

Forward runtime candidate:

- profile id: `l1_weak_234_box_v1`
- disabled by default
- six-ticket trifecta box

Alignment notes:

- the race read and the ticket expression are unchanged from the research shape
- even though `2-3-4` is the modal order, the branch still behaves like a disturbed `2/3/4` ordering problem rather than a clean single-order signal
- so the forward candidate intentionally keeps the full six-ticket box instead of forcing a narrower slice
- this branch is broad-scan and beforeinfo-driven, so it should stay isolated from the current promoted trio during forward evaluation

Promotion guardrail:

- keep the profile disabled until the shared runtime implementation and forward test both stay stable
- existing promoted lines must remain untouched while this branch is evaluated
