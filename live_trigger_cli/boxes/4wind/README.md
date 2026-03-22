# BOX 4wind

`4wind` は現状の shared `live_trigger/boxes/` にはまだ載せていないため、
この新ライン専用の local box としてここに持ちます。

現在の runtime shape:

- wind `5-6m`
- `lane4_st_diff_from_inside <= -0.05`
- `lane4_exhibition_time_rank <= 3`
- `lane3_class in ('A1', 'A2')`
- quoted `min_odds 10-50`
- exacta `4-1 / 4-5`

この box は `live_trigger_cli/runtime.py` の local evaluator でのみ解釈されます。
