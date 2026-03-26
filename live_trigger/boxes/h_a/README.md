# H-A

`H-A` is the current leading dormant exacta branch promoted into shared runtime ownership as a disabled candidate.

Current candidate shape:

- bet:
  - exacta `4-1`
- adopted refinement:
  - final meeting day excluded
- beforeinfo confirmation:
  - `lane1` exhibition ST rank `<= 3`
  - `lane4` exhibition ST ahead of `lane1` by `>= 0.05`

This box exists so:

- `live_trigger_cli` can consume the same shared truth as other strategies
- future replay / backtest / runtime comparisons do not keep a local-only copy

Operational note:

- keep this profile `disabled` by default until stake sizing and runtime adoption are explicitly approved
