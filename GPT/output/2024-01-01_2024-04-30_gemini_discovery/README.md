# 2024-01-01 to 2024-04-30 Gemini Discovery Package

This folder is reserved for the first zero-base discovery package to send to Gemini.

## Purpose

- Discovery period only: `2024-01-01` to `2024-04-30`
- No reuse of existing human-created logic as a starting point
- Gemini is used first for data-package design and later for fresh hypothesis generation
- Human-side backtesting will be done later on separate periods

## File Budget

Gemini upload limit is assumed to be `10 files` maximum in one batch.

Because of that, this package should prefer:

- a small number of dense CSV files
- one Markdown data dictionary
- one Markdown instruction file if needed

## Planned Contents

- `data_dictionary.md`
- `races_sample.csv`
- `entries_sample.csv`
- optional aggregated CSVs if Gemini explicitly asks for them

## Prompt Reference

Primary request prompt:

- [gemini_request_2024-01-01_2024-04-30_discovery.md](/d:/boat/GPT/prompts/gemini_request_2024-01-01_2024-04-30_discovery.md)

