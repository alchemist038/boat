from __future__ import annotations

import os
from pathlib import Path

BASE_URL = "https://www.boatrace.jp"
PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BRONZE_ROOT = str(PACKAGE_ROOT / "data" / "bronze")
DEFAULT_DB_PATH = str(PACKAGE_ROOT / "data" / "silver" / "boat_race.duckdb")
DEFAULT_RAW_ROOT = str(PACKAGE_ROOT / "data" / "raw")
DEFAULT_SLEEP_SECONDS = 0.5
DEFAULT_TIMEOUT_SECONDS = 30
LOCAL_CANONICAL_ROOT = Path(r"C:\boat")
DATA_ROOT_ENV_VAR = "BOAT_DATA_ROOT"
RAW_ROOT_ENV_VAR = "BOAT_RAW_ROOT"
BRONZE_ROOT_ENV_VAR = "BOAT_BRONZE_ROOT"
DB_PATH_ENV_VAR = "BOAT_DB_PATH"
LIVE_TRIGGER_ROOT_ENV_VAR = "BOAT_LIVE_TRIGGER_ROOT"
CANONICAL_ROOT_ENV_VAR = "BOAT_CANONICAL_ROOT"
REPORTS_ROOT_ENV_VAR = "BOAT_REPORTS_ROOT"
PREDICT_SCRIPT_PATH_ENV_VAR = "BOAT_PREDICT_SCRIPT_PATH"
TERM_LAYOUT_URL = f"{BASE_URL}/owpc/pc/extra/data/layout.html"
TERM_DOWNLOAD_URL = f"{BASE_URL}/owpc/pc/extra/data/download.html"


def _path_under_data_root(*parts: str) -> str:
    data_root = os.environ.get(DATA_ROOT_ENV_VAR)
    if not data_root:
        raise RuntimeError(f"{DATA_ROOT_ENV_VAR} is not set")
    return str(Path(data_root).joinpath(*parts))


def _package_canonical_root() -> Path | None:
    db_path = PACKAGE_ROOT / "data" / "silver" / "boat_race.duckdb"
    if db_path.exists():
        return PACKAGE_ROOT
    return None


def _existing_local_canonical_root() -> Path | None:
    db_path = LOCAL_CANONICAL_ROOT / "data" / "silver" / "boat_race.duckdb"
    if db_path.exists():
        return LOCAL_CANONICAL_ROOT
    return None


def _local_data_root() -> str | None:
    canonical_root = _package_canonical_root()
    if canonical_root is None:
        canonical_root = _existing_local_canonical_root()
    if canonical_root is None:
        return None
    data_root = canonical_root / "data"
    if data_root.exists():
        return str(data_root)
    return None


def get_default_raw_root() -> str:
    env_value = os.environ.get(RAW_ROOT_ENV_VAR)
    if env_value:
        return env_value
    if os.environ.get(DATA_ROOT_ENV_VAR):
        return _path_under_data_root("raw")
    local_data_root = _local_data_root()
    if local_data_root:
        return str(Path(local_data_root) / "raw")
    return DEFAULT_RAW_ROOT


def get_default_bronze_root() -> str:
    env_value = os.environ.get(BRONZE_ROOT_ENV_VAR)
    if env_value:
        return env_value
    if os.environ.get(DATA_ROOT_ENV_VAR):
        return _path_under_data_root("bronze")
    local_data_root = _local_data_root()
    if local_data_root:
        return str(Path(local_data_root) / "bronze")
    return DEFAULT_BRONZE_ROOT


def get_default_db_path() -> str:
    env_value = os.environ.get(DB_PATH_ENV_VAR)
    if env_value:
        return env_value
    if os.environ.get(DATA_ROOT_ENV_VAR):
        return _path_under_data_root("silver", "boat_race.duckdb")
    local_data_root = _local_data_root()
    if local_data_root:
        return str(Path(local_data_root) / "silver" / "boat_race.duckdb")
    return DEFAULT_DB_PATH


def get_default_live_trigger_root() -> str:
    return os.environ.get(LIVE_TRIGGER_ROOT_ENV_VAR) or str(PACKAGE_ROOT / "live_trigger")


def _canonical_root_from_data_root() -> str | None:
    data_root = os.environ.get(DATA_ROOT_ENV_VAR)
    if not data_root:
        return None
    data_path = Path(data_root)
    if data_path.name.lower() == "data":
        return str(data_path.parent)
    return str(data_path)


def get_default_canonical_root() -> str:
    return (
        os.environ.get(CANONICAL_ROOT_ENV_VAR)
        or _canonical_root_from_data_root()
        or (str(_package_canonical_root()) if _package_canonical_root() is not None else None)
        or (str(_existing_local_canonical_root()) if _existing_local_canonical_root() is not None else None)
        or str(PACKAGE_ROOT)
    )


def get_default_reports_root() -> str:
    return os.environ.get(REPORTS_ROOT_ENV_VAR) or str(Path(get_default_canonical_root()) / "reports" / "strategies")


def get_default_predict_script_path() -> str:
    return os.environ.get(PREDICT_SCRIPT_PATH_ENV_VAR) or str(
        Path(get_default_canonical_root()) / "workspace_codex" / "scripts" / "predict_racer_rank_live.py"
    )

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
