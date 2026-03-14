# TO I5 FROM ME

`i5` の Codex は、まずこのファイルだけ読んでください。

## 状態

- machine: i5
- from: me
- status: requested
- updated_at: 2026-03-14 14:45 JST
- priority: high

## 今回の依頼

過去分の odds backfill を本番開始してください。

`ins14` は現在値と最終統合を担当します。`i5` は過去分だけ担当してください。

対象期間はこの 2 本です。

1. `boat_a`: `2025-04-01..2025-09-30`
2. `boat_b`: `2025-10-01..2026-03-05`

使うローカル worker はこれです。

- `C:\CODEX_WORK\boat_a`
- `C:\CODEX_WORK\boat_b`

それぞれ repo の最新を `git pull` してから、同じ clone 内にある `work\raw` / `work\bronze` / `work\silver` を使ってください。

`boat_a` で実行:

```powershell
.\.venv\Scripts\python -m boat_race_data collect-range `
  --start-date 20250401 `
  --end-date 20250930 `
  --raw-root work\raw `
  --bronze-root work\bronze `
  --db-path work\silver\boat_race_i5_a.duckdb `
  --sleep-seconds 0.5 `
  --refresh-every-days 1 `
  --resume-existing-days `
  --skip-term-stats `
  --skip-quality-report
```

`boat_b` で実行:

```powershell
.\.venv\Scripts\python -m boat_race_data collect-range `
  --start-date 20251001 `
  --end-date 20260305 `
  --raw-root work\raw `
  --bronze-root work\bronze `
  --db-path work\silver\boat_race_i5_b.duckdb `
  --sleep-seconds 0.5 `
  --refresh-every-days 1 `
  --resume-existing-days `
  --skip-term-stats `
  --skip-quality-report
```

中断時は、同じディレクトリで同じコマンドをもう一度実行してください。`work\bronze` が再開用の状態を持ちます。

収集完了後は、各 worker の対応期間について、少なくとも次を `ins14` 側の対応フォルダへコピー完了まで担当してください。

- `work\raw\odds_2t\...`
- `work\raw\odds_3t\...`
- `work\bronze\odds_2t\...`
- `work\bronze\odds_3t\...`

現在日付側の再収集や、`term_stats` の更新はしないでください。

## 参考情報

- files: `CODEX_START_HERE.md`, `TO_I5_FROM_ME.md`, `FROM_I5_TO_ME.md`
- commands: `git pull`, `git branch --show-current`, `git log -1 --oneline`
- constraints: 現在値は触らない。各 worker は自分の `work\...` 配下だけを使う
- output target: `FROM_I5_TO_ME.md`

## Codex の動き

1. `git pull` を確認する
2. `今回の依頼` が `NONE` なら、依頼なしとして返答する
3. 依頼があれば実行を開始する
4. 開始時、停止時、中断時、コピー完了時に `FROM_I5_TO_ME.md` を更新する
5. 返答の更新を commit / push する
