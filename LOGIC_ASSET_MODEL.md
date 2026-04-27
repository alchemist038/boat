# Logic Asset Model

This file defines how to preserve logic-exploration assets without mixing them
directly into the live forward operating line.

## Purpose

The current auto line only reflects the active forward set.

But the project has additional long-lived assets that should not be lost:

- dormant but still valuable logic concepts
- candidate filters and overlays
- cross-project structural reads
- zero-base discovery notes
- backtest and walk-forward evidence
- project-level reasoning that explains why a logic was promoted, held, or
  parked

These should be integrated and kept reachable even when they are not running in
`live_trigger_cli`.

## Standard Four-Layer Model

### 1. `projects/<name>/`

Use this as the owner folder for the concept itself.

Keep here:

- `README.md`
- `logic_considerations.md`
- `status_*.txt` or equivalent project memo
- links to the current runtime profile if one exists
- links to the main evidence folders and promoted reports

This is the best home for:

- logic ideas that may return later
- logic families with multiple revisions
- project-specific reasoning that matters beyond one report run

Think of `projects/` as the concept shelf.

### 2. `workspace_codex/analysis/<name>/`

Use this for raw or semi-raw exploration outputs.

Keep here:

- probe CSVs
- one-off scan outputs
- notebook-style markdown
- temporary comparison slices
- pre-promotion evidence folders

This is the best home for:

- trial-and-error work
- intermediate outputs
- evidence that is useful, but not yet polished enough for the canonical
  strategy summary shelf

Think of `workspace_codex/analysis/` as the lab bench.

### 3. `reports/strategies/<name>/`

Use this for curated human-facing summaries that are worth preserving.

Keep here:

- promoted summary markdown
- walk-forward summary outputs
- canonical comparison tables
- monthly summaries and report bundles that explain the current read

This is the best home for:

- summaries that should survive beyond one coding session
- evidence that may support future re-adoption
- operator-readable logic history

Think of `reports/strategies/` as the archive shelf.

### 4. `live_trigger/boxes/<name>/`

Use this only when the concept has become a runtime logic owner.

Keep here:

- runtime profiles
- shared logic code
- box-expansion inputs that belong to the live/shared logic path

This is not the place for broad exploration notes.

Think of `live_trigger/boxes/` as the production shelf.

## What Goes To `C:\boat`

`C:\boat` should hold the operationally valuable canonical copy, not every raw
experiment.

Current recommendation:

- keep active editing and analysis generation in:
  - `C:\CODEX_WORK\boat_clone`
- sync/promote stable human-readable strategy summaries to:
  - `C:\boat\reports\strategies`
- keep `projects/` mirrored to `C:\boat` when the notes are worth operational
  reference
- do not treat `C:\boat` as the home for raw exploration churn by default

In short:

- raw exploration:
  - workspace-first
- concept ownership notes:
  - repo-first, mirror when useful
- canonical summaries:
  - repo-first, then mirror to `C:\boat`
- live runtime logic:
  - shared logic owner under `live_trigger/boxes/`

## Promotion Rule

When a concept starts to matter, move it through these stages:

1. exploration evidence in `workspace_codex/analysis/`
2. concept ownership note in `projects/<name>/`
3. curated summary in `reports/strategies/<name>/`
4. runtime profile or shared logic only if it becomes forward/adopted

This gives us a durable record even if the logic is not currently on auto.

## Current Practical Read

For this repo, the best integration model is:

- keep non-forward logic assets reachable in the workspace-managed concept and
  analysis shelves
- preserve important summaries in `reports/strategies/`
- mirror stable summaries and key root docs to `C:\boat`
- reserve the forward/runtime shelves for the smaller set that actually reaches
  live operation
