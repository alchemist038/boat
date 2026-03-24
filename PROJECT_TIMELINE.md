# Project Timeline

This file records the major steps in the project's recent evolution so the path is easy to follow.

## 2026-03-19

- shared operational model became explicit:
  - `\\038INS\boat\data` is the canonical data root
  - shared DuckDB is the canonical DB
- shared DB was rebuilt from shared bronze
- current / recent collection and shared integration were centered on `ins14`

## 2026-03-21

- clean rebuild and promote flow for the shared DuckDB was completed
- daily recent collection was formalized around the shared root
- fresh execution line was documented as a separate execution path

## 2026-03-22

- remaining odds gaps were isolated into dedicated recovery jobs
- new bet line work shifted toward a separate CLI-driven runtime
- `4wind` was promoted into the active project direction

## 2026-03-23

- `live_trigger_cli` became self-contained enough to generate its own watchlists
- `4wind`, `c2`, and `125` were aligned under the new line
- `4wind` was confirmed as a local runtime profile in the new line
- common `final day cut` direction became clearer across the active projects

## 2026-03-24

- `live_trigger_cli` was fixed as the main bet line
- current main forward set was fixed to:
  - `4wind`
  - `c2`
  - `125_broad_four_stadium`
- `C2` was refined with:
  - women6 proxy support
  - `B2 cut`
  - final-day exclusion
- `125` and `4wind` were also confirmed with final-day exclusion
- Telegram support advanced from simple `GO` alerting to:
  - `GO` message
  - approval / reject buttons
  - assist-mode approval callback
  - completion callback after submit
- racer-index work on `ins14` was recognized as a logic substrate, not a separate operating line

## Current Read

- DB safety is the top non-negotiable.
- `live_trigger_cli` is the main execution line.
- shared logic ownership stays under `live_trigger`.
- `racer_index` belongs under logic research.
