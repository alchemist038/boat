# H-A Forward / BT Alignment Check

- generated_at: 2026-04-23 23:55 JST
- scope: `h_a_final_day_cut_v1`
- forward_period: `2026-03-28..2026-04-22`
- forward_db: `C:\CODEX_WORK\boat_clone\live_trigger_cli\data\system.db`
- bt_db: `\\038INS\boat\data\silver\boat_race.duckdb`
- local_beforeinfo_raw: `C:\CODEX_WORK\boat_clone\live_trigger_cli\raw\beforeinfo`

## Summary

H-Aの実フォワードとBT条件を同一期間で照合した結果、買われた59件はすべてBT条件と一致した。

差分は2件で、どちらもロジック差ではなく運用差。

| source | candidates | hit | hit_rate | return | flat_roi |
| --- | ---: | ---: | ---: | ---: | ---: |
| forward submitted | 59 | 1 | 1.69% | 1,060 yen | 17.97% |
| repaired DuckDB BT | 61 | 1 | 1.64% | 1,060 yen | 17.38% |

## Differences

| race_id | date | reason | BT result |
| --- | --- | --- | --- |
| `202604211807` | 2026-04-21 | forward target expired: `window closed at 11:17:00` | miss |
| `202604221405` | 2026-04-22 | forward execution failed: insufficient funds | miss |

The runtime condition and BT condition are aligned:

- lane1 start exhibition rank `<= 3`
- lane4 start exhibition ahead of lane1 by `>= 0.05`
- non-final day
- exacta `4-1`

Rank tie handling was also checked. Runtime ranks equal ST values together, while the original BT SQL breaks ties by lane. In this forward period this produced no H-A candidate difference.

## DB Repair

The shared DuckDB had many forward-period `beforeinfo_entries.start_exhibition_st` gaps. A backup was created before repair:

- `\\038INS\boat\data\silver\boat_race.duckdb.bak_20260423_ha_beforeinfo_repair`

Repaired by reparsing merged local raw beforeinfo folders (`YYYY-MM-DD` and `YYYYMMDD`) and replacing only race_ids that had local raw:

- parsed races: `2964`
- parsed rows: `17784`
- target ST non-null before repair: `4268`
- target ST non-null after repair: `17675`
- duplicate `(race_id, lane)` rows after repair: `0`

## Interpretation

Current H-A forward weakness is not explained by a forward/BT implementation mismatch. The same slice is weak in BT when replayed against repaired same-period data.

Historical H-A BT remains much stronger:

- `2025-04-01..2026-03-09`: 931 races / 99 hits / 10.63% hit rate / 209.86% ROI
- `2026_ytd` reference: 248 races / 26 hits / 10.48% hit rate / 160.16% ROI

So the current forward window is a materially bad slice, not a confirmed logic drift.
