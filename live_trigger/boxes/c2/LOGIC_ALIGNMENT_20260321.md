# BOX C2 Logic Alignment 2026-03-21

Scope:

- `projects/c2/`
- `reports/strategies/c2/`
- `live_trigger/boxes/c2/`

Canonical references:

- `projects/c2/status_notebooklm_20260313.txt`
- `reports/strategies/c2/README.md`

Strict refined C2:

- women race
- `st1 - min(st2..st6) >= 0.10`
- `wind <= 2`
- `ex1 <= ex2`
- `ex1 <= ex3`

Current runtime:

- `c2_provisional_v1`
- women-race title proxy
- `st1 - min(st2..st6) >= 0.12`
- `ex1 <= ex2 + 0.02`
- `ex1 <= ex3 + 0.02`
- no wind filter

Operational reading:

- Runtime intentionally follows the project provisional branch.
- Runtime does not claim to be the strict refined C2 rule set.
- This is the adopted branch for live use until a stricter change is explicitly chosen.
