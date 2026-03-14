# Codex Workspace

このフォルダは Codex の作業用ワークスペースです。

目的:

- root や `GPT/output` を一時ファイルで散らかさない
- 試作物と正式成果物を分ける
- 途中計算、SQL、検算CSV、作業ログをまとめる

## フォルダ構成

- `scratch/`
  - 一時SQL、一時CSV、一発検算ファイル
- `analysis/`
  - 進行中の分析ごとの作業ディレクトリ
- `reports/`
  - ユーザー向けに整形する前の中間レポート
- `archive/`
  - 使い終わった中間物の退避先
- `logs/`
  - Codex専用ログ
- `templates/`
  - 再利用する雛形
- `coordination/`
  - `ins14` / `i5` 間の task inbox と handoff

## 運用ルール

1. 一時ファイルはまず `workspace_codex` に置く
2. 採用した成果物だけを `GPT/output` へ昇格する
3. root 直下には運用ファイル以外を置かない
4. 手動サンプルは `docs/manual_debug_samples/` に退避する

## 使い分け

- `workspace_codex`: 試作・検算・途中作業
- `GPT/output`: 採用済みの成果物
- `docs`: 長期保存したい説明資料

## Multi-Machine Rule

- `workspace_codex/coordination/inbox/ins14/`: tasks for `ins14`
- `workspace_codex/coordination/inbox/i5/`: tasks for `i5`
- `workspace_codex/coordination/handoffs/`: completion or blocked notes
- `workspace_codex/coordination/done/`: completed task files

Use one task per markdown file. Keep cross-machine instructions out of chat history
alone and commit them into the repo so the other Codex session can read them after
`git pull`.
