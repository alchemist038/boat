# Live Trigger Project Rules

## Single Source Of Truth

1. `live_trigger/boxes/` is the only canonical runtime source for strategy conditions.
2. `trigger app`, `auto_system`, `replay tools`, `fresh_exec`, and future real executors must reference this shared `boxes/` root.
3. No parallel tree may keep its own copied `125`, `c2`, `4wind`, or `h_a` profile JSON files.

## Strategy Ownership

1. Project notes under `projects/125/` and `projects/c2/` are research sources.
2. Runtime-adopted conditions must be expressed in `live_trigger/boxes/*/profiles/*.json`.
3. If canonical notes and runtime proxy differ, that difference must be documented in the box README or alignment memo.

## Bet Definition Ownership

1. `live_trigger/auto_system/app/core/bets.py` is the single shared source for bet expansion.
2. Execution-line differences may change how bets are submitted, but not duplicate strategy-to-bet mapping in separate trees.

## Execution-Line Rule

1. `live_trigger/app.py` and `live_trigger/auto_system/` share the same BOX definitions.
2. `live_trigger_fresh_exec/` is execution-focused, but when it needs profile-aware selection it must read the shared BOX root instead of defining local copies.
3. Execution innovation is allowed; profile duplication is not.

## Update Rule

1. When a strategy changes, update the relevant project note, shared BOX profile, and alignment memo together.
2. If the change is not yet adopted in runtime, document it as a comparison or candidate, not as an active rule.
