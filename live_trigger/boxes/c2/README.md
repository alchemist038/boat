# BOX C2

`C2` の分離 box。

参照:

- `projects/c2/README.md`
- `projects/c2/status_notebooklm_20260313.txt`
- `reports/strategies/c2/README.md`

現時点の扱い:

- `C2` は semi-regular strategy candidate
- women-race 条件は title proxy ベース
- 本運用確定ではなく、trigger 条件を保持した上で待機

現在の provisional profile は次を表現しています。

- 事前:
  - women-race title proxy
- 直前:
  - `lane1_start_gap_over_rest >= 0.12`
  - `ex1 <= ex2 + 0.02`
  - `ex1 <= ex3 + 0.02`

運用を開始する時点で `enabled: true` に切り替えます。
