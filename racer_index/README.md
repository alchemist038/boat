# Racer Index

This folder is the home for racer-centric indicator work and point-in-time prediction operations.

## Position In The Project

- `racer_index` sits under logic research
- it is not the main bet line
- it is not the DB owner
- it is a reusable logic substrate

The owner docs are:

- [../LOGIC_STATUS.md](../LOGIC_STATUS.md)
- [../RACER_INDEX_STATUS.md](../RACER_INDEX_STATUS.md)

## Current Position

- The first operating window is `5M`
- `M` means month, so `5M` means the prior `5 months`
- Keep `8M` and `12M` as benchmarks and compare them monthly
- Keep all predictions strictly `point-in-time`
- Keep outputs `append-only` and never overwrite past predictions

## What Lives Here

- [OPERATIONS.md](./OPERATIONS.md)
  - daily, weekly, and monthly operating rules
- [SCHEMA.md](./SCHEMA.md)
  - recommended table and view design

## Promotion Policy

- Keep exploratory scripts in the operational workspace until stabilized
- Promote stable logic here once the shape is settled
- Treat [../RACER_INDEX_STATUS.md](../RACER_INDEX_STATUS.md) as the owner doc for this layer
