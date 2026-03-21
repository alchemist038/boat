# BOX 125 Logic Alignment 2026-03-21

Scope:

- `projects/125/`
- `reports/strategies/125/`
- `live_trigger/boxes/125/`

Canonical references:

- `projects/125/status_notebooklm_20260313.txt`
- `reports/strategies/125/summary_20260314.md`

Canonical memo-style conditions:

- Main Suminoe branch:
  - `lane1=B1`
  - `lane6=B2`
  - `lane5!=B2`
  - `lane1 exhibition_time - best_exhibition_time <= 0.02`
- Current four-stadium branch used in runtime:
  - Suminoe
  - Naruto
  - Ashiya
  - Edogawa

Current runtime status:

- `125_suminoe_main`
  - Matches the canonical Suminoe branch closely
  - Still disabled
- `125_broad_four_stadium`
  - Tightened from the older loose proxy
  - Runtime now requires:
    - `lane1=B1`
    - `lane6=B2`
    - `lane5!=B2`
    - `exgap<=0.02`

What was fixed:

1. `lane6=A1` can no longer pass the broad runtime profile.
2. The old motor-based proxy conditions were removed.
3. The runtime description now matches the adopted branch better.

Remaining simplification:

- The project summary treats Ashiya as a separate `lane5=B1` branch inside the four-stadium review.
- Runtime still keeps one shared broad profile, so Ashiya is currently handled by the common `lane5!=B2` condition.

Operational reading:

- Runtime now reflects the adopted broad branch much more closely than before.
- It is still not a full per-stadium decomposition.
