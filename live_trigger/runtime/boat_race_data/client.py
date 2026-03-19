from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from boat_race_data.constants import (
    BASE_URL,
    DEFAULT_TIMEOUT_SECONDS,
    RACE_ENDPOINTS,
    STADIUMS,
)
from boat_race_data.utils import clean_text, ensure_dir, has_no_data


@dataclass(slots=True)
class FetchResult:
    url: str
    fetched_at: str
    raw_path: Path
    content: bytes
    text: str | None = None


class BoatRaceClient:
    def __init__(self, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> None:
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.headers.update(
            {
                "User-Agent": "boat-race-data/0.1 (+local analytics pipeline)",
            }
        )

    def build_race_url(self, page_name: str, race_date: str, stadium_code: str, race_no: int) -> str:
        path = RACE_ENDPOINTS[page_name].format(
            date=race_date,
            stadium_code=stadium_code,
            race_no=race_no,
        )
        return f"{BASE_URL}{path}"

    def fetch_text(self, url: str, raw_path: Path) -> FetchResult:
        response = self.session.get(url, timeout=self.timeout_seconds)
        response.raise_for_status()
        ensure_dir(raw_path.parent)
        raw_path.write_bytes(response.content)
        encoding = response.encoding or response.apparent_encoding or "utf-8"
        text = response.content.decode(encoding, errors="replace")
        return FetchResult(
            url=url,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            raw_path=raw_path,
            content=response.content,
            text=text,
        )

    def fetch_binary(self, url: str, raw_path: Path) -> FetchResult:
        response = self.session.get(url, timeout=self.timeout_seconds)
        response.raise_for_status()
        ensure_dir(raw_path.parent)
        raw_path.write_bytes(response.content)
        return FetchResult(
            url=url,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            raw_path=raw_path,
            content=response.content,
        )

    def discover_active_stadiums(self, race_date: str, sample_race_no: int = 1) -> list[str]:
        active: list[str] = []
        for stadium_code in STADIUMS:
            url = self.build_race_url("racelist", race_date, stadium_code, sample_race_no)
            response = self.session.get(url, timeout=self.timeout_seconds)
            response.raise_for_status()
            encoding = response.encoding or response.apparent_encoding or "utf-8"
            text = response.content.decode(encoding, errors="replace")
            if not has_no_data(text):
                active.append(stadium_code)
        return active

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "BoatRaceClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def absolute_url(path_or_url: str) -> str:
    text = clean_text(path_or_url)
    if text.startswith("http://") or text.startswith("https://"):
        return text
    return f"{BASE_URL}{text}"
