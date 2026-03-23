# High-Hit Structural Path 2026-03-22

## Purpose

- `1強い` 系の高勝率探索で、どこまでが構造理解で、どこから先が市場に織り込まれているかを記録する。
- これは採用メモではなく、探索の到達点を残すための path note。

## Base Frame

今回の基礎フレームは次の通り。

- 期間の起点 discovery:
  - `2023-03-11..2023-09-10`
- その後の拡張確認:
  - `2023-03-11..2023-12-31`
  - `2024-01-01..2024-12-31`

探索の土台にした `1強い` は、実務上は次の形だった。

- `lane1_exhibition_rank = 1`
- `wave_height_cm <= 4`
- `lane2` と `lane3` のうち、A級がちょうど片方だけ

この土台だけで見た `2023-03-11..2023-12-31` の結果は:

- races: `5192`
- `1-2`: `20.38%`
- `1-3`: `17.30%`
- `1-2/1-3`: `37.67%`
- ROI: `83.70%`

ここが基準線になった。

## Core Lesson

今回の一番大きい学びは単純だった。

- 構造の読み自体は間違っていない
- ただし、分かりやすい強弱は市場もかなり読んでいる
- そのため、的中率が上がってもオッズのうまみが削られやすい

つまり:

- race-shape understanding: `yes`
- stable market edge: `not enough yet`

## 4 Weak Path

最初に効いたのは `4が弱い` 側だった。

単純定義:

- `lane4_class in ('B1', 'B2')`

`2023-03-11..2023-09-10` の主軸土台に対して:

- base:
  - races: `3347`
  - `1-2/1-3`: `37.41%`
  - ROI: `82.86%`
- plus `lane4 weak`:
  - races: `1875`
  - `1-2/1-3`: `40.48%`
  - ROI: `85.53%`

さらに `4の弱さ` を live 側で寄せると:

- `lane4_class in ('B1', 'B2')`
- `lane4_exhibition_rank >= 4`
- `lane4_motor_place_rate < min(lane2_motor_place_rate, lane3_motor_place_rate)`

`2023-03-11..2023-12-31` では:

- races: `587`
- `1-2`: `20.44%`
- `1-3`: `22.32%`
- `1-2/1-3`: `42.76%`
- ROI: `89.19%`

解釈:

- `4が理論上弱い` だけより
- `4がその日も弱い` のほうが自然だった

ただし、ROI の伸びはまだ十分ではなかった。

## 6 Strong Path

次に見たのは `6が強い` 側だった。

単純に `6が強い` と言っても、それだけでは:

- `4/5` を消す
- ただし `6自身も2着に来る`

という二面性があった。

`2023-03-11..2023-09-10` で一番自然だった切り方は:

- `lane6_class in ('A1', 'A2')`
- `lane6_exhibition_rank <= 3`

結果:

- races: `482`
- `1-2`: `21.99%`
- `1-3`: `17.22%`
- `1-2/1-3`: `39.21%`
- ROI: `96.01%`

これは悪くなかった。

ただし、構造の読みは次の通りだった。

- `6` は `4/5` を押さえる
- しかし `6` も少し2着を取る
- したがって `6強い` は `2/3保護` と同義ではない

そこで、より良かった読みは:

- `6は強い`
- ただし `6は最上位展示ではない`
- `6` は `4/5` を止める役で、自分は少し届き切らない

この発想から:

- `lane6_class in ('A1', 'A2')`
- `lane6_exhibition_rank in (2, 3)`
- `lane6_national_win_rate > max(lane4_national_win_rate, lane5_national_win_rate)`

を `6strong_not1` として確認した。

`2023-03-11..2023-12-31` では:

- races: `499`
- `1-2`: `24.45%`
- `1-3`: `15.03%`
- `1-2/1-3`: `39.48%`
- ROI: `92.99%`

この枝は `1-2` 側に寄りやすかったが、ROI はまだ抜けなかった。

## Combined Read: 1 Strong + 4 Weak + 6 Strong

`1強い + 4弱い + 6強い` を重ねた時点で、枝としてはかなり面白く見えた。

条件:

- `lane1_exhibition_rank = 1`
- `wave_height_cm <= 4`
- `lane2` と `lane3` のうち A級がちょうど片方だけ
- `lane4_class in ('B1', 'B2')`
- `lane6_class in ('A1', 'A2')`
- `lane6_exhibition_rank <= 3`

`2023-03-11..2023-09-10`:

- races: `295`
- `1-2`: `25.76%`
- `1-3`: `15.93%`
- `1-2/1-3`: `41.69%`
- ROI: `95.24%`

`2023-03-11..2023-12-31`:

- races: `456`
- `1-2`: `24.56%`
- `1-3`: `16.01%`
- `1-2/1-3`: `40.57%`
- ROI: `96.21%`

この時点で:

- 6か月で崩れず
- 2023年全体でもほぼ維持

だったため、一度は主枝候補に見えた。

## Lane1 Class Split

この複合枝を `lane1_class` で割ると、かなりはっきりした。

`2023-03-11..2023-12-31`:

- `A1`:
  - races: `101`
  - `1-2/1-3`: `49.50%`
  - ROI: `79.65%`
- `A2`:
  - races: `164`
  - `1-2/1-3`: `47.56%`
  - ROI: `105.34%`
- `B1`:
  - races: `174`
  - `1-2/1-3`: `30.46%`
  - ROI: `94.25%`

読み:

- `A1` は当たりやすいが売れすぎ
- `A2` は hit rate を保ちつつ、まだ price が残る
- `B1` は payout は上がるが hit rate が落ちすぎる

このため、複合枝の中では `lane1 = A2` が最有力に見えた。

## A2 Path

ここからは `lane1 = A2` を固定して、数本の枝を切った。

### Strongest 2023-only branch

`2023-03-11..2023-12-31` で一番きれいだったのは:

- `lane1_class = 'A2'`
- `lane2 in ('B1', 'B2')`
- `lane3 in ('A1', 'A2')`

つまり `3strong_side`。

結果:

- races: `89`
- `1-2`: `28.09%`
- `1-3`: `22.47%`
- `1-2/1-3`: `50.56%`
- ROI: `132.53%`

さらに:

- `lane1_st_bucket = near_even`

を足した `3strong_near_even` は:

- races: `35`
- `1-2/1-3`: `60.00%`
- ROI: `159.29%`

これもかなり良く見えた。

### Other interesting A2 branches

- `lane1_st_bucket = lane1_faster`
  - races: `39`
  - `1-2/1-3`: `53.85%`
  - ROI: `139.10%`
- `wind_bucket = 3-4`
  - races: `72`
  - `1-2/1-3`: `47.22%`
  - ROI: `114.10%`
- `lane6_nwr > lane2_nwr and lane3_nwr`
  - races: `89`
  - `1-2/1-3`: `48.31%`
  - ROI: `113.93%`

この時点では:

- `3strong_side`
- `3strong_near_even`
- `lane1_faster`

が主要候補に見えた。

## 2024 Forward Check

この枝を `2024-01-01..2024-12-31` で確認した。

### Base A2 branch

- `2023`: `164 races`, `47.56%`, ROI `105.34%`
- `2024`: `180 races`, `38.89%`, ROI `77.11%`

この時点でかなり悪化した。

### Candidate branches

- `3strong_side`
  - `2023`: `89 races`, `50.56%`, ROI `132.53%`
  - `2024`: `105 races`, `38.10%`, ROI `67.95%`
- `3strong_near_even`
  - `2023`: `35 races`, `60.00%`, ROI `159.29%`
  - `2024`: `44 races`, `52.27%`, ROI `104.77%`
- `lane1_faster`
  - `2023`: `39 races`, `53.85%`, ROI `139.10%`
  - `2024`: `39 races`, `48.72%`, ROI `96.15%`
- `wind_3_4`
  - `2023`: `72 races`, `47.22%`, ROI `114.10%`
  - `2024`: `70 races`, `38.57%`, ROI `93.36%`
- `lane6_nwr_gt23`
  - `2023`: `89 races`, `48.31%`, ROI `113.93%`
  - `2024`: `88 races`, `34.09%`, ROI `83.35%`

解釈:

- `3strong_side` は forward でかなり崩れた
- `lane1_faster` も優位を失った
- `3strong_near_even` だけは生き残ったが、母数は小さい

つまり:

- structure-side explanation: `still plausible`
- durable market edge: `not proven`

## Current Meaning

ここまでの考察で残った整理は次の通り。

- `1強い`
- `4弱い`
- `6強い`

という構造読みそのものは大きく間違っていない。

ただし、それをそのまま bet condition にすると:

- 市場も似た形を読んでいる
- obvious strength / weakness は価格に織り込まれやすい
- 2023 discovery で良く見えても、2024 forward でうまみが消えやすい

現状では:

- structural understanding is improving
- but obvious structural strength does not automatically create an odds edge

という結論。

## What Still Looks Worth Keeping

完全に捨てる必要はないが、次回再開時に残すならこの順。

- `3strong_near_even`
  - 理由: `2024` でも `52.27% / 104.77%`
  - ただし `44 races` と薄い
- `4_live_weak`
  - 理由: `4` の弱さを static class ではなく live weakness で見る発想は自然
- `6strong_not1`
  - 理由: `6` を winner ではなく blocker として扱う読みは今後も使える

## Current Stop Point

今回の stop point は:

- logic understanding は前進した
- しかし、いま見えている枝はまだ market edge として弱い
- obvious structural filters だけでは price advantage が足りない

したがって、ここから先は:

- same-idea over-slicing で掘り切るより
- market が読み切っていない interaction を探す方向へ戻す

のが自然。
