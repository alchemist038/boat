# FROM I5 TO ME

`i5` の Codex は、返答をこのファイルに書いてください。

## 状態

- machine: i5
- status: done
- updated_at: 2026-03-14 14:23:13 +09:00
- branch: i5/20260314_odds_backfill_prep
- commit: dede684

## 結果

- summary:
  - `git pull` 相当の最新取り込みは `origin/main` まで確認済みで、現在は `origin/main` 最新の `dede684 Update i5 instruction for backfill preparation` を基点にしたブランチで repo を読めています
  - 作業に使うローカル clone は `C:\CODEX_WORK\boat_clone`
  - 2本並列で回す候補ディレクトリは `C:\CODEX_WORK\boat_a` と `C:\CODEX_WORK\boat_b`
  - `workspace_codex/coordination/LONGRUN_BACKFILL_RUNBOOK.md` は読めます
  - `2025-04-01..2026-03-05` の 2 分割は、運用の分かりやすさ優先で `2025-09-30 / 2025-10-01` で切る案を推奨します
  - 実行コマンド草案は下記のとおりです
  - `i5` が収集完了後の `ins14` へのコピー完了まで担当する運用は可能です
- touched_files:
  - `FROM_I5_TO_ME.md`
- checks:
  - `git fetch origin`
  - `git show origin/main:TO_I5_FROM_ME.md`
  - `git show origin/main:workspace_codex/coordination/LONGRUN_BACKFILL_RUNBOOK.md`
  - `git checkout -b i5/20260314_odds_backfill_prep origin/main`
  - `git status --short --branch`
  - `rg "db-path|skip-quality-report|resume-existing-days|skip-term-stats|collect-range" src README.md`
  - 現在ブランチはクリーンで、runbook と CLI オプションも確認済みです
- blocker:
  - まだ本番収集開始の指示はないため未実行です
  - `boat_a` / `boat_b` は未作成です
- next_step:
  - GO が出たら `C:\CODEX_WORK\boat_a` と `C:\CODEX_WORK\boat_b` を用意し、各ディレクトリで非重複期間の backfill を開始します
  - 開始時は `jobs/active/` にジョブファイルを作成し、停止時は same tree で resume します

## 実行コマンド草案

`boat_a` 用:

```powershell
.\.venv\Scripts\python -m boat_race_data collect-range `
  --start-date 20250401 `
  --end-date 20250930 `
  --db-path data/silver/boat_race_i5_a.duckdb `
  --sleep-seconds 0.5 `
  --refresh-every-days 1 `
  --resume-existing-days `
  --skip-term-stats `
  --skip-quality-report
```

`boat_b` 用:

```powershell
.\.venv\Scripts\python -m boat_race_data collect-range `
  --start-date 20251001 `
  --end-date 20260305 `
  --db-path data/silver/boat_race_i5_b.duckdb `
  --sleep-seconds 0.5 `
  --refresh-every-days 1 `
  --resume-existing-days `
  --skip-term-stats `
  --skip-quality-report
```
