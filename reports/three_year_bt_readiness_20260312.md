# 3-Year BT Readiness Report

更新日: `2026-03-12`

## 1. 目的

BOAT RACE公式ベースのローカル研究DBを、3年規模の確定払戻ベースBTに使える状態まで拡張できたかを確認する。

このレポートでは、次を明確にする。

- どこまで収集できたか
- どのテーブルが3年BTに使えるか
- 欠損率はどの程度か
- 今すぐ回せるBT範囲はどこか

## 2. 実行ログ

### 収集コマンド

```powershell
.\.venv\Scripts\python -m boat_race_data collect-mbrace-range `
  --start-date 20230311 `
  --end-date 20250414 `
  --sleep-seconds 0.5 `
  --refresh-every-days 60 `
  --resume-existing-days `
  --skip-term-stats
```

### 収集結果の要点

- 既存の `2025-04-15` から `2026-03-10` に接続
- mbrace ベースで `2023-03-11` から `2026-03-10` を連結
- 追加収集完了後の総件数:
  - `races=168036`
  - `entries=1008216`
  - `results=165771`
  - `beforeinfo_entries=980531`
  - `race_meta=168036`

## 3. 確認SQL

### 日付範囲

```sql
select min(race_date), max(race_date), count(distinct race_date)
from races;
```

### テーブル件数

```sql
select count(*) from races;
select count(*) from entries;
select count(*) from results;
select count(*) from beforeinfo_entries;
select count(*) from race_meta;
select count(*) from odds_2t;
select count(*) from odds_3t;
```

### 年別件数

```sql
select year(race_date) as yr, count(*)
from races
group by 1
order by 1;
```

### grade別件数

```sql
select grade, count(*)
from race_meta
group by 1
order by 1;
```

### stadium別件数

```sql
select stadium_code, max(stadium_name), count(*) as races
from races
group by 1
order by 1;
```

### results 欠損率

```sql
select
  ((select count(*) from races) - (select count(*) from results)) as missing_results,
  ((select count(*) from races) - (select count(*) from results)) * 100.0
    / (select count(*) from races) as missing_rate_pct;
```

### beforeinfo_entries 欠損率

```sql
select
  ((select count(*) from entries) - (select count(*) from beforeinfo_entries)) as missing_beforeinfo,
  ((select count(*) from entries) - (select count(*) from beforeinfo_entries)) * 100.0
    / (select count(*) from entries) as missing_rate_pct;
```

### race_meta 欠損有無

```sql
select count(*)
from races r
left join race_meta rm using (race_id)
where rm.race_id is null;
```

## 4. DuckDB 更新後サマリ

### race_date 範囲

- `min(race_date)=2023-03-11`
- `max(race_date)=2026-03-10`
- `count(distinct race_date)=1096`

### テーブル件数

- `races=168036`
- `entries=1008216`
- `results=165771`
- `beforeinfo_entries=980531`
- `race_meta=168036`
- `odds_2t=169425`
- `odds_3t=1440`
- `racer_stats_term=1625`

### grade別件数

- `一般=165444`
- `G1=2244`
- `SG=348`

### 年別件数

- `2023=45096`
- `2024=56064`
- `2025=55908`
- `2026=10968`

### stadium別件数

- `01 桐生=6984`
- `02 戸田=7164`
- `03 江戸川=6936`
- `04 平和島=6468`
- `05 多摩川=6876`
- `06 浜名湖=7368`
- `07 蒲郡=7296`
- `08 常滑=7224`
- `09 津=7020`
- `10 三国=7068`
- `11 びわこ=6816`
- `12 住之江=7164`
- `13 尼崎=6588`
- `14 鳴門=6648`
- `15 丸亀=7008`
- `16 児島=6768`
- `17 宮島=7260`
- `18 徳山=6936`
- `19 下関=7008`
- `20 若松=7260`
- `21 芦屋=6996`
- `22 福岡=6972`
- `23 唐津=6936`
- `24 大村=7272`

## 5. 欠損確認

### 全体

- `results が races より 2265件少ない`
- `results 欠損率 = 1.3479%`
- `beforeinfo_entries が entries より 27685件少ない`
- `beforeinfo_entries 欠損率 = 2.7459%`
- `race_meta 欠損 = 0`

### 年別

- `2023`
  - `results_missing_rate_pct=1.1841`
  - `beforeinfo_missing_rate_pct=2.6292`

- `2024`
  - `results_missing_rate_pct=1.2896`
  - `beforeinfo_missing_rate_pct=2.7017`

- `2025`
  - `results_missing_rate_pct=1.3755`
  - `beforeinfo_missing_rate_pct=2.7107`

- `2026`
  - `results_missing_rate_pct=2.1791`
  - `beforeinfo_missing_rate_pct=3.6318`

## 6. 3年BT可否レポート

### 可

次のテーブルを使う **確定払戻ベースBT** は、3年範囲で実施可能。

- `races`
- `entries`
- `results`
- `beforeinfo_entries`
- `race_meta`

信頼できるBT範囲:

- `2023-03-11` から `2026-03-10`

理由:

- `race_meta` 欠損が `0`
- `results` 欠損率が約 `1.35%`
- `beforeinfo_entries` 欠損率が約 `2.75%`
- mbrace 日次LZHで再取得可能

### 不可 / 未整備

次の用途はまだ3年では未整備。

- `odds_3t` を前提にした期待値BT
- `odds_2t` を全面に使う長期オッズBT

理由:

- `odds_2t=169425`
- `odds_3t=1440`
- レース総数 `168036` と比較すると、オッズ系は3年フルで揃っていない

## 7. 3年BTに使える最小ロジック確認

確認用の最小ロジック:

- `SG/G1`
- `4日目ナイター場(01,07,12,15,16,20,24)` または `6日目`
- `1号艇=A1/A2`
- `2連単 1-3` の1点

3年フルレンジ結果:

- `played_races=315`
- `bet_count=315`
- `hit_count=76`
- `ROI=94.03%`
- `max_drawdown_yen=4380`
- `max_losing_streak=20`

解釈:

- 3年BTは実行可能
- ただし、330日範囲では良かったロジックでも、3年では優位性を維持しないことが確認できた
- これはBT母集団が機能していることを示す

## 8. 推奨BT対象期間

### すぐ回せる最大範囲

- `2023-03-11` から `2026-03-10`

### 年比較しやすい範囲

- `2024-01-01` から `2025-12-31`

理由:

- 2023年と2026年は部分年
- 完全年で比較したい場合は 2024-2025 が扱いやすい

## 9. 結論

1. mbrace ベースで約3年分の固定払戻BT母集団は構築できた
2. `results / race_meta / entries / beforeinfo_entries` は長期BTに使える
3. `odds_2t / odds_3t` は未整備なので期待値BTにはまだ不十分
4. 次に回すBT期間は、最大なら `2023-03-11` から `2026-03-10`、年比較なら `2024-01-01` から `2025-12-31`
