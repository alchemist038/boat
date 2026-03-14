# FROM I5 TO ME

`i5` の Codex は、返答をこのファイルに書いてください。

## 状態

- machine: i5
- status: done
- updated_at: 2026-03-14 14:41:55 +09:00
- branch: main
- commit: 7afa129

## 結果

- summary:
  - `git pull --ff-only origin main` 後、repo は正常です。現在の先頭は `7afa129 Add isolated worker roots for range collection` です
  - 作業に使うローカル clone は `C:\CODEX_WORK\boat_clone`
  - 2本並列で回す作業ディレクトリは、今回追加された isolated worker roots に合わせて `C:\CODEX_WORK\boat_clone\work\boat_a` と `C:\CODEX_WORK\boat_clone\work\boat_b` を使う案に更新します
  - `workspace_codex/coordination/LONGRUN_BACKFILL_RUNBOOK.md` は読めます
  - `2025-04-01..2026-03-05` の 2 分割は、運用の分かりやすさ優先で `2025-09-30 / 2025-10-01` で切る案を推奨します
  - 実行コマンド草案は下記のとおりです
  - `i5` が収集完了後の `ins14` へのコピー完了まで担当する運用は可能です
- touched_files:
  - `FROM_I5_TO_ME.md`
- checks:
  - `git pull --ff-only origin main`
  - `git status --short --branch`
  - `rg "root-dir|db-path|skip-quality-report|resume-existing-days|skip-term-stats|collect-range" README.md src tests`
  - 現在ブランチはクリーンで、runbook、README、CLI オプション追加を確認済みです
- blocker:
  - まだ本番収集開始の指示はないため未実行です
  - `work\boat_a` / `work\boat_b` は未作成です
- next_step:
  - GO が出たら `C:\CODEX_WORK\boat_clone\work\boat_a` と `C:\CODEX_WORK\boat_clone\work\boat_b` を使い、各 worker root で非重複期間の backfill を開始します
  - 開始時は `jobs/active/` にジョブファイルを作成し、停止時は same tree で resume します

## 実行コマンド草案

`boat_a` 用:

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

`boat_b` 用:

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
