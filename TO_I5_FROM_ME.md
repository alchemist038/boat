# TO I5 FROM ME

`i5` の Codex は、このファイルを現時点の連絡メモとして読んでください。

## Context
- machine: i5
- from: me
- status: info
- updated_at: 2026-03-14 22:25 JST
- priority: medium

## Current Note

いま `i5` はアラートシステム作業を優先してよいです。
このメモは「125 の整理が完了したこと」を共有するための情報更新です。
現在の作業を中断する必要はありません。

## Folder Intent

今回から、戦略ごとに見る場所をそろえました。

- project notes:
  - `projects/125/`
  - `projects/c2/`
- human-readable strategy reports:
  - `reports/strategies/125/`
  - `reports/strategies/c2/`
- raw analysis outputs:
  - `workspace_codex/analysis/125/`
  - `workspace_codex/analysis/c2/`
  - `workspace_codex/analysis/combined/`

つまり、
- `projects/...` = 案件ノート
- `reports/strategies/...` = 人が読む要約
- `workspace_codex/analysis/...` = 生の分析出力
です。

## 125 Status

`125` は、いったん完成候補として整理済みです。

Current main interpretation:
- core is `lane1=B1`
- `lane6=B2` is a valid remove condition
- `lane5=B2` is clearly bad for `1-2-5`
- `exgap<=0.02` strengthens the Suminoe-style setup

Current adopted candidates:
- main single-stadium logic:
  - Suminoe `1-2-5`
- broad candidate:
  - Suminoe + Naruto + Ashiya + Edogawa

Canonical files:
- `projects/125/status_notebooklm_20260313.txt`
- `reports/strategies/125/summary_20260314.md`
- `reports/strategies/125/review_20260314.md`
- `projects/125/README.md`

## How To Confirm The Logic

If you want to verify the current `125` logic, use this order:

1. Read `projects/125/README.md`
2. Read `reports/strategies/125/summary_20260314.md`
3. Confirm the adopted conditions and BT/FW numbers there
4. If you need source evidence, open these folders under `workspace_codex/analysis/125/`

Main evidence folders:
- `125line_relative_rank_probe_20260314`
- `125line_lane1_class_split_20260314`
- `top5_lane1_b1_stadium_deep_20260314`
- `all_stadium_lane1_b1_theory_scan_20260314`
- `four_stadium_monthly_20260314`

## Requested Response

作業の切れ目でよいので、次の3点だけ `FROM_I5_TO_ME.md` に短く書いてください。

- 新しいフォルダ構成を読めたか
- `125` の完成状態を理解できたか
- `125` の確認手順を理解できたか

## Codex Action

1. `git pull`
2. このファイルを読む
3. 必要なら `projects/125/README.md` と `reports/strategies/125/summary_20260314.md` を読む
4. 現在のアラートシステム作業は優先して継続
5. 区切りのよいタイミングで `FROM_I5_TO_ME.md` に短く返答
