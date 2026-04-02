# l3_124 Logic Considerations

This note records the candidate logic for the weak-lane3 branch.

Core observation:

- when lane 3 is both the slowest exhibition lane and the worst ST lane among lanes 1-4, the race often collapses into the `1-2-4` shape
- the branch becomes cleaner when exactly one of lanes 5/6 is A-class
- `2-4-1` is the weakest ticket in the six-ticket box view, so the forward runtime candidate keeps the five-ticket slice without it

Research summary:

- `2024` keeps the branch alive with a stable `1-2-4 BOX`
- `2025` remains strong in both halves
- `2026YTD` is slightly softer, but still above the unconditional baseline

Forward-test position:

- canonical research shape: `1-2-4 / 1-4-2 / 2-1-4 / 2-4-1 / 4-1-2 / 4-2-1`
- runtime refinement candidate: `l3_weak_124_box_one_a_ex241_v1`
- runtime ticket set: `1-2-4 / 1-4-2 / 2-1-4 / 4-1-2 / 4-2-1`

Operational note:

- keep the runtime profile disabled by default
- if this branch is promoted later, align the project note, shared box README, and the box profile together
