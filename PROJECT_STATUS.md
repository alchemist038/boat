# PROJECT STATUS

## 1. このファイルの目的

このファイルは、このプロジェクトの「現状確認」と「履歴台帳」を兼ねる。

用途は次の2つ。

1. スレッドが変わっても、収集基盤・DB・戦略検証の現在地をすぐ把握できるようにする
2. すでに試した戦略ロジックを再度同じ条件で回してしまうことを防ぐ

特に戦略案については、必ずこのファイルの「時系列履歴」と「検証済みロジック台帳」を見てから次のBTを設計する。

---

## 2. プロジェクトの主目的

このプロジェクトの主目的は、BOAT RACE公式ベースのデータをローカルに蓄積し、後から統計分析・バックテスト・期待値検証を再現可能な形で行えるようにすること。

予想ロジックそのものより先に、以下を優先している。

- 公式データ中心の収集
- raw と整形済みデータの分離
- 再取得可能な保存構造
- DuckDB による分析しやすい正規化
- 戦略BTの結果を履歴として残すこと

---

## 3. ディレクトリ / DB / スクリプトの役割

### 3.1 ディレクトリ

- `data/raw`
  - 取得した原本を保存する場所
  - HTML / LZH / TXT をそのまま保持する

- `data/bronze`
  - 抽出済みの中間CSV置き場
  - raw の再パースや確認に使う

- `data/silver`
  - DuckDB 本体置き場
  - 分析・BTの主参照先

- `reports/data_quality`
  - 日次の品質確認レポート

- `src/boat_race_data`
  - 実装本体

- `tests`
  - 収集・パース・CLI 補正の検証

- `GPT`
  - GPT / Gemini に渡す CSV / Markdown / BT出力

- `docs`
  - 補足ドキュメント

### 3.2 主なスクリプト

- `src/boat_race_data/cli.py`
  - CLI の入口
  - `collect-day`
  - `collect-range`
- `collect-mbrace-range`
- `export-gpt`
- `export-correlation-study`
- `backtest-strategies`

- `src/boat_race_data/client.py`
  - 公式HTML取得クライアント

- `src/boat_race_data/parsers.py`
  - 公式HTMLのパーサ
  - 出走表 / 2連単 / 3連単 / 結果 / beforeinfo

- `src/boat_race_data/mbrace.py`
  - mbrace 日次LZHの高速収集
  - `B` から `races / entries / race_meta`
  - `K` から `results / beforeinfo_entries`

- `src/boat_race_data/storage.py`
  - bronze / silver への保存
  - DuckDB テーブル作成と upsert

- `src/boat_race_data/gpt_export.py`
  - GPT向けCSV / Markdown の出力

- `src/boat_race_data/correlation_study.py`
  - 発見用区間と検証用区間を分けた相関探索パッケージの出力

- `src/boat_race_data/backtest.py`
  - 現在の戦略BTロジック
  - 2026-03-11 時点では `StrategyA_v4_Context_1_35_All_3t` を実装

- `src/boat_race_data/quality.py`
  - データ品質チェック

### 3.3 DBレイヤ

#### raw 原本

- `data/raw/...`

#### bronze 層

- `bronze_races`
- `bronze_entries`
- `bronze_odds_2t`
- `bronze_odds_3t`
- `bronze_results`
- `bronze_beforeinfo_entries`
- `bronze_race_meta`
- `bronze_racer_stats_term`

#### silver 層

- `races`
- `entries`
- `odds_2t`
- `odds_3t`
- `results`
- `beforeinfo_entries`
- `race_meta`
- `racer_stats_term`

#### 確認用ビュー

- `collection_day_summary`

---

## 4. 現在のDB状態

更新日: `2026-03-12`

### 4.1 収集期間

- 現在の収集期間: `2023-03-11` から `2026-03-10`
- カバー日数: `1096日`

### 4.2 テーブル件数

- `races`: `168036`
- `entries`: `1008216`
- `results`: `165771`
- `beforeinfo_entries`: `980531`
- `race_meta`: `168036`
- `odds_2t`: `169425`
- `odds_3t`: `1440`
- `racer_stats_term`: `1625`

### 4.3 race_meta.grade 件数

- `一般`: `165444`
- `G1`: `2244`
- `SG`: `348`

### 4.4 既知の欠損

- `results` は `races` より `2265件` 少ない
- `beforeinfo_entries` は `entries` より `27685件` 少ない
- `odds_3t` は全期間では揃っておらず、現状 `2026-03-06` 中心の一部のみ

注意:

- 3連単の戦略BTは、現状は `odds_3t` による期待値検証ではなく、確定払戻ベースの固定点数BTとして扱っている

---

## 5. 時系列履歴

この節は「何をいつ追加したか」と「何を試したか」を時系列で残す。

### 2026-03-11 フェーズ1: 公式中心の収集基盤を作成

実施内容:

- `raw -> bronze -> silver` の3層構造を作成
- DuckDB を分析の中心に採用
- 公式HTMLから以下を取得可能にした
  - 出走表
  - 2連単オッズ
  - 3連単オッズ
  - 結果
  - beforeinfo
- `racer_stats_term` の取り込みを実装
- 品質チェックレポートを出力可能にした

意味:

- 再取得可能な土台が完成
- 以降のBTは DuckDB を基準に回せるようになった

### 2026-03-11 フェーズ2: 1日サンプルで初期BTを実施

対象日:

- `2026-03-06`

実施内容:

- B系の初期戦略比較を1日12レースで実施

主な結果:

- `StrategyA_2t_inner_weak_23_head`
  - `bet_count=11`
  - `hit_count=1`
  - `ROI=56.36%`

- `StrategyB_2t_mid_odds_filter`
  - `bet_count=30`
  - `hit_count=2`
  - `ROI=111.33%`

- `StrategyC_3t_inner_pair_plus_one_hole`
  - `bet_count=24`
  - `hit_count=0`
  - `ROI=0.0%`

判断:

- `A` と `C` は早期に廃棄
- `B` 系だけを残して絞り込み検証へ

### 2026-03-11 フェーズ3: B系の感度分析

実施内容:

- `B'` などの厳選版を試行
- `multiple_heads` がサンプルを殺している主要因と判明

代表結果:

- `B_prime_15_30_single_head_max2`
  - `played_races=2`
  - `bet_count=3`
  - `hit_count=0`
  - `ROI=0.0%`

判断:

- `single head 固定` は厳しすぎる
- B系は絞りすぎると検証不能になる

### 2026-03-11 フェーズ4: beforeinfo / race_meta を追加

実施内容:

- `beforeinfo_entries` テーブルを追加
- `race_meta` テーブルを追加
- `FEATURES_QUERY` を更新し、以下を結合可能にした
  - `grade`
  - `meeting_day_no`
  - `exhibition_time`
  - `tilt`
  - `course_entry`
  - `start_exhibition_st`

意味:

- SG/G1 条件や開催日条件を使う戦略BTが可能になった
- 展示タイム異常のような戦略も検証可能になった

### 2026-03-11 フェーズ5: mbrace 日次LZHで100日分を高速収集

実施内容:

- `collect-mbrace-range` を追加
- mbrace `B/K` 日次LZHから `races / entries / race_meta / results / beforeinfo_entries` を高速収集

意味:

- HTML逐次取得だけでは非現実的だった3か月収集が現実的になった
- 100日分の検証母数を短時間で確保

### 2026-03-11 フェーズ6: 100日分で新戦略A/Bを初回検証

出力先:

- `GPT/output/2025-12-01_2026-03-10_strategies_ab`

結果:

- `StrategyA_Optimal_1_All_All_3t`
  - `played_races=84`
  - `bet_count=1680`
  - `hit_count=49`
  - `ROI=66.54%`

- `StrategyB_Exhibition_Anomaly_B1_Motor_2t`
  - `played_races=3719`
  - `bet_count=18595`
  - `hit_count=245`
  - `ROI=46.77%`

判断:

- どちらも負け
- A は買い目が広すぎ、B は構造的に勝率不足

### 2026-03-11 フェーズ7: v2 検証

出力先:

- `GPT/output/2025-12-01_2026-03-10_strategies_ab_v2`

結果:

- `StrategyA_v2_1_35_All_3t`
  - 条件: `SG/G1 + 4日目 + 晴れ`
  - 買い目: `1-3/5-全` の8点
  - `played_races=84`
  - `bet_count=672`
  - `hit_count=29`
  - `ROI=105.24%`

- `StrategyB_v2_Exhibition_Anomaly_B1_2or5_2t`
  - 条件: `展示遅れ0.20以上 + B1 + motor_place_rate>=40 + 2 or 5コース`
  - `played_races=1726`
  - `bet_count=9170`
  - `hit_count=149`
  - `ROI=58.75%`

判断:

- A はプラス化したが、`played_races=84` で小標本すぎる
- B は改善してもなお大幅マイナス
- B系はここで廃案方向

### 2026-03-11 フェーズ8: v3 広域検証

出力先:

- `GPT/output/2025-12-01_2026-03-10_strategy_a_v3`

結果:

- `StrategyA_v3_Broad_G1_1_35_All_3t`
  - 条件: `SG/G1 のみ`
  - 買い目: `1-3/5-全` の8点
  - `played_races=576`
  - `bet_count=4608`
  - `hit_count=135`
  - `ROI=78.0%`

判断:

- サンプル数は増えた
- ただし ROI はマイナス化
- 「1-35-全」は SG/G1 全体では優位性不足

### 2026-03-11 フェーズ9: v4 コンテキスト特化検証

出力先:

- `GPT/output/2025-12-01_2026-03-10_strategy_a_v4`

結果:

- `StrategyA_v4_Context_1_35_All_3t`
  - 条件:
    - `SG/G1`
    - かつ次のどちらか
      - `4日目` かつ `ナイター場(01,07,12,15,16,20,24)`
      - `6日目(最終日)` は全場
  - 買い目: `1-3/5-全` の8点
  - `played_races=144`
  - `bet_count=1152`
  - `hit_count=53`
  - `ROI=132.05%`

判断:

- v3 よりサンプルは減ったが ROI は改善
- 現時点で最も有望な形は v4
- ただし、まだ100日・SG/G1中心の限定条件なので、次は期間拡張か開催別分解が必要

### 2026-03-11 フェーズ10: v4 のアウトオブサンプル検証

出力先:

- `GPT/output/2025-08-20_2025-11-30_strategy_a_v4_OOS`
- `GPT/output/2025-04-15_2025-08-19_strategy_a_v4_OOS2`

結果:

- `StrategyA_v4_Context_1_35_All_3t`
  - OOS1 `2025-08-20` から `2025-11-30`
  - `played_races=60`
  - `bet_count=480`
  - `hit_count=12`
  - `ROI=55.25%`

- `StrategyA_v4_Context_1_35_All_3t`
  - OOS2 `2025-04-15` から `2025-08-19`
  - `played_races=48`
  - `bet_count=384`
  - `hit_count=11`
  - `ROI=70.10%`

- v4 通算
  - `played_races=252`
  - `bet_count=2016`
  - `hit_count=76`
  - `ROI=101.96%`

判断:

- IS では強く見えたが、OOS では再現性が弱い
- 通算ではわずかにプラスでも、3連単8点としては一撃配当依存が強い
- 次は券種と点数を落として DD 耐性を見るべきと判断

### 2026-03-11 フェーズ11: v4 の配当依存と DD を点検

実施内容:

- v4 の `IS + OOS1 + OOS2` を合算して、配当集中度と最大DDを確認

結果:

- 通算 `bets=2016`
- 通算 `hits=76`
- 通算 `ROI=101.96%`
- 通算 `max_drawdown_yen=41490`
- 最大DD終点: `2025-11-04 / 01 / 4R`
- `top1_share_pct=14.94%`
- `top3_share_pct=23.46%`
- `top5_share_pct=29.91%`
- `median_hit_payout=1680`

- OOS1
  - `top3_share_pct=55.05%`
- OOS2
  - `top3_share_pct=64.41%`

判断:

- v4 は通算ROIだけを見るとギリギリ残るが、DDと配当集中の観点ではかなり重い
- 「一撃の配当に守られたROI」という懸念は妥当
- 実運用候補としては、3連単8点のままでは採用しにくい

### 2026-03-11 フェーズ12: 2連単 `1-3` のクイックBT

出力先:

- `GPT/output/quick_bt_context_a1a2_2t_13`

ロジック:

- `SG/G1`
- かつ次のどちらか
  - `4日目` かつ `ナイター場(01,07,12,15,16,20,24)`
  - `6日目(最終日)` は全場
- `1号艇` の級別が `A1` または `A2`
- 買い目は `2連単 1-3` の1点

結果:

- IS
  - `played_races=87`
  - `bet_count=87`
  - `hit_count=25`
  - `ROI=110.23%`
  - `max_drawdown_yen=1400`

- OOS1
  - `played_races=37`
  - `bet_count=37`
  - `hit_count=7`
  - `ROI=103.78%`
  - `max_drawdown_yen=2000`

- OOS2
  - `played_races=24`
  - `bet_count=24`
  - `hit_count=7`
  - `ROI=108.75%`
  - `max_drawdown_yen=500`

- 通算
  - `played_races=148`
  - `bet_count=148`
  - `hit_count=39`
  - `ROI=108.38%`
  - `max_drawdown_yen=2000`
  - `max_losing_streak=20`

データ品質確認:

- このBTで使った対象148レースに対して
  - `race_id` 重複: `0`
  - `1着/2着欠損`: `0`
  - `exacta_payout` 欠損: `0`
  - `1号艇級別欠損`: `0`
  - `grade` 欠損: `0`
  - `meeting_day_no` 欠損: `0`

判断:

- v4 の文脈は活かしつつ、券種を2連単1点まで落とすと DD が大きく改善
- OOS1 / OOS2 でもプラスを維持しており、現時点では v4 より実運用に近い
- 次に正式実装・長期BTする候補はこの2連単ロジック

### 2026-03-12 フェーズ13: 3年BT母集団の拡張

実施内容:

- `collect-mbrace-range --start-date 20230311 --end-date 20250414 --resume-existing-days --refresh-every-days 60 --skip-term-stats`
  を実行
- 既存の `2025-04-15` から `2026-03-10` と接続し、約3年分を mbrace ベースで連結

結果:

- 収集範囲は `2023-03-11` から `2026-03-10`
- `count(distinct race_date)=1096`
- `race_meta` 欠損は `0`
- `results_missing_rate_pct=1.3479`
- `beforeinfo_missing_rate_pct=2.7459`

判断:

- `results / race_meta / entries / beforeinfo_entries` を使う確定払戻ベースBT母集団としては、3年規模で実用域
- `odds_2t / odds_3t` は全面整備されていないため、期待値BTの基盤としては未完成
- したがって「3年の固定ルールBT」は可能、「3年のオッズ前提BT」はまだ不可

### 2026-03-12 フェーズ14: 3年フルレンジでの最小BT確認

対象ロジック:

- `SG/G1`
- `4日目` かつ `ナイター場(01,07,12,15,16,20,24)` または `6日目`
- `1号艇=A1/A2`
- `2連単 1-3` の1点

結果:

- `played_races=315`
- `bet_count=315`
- `hit_count=76`
- `ROI=94.03%`
- `max_drawdown_yen=4380`
- `max_losing_streak=20`

判断:

- 330日範囲では良く見えたが、3年フルレンジではプラスを維持できなかった
- これは収集基盤の問題ではなく、ロジックの一般化不足を示す
- 逆に言えば、3年BT母集団がロジックの過剰適合を弾ける状態まで整った

### 2026-03-12 フェーズ15: 発見用3か月と検証用3か月の相関探索パッケージを追加

実施内容:

- `export-correlation-study` CLI を追加
- 発見用 `2025-01-01..2025-03-31`
- 検証用 `2025-04-01..2025-06-30`
- discovery / validation を分けたパッケージを同時出力
- GPT / Gemini 向けの専用プロンプトを追加
- 相関探索用に以下の集計CSVを追加
  - `summary_meeting_day_lane.csv`
  - `summary_context_signal_matrix.csv`
  - `summary_stadium_day_signal_matrix.csv`
  - `summary_exacta_context_roi.csv`

出力先:

- `GPT/output/2025Q1_vs_2025Q2_correlation_study`

判断:

- LLM に discovery だけを渡し、validation を holdout に残す導線ができた
- `2025Q1/Q2` はオッズ系が未整備なので、`market_results_joined.csv` は空
- 今回の用途は期待値探索ではなく、結果ベースの相関仮説生成

### 2026-03-12 フェーズ16: v6 3戦略の validation BT

出力先:

- `GPT/output/2025-04-01_2025-06-30_v6_validation`

validation期間:

- `2025-04-01` から `2025-06-30`

結果:

- `StrategyV6_A_G1_EarlyDays_1_3`
  - 条件: `SG/G1` かつ `1-3日目` かつ `1号艇=A1/A2`
  - 買い目: `2連単 1-3`
  - `played_races=55`
  - `bet_count=55`
  - `hit_count=6`
  - `ROI=39.27%`
  - `max_drawdown_yen=3810`

- `StrategyV6_B_WeakInStadium_21_31`
  - 条件: `対象場(14,09,02,01,04)` かつ `1号艇=A2/B1/B2`
  - 買い目: `2連単 2-1, 3-1`
  - `played_races=2043`
  - `bet_count=4086`
  - `hit_count=236`
  - `ROI=66.44%`
  - `max_drawdown_yen=140080`

- `StrategyV6_C_HighWind_13_31`
  - 条件: `風速6m以上` かつ `1号艇=A1`
  - 買い目: `2連単 1-3, 3-1`
  - `played_races=338`
  - `bet_count=676`
  - `hit_count=78`
  - `ROI=88.05%`
  - `max_drawdown_yen=16530`

判断:

- 3案とも validation では `ROI < 100` で再現性なし
- `V6_B` は母数はあるが DD が深く、実運用候補から外す
- `V6_C` は相対的には最もましだが、それでもマイナス域で採用不可
- `V6_A` は小標本かつ大幅マイナスで即廃棄

---

## 6. 検証済みロジック台帳

この表は「同じロジックを別スレッドでうっかり再実行しない」ための一覧。

| ID | 戦略名 | ロジック要約 | 検証期間 | 結果 | 判定 |
| --- | --- | --- | --- | --- | --- |
| R001 | StrategyA_2t_inner_weak_23_head | 1号艇弱含み時の2-3頭狙い | 2026-03-06 1日 | ROI 56.36% | 廃棄 |
| R002 | StrategyB_2t_mid_odds_filter | 2連単中穴帯の広めフィルタ | 2026-03-06 1日 | ROI 111.33% | 感度分析へ |
| R003 | StrategyC_3t_inner_pair_plus_one_hole | 3連単準穴少点数 | 2026-03-06 1日 | ROI 0.0% | 廃棄 |
| R004 | B_prime_15_30_single_head_max2 | B系を single head / 15-30 / 最大2点に絞る | 2026-03-06 1日 | played 2 / ROI 0.0% | 絞りすぎで廃棄 |
| R005 | StrategyA_Optimal_1_All_All_3t | SG/G1・4日目・晴れの 1-全-全 | 100日 | ROI 66.54% | 廃棄 |
| R006 | StrategyB_Exhibition_Anomaly_B1_Motor_2t | 展示異常×B1好モーター | 100日 | ROI 46.77% | 廃棄 |
| R007 | StrategyA_v2_1_35_All_3t | SG/G1・4日目・晴れの 1-35-全 | 100日 | ROI 105.24% / played 84 | 小標本注意 |
| R008 | StrategyB_v2_Exhibition_Anomaly_B1_2or5_2t | 展示異常×B1×2or5限定 | 100日 | ROI 58.75% | 廃棄 |
| R009 | StrategyA_v3_Broad_G1_1_35_All_3t | SG/G1 全体の 1-35-全 | 100日 | ROI 78.0% | 優位性なし |
| R010 | StrategyA_v4_Context_1_35_All_3t | SG/G1 + 4日目ナイター or 6日目 の 1-35-全 | 100日 IS | ROI 132.05% | OOS確認へ |
| R011 | StrategyA_v4_Context_1_35_All_3t | 同上 | OOS1 103日 | ROI 55.25% | 再現性弱い |
| R012 | StrategyA_v4_Context_1_35_All_3t | 同上 | OOS2 127日 | ROI 70.10% | 再現性弱い |
| R013 | StrategyX_Context_A1A2_2t_1_3 | SG/G1 + 4日目ナイター or 6日目 + 1号艇A1/A2 の 2連単 1-3 | IS+OOS1+OOS2 | ROI 108.38% / maxDD 2000円 | 暫定本命 |
| R014 | StrategyX_Context_A1A2_2t_1_3 | 同上 | 3年フルレンジ | ROI 94.03% / maxDD 4380円 | 長期では不採用 |
| R015 | StrategyV6_A_G1_EarlyDays_1_3 | SG/G1 + 1-3日目 + 1号艇A1/A2 の 2連単 1-3 | 2025Q2 validation | ROI 39.27% / maxDD 3810円 | 廃棄 |
| R016 | StrategyV6_B_WeakInStadium_21_31 | 対象場(14,09,02,01,04) + 1号艇A2/B1/B2 の 2連単 2-1,3-1 | 2025Q2 validation | ROI 66.44% / maxDD 140080円 | 廃棄 |
| R017 | StrategyV6_C_HighWind_13_31 | 風速6m以上 + 1号艇A1 の 2連単 1-3,3-1 | 2025Q2 validation | ROI 88.05% / maxDD 16530円 | 廃棄 |

### 同一ロジックの再検証を避けるルール

次の3つが同じなら、別名でも「同じロジック」とみなす。

1. 買い目フォーマットが同じ
2. フィルタ条件が実質同じ
3. 対象期間だけを変えただけで、新しい特徴量や追加データが増えていない

再検証してよいのは次の場合だけ。

- 期間を大きく増やした
- 収集データが増えた
- フィルタ条件を明確に追加・削除した
- 買い目点数やフォーメーションを変えた

---

## 7. 現在の有力戦略

2026-03-12 時点では、**3年フルレンジで採用確定できる戦略はまだない**。

補足:

- `StrategyA_v4_Context_1_35_All_3t` は通算 `ROI=101.96%` だが、`max_drawdown_yen=41490` で配当集中が重い
- `StrategyX_Context_A1A2_2t_1_3` は 330日範囲では有望だったが、3年フルレンジでは `ROI=94.03%`
- `2025Q1 discovery` 由来の `v6` 3案も `2025Q2 validation` では全て `ROI < 100`
- つまり現在の成果は「強い戦略」よりも、「3年で過剰適合を弾けるBT基盤」を持てたことにある

---

## 8. 次にやる候補

優先順は以下。

1. 3年母集団を基準にした最小ロジック比較
   - 2連単1点系を複数並べて長期安定性を見る

2. `4日目ナイター` と `6日目最終日` の分解
   - 文脈を混ぜずに年別・期別で切る

3. 年別 / 場別 / grade別の安定性確認
   - 2023 / 2024 / 2025 / 2026年初で分解

4. 3連単オッズの蓄積を強化
   - 将来的に期待値BTへ移行するための後続整備

5. 欠損の改善
   - `results` と `beforeinfo_entries` の欠損要因の切り分け

6. discovery / validation 分離型の仮説生成
   - `2025Q1 discovery -> 2025Q2 validation` の順で GPT / Gemini に仮説だけ作らせる

---

## 9. 参照先

### 主な出力フォルダ

- `GPT/output/2025-12-01_2026-03-10_package`
- `GPT/output/2025-12-01_2026-03-10_strategies_ab`
- `GPT/output/2025-12-01_2026-03-10_strategies_ab_v2`
- `GPT/output/2025-12-01_2026-03-10_strategy_a_v3`
- `GPT/output/2025-12-01_2026-03-10_strategy_a_v4`
- `GPT/output/2025-08-20_2025-11-30_strategy_a_v4_OOS`
- `GPT/output/2025-04-15_2025-08-19_strategy_a_v4_OOS2`
- `GPT/output/quick_bt_context_a1a2_2t_13`
- `GPT/output/2025Q1_vs_2025Q2_correlation_study`
- `reports/three_year_bt_readiness_20260312.md`

### 主なコード

- `src/boat_race_data/backtest.py`
- `src/boat_race_data/correlation_study.py`
- `src/boat_race_data/gpt_export.py`
- `src/boat_race_data/mbrace.py`
- `src/boat_race_data/storage.py`
- `src/boat_race_data/cli.py`
