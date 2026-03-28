# High-Hit Candidate 1 Outer-Pressure Review 2026-03-29

## Source

- source package:
  - [README.md](/c:/CODEX_WORK/boat_clone/GPT/output/2023-03-11_2023-09-10_high_hit_discovery/README.md)
- source idea:
  - Gemini high-hit candidate 1
  - strong lane-1 trust structure
  - original exacta buy:
    - `1-2`
    - `1-3`

## Original Candidate Shape

Initial zero-base read used:

- `lane1_national_win_rate >= 6.0`
- `best_exhibition_lane = 1`
- `lane1_win_rate_rank = 1`

Initial tickets:

- exacta:
  - `1-2`
  - `1-3`
- trifecta:
  - `1-2-3`
  - `1-3-2`
  - `1-2-4`
  - `1-4-2`

## First Broad Recheck

### `2023-03-11 .. 2023-12-31`

- exacta `1-2 / 1-3`:
  - `3,235 races`
  - `1,646 hits`
  - `ROI 82.78%`
- trifecta 4-point:
  - `3,235 races`
  - `1,057 hits`
  - `ROI 78.83%`

Read:

- high-hit structure is real
- but the broad candidate is too low-return to promote

## Exacta Slice Direction

Within the exacta branch, the useful structural observation was:

- when lane 5 is strong and lane 6 is not equally strong, the outside pressure may suppress lanes 3/4 enough to let `1-2` settle more often

Working refinement:

- keep the original lane-1 trust conditions
- add:
  - `lane5_class = A1`
  - `lane6_class != A1`
- narrow the ticket to:
  - `1-2`

### `2023-03-11 .. 2023-12-31`

- `306 races`
- hit rate `30.72%`
- `ROI 103.46%`

Read:

- this was the cleanest version of the idea
- it justified a cross-year recheck

## Cross-Year Recheck

### `2024-01-01 .. 2024-12-31`

Condition:

- `lane1_national_win_rate >= 6.0`
- `best_exhibition_lane = 1`
- `lane1_win_rate_rank = 1`
- `lane5_class = A1`
- `lane6_class != A1`
- buy `1-2`

Result:

- `366 bets`
- `93 hits`
- `ROI 88.28%`

Half split:

- `2024_h1`: `163 bets`, `ROI 96.26%`
- `2024_h2`: `203 bets`, `ROI 81.87%`

### `2025-01-01 .. 2025-12-31`

Same condition, official-settle proxy:

- `351 bets`
- `95 hits`
- `ROI 88.52%`

Half split:

- `2025_h1`: `185 bets`, `ROI 94.76%`
- `2025_h2`: `166 bets`, `ROI 81.57%`

Cross-year read:

- the branch does not keep the 2023 edge
- shape is too weak for promotion

## Structural Slices Tried

### 2024 lane 3 / lane 4 class slice

Single-axis reads:

- `lane3 = A1`: `100 bets`, `ROI 100.30%`
- `lane4 = B1`: `155 bets`, `ROI 99.55%`
- `lane4 = A2`: `126 bets`, `ROI 71.11%`

Pair reads:

- `lane3 = A1`, `lane4 = B1`: `31 bets`, `ROI 118.71%`
- `lane3 = A1`, `lane4 = A1`: `32 bets`, `ROI 115.00%`
- `lane3 = A2`, `lane4 = A1`: `28 bets`, `ROI 107.50%`

Read:

- `lane3 = A1` helps
- `lane4 = A2` is weak
- but sample stays too small to rescue the branch

### 2024 racer-index slice

On the index-covered 2024 subset:

- baseline subset:
  - `359 bets`
  - `93 hits`
  - `ROI 90.00%`

`pred6_lane` check:

- `pred6_lane = 4`: `45 bets`, `ROI 69.11%`
- `pred6_lane = 6`: `253 bets`, `ROI 97.47%`

`pred1_lane` check:

- all baseline subset races were already `pred1_lane = 1`
- so `pred1` added no extra filtering value

Read:

- `pred6_lane = 4` does not help this branch
- `pred1` is redundant because the branch already hard-locks a lane-1 trust shape

### 2025 odds cut (`2025-04-01 .. 2025-12-31`)

Shared `odds_2t` coverage begins on `2025-04-01`, so practical odds cuts were checked only on that subperiod.

Base branch over odds-covered range:

- `268 bets`
- `63 hits`
- `ROI 79.25%`

Lower-bound cuts on quoted `1-2` odds:

- `odds >= 2.0`: `245 bets`, `ROI 82.41%`
- `odds >= 3.0`: `164 bets`, `ROI 87.26%`
- `odds >= 4.0`: `104 bets`, `ROI 82.21%`

Bucket read:

- `0-2`: `ROI 45.65%`
- `3-4`: `ROI 96.00%`
- `5-10`: `ROI 113.33%`
- `10+`: `15 bets`, `0 hits`

Read:

- cutting only the very lowest odds helps a little
- `odds >= 3.0` is the best light cut among the quick checks
- but the branch is still not close to promotion-ready

## Final Read

Preserve this as a closed exploratory note, not as a candidate to keep pushing now.

Current interpretation:

- the most coherent sub-idea was:
  - `lane5_class = A1`
  - `lane6_class != A1`
  - buy `1-2`
- but it fails the cross-year stability check:
  - `2023`: `ROI 103.46%`
  - `2024`: `ROI 88.28%`
  - `2025`: `ROI 88.52%`
- racer-index overlays did not rescue it:
  - `pred6_lane = 4` worsened it
  - `pred1` was redundant
- light odds cuts also did not rescue it enough

Decision:

- record the logic and slices
- stop further work on this branch for now
- no bet-line promotion
- no runtime / shared-box adoption
