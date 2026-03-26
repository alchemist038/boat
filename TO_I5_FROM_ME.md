# TO I5 FROM ME

`i5` 側の Codex に渡す、現時点の handoff / delta メモです。
bootstrap はこの 1 枚だけに頼らず、まず `I5_START.md` を読んでください。

## Context

- machine: i5
- from: me
- status: active
- updated_at: 2026-03-26 21:40 JST
- priority: high

## First Read Order

最初に次の順で読んでください。

1. `I5_START.md`
2. `ROOT_DOC_MAP.md`
3. `OPERATING_MODEL.md`

その後、作業ごとに分岐してください。

- DB / gap recovery:
  - `DB_STATUS.md`
  - `FROM_INS14_TO_ME.md`
- main bet line / operation:
  - `BET_PROJECT_STATUS.md`
  - `live_trigger_cli/README.md`
- logic / racer work:
  - `LOGIC_STATUS.md`
  - `RACER_INDEX_STATUS.md`

## Current Fixed Rules

以下は当面固定です。

- canonical shared data root:
  - `\\038INS\boat\data`
- canonical shared DB:
  - `\\038INS\boat\data\silver\boat_race.duckdb`
- main bet line:
  - `live_trigger_cli`
- logic source of truth:
  - `live_trigger/boxes/`
  - `live_trigger/shared_contract.py`
  - `live_trigger/auto_system/app/core/bets.py`
- logic substrate:
  - `racer_index`

runtime state は source として扱わないでください。
特に `live_trigger_cli/data/`, `live_trigger_cli/raw/`, `*.db`, `*.log`, `*.pid` を share と丸ごと混ぜないでください。

## Machine Split

`i5` の主担当:

- historical DB recovery
- isolated odds-gap collection in local worker trees
- `live_trigger_cli` construction and forward operation
- execution-line UX / notification / operator assist

`ins14` の主担当:

- current and recent collection
- shared bronze import
- final shared `refresh-silver`
- shared DB integration
- logic scan
- racer-index work

## Main Forward Set

現行の主戦ロジックは次の 3 本です。

- `4wind_base_415`
- `c2_provisional_v1`
- `125_broad_four_stadium`

補足:

- `4wind` は shared `live_trigger/boxes/4wind/` に昇格済み
- `c2` は `women6/title proxy + final day cut + B2 cut`
- `125` は broad four stadium 版を主戦に採用

## Current i5 Actionables

## 2026-03-26 Delta

本日の主な進展は `live_trigger_cli` 主系の安定化、`H-A` の shared 候補化、`H-B` の exploratory review です。

### A. Main Bet Line / Operation

- `live_trigger_cli` は引き続き main bet line です。
- `C2` に `racer_index pred1 != lane1` overlay を導入済みです。
  - watchlist-stage で事前除外
  - evaluate-stage にも fallback check を残しています
- Teleboat の `三国` クリック遮蔽エラー対策を入れています。
  - `headerContainer / newsoverviewInfo` を避けて場カードを選ぶ再試行付き
- `auto-loop` は「落ちる」より、`sync_watchlists` が重くて visible console が長時間止まって見えるのが主因と判断しています。
  - 重複 racelist fetch/parse を削減
  - `sync/evaluate/execute` phase timing を `auto_run.log` に追加
  - `sync_interval_seconds = 300` を導入
  - 通常周回は `evaluate/execute` 中心、`sync` は数分おき
- 次の broad-scan logic 追加先として、別系統の最小箱を切りました。
  - `live_trigger_cli_split/`
  - `sync_loop` と `bet_loop` を分離
  - ただし shared logic / shared bets はそのまま再利用
  - current main line は引き続き `live_trigger_cli`

### B. H-A

- `H-A` は shared candidate として実装済みです。
  - `live_trigger/boxes/h_a/profiles/final_day_cut_v1.json`
  - 既定は `enabled=false`
- ロジック:
  - `exacta 4-1`
  - `lane1_st_top3`
  - `lane4_ahead_lane1_005`
  - `final day cut`
- 年比較と主戦3本重ねのメモを追加済みです。
  - `reports/strategies/zero_base_period_2025-03-11_to_2025-06-16_20260324/h_a_yearly_comparison_2024_2026ytd_20260325.md`
  - `reports/strategies/combined/h_a_vs_main_forward_trio_2025-04-01_to_2026-03-09_20260326/README.md`
- 現時点の読み:
  - 通年でまだ正
  - ただし DD 改善はまだ継続 review 対象
  - `final day cut` は採用寄り
  - `lane4 != B1` は強すぎて 2025 のうまみを削る

### C. H-B

- `H-B` はまだ `検討前` の exploratory logic です。実装には進めていません。
- まず `2025-01-01 .. 2025-06-30` で official-settle proxy を確認しました。
  - baseline: `442 bets / ROI 187.04% / profit +38,470円 / max DD -11,800円`
- `racer_index pred1 = 4` overlay は不採用寄りです。
  - `43 bets / ROI 64.65% / profit -1,520円`
- `pred6` side を見た結果、最初の実務候補は
  - `exclude pred6_lane = 2`
  です。
  - `398 bets / ROI 205.40% / profit +41,950円 / max DD -11,300円`
- つまり `H-B` の next review 順は:
  1. `pred6_lane != 2`
  2. `final day cut`
  3. その交差

### D. Docs / Ownership

- `I5_START.md / INS14_START.md / OPERATING_MODEL.md / LOGIC_STATUS.md / RACER_INDEX_STATUS.md` の導線は整備済みです。
- `4wind` は shared `live_trigger/boxes/4wind/` に昇格済みです。
- `racer_index` は logic substrate として位置づけ直しています。

### 1. DB / Gap Recovery

`i5` では引き続き historical 側の gap 回収を担当してください。
shared canonical DB に直接ぶつける前に、local worker tree で raw / bronze / silver を確認する前提です。

読む場所:

- `DB_STATUS.md`
- `workspace_codex/coordination/LONGRUN_BACKFILL_RUNBOOK.md`
- `FROM_INS14_TO_ME.md`

### 2. live_trigger_cli

main bet line は `live_trigger_cli` です。
ロジックを line-local に fork せず、shared `boxes` を使う側として扱ってください。

特に守ること:

- runtime logic は `live_trigger/boxes/` を正本にする
- execution / Telegram / UI / waiting behavior は `live_trigger_cli` で進める
- runtime 生成物は Git や share の source 扱いにしない

### 3. racer_index / live-score

`2026-03-25` の更新として、`pred1 != lane1` slice の live-score 読みを追加しています。
これは i5 で継続してよい主タスクです。

読む場所:

- `RACER_INDEX_STATUS.md`
- `racer_index/OPERATIONS.md`
- `reports/strategies/racer_rank_live_20260325/summary.md`

見るスクリプト:

- `workspace_codex/scripts/predict_racer_rank_live.py`

次にやってほしいこと:

1. `pred1 != lane1` を one-day anecdote で終わらせず multi-day に拡張
2. 次の 3 形を比較
   - head-fixed exacta
   - `pred1..pred4` `2連複BOX`
   - `1-2 / 1-3 / 1-4` `2連複`
3. 結論を `FROM_I5_TO_ME.md` に返す

## Preserved Older Context

旧 `125` メモは historical context として preserve しますが、いまの正本は以下です。

- `projects/125/README.md`
- `reports/strategies/125/summary_20260314.md`
- `LOGIC_STATUS.md`

つまり、このファイルは `125` 単独メモではなく、今後は `i5` の delta / handoff 専用として使います。

## Requested Response

区切りのよいところで `FROM_I5_TO_ME.md` に短く返答してください。

- 今回どの task を進めたか
- block があるか
- 次に何を見るか

## Codex Action

1. `git pull --ff-only origin main`
2. `I5_START.md` を読む
3. このファイルを読む
4. 担当 task の status doc を読む
5. 作業を進める
6. 区切りで `FROM_I5_TO_ME.md` に返答
