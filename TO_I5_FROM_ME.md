# TO I5 FROM ME

`i5` の Codex は、まずこのファイルだけ読んでください。

## 状態

- machine: i5
- from: me
- status: go
- updated_at: 2026-03-14 15:05 JST
- priority: high

## 今回の依頼

過去分の odds backfill を本番開始してください。

`ins14` は現在値と最終統合を担当します。`i5` は過去分だけ担当してください。

対象期間はこの 2 本です。

1. `boat_a`: `2025-04-01..2025-09-30`
2. `boat_b`: `2025-10-01..2026-03-05`

使う repo はこれです。

- `C:\CODEX_WORK\boat_clone`

この 1 clone の中で、worker root を 2 本に分けてください。

- `work\boat_a`
- `work\boat_b`

つまり、「1 clone + 2 worker roots」で進めてください。

`boat_a` で実行:

```powershell
.\.venv\Scripts\python -m boat_race_data collect-range `
  --start-date 20250401 `
  --end-date 20250930 `
  --raw-root work\boat_a\raw `
  --bronze-root work\boat_a\bronze `
  --db-path work\boat_a\silver\boat_race.duckdb `
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
  --raw-root work\boat_b\raw `
  --bronze-root work\boat_b\bronze `
  --db-path work\boat_b\silver\boat_race.duckdb `
  --sleep-seconds 0.5 `
  --refresh-every-days 1 `
  --resume-existing-days `
  --skip-term-stats `
  --skip-quality-report
```

これは `GO` 指示です。準備返答ではなく、実行開始してください。

中断時は、同じディレクトリで同じコマンドをもう一度実行してください。各 `work\boat_*\bronze` が再開用の状態を持ちます。

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
