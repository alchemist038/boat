# Forward Monitoring Tools

このフォルダには、ボートレース戦略のパフォーマンスを継続的に監視（フォワードテスト）するためのスクリプトが格納されています。

## 格納されているスクリプト

### 1. `c2_monitor.py`
- **戦略:** C2（女子戦・1号艇ST遅れ・展示タイム優位）
- **対象:** 全場
- **買い目:** 3連単 2-ALL-ALL (12点) + 3-ALL-ALL (12点) = 計24点
- **実行方法:**
  ```bash
  .venv\Scripts\python.exe forward\c2_monitor.py --days 7
  ```

### 2. `125_monitor.py`
- **戦略:** 125（特定場での1-2-5固定買い）
- **対象場:** 住之江(12), 鳴門(14), 芦屋(21), 江戸川(03)
- **買い目:** 3連単 1-2-5 (1点固定)
- **実行方法:**
  ```bash
  .venv\Scripts\python.exe forward\125_monitor.py --days 7
  ```

## 履歴データ
`forward\history` フォルダには、過去の検証結果が保存されています。

- `c2_recent_analysis_result.csv`: 2026-03-08〜15のC2戦略検証結果 (ROI 57.22%)
- `125_recent_analysis_result.csv`: 2026-03-08〜15の125戦略検証結果 (ROI 1130.00%)

## 使い方
1. 最新の生データ（HTML）が `data/raw` に存在することを確認してください。
2. 上記のコマンドを実行すると、指定した日数（デフォルト 7日間）を遡って合致レースとその成績を計算します。
3. 2026年3月15日時点の環境では、仮想環境のPython（`.venv\Scripts\python.exe`）を使用して実行してください。
