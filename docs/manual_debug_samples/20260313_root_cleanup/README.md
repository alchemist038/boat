# Root Cleanup 2026-03-13

このフォルダは、`d:/boat` ルート直下に散在していた単発の手動検証用サンプルを退避したものです。

## 退避対象

- `B260306.TXT`
- `K260306.TXT`
- `beforeinfo_20251217_23_12.html`
- `beforeinfo_sample.html`
- `sample_b260306.lzh`
- `sample_k260306.lzh`

## 理由

- parser 調査や手動確認用の単発サンプルであり、通常運用のルート直下に置き続ける必要が低い
- ルートには運用に必要なものだけを残したい

## ルートに残したもの

以下は運用・参照に使うため、そのまま残している。

- `data/`
- `src/`
- `tests/`
- `reports/`
- `docs/`
- `GPT/`
- `.venv/`
- `README.md`
- `PROJECT_STATUS.md`
- `PROJECT_STATUS_NOTEBOOKLM_20260313.txt`
- `resume_q2_trifecta_collect_20260313.cmd`

## 注意

- `resume_q2_trifecta_collect_20260313.cmd` は現在の収集中タスクが参照している可能性があるため未移動
- `.tmp.drive*` は外部同期系の一時ディレクトリなので未操作
