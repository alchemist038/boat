# Teleboat ログイン問題メモ

- updated_at: 2026-03-21 08:00 JST
- scope: `C:\CODEX_WORK\boat_clone\live_trigger\auto_system`
- purpose: Teleboat ログイン不安定問題の経緯、現在の状態、今後の改善論点を LLM に共有するための整理

## 1. 結論

現時点では、Teleboat 実投票系は `常駐ブラウザ方式` を主経路にしている。

- resident browser を 1 枚立てる
- そのブラウザにログインする
- `Teleboat ログイン確認` で、いま自動側が掴んでいるブラウザが本当にログイン済みかを検証する

この方式でかなり改善したが、まだ「完全自動で長時間安定」とまでは言えない。

主な理由:

- `ログイン情報を保持する (7 日間有効)` が、入力補助 cookie の保持に寄っていて、実セッション保持を保証していない可能性が高い
- Teleboat 側で `一定時間が経過したため、処理できませんでした。再度ログインして、操作をやり直してください。` の期限切れページが出る
- resident browser 内に `ログイン画面タブ` と `トップ画面タブ` が共存すると、自動側が誤ってログイン画面側を掴むことがある

## 2. 実際に起こった事象

### 2-1. ログイン済みのはずなのに、自動側はログイン失敗に見える

観測された状態:

- 人間の目では Teleboat トップへ入れている
- しかし自動側の `Teleboat ログイン確認` は失敗扱いになる

原因として判明したこと:

- 同じ Teleboat 画面に見えても、自動側が実際に掴んでいるタブが別のことがある
- ログイン済みトップではなく、古いログイン画面タブを掴んでいたケースがあった

### 2-2. `Teleboat ログイン確認` でログイン画面が出るが、しばらくするとトップ画面が出る

観測された状態:

- `Teleboat ログイン確認` を押す
- 最初にログイン画面が出る
- 数秒待つと、無入力でもトップ画面が出る
- ただし元のログイン画面タブは残る
- そのログイン画面タブだけを閉じ、トップ画面だけ残した状態で再度確認すると `OK` になる

意味合い:

- 実セッション自体は生きている可能性がある
- ただし `不要なログイン画面タブの後始末` が弱く、自動側のタブ選択が不安定になる

### 2-3. セッション期限切れページが出る

実際に確認したページ:

- URL 例: `/tohyo-ap-pctohyo-web/service/bet/top/init`
- title: `エラー`
- 本文:
  - `一定時間が経過したため、処理できませんでした。再度ログインして、操作をやり直してください。`

意味合い:

- Teleboat セッションは長時間無条件に保持されるわけではない
- `トップ画面の見た目が残っている` ことと `実セッションが有効` は別問題

### 2-4. `7 日間有効` の期待と実態がずれる

観測:

- `memberNoCookie`
- `pinCookie`
- `authPasswordCookie`

のような入力補助 cookie は残る

一方で:

- 再起動後や時間経過後に Teleboat トップへ自動復帰しないことがある
- つまり `7 日間有効` は実ログインセッション保持ではなく、入力情報保持寄りの可能性が高い

## 3. これまでに入れた修正

### 3-1. resident browser 主経路

保存済み `storage_state` を開き直す方式から、resident browser を主経路に切り替えた。

現行方針:

- `teleboat_resident_browser = true`
- debug port は `9333`
- `Teleboat セッション準備` で常駐ブラウザを使う
- `Teleboat ログイン確認` も同じ常駐ブラウザへ接続して見る

### 3-2. タブ整理の改善

入れた改善:

- resident browser 内の全 Teleboat タブを見る
- `ログイン済みトップ` を優先して採用する
- 不要な Teleboat タブは閉じる

狙い:

- `ログイン画面タブ` を誤って掴む確率を減らす
- できるだけ `トップ 1 タブ` に収束させる

### 3-3. 期限切れページ検知

入れた改善:

- 期限切れページの文言を専用検知
- その状態を `prepared` や `verified` と誤認しない
- `login_required` として扱う

さらに:

- 期限切れページを見つけたら
  - `閉じる` を試す
  - だめなら `BASE_URL` へ戻す
  - その後に自動再ログインを試す

方向に寄せた

### 3-4. `Teleboat セッション準備` と `Teleboat ログイン確認` の役割分離

- `Teleboat セッション準備`
  - resident browser を立てる
  - 必要なら手動ログイン導線を作る
- `Teleboat ログイン確認`
  - 自動側が掴んでいる resident browser が本当にログイン済みかを見る

これにより:

- 手動でログインを作る工程
- 実運用前の確認工程

を分離した

## 4. いまの実装状態

関連ファイル:

- [teleboat.py](/c:/CODEX_WORK/boat_clone/live_trigger/auto_system/app/core/teleboat.py)
- [00_check_teleboat_session.py](/c:/CODEX_WORK/boat_clone/live_trigger/auto_system/app/modules/00_check_teleboat_session.py)
- [web_app.py](/c:/CODEX_WORK/boat_clone/live_trigger/auto_system/web_app.py)

状態ファイル:

- [teleboat_session_state.json](/c:/CODEX_WORK/boat_clone/live_trigger/auto_system/data/teleboat_session_state.json)
- [teleboat_resident_browser.json](/c:/CODEX_WORK/boat_clone/live_trigger/auto_system/data/teleboat_resident_browser.json)

### 4-1. 現在の session state

2026-03-21 07:54:41 JST 時点:

- `status = verified`
- `session_state = reused_session`
- `prepared_at = 2026-03-21T07:50:53`
- `last_verified_at = 2026-03-21T07:54:41`
- `assumed_valid_until = 2026-03-28T07:50:53`

### 4-2. 現在の resident browser state

2026-03-21 07:55:01 JST 時点:

- `status = running`
- `port = 9333`
- `pid = 13596`
- `user_data_dir = C:\CODEX_WORK\boat_clone\live_trigger\auto_system\data\playwright_user_data`

### 4-3. 運用側設定

[settings.json](/c:/CODEX_WORK/boat_clone/live_trigger/auto_system/data/settings.json)

- `system_running = false`
- `execution_mode = assist_real`
- `teleboat_resident_browser = true`
- `real_headless = false`

注意:

- 現在は auto system 自体は停止状態
- 実投票モードとしては `assist_real` が保存されているが、運用再開時は安全側で `air` へ戻して使う前提が望ましい

## 5. いま残っている課題

### 5-1. 完全自動の再ログイン

必要な機能:

- セッション切れを検知
- resident browser にトップがあればそれを優先
- なければ自動再ログインを 1 回試す
- それでもだめなら `login_required` で停止

### 5-2. トップ画面 1 タブへの完全収束

今の改善でかなり良くなったが、まだ運用としては

- ログイン後にログイン画面タブを閉じる
- トップ画面だけ残す

が有効

理想:

- ログイン成功後に自動側が不要タブを完全整理する
- resident browser は常に `1 ウィンドウ / 1 タブ / トップ画面` に収束する

### 5-3. 長時間放置時の安定性

未確認点:

- `verified` を取った後、何分〜何時間で期限切れになるか
- 放置中に resident browser がトップを保てるか
- 再ログイン試行の成功率

## 6. LLM に投げたい論点

### 6-1. セッション設計

- Teleboat のように `入力保持はあるが実セッションは切れやすい` サイトで、最も安全な実投票セッション設計は何か
- resident browser 1 枚常駐方式は妥当か

### 6-2. 自動再ログインの境界

- どこまでを自動再ログインにしてよいか
- `reCAPTCHA / 追加認証` がある可能性を前提に、どこで人へ戻すべきか

### 6-3. タブ整理戦略

- `ログイン画面タブ` と `トップ画面タブ` が同時にある時、どの基準で安全にトップを正と判定するべきか
- 自動でタブを閉じるロジックの安全条件は何か

### 6-4. 実投票前の安全確認

- `Assist Real` / `Armed Real` の直前に毎回 `ensure_session()` を走らせる設計は妥当か
- セッション切れ時に `自動再ログイン -> 再確認 -> 投票続行` としてよいか、それとも当該レースは必ず skip すべきか

## 7. 現時点の運用上の暫定ルール

- resident browser は `1 ウィンドウ / 1 タブ`
- ログイン後はトップ画面だけ残す
- `Teleboat ログイン確認` で `verified` を取ってから実投票系へ進む
- 期限切れページが出たら、実セッションは切れた前提で扱う
- 完全自動に上げる前に、`セッション切れ -> 自動再ログイン試行` の安定化が必要

## 8. 今後の改善プラン

完全自動を最終目標に置くなら、単に `verified / login_required` の 2 値を増やすだけでは足りない。

今後は次の 2 本を主軸に進めるのが自然。

### 8-1. 現行路線の強化案: session state machine 化

現状の `verified` には、次の意味が混ざっている。

- 直前に確認できたので今は使えそう
- しばらく前に確認できたのでおそらく使えそう
- top にいるが、別タブや timeout の影響をまだ受けているかもしれない

この曖昧さを減らすため、最低でも次の状態に分ける方針が有効。

- `verified_fresh`
  - 直近確認済みで、実投票へ進んでよい状態
- `verified_stale`
  - 以前は有効だったが、時間経過により再確認が必要な状態
- `session_timeout_detected`
  - 期限切れページを検知した状態
- `reauth_in_progress`
  - 自動再ログインや再確認を試みている状態
- `unsafe_tab_state`
  - resident browser のタブ状態が不安定で、どの画面を正とするか危ない状態
- `login_required`
  - もう人の介入が必要な停止状態

この方向の利点:

- `いま投票してよいか` を機械判定しやすい
- `Assist Real` と `Armed Real` の分岐条件を整理しやすい
- `skip / retry / stop` の判断を明文化しやすい
- 後から notification や LLM 監視を入れるときに扱いやすい

短期の実装順:

1. `teleboat_session_state.json` に状態細分化を導入
2. UI で状態名と理由をそのまま見せる
3. `place_target()` 前に `fresh` でなければ再確認を強制
4. `timeout -> reauth -> still unsafe -> stop` の遷移を固定化

### 8-2. 別視点の最終形: resident browser と executor の分離

現行は resident browser に

- ログイン状態
- タブ状態
- 実投票直前画面
- 実投票処理

をまとめて持たせている。

ただし、完全自動を本気で狙うなら、最終的には

- resident browser = `監視 / 認証維持 / 人の介入窓口`
- short-lived executor = `投票時だけ起動する実行体`

に分離する方が安定しやすい。

イメージ:

- supervisor
  - resident browser を監視
  - session state machine を管理
  - unsafe なら自動再認証を試す
  - 無理なら停止と通知
- executor
  - レースごとに短命で起動
  - 直前確認
  - 投票内容投入
  - 結果保存
  - 終了

この方向の利点:

- long-lived browser state の劣化を executor 側へ持ち込みにくい
- 投票処理ごとに責務を切れる
- 実投票失敗時の再試行・証跡・隔離がしやすい
- 将来的な完全自動で `resident browser 一本足` の不安定さを減らせる

注意点:

- いきなり全部分離すると実装量が大きい
- 当面は resident browser 主体のまま、state machine を先に入れる方が現実的

### 8-3. 現時点の優先順位

今すぐ着手すべき順は次。

1. `session state machine 化`
2. `timeout / unsafe tab / reauth` の状態可視化
3. `投票直前は fresh でないと進めない` 制約
4. `executor 分離` の設計化
5. 最後に完全自動の retry policy を詰める

要するに:

- 近い次手は `state machine 化`
- 長期の最終形は `resident browser + short-lived executor` 分離

この 2 本を軸にすると、今の resident browser 改善を無駄にせず、そのまま完全自動へ伸ばしやすい。
