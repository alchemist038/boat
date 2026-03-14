@echo off
cd /d d:\boat
d:\boat\.venv\Scripts\python.exe -m boat_race_data collect-range ^
  --start-date 20250401 ^
  --end-date 20250630 ^
  --db-path data/silver/boat_race_q2_trifecta.duckdb ^
  --sleep-seconds 0.5 ^
  --refresh-every-days 7 ^
  --resume-existing-days ^
  --skip-term-stats ^
  --skip-quality-report
