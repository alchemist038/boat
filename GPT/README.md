# GPT Package

このフォルダは、戦略相談用にGPTへ渡す提出物をまとめる場所です。  
目的は「生データを見せること」ではなく、「仮説を出しやすい形に整えて渡すこと」です。

## 基本方針

- GPTには戦略仮説の提案をさせる
- 採用判断はローカルのバックテストで行う
- 期待値、見送り条件、資金管理を重視する
- マーチンゲール系は前提にしない

## 含めるもの

- `strategy_brief.md`
- `race_boat_features.csv`
- `market_results_joined.csv`
- `summary_stadium_lane.csv`
- `summary_class_lane.csv`
- `summary_weather_lane.csv`
- `summary_market_roi.csv`
- `racer_term_reference.csv`
- `prompt_ideal.md`

## 更新方法

例:

```powershell
.\.venv\Scripts\python -m boat_race_data export-gpt --start-date 2026-03-06 --end-date 2026-03-06 --output-dir GPT/output/latest
```

数か月分をまとめるなら:

```powershell
.\.venv\Scripts\python -m boat_race_data export-gpt --start-date 2025-12-01 --end-date 2026-03-10 --output-dir GPT/output/2025-12-01_2026-03-10
```

GPTの提案をローカルで検証して、返却用資料まで作る場合:

```powershell
.\.venv\Scripts\python -m boat_race_data backtest-strategies --start-date 2025-12-01 --end-date 2026-03-10 --output-dir GPT/output/2025-12-01_2026-03-10
```

## 実務上の使い方

1. 数か月分のデータを DuckDB に蓄積する
2. `export-gpt` で `GPT/output/<期間>/` を作る
3. `prompt_ideal.md` をベースに GPT に渡す
4. `backtest-strategies` で結果をまとめる
5. `prompt_after_backtest.md` を使って GPT に再度返す

## Backtest Output

`backtest-strategies` は、現在は単一戦略ではなく B 系バリアント比較を出します。

- `backtest_variant_specs.csv`
- `backtest_strategy_summary.csv`
- `backtest_skip_reason_summary.csv`
- `backtest_bets.csv`
- `backtest_race_decisions.csv`
- `backtest_report.md`
- `prompt_after_backtest.md`
