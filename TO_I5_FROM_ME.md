# TO I5 FROM ME

`i5` の Codex は、まずこのファイルだけ読んでください。

## 状態

- machine: i5
- from: me
- status: requested
- updated_at: 2026-03-14 JST
- priority: medium

## 今回の依頼

オッズ backfill の実行準備をしてください。

まだ長時間の収集は開始しないでください。

まず以下を確認して、結果を `FROM_I5_TO_ME.md` に書いてください。

1. `git pull` 後に repo が正常か
2. 作業に使うローカル clone の場所
3. 2本並列で回すなら、どの2ディレクトリを使うか
4. `workspace_codex/coordination/LONGRUN_BACKFILL_RUNBOOK.md` を読めるか
5. `2025-04-01..2026-03-05` の odds backfill を 2 分割するなら、どこで切るのがよいか
6. 実行コマンドの草案
7. 収集完了後に `ins14` へコピー完了まで担当できるか

必要なら、`i5` 側の都合に合わせて期間分割を少し修正してよいです。

## 参考情報

- files: `CODEX_START_HERE.md`, `TO_I5_FROM_ME.md`, `FROM_I5_TO_ME.md`, `workspace_codex/coordination/LONGRUN_BACKFILL_RUNBOOK.md`
- commands: `git pull`, `git branch --show-current`, `git log -1 --oneline`
- constraints: まだ本番収集は開始しない。まず準備内容だけ返答する
- output target: `FROM_I5_TO_ME.md`

## Codex の動き

1. `git pull` を確認する
2. `今回の依頼` が `NONE` なら、依頼なしとして返答する
3. 依頼があれば実行する
4. 完了または中断時に `FROM_I5_TO_ME.md` を更新する
