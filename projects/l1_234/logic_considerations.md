# l1_234 Logic Considerations

## Canonical Read

- Remove lane `1` from the `1..4` top-3 frame when lane `1` is the slowest exhibition lane and worst ST lane among lanes `1..4`.
- Use the remaining `2,3,4` structure as a trifecta box.

## Current Runtime Shape

- strategy id:
  - `l1_234`
- forward profile:
  - `l1_weak_234_box_v1`
- ticket expression:
  - `2-3-4 / 2-4-3 / 3-2-4 / 3-4-2 / 4-2-3 / 4-3-2`

## Guardrail

- Keep the profile disabled by default until the branch has been observed in forward without disturbing the existing main trio.
