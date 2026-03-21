# Live Trigger Fresh Exec

`live_trigger_fresh_exec/` は、新しい実投票フローを別ラインで組み上げるための並行ツリーです。  
既存の `live_trigger/` を大きく崩さずに、`air 常時 + real 都度起動` を検証していきます。

## 目的

- `air` は常時回す
- `GO` 後にだけ fresh executor を起動する
- ログイン後にトップページを 1 枚へ収束させる
- 実投票処理後はログアウトして閉じる
- strategy BOX は `live_trigger/boxes/` を共有し、ローカル BOX は持たない

## 主なファイル

- [run_auto_ui.cmd](/c:/CODEX_WORK/boat_clone/live_trigger_fresh_exec/run_auto_ui.cmd)
  - fresh auto ラインの起動入口
- [FRESH_EXECUTION_FLOW.md](/c:/CODEX_WORK/boat_clone/live_trigger_fresh_exec/FRESH_EXECUTION_FLOW.md)
  - 新ラインのフロー整理
- [web_app.py](/c:/CODEX_WORK/boat_clone/live_trigger_fresh_exec/auto_system/web_app.py)
  - fresh 管理 UI
- [auto_run.py](/c:/CODEX_WORK/boat_clone/live_trigger_fresh_exec/auto_system/auto_run.py)
  - `sync -> evaluate -> execute` のループ
- [01_sync_watchlists.py](/c:/CODEX_WORK/boat_clone/live_trigger_fresh_exec/auto_system/app/modules/01_sync_watchlists.py)
  - shared watchlist を fresh DB に同期
- [02_evaluate_targets.py](/c:/CODEX_WORK/boat_clone/live_trigger_fresh_exec/auto_system/app/modules/02_evaluate_targets.py)
  - shared BOX で当日判定
- [03_execute_fresh_bets.py](/c:/CODEX_WORK/boat_clone/live_trigger_fresh_exec/auto_system/app/modules/03_execute_fresh_bets.py)
  - `air` 記録と fresh 実投票実行
- [fresh_executor.py](/c:/CODEX_WORK/boat_clone/live_trigger_fresh_exec/auto_system/app/core/fresh_executor.py)
  - fresh browser 起動、ログイン、トップ収束、投票、ログアウト
- [01_manual_fresh_executor_test.py](/c:/CODEX_WORK/boat_clone/live_trigger_fresh_exec/auto_system/app/modules/01_manual_fresh_executor_test.py)
  - `login_only / confirm_only / confirm_prefill / assist_real / armed_real` の手動検証入口

## 現状

- fresh ラインは独自の `settings.json`、`system.db`、`auto_run.log`、UI、ループを持つ
- `watchlists/raw/boxes` は `live_trigger/` を共有する
- `trigger` が当日 watchlist の元を作り、fresh はそれを取り込んで `beforeinfo` を自動取得し、shared BOX で GO 判定する
- executor は resident browser を使わず、実行ごとに dedicated browser を立ち上げる
- ログイン後は stable な ready page を待ち、余分ページを閉じてトップ 1 枚へ収束させる
- `assist_real` は確認画面で購入金額と投票パスを入力して人待ちする
- `armed_real` は自動送信し、結果確認後にログアウトする
- `real_session_strategy=burst_reuse` のときだけ、次の real target が近ければセッションを維持できる

## 2026-03-21 時点の確認結果

- `sync -> evaluate -> execute` の単独ループは起動確認済み
- 画面の日本語表記を優先した fresh 管理 UI へ更新済み
- `対象` タブは当日分を中心に見せ、判定後の行は色を落として表示する
- 手動 Fresh テストで `1-2-5 / 3連単` は確認画面到達まで通過
- 手動 Fresh テストで `2-ALL-ALL / 3連単` も確認画面到達まで通過
- テスト後の `cleanup_after_test=true` でログアウト完了まで確認済み
- selector 修正は shared `teleboat.py` 側に入っているため、旧ラインと fresh ラインの両方に効く

## 手動テスト例

```powershell
@'
{
  "test_mode": "confirm_only",
  "stadium_code": "01",
  "race_no": 12,
  "bets": [
    {"bet_type": "trifecta", "combo": "1-2-5", "amount": 100}
  ],
  "cleanup_after_test": true
}
'@ | python C:\CODEX_WORK\boat_clone\live_trigger_fresh_exec\auto_system\app\modules\01_manual_fresh_executor_test.py
```

## 起動

```powershell
C:\CODEX_WORK\boat_clone\live_trigger_fresh_exec\run_auto_ui.cmd
```
