from __future__ import annotations

BASE_URL = "https://www.boatrace.jp"
DEFAULT_BRONZE_ROOT = "data/bronze"
DEFAULT_DB_PATH = "data/silver/boat_race.duckdb"
DEFAULT_RAW_ROOT = "data/raw"
DEFAULT_SLEEP_SECONDS = 0.5
DEFAULT_TIMEOUT_SECONDS = 30
TERM_LAYOUT_URL = f"{BASE_URL}/owpc/pc/extra/data/layout.html"
TERM_DOWNLOAD_URL = f"{BASE_URL}/owpc/pc/extra/data/download.html"

STADIUMS = {
    "01": "桐生",
    "02": "戸田",
    "03": "江戸川",
    "04": "平和島",
    "05": "多摩川",
    "06": "浜名湖",
    "07": "蒲郡",
    "08": "常滑",
    "09": "津",
    "10": "三国",
    "11": "びわこ",
    "12": "住之江",
    "13": "尼崎",
    "14": "鳴門",
    "15": "丸亀",
    "16": "児島",
    "17": "宮島",
    "18": "徳山",
    "19": "下関",
    "20": "若松",
    "21": "芦屋",
    "22": "福岡",
    "23": "唐津",
    "24": "大村",
}

RACE_ENDPOINTS = {
    "racelist": "/owpc/pc/race/racelist?hd={date}&jcd={stadium_code}&rno={race_no}",
    "odds2t": "/owpc/pc/race/odds2tf?hd={date}&jcd={stadium_code}&rno={race_no}",
    "odds3t": "/owpc/pc/race/odds3t?hd={date}&jcd={stadium_code}&rno={race_no}",
    "beforeinfo": "/owpc/pc/race/beforeinfo?hd={date}&jcd={stadium_code}&rno={race_no}",
    "result": "/owpc/pc/race/raceresult?hd={date}&jcd={stadium_code}&rno={race_no}",
}
