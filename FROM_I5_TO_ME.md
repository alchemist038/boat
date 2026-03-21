# FROM I5 TO ME

`ins14` へ Git を使わずに引き継ぐための現状メモです。データの正は `\\038INS\boat\data` とし、コード変更は必要になったときだけ別扱いにします。

## 現状

- handoff updated at: `2026-03-21 19:03:05 +09:00`
- `i5` のオッズ収集 worker は停止済み
- 正規ルート: `\\038INS\boat\data`
- 共有先の構成: `raw/`, `bronze/`, `silver/`
- 正規 DuckDB: `\\038INS\boat\data\silver\boat_race.duckdb`
- 共有 bronze から `refresh-silver` を実行できることは確認済み
- `boat_a` / `boat_b` は一時ワークツリーで、整理・退避後に削除する前提

## 共有DBの目安

- `races`: 168,528 rows, `2023-03-11..2026-03-13`
- `entries`: 1,011,168 rows, `2023-03-11..2026-03-13`
- `odds_2t`: 1,123,875 rows, `2025-04-01..2026-03-13`
- `odds_3t`: 1,467,840 rows, `2025-04-01..2026-03-13`
- `results`: 166,268 rows, `2023-03-11..2026-03-13`
- `beforeinfo_entries`: 985,009 rows, `2023-03-11..2026-03-13`
- `race_meta`: 168,528 rows, `2023-03-11..2026-03-13`

## copy_inbox にある i5 オッズ bundle

- 既存 bundle:
  - `\\038INS\boat\copy_inbox\from_i5\20260319_odds_backfill\`
  - `bronze/odds_2t`: `160` files, `20250401..20250614` and `20251001..20251224`
  - `bronze/odds_3t`: `160` files, `20250401..20250614` and `20251001..20251224`
- 今回追加した delta bundle:
  - `\\038INS\boat\copy_inbox\from_i5\20260321_odds_backfill_delta_stop\`
  - `bronze/odds_2t`: `89` files, `20250615..20250930`
  - `bronze/odds_3t`: `89` files, `20250615..20250930`
  - `raw/odds_2t`, `raw/odds_3t`: empty

## worker 停止時点の進捗

- `boat_a`
  - command range: `20250608..20250908`
  - completed through: `20250820`
  - next day at stop time: `20250821`
  - remaining days in that worker range: `19`
- `boat_b`
  - command range: `20250909..20251210`
  - completed through: `20251207`
  - next day at stop time: `20251208`
  - remaining days in that worker range: `3`

## 重要メモ

- local gap worker は各日収集後に `data/bronze/racer_stats_term/*.csv` 不在で DuckDB refresh error を出していた
- ただし error は bronze odds CSV の保存後に起きている
- そのため、信用すべき成果物は `boat_a/data/bronze/odds_2t`, `boat_a/data/bronze/odds_3t`, `boat_b/data/bronze/odds_2t`, `boat_b/data/bronze/odds_3t` と、copy 済み bundle 側の CSV
- `boat_a` / `boat_b` の gap DuckDB は正本として扱わない

## ins14 での引継ぎ手順

1. `\\038INS\boat\copy_inbox\from_i5\20260319_odds_backfill\` と `\\038INS\boat\copy_inbox\from_i5\20260321_odds_backfill_delta_stop\` の両方を確認する。
2. 2つの bundle の `bronze/odds_2t` と `bronze/odds_3t` を `\\038INS\boat\data\bronze\odds_2t` と `\\038INS\boat\data\bronze\odds_3t` へ取り込む。
3. 同日ファイルがあれば overwrite してよい。
4. `BOAT_DATA_ROOT="\\038INS\boat\data"` を設定して `refresh-silver` を実行する。
5. 再構築後、`odds_2t` / `odds_3t` の件数と日付レンジを確認する。
6. 必要なら不足分 `20250821..20250908` と `20251208..20251210` を `ins14` 側で回収する。

## 実行例

```powershell
$env:BOAT_DATA_ROOT="\\038INS\boat\data"
python -m boat_race_data refresh-silver
```
