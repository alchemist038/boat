# Live Trigger CLI

`live_trigger_cli/` は、現在の主系ベットラインです。

このライン自体はロジック正本を持ちません。
このラインが持つのは次です。

- CLI / UI の入口
- 実行ライン固有の状態
- runtime DB / log / operator flow
- Telegram 連携を含む `assist_real` 承認フロー

ロジックは shared 側を参照します。

- `live_trigger/boxes/125`
- `live_trigger/boxes/c2`
- `live_trigger/boxes/4wind`
- `live_trigger/auto_system/app/core/bets.py`

このライン固有の runtime 状態は次にあります。

- `live_trigger_cli/data/settings.json`
- `live_trigger_cli/data/system.db`
- `live_trigger_cli/data/auto_run.log`
- `live_trigger_cli/raw/`

## 現在の主戦3本

- `125_broad_four_stadium`
- `c2_provisional_v1`
- `4wind_base_415`

この3本はすべて shared `live_trigger/boxes/` 配下が正本です。

## 実行モード

- `air`
  - 最終投票はしません
- `assist_real`
  - 投票導線は開きますが、最終 submit は承認待ちです
- `armed_real`
  - 自動で submit まで進みます

## assist_real の流れ

`assist_real` は次の流れです。

1. `GO` を検知する
2. Telegram に `GO` 通知を送る
3. operator が `承認` または `却下` を押す
4. `承認` なら assist window 内で submit
5. `却下` なら破棄
6. 無操作のまま締切を過ぎたら timeout discard
7. submit できた場合は完了通知を返す

## UI 起動

UI は次で起動します。

```powershell
live_trigger_cli\run_ui.cmd
```

既定の URL は次です。

```text
http://localhost:8502
```

## UI の見方

- 上段メトリクスは `today targets` と `all targets` を分けて表示します
- `概要` タブでは、当日 `race_date` に絞ったロジック別 target 件数を確認できます
- `C2` の `pred1_lane = 1` 除外は CLI 独自判定ではなく、shared box 側の `racer_index_overlay` を消費した結果として表示されます
- これらの件数は watchlist 作成直後ではなく、`target_races` に同期された後の状態を示します

## 監視窓

- 現在の main-line 監視窓は `締切 10 分前` から `締切 3 分前` です
- 監視中は `beforeinfo` と `4wind odds2t` を stale cache のまま固定せず、一定間隔で再取得します

## 所有権ルール

- 主系実行ライン: `live_trigger_cli`
- ロジック正本: `live_trigger/boxes`
- 買い目展開の正本: `live_trigger/auto_system/app/core/bets.py`
- canonical DB: `\\038INS\boat\data`

戦略を変更する場合は、まず shared box を更新し、その後に CLI ラインがそれを消費する形を守ります。
