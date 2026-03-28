# BOX GO Runtime Concept

- updated_at: 2026-03-22 JST
- status: concept note
- scope: future box-driven runtime that separates logic evaluation from bet execution

## Intent

The current trigger flow can identify candidate races ahead of time, but future logic is expected to become more complex.
To keep that complexity manageable, the next runtime should treat the BOX as the decision owner and split the runtime into:

- target acquisition
- logic evaluation
- market check
- bet execution
- audit

This note records that target structure before implementation work starts.

## Core Idea

The runtime should not let the DB decide which race to buy.
Instead:

- the DB stores snapshots, features, statuses, and audit history
- the BOX decides whether a race is structurally actionable
- the execution loop checks live odds at the designated time and decides whether the BOX result is still buyable

In short:

- structure decides early
- price decides late

## Why This Split

This design is useful for `4wind`, but it is not only for `4wind`.
It is aimed at future rules that may combine:

- racelist-stage information
- beforeinfo-stage information
- live odds constraints
- strategy-specific bet plans

The hard part is not data storage.
The hard part is keeping logic ownership clear when conditions become heterogeneous.

## Proposed Single-Folder Runtime

If we rebuild this as the next main runtime, a single root such as `live_trigger_v2/` can own the whole loop.

Suggested structure:

- `boxes/`
  - canonical strategy definitions
- `providers/`
  - fetch `racelist`, `beforeinfo`, `odds2t`, `odds3t`, `result`
- `features/`
  - build normalized feature snapshots from provider data
- `logic_loop/`
  - fetch and store pre-bet data, then ask BOX for a decision
- `execution_loop/`
  - run only near deadline, re-check market conditions, and submit bets
- `markets/`
  - turn strategy outputs into concrete bet rows
- `risk/`
  - convert `R` into final bet size
- `executor/`
  - Teleboat execution only
- `audit/`
  - air-bet logs, result settlement, payout review
- `state/`
  - DB models and loop status

The important point is not the exact folder names.
The important point is that logic and execution should be separate loops inside one runtime root.

## Ownership Model

### BOX

The BOX should be the single source of truth for strategy judgment.
It should own:

- required features
- structural conditions
- market conditions that must be checked before submission
- bet-plan template
- risk profile reference
- explanation strings

### DB

The DB should not be the strategy brain.
It should own:

- cached raw snapshots
- normalized features
- target status
- execution status
- audit trail

### Runtime Engine

The engine should:

- collect inputs
- build features
- call the BOX
- apply risk sizing
- schedule the market check
- execute approved bets

## Suggested BOX Contract

A future BOX should receive a normalized feature context and return a structured decision.

Example shape:

- input
  - race identity
  - racelist features
  - beforeinfo features
  - optional market snapshot
  - deadline context
- output
  - `decision`
  - `reasons`
- `missing_features`
- `required_markets`
- `bet_plan_template`
- `risk_profile_ref`
- `next_check_at`

Suggested decision states:

- `WAIT_DATA`
- `NO_GO`
- `GO_PENDING_MARKET`
- `GO_FOR_BET`

This allows a BOX to say:

- "structure is good, but beforeinfo is not ready yet"
- "structure is good, wait for odds"
- "all conditions are satisfied, place bet now"

## Recommended Loop Split

### 1. Trigger Loop

Purpose:

- identify candidate races in advance
- create target records for the day

Typical sources:

- race schedule
- shared BOX enablement
- pre-race candidate rules

### 2. Logic Loop

Purpose:

- fetch `beforeinfo` for all active targets
- store snapshots into DB
- build features
- ask each BOX for a structural decision

Main output:

- `GO_PENDING_MARKET` or `NO_GO`

### 3. Execution Loop

Purpose:

- run only in a short window before deadline
- fetch live `odds2t` and `odds3t`
- apply market constraints
- freeze final bet rows
- submit through Teleboat or log air bet

Main output:

- `GO_FOR_BET`
- `MARKET_REJECTED`
- `SUBMITTED`

### 4. Risk Sizing Layer

Purpose:

- convert precomputed `R` into final yen amount
- keep portfolio drawdown contribution closer across strategies

Recommended rule:

- the BOX does not compute `MAX DD` live
- `R` is precomputed from aligned backtest periods
- runtime only loads the chosen `R` table and applies it

Example sizing formula:

- `stake_yen = round_to_ticket_unit(base_r_yen * strategy_R * profile_multiplier)`

This allows the system to keep:

- structural judgment inside the BOX
- market judgment inside the execution window
- stake sizing inside the risk layer

## Suggested State Flow

One possible state model:

1. `imported`
2. `waiting_beforeinfo`
3. `feature_ready`
4. `go_pending_market`
5. `waiting_execution_window`
6. `market_checking`
7. `go_for_bet`
8. `market_rejected`
9. `submitted`

Operational terminal states:

- `expired`
- `assist_timeout`
- `error`

Optional sizing-related states:

- `risk_sized`
- `risk_blocked`

## Odds Handling Rule

Odds should not be treated as a settled DB fact for pre-bet judgment.
They should be checked at bet time.

That means:

- structural conditions can be judged before the final window
- price conditions must be judged inside the execution loop

For example, a strategy may be:

- structurally `GO_PENDING_MARKET`
- but finally rejected because `min_odds` is too low at `-60s`

## Why This Is Better Than DB-Led Selection

If the DB becomes the main selector, complex logic tends to scatter across:

- SQL
- ad-hoc scripts
- execution exceptions
- per-strategy patches

If the BOX remains the judge, then:

- the strategy stays explainable
- the runtime can support many rule shapes
- the same strategy can be replayed, audited, and executed with one contract

The same applies to stake sizing:

- `R` should be a declared runtime input
- not an ad-hoc manual amount edit hidden in UI or scripts

## Migration Direction

The safest migration path is:

1. keep current `live_trigger/` and `live_trigger_fresh_exec/` working
2. write the future BOX contract and state model first
3. build the next runtime as one root with separate loops
4. migrate `125`, `c2`, and future `4wind`-class logic onto that contract
5. retire duplicated execution paths after parity is confirmed

## Current Reading

At this point, the repo already has enough pieces to support this direction:

- candidate race acquisition exists
- beforeinfo fetch exists
- odds endpoints exist
- Teleboat execution exists
- audit and target DB state already exist in partial form
- `R` concept already exists at the repo level

So this is not blocked by missing data.
It is mainly a runtime architecture decision.

Related concept:

- [R_CONCEPT.md](/c:/CODEX_WORK/boat_clone/R_CONCEPT.md)
