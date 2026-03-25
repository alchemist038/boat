# TO I5 FROM ME

`i5` 側の Codex に渡す、現時点の handoff / delta メモです。
bootstrap はこの 1 枚だけに頼らず、まず `I5_START.md` を読んでください。

## Context

- machine: i5
- from: me
- status: active
- updated_at: 2026-03-25 22:10 JST
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
