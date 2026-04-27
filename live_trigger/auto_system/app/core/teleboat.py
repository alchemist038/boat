from __future__ import annotations

import json
import os
import re
import socket
import sqlite3
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

BASE_URL = "https://ib.mbrace.or.jp/"
BET_TOP_URL = "https://ib.mbrace.or.jp/tohyo-ap-pctohyo-web/service/bet/top/init"

STADIUM_CODE_TO_NAME = {
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

BET_TYPE_TO_LABEL = {
    "trifecta": "3連単",
    "trio": "3連複",
    "exacta": "2連単",
    "quinella": "2連複",
    "quinella_place": "拡連複",
    "win": "単勝",
    "place": "複勝",
}

INSUFFICIENT_FUNDS_PATTERNS = (
    re.compile(r"(残高|資金).{0,20}(不足|足りません|足りない|ありません|超え)"),
    re.compile(r"(投票可能金額|投票可能額|購入可能額|購入可能金額).{0,20}(不足|超え)"),
    re.compile(r"入金.{0,20}(必要|してください)"),
)

VOTE_SUCCESS_SELECTORS = (
    'text="投票結果"',
    'text="契約番号"',
    'text="次の場で投票する"',
)

VOTE_PASSWORD_SELECTORS = (
    "#pass",
    "input[name='betPassword']",
    "input[title='謚慕･ｨ逕ｨ繝代せ繝ｯ繝ｼ繝・]",
    "input[aria-label='謚慕･ｨ逕ｨ繝代せ繝ｯ繝ｼ繝・]",
    "input[name*='vote']",
    "input[name*='password']",
    "input[type='password']",
)

VOTE_PASSWORD_RETRY_WAIT_MS = 10_000
VOTE_PASSWORD_RETRY_ATTEMPTS = 3

SESSION_READY_SELECTORS = (
    'text="マイページ"',
    'text="照会"',
    'text="ログアウト"',
    'text="入金・精算"',
    'text="会員情報変更"',
    'text="お知らせ"',
    'text="購入限度額"',
    'text="購入可能ベット数"',
)

LOGIN_FORM_SELECTORS = (
    "#memberNo",
    "#pin",
    "#authPassword",
    "#loginButton",
    "input[name='memberNo']",
    "input[name='pin']",
    "input[name='authPassword']",
)

MANUAL_AUTH_SELECTORS = (
    'text="reCAPTCHA"',
    'text="追加認証"',
    'text="認証コード"',
    'text="ワンタイム"',
    'text="二段階認証"',
    'text="画像認証"',
)

SESSION_TIMEOUT_TEXTS = (
    "一定時間が経過したため、処理できませんでした",
    "再度ログインして、操作をやり直してください",
)

SESSION_KEEP_LOGIN_DAYS = 7
SESSION_STATE_FILENAME = "teleboat_session_state.json"
STORAGE_STATE_FILENAME = "teleboat_storage_state.json"
RESIDENT_STATE_FILENAME = "teleboat_resident_browser.json"

METHOD_SELECTOR_MAP = {
    "通常投票": "#betway1",
    "ボックス投票": "#betway3",
    "フォーメーション投票": "#betway4",
}

METHOD_SELECTOR_BY_KEY = {
    "regular": "#betway1",
    "box": "#betway3",
    "formation": "#betway4",
}

BET_TYPE_SELECTOR_MAP = {
    "3連単": "#betkati6",
    "3連複": "#betkati7",
    "2連単": "#betkati3",
    "2連複": "#betkati4",
    "拡連複": "#betkati5",
    "単勝": "#betkati1",
}

BET_TYPE_SELECTOR_BY_CODE = {
    "trifecta": "#betkati6",
    "trio": "#betkati7",
    "exacta": "#betkati3",
    "quinella": "#betkati4",
    "quinella_place": "#betkati5",
    "win": "#betkati1",
}

ADD_BUTTON_SELECTOR_BY_METHOD_KEY = {
    "regular": "#regAmountBtn",
    "box": "#boxAmountBtn",
    "formation": "#formaAmountBtn",
}

COMBINATION_CONFIRM_SELECTOR_BY_METHOD_KEY = {
    "box": "#combiConfirmBtnBox",
    "formation": "#combiConfirmBtnForma",
}


@dataclass
class TeleboatCredentials:
    subscriber_no: str
    pin: str
    auth_password: str
    vote_password: str


@dataclass
class TeleboatResult:
    execution_status: str
    message: str
    submitted_at: datetime = field(default_factory=datetime.now)
    contract_no: str | None = None
    screenshot_path: str | None = None
    html_path: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


class TeleboatError(RuntimeError):
    pass


class TeleboatConfigurationError(TeleboatError):
    pass


class TeleboatPreparationPending(TeleboatError):
    pass


class TeleboatExecutionError(TeleboatError):
    def __init__(
        self,
        message: str,
        *,
        screenshot_path: str | None = None,
        html_path: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.screenshot_path = screenshot_path
        self.html_path = html_path
        self.details = details or {}


class TeleboatInsufficientFundsError(TeleboatExecutionError):
    pass


def _load_env() -> None:
    root = Path(__file__).resolve().parents[2]
    live_trigger_root = root.parent
    for path in (live_trigger_root / ".env", root / ".env"):
        if path.exists():
            # Favor the project .env over inherited process env so credential
            # updates are reflected in long-running worker processes.
            load_dotenv(path, override=True)
    load_dotenv(override=False)


def _teleboat_session_state_path(data_dir: Path) -> Path:
    return data_dir / SESSION_STATE_FILENAME


def _teleboat_storage_state_path(data_dir: Path) -> Path:
    return data_dir / STORAGE_STATE_FILENAME


def _teleboat_resident_state_path(data_dir: Path) -> Path:
    return data_dir / RESIDENT_STATE_FILENAME


def load_teleboat_session_state(data_dir: Path) -> dict[str, Any]:
    path = _teleboat_session_state_path(data_dir)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def load_teleboat_resident_state(data_dir: Path) -> dict[str, Any]:
    path = _teleboat_resident_state_path(data_dir)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _save_teleboat_session_state(data_dir: Path, payload: dict[str, Any]) -> None:
    path = _teleboat_session_state_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _save_teleboat_resident_state(data_dir: Path, payload: dict[str, Any]) -> None:
    path = _teleboat_resident_state_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _record_teleboat_session_state(
    data_dir: Path,
    *,
    status: str,
    message: str,
    user_data_dir: Path,
    session_state: str | None = None,
    refresh_validity: bool = False,
) -> dict[str, Any]:
    now = datetime.now()
    payload = load_teleboat_session_state(data_dir)
    payload.update(
        {
            "status": status,
            "message": message,
            "last_updated_at": now.isoformat(timespec="seconds"),
            "user_data_dir": str(user_data_dir),
            "storage_state_path": str(_teleboat_storage_state_path(data_dir)),
            "keep_login_requested": True,
            "keep_login_valid_days": SESSION_KEEP_LOGIN_DAYS,
        }
    )
    if session_state:
        payload["session_state"] = session_state

    if status == "prepared":
        payload["prepared_at"] = now.isoformat(timespec="seconds")
    if status in {"prepared", "verified"}:
        payload["last_verified_at"] = now.isoformat(timespec="seconds")
    if refresh_validity:
        payload["assumed_valid_until"] = (now + timedelta(days=SESSION_KEEP_LOGIN_DAYS)).isoformat(timespec="seconds")
    if status == "login_required":
        payload["last_failure_at"] = now.isoformat(timespec="seconds")
        payload["last_failure_message"] = message

    _save_teleboat_session_state(data_dir, payload)
    return payload


def _format_session_hint(payload: dict[str, Any]) -> str:
    if not payload:
        return ""
    parts: list[str] = []
    prepared_at = payload.get("prepared_at")
    valid_until = payload.get("assumed_valid_until")
    if prepared_at:
        parts.append(f"前回準備: {prepared_at}")
    if valid_until:
        parts.append(f"7日保持想定期限: {valid_until}")
    if not parts:
        return ""
    return " / ".join(parts)


def _profile_lock_paths(user_data_dir: Path) -> list[Path]:
    candidates = [
        user_data_dir / "lockfile",
        user_data_dir / "SingletonLock",
        user_data_dir / "SingletonCookie",
        user_data_dir / "SingletonSocket",
        user_data_dir / "Default" / "LOCK",
    ]
    return [path for path in candidates if path.exists()]


def _resident_debug_url(port: int) -> str:
    return f"http://127.0.0.1:{int(port)}"


def _is_port_open(port: int, *, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, int(port))) == 0


def _wait_for_port(port: int, *, timeout_seconds: int = 15) -> bool:
    deadline = time.time() + max(1, timeout_seconds)
    while time.time() < deadline:
        if _is_port_open(port):
            return True
        time.sleep(0.25)
    return _is_port_open(port)


def _launch_resident_browser(*, executable_path: str, user_data_dir: Path, port: int) -> subprocess.Popen[str]:
    user_data_dir.mkdir(parents=True, exist_ok=True)
    args = [
        executable_path,
        f"--remote-debugging-port={int(port)}",
        "--remote-allow-origins=*",
        f"--user-data-dir={str(user_data_dir)}",
        "--no-first-run",
        "--no-default-browser-check",
        "--new-window",
        BASE_URL,
    ]
    kwargs: dict[str, Any] = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "stdin": subprocess.DEVNULL,
        "text": True,
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    return subprocess.Popen(args, **kwargs)


def _record_resident_browser_state(
    data_dir: Path,
    *,
    status: str,
    port: int,
    user_data_dir: Path,
    pid: int | None = None,
    executable_path: str | None = None,
    message: str | None = None,
) -> None:
    payload = load_teleboat_resident_state(data_dir)
    payload.update(
        {
            "status": status,
            "port": int(port),
            "debug_url": _resident_debug_url(port),
            "user_data_dir": str(user_data_dir),
            "last_updated_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    if pid is not None:
        payload["pid"] = int(pid)
    if executable_path:
        payload["executable_path"] = executable_path
    if message:
        payload["message"] = message
    _save_teleboat_resident_state(data_dir, payload)


def _saved_cookie_names(user_data_dir: Path) -> set[str]:
    cookies_path = user_data_dir / "Default" / "Network" / "Cookies"
    if not cookies_path.exists():
        return set()
    try:
        conn = sqlite3.connect(f"file:{cookies_path}?mode=ro", uri=True)
    except sqlite3.Error:
        return set()
    try:
        cur = conn.cursor()
        rows = cur.execute(
            """
            select name
            from cookies
            where host_key = 'ib.mbrace.or.jp'
            """
        ).fetchall()
    except sqlite3.Error:
        return set()
    finally:
        conn.close()
    return {str(row[0]) for row in rows if row and row[0]}


def _looks_like_saved_login_form_only(user_data_dir: Path) -> bool:
    cookie_names = _saved_cookie_names(user_data_dir)
    if not cookie_names:
        return False
    return cookie_names <= {"memberNoCookie", "pinCookie", "authPasswordCookie"}


def load_credentials(*, require_vote_password: bool) -> TeleboatCredentials:
    _load_env()
    subscriber_no = os.getenv("TELEBOAT_SUBSCRIBER_NO", "").strip()
    pin = os.getenv("TELEBOAT_PIN", "").strip()
    auth_password = os.getenv("TELEBOAT_PASSWORD", "").strip()
    vote_password = os.getenv("TELEBOAT_VOTE_PASSWORD", "").strip() or auth_password

    missing: list[str] = []
    if not subscriber_no:
        missing.append("TELEBOAT_SUBSCRIBER_NO")
    if not pin:
        missing.append("TELEBOAT_PIN")
    if not auth_password:
        missing.append("TELEBOAT_PASSWORD")
    if require_vote_password and not vote_password:
        missing.append("TELEBOAT_VOTE_PASSWORD")

    if missing:
        raise TeleboatConfigurationError("不足している環境変数: " + ", ".join(missing))

    return TeleboatCredentials(
        subscriber_no=subscriber_no,
        pin=pin,
        auth_password=auth_password,
        vote_password=vote_password,
    )


def _settle(page: Page, *, milliseconds: int = 800) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=5_000)
    except PlaywrightTimeoutError:
        pass
    page.wait_for_timeout(milliseconds)


def _count(locator) -> int:
    try:
        return locator.count()
    except PlaywrightError:
        return 0


def _click_first(page: Page, selectors: Iterable[str], *, description: str, timeout_ms: int = 5_000) -> str:
    last_error: Exception | None = None
    for selector in selectors:
        if not selector:
            continue
        locator = page.locator(selector).first
        if _count(locator) == 0:
            continue
        try:
            locator.click(timeout=timeout_ms)
            return selector
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue
    if last_error is not None:
        raise TeleboatError(f"{description} のクリックに失敗しました: {last_error}")
    raise TeleboatError(f"{description} に使える要素が見つかりません")


def _clear_bet_top_click_obstructions(page: Page) -> None:
    for selectors in (
        [
            "#newsoverviewdispCloseButton",
            "#newsoverviewDisp .btn.close a",
            "#newsoverviewDisp .btn.close",
        ],
        [
            "#toNoticeButton a",
            "#toNoticeButton",
        ],
    ):
        try:
            if not _wait_for_any_selector(page, selectors, timeout_ms=500):
                continue
            _click_first(
                page,
                selectors,
                description="お知らせオーバーレイを閉じる",
                timeout_ms=1_500,
            )
            _settle(page, milliseconds=300)
        except Exception:  # noqa: BLE001
            continue

    try:
        page.evaluate(
            """
            () => {
              const hideSelectors = [
                '#overlay',
                '#overlay2',
                '#overlayProgress',
                '#overlayDropDownList',
                '#headerContainer .newsoverviewInfo',
                '#headerContainer pre',
              ];
              const passthroughSelectors = [
                '#headerContainer',
                '#headerContainer *',
              ];

              for (const selector of hideSelectors) {
                for (const element of document.querySelectorAll(selector)) {
                  element.style.setProperty('display', 'none', 'important');
                  element.style.setProperty('visibility', 'hidden', 'important');
                  element.style.setProperty('pointer-events', 'none', 'important');
                }
              }

              for (const selector of passthroughSelectors) {
                for (const element of document.querySelectorAll(selector)) {
                  element.style.setProperty('pointer-events', 'none', 'important');
                }
              }
            }
            """
        )
    except Exception:  # noqa: BLE001
        return


def _wait_for_any_selector(page: Page, selectors: Iterable[str], *, timeout_ms: int = 5_000) -> bool:
    deadline = time.time() + max(1, timeout_ms / 1000)
    candidates = [selector for selector in selectors if selector]
    while time.time() < deadline:
        for selector in candidates:
            locator = page.locator(selector).first
            if _count(locator) == 0:
                continue
            try:
                locator.scroll_into_view_if_needed(timeout=1_000)
            except Exception:  # noqa: BLE001
                pass
            return True
        page.wait_for_timeout(200)
    return False


def _wait_for_regular_value_ready(page: Page, selector: str, *, description: str, timeout_ms: int = 5_000):
    locator = page.locator(selector).first
    last_class_name = ""
    deadline = time.time() + max(1, timeout_ms / 1000)
    while time.time() < deadline:
        if _count(locator) == 0:
            page.wait_for_timeout(150)
            continue
        try:
            locator.scroll_into_view_if_needed(timeout=1_000)
        except Exception:  # noqa: BLE001
            pass
        try:
            if not locator.is_visible(timeout=500):
                page.wait_for_timeout(150)
                continue
            class_name = (locator.get_attribute("class") or "").strip()
            last_class_name = class_name
            if "miss" not in class_name.lower().split():
                return locator
        except Exception:  # noqa: BLE001
            pass
        page.wait_for_timeout(150)
    raise TeleboatError(f"{description} が選択可能状態になりませんでした: class={last_class_name or '-'}")


def _click_regular_value(page: Page, *, selector: str, description: str, timeout_ms: int = 4_000) -> None:
    cell = _wait_for_regular_value_ready(
        page,
        selector,
        description=description,
        timeout_ms=max(timeout_ms, 5_000),
    )
    anchor = page.locator(f"{selector} a").first

    attempts = [
        (anchor, False, False),
        (cell, False, False),
        (anchor, True, False),
        (cell, True, False),
        (anchor, False, True),
        (cell, False, True),
    ]

    last_error: Exception | None = None
    for locator, force, js_click in attempts:
        if _count(locator) == 0:
            continue
        try:
            try:
                locator.scroll_into_view_if_needed(timeout=1_000)
            except Exception:  # noqa: BLE001
                pass
            if js_click:
                locator.evaluate("(el) => { if (el && typeof el.click === 'function') { el.click(); } }")
            else:
                locator.click(timeout=timeout_ms, force=force)
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            page.wait_for_timeout(250)
            continue

    if last_error is not None:
        raise TeleboatError(f"{description} のクリックに失敗しました: {last_error}")
    raise TeleboatError(f"{description} のクリック対象が見つかりませんでした")


def _fill_first(page: Page, selectors: Iterable[str], value: str, *, description: str, timeout_ms: int = 5_000) -> str:
    last_error: Exception | None = None
    for selector in selectors:
        if not selector:
            continue
        locator = page.locator(selector).first
        if _count(locator) == 0:
            continue
        try:
            locator.fill(value, timeout=timeout_ms)
            return selector
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue
    if last_error is not None:
        raise TeleboatError(f"{description} の入力に失敗しました: {last_error}")
    raise TeleboatError(f"{description} の入力欄が見つかりません")


def _exists(page: Page, selectors: Iterable[str]) -> bool:
    for selector in selectors:
        if _count(page.locator(selector).first) > 0:
            return True
    return False


def _visible_exists(page: Page, selectors: Iterable[str]) -> bool:
    for selector in selectors:
        locator = page.locator(selector).first
        if _count(locator) == 0:
            continue
        try:
            if locator.is_visible(timeout=500):
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


def _save_debug_artifacts(page: Page, *, prefix: str, data_dir: Path) -> tuple[str | None, str | None]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_dir = data_dir / "teleboat_screenshots"
    html_dir = data_dir / "teleboat_html"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    html_dir.mkdir(parents=True, exist_ok=True)

    screenshot_path = screenshot_dir / f"{timestamp}_{prefix}.png"
    html_path = html_dir / f"{timestamp}_{prefix}.html"

    try:
        page.screenshot(path=str(screenshot_path), full_page=True)
    except Exception:  # noqa: BLE001
        screenshot_path = None

    try:
        html_path.write_text(page.content(), encoding="utf-8")
    except Exception:  # noqa: BLE001
        html_path = None

    return (
        str(screenshot_path) if screenshot_path is not None else None,
        str(html_path) if html_path is not None else None,
    )


def _current_page_url(page: Page) -> str:
    try:
        return page.url or ""
    except Exception:  # noqa: BLE001
        return ""


def _fill_confirmation_vote_password(
    page: Page,
    *,
    vote_password: str,
    data_dir: Path | None = None,
    debug_prefix: str | None = None,
    retry_wait_ms: int = VOTE_PASSWORD_RETRY_WAIT_MS,
    retry_attempts: int = VOTE_PASSWORD_RETRY_ATTEMPTS,
) -> None:
    for attempt in range(retry_attempts + 1):
        _raise_if_session_timeout(page)
        try:
            _fill_first(
                page,
                list(VOTE_PASSWORD_SELECTORS),
                vote_password,
                description="投票用パスワード",
            )
            return
        except TeleboatError as exc:
            if str(exc) != "投票用パスワード の入力欄が見つかりません":
                raise
            if attempt >= retry_attempts:
                screenshot_path = None
                html_path = None
                if data_dir is not None and debug_prefix:
                    screenshot_path, html_path = _save_debug_artifacts(
                        page,
                        prefix=f"{debug_prefix}_vote_password_missing",
                        data_dir=data_dir,
                    )
                raise TeleboatExecutionError(
                    str(exc),
                    screenshot_path=screenshot_path,
                    html_path=html_path,
                    details={
                        "current_url": _current_page_url(page),
                        "retry_attempts": retry_attempts,
                        "retry_wait_ms": retry_wait_ms,
                    },
                ) from exc
            page.wait_for_timeout(retry_wait_ms)
            _settle(page, milliseconds=500)


def _normalize_visible_text(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def _extract_insufficient_funds_message(text: str | None) -> str | None:
    if not text:
        return None

    for raw_line in str(text).splitlines():
        line = _normalize_visible_text(raw_line)
        if line and any(pattern.search(line) for pattern in INSUFFICIENT_FUNDS_PATTERNS):
            return line[:200]

    merged = _normalize_visible_text(text)
    if merged and any(pattern.search(merged) for pattern in INSUFFICIENT_FUNDS_PATTERNS):
        return merged[:200]
    return None


def _body_text(page: Page) -> str:
    try:
        return page.locator("body").inner_text(timeout=2_000)
    except Exception:  # noqa: BLE001
        return ""


def _is_session_timeout_page(page: Page) -> bool:
    body = _normalize_visible_text(_body_text(page))
    if not body:
        return False
    return all(text in body for text in SESSION_TIMEOUT_TEXTS)


def _session_timeout_error() -> TeleboatError:
    return TeleboatError("Teleboat のセッションが期限切れです。再ログインして操作をやり直してください。")


def _recover_session_timeout_page(page: Page) -> bool:
    if not _is_session_timeout_page(page):
        return True

    try:
        _click_first(
            page,
            [
                "#close",
                'text="閉じる"',
                "a:has-text('閉じる')",
                "button:has-text('閉じる')",
            ],
            description="期限切れ画面を閉じる",
            timeout_ms=2_000,
        )
        _settle(page, milliseconds=500)
    except TeleboatError:
        pass
    except Exception:  # noqa: BLE001
        return False

    try:
        if page.is_closed():
            return False
    except Exception:  # noqa: BLE001
        return False

    if _is_session_timeout_page(page):
        try:
            page.goto(BASE_URL, wait_until="domcontentloaded", timeout=15_000)
            _settle(page, milliseconds=700)
        except Exception:  # noqa: BLE001
            return False

    try:
        if page.is_closed():
            return False
    except Exception:  # noqa: BLE001
        return False

    return not _is_session_timeout_page(page)


def _recover_timeout_or_raise(page: Page) -> None:
    if not _is_session_timeout_page(page):
        return
    if not _recover_session_timeout_page(page):
        raise _session_timeout_error()


def _read_int_from_locator(locator) -> int | None:
    try:
        text = locator.inner_text(timeout=1_000)
    except Exception:  # noqa: BLE001
        return None

    match = re.search(r"\d[\d,]*", text.replace(",", ""))
    if not match:
        return None

    try:
        return int(match.group(0))
    except ValueError:
        return None


def _button_is_enabled(page: Page, selector: str) -> bool:
    locator = page.locator(selector).first
    if _count(locator) == 0:
        return False
    try:
        if not locator.is_visible(timeout=500):
            return False
        class_name = (locator.get_attribute("class") or "").lower()
        return "off" not in class_name.split() and "off" not in class_name
    except Exception:  # noqa: BLE001
        return False


def _current_combination_count(page: Page) -> int:
    for selector in ("#combiCount", ".combinationArea .betBox strong"):
        locator = page.locator(selector).first
        if _count(locator) == 0:
            continue
        value = _read_int_from_locator(locator)
        if value is not None:
            return value
    return 0


def _current_total_bet_count(page: Page) -> int:
    locator = page.locator(".inputCompletion .betNumber strong").first
    if _count(locator) == 0:
        return 0
    value = _read_int_from_locator(locator)
    return value or 0


def _current_total_amount(page: Page) -> int:
    for selector in ("#totalAmount", ".inputCompletion .total strong"):
        locator = page.locator(selector).first
        if _count(locator) == 0:
            continue
        value = _read_int_from_locator(locator)
        if value is not None:
            return value
    return 0


def _current_purchase_limit_amount(page: Page) -> int | None:
    body = _body_text(page)
    if not body:
        return None

    match = re.search(r"購入限度額[^0-9]*(\d[\d,]*)\s*円", body)
    if not match:
        return None

    raw_value = match.group(1).replace(",", "")
    try:
        return int(raw_value)
    except ValueError:
        return None


def _raise_preparation_error(
    page: Page,
    *,
    data_dir: Path,
    debug_prefix: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> None:
    screenshot_path, html_path = _save_debug_artifacts(page, prefix=debug_prefix, data_dir=data_dir)
    raise TeleboatExecutionError(
        message,
        screenshot_path=screenshot_path,
        html_path=html_path,
        details=details or {},
    )


def _insufficient_funds_message(page: Page, *, dialog_messages: Iterable[str] = ()) -> str | None:
    for dialog_message in dialog_messages:
        detected = _extract_insufficient_funds_message(dialog_message)
        if detected:
            return detected
    return _extract_insufficient_funds_message(_body_text(page))


def _raise_if_insufficient_funds(
    page: Page,
    *,
    data_dir: Path,
    debug_prefix: str,
    dialog_messages: Iterable[str] = (),
) -> None:
    detected_message = _insufficient_funds_message(page, dialog_messages=dialog_messages)
    if not detected_message:
        return

    screenshot_path, html_path = _save_debug_artifacts(
        page,
        prefix=f"{debug_prefix}_insufficient_funds",
        data_dir=data_dir,
    )
    raise TeleboatInsufficientFundsError(
        f"資金不足により投票できませんでした: {detected_message}",
        screenshot_path=screenshot_path,
        html_path=html_path,
        details={"detected_message": detected_message},
    )


def _extract_contract_no(page: Page) -> str | None:
    try:
        body = page.locator("body").inner_text(timeout=3_000)
    except Exception:  # noqa: BLE001
        return None

    match = re.search(r"契約番号[^0-9]*([0-9]{4,})", body)
    if match:
        return match.group(1)
    return None


def _session_is_ready(page: Page) -> bool:
    if _is_session_timeout_page(page):
        return False
    if _visible_exists(page, LOGIN_FORM_SELECTORS):
        return False
    return _visible_exists(page, SESSION_READY_SELECTORS)


def _requires_manual_auth(page: Page) -> bool:
    return _visible_exists(page, MANUAL_AUTH_SELECTORS)


def _pick_teleboat_page(context) -> Page:
    candidates: list[tuple[int, Page]] = []
    for page in context.pages:
        current_url = page.url or ""
        score = 0
        if "ib.mbrace.or.jp" in current_url:
            score += 10
        if "/tohyo-ap-pctohyo-web/service/bet/top/" in current_url:
            score += 100
        elif _session_is_ready(page):
            score += 80
        if _is_session_timeout_page(page):
            score -= 100
        if _visible_exists(page, LOGIN_FORM_SELECTORS):
            score -= 20
        candidates.append((score, page))
    if candidates:
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]
    if context.pages:
        return context.pages[0]
    return context.new_page()


def _cleanup_resident_pages(context, *, preferred_page: Page | None = None) -> Page:
    target_page = preferred_page or _pick_teleboat_page(context)
    for page in list(context.pages):
        if page is target_page:
            continue
        current_url = page.url or ""
        if "ib.mbrace.or.jp" not in current_url:
            continue
        try:
            page.close()
        except Exception:  # noqa: BLE001
            continue
    return target_page


def _find_ready_resident_page(context) -> Page | None:
    ready_pages: list[Page] = []
    for page in list(context.pages):
        try:
            if _session_is_ready(page):
                ready_pages.append(page)
        except Exception:  # noqa: BLE001
            continue
    if not ready_pages:
        return None
    if len(ready_pages) == 1:
        return ready_pages[0]

    def _score(page: Page) -> int:
        current_url = page.url or ""
        score = 0
        if "/tohyo-ap-pctohyo-web/service/bet/top/" in current_url:
            score += 100
        elif "/tohyo-ap-pctohyo-web/service/bet/" in current_url:
            score += 50
        if "ib.mbrace.or.jp" in current_url:
            score += 10
        return score

    ready_pages.sort(key=_score, reverse=True)
    return ready_pages[0]


def _resident_teleboat_pages(context) -> list[Page]:
    pages: list[Page] = []
    for page in list(context.pages):
        try:
            if page.is_closed():
                continue
            current_url = page.url or ""
        except Exception:  # noqa: BLE001
            continue
        if "ib.mbrace.or.jp" in current_url:
            pages.append(page)
    return pages


def _refresh_resident_pages(context, *, force_base_url: bool) -> None:
    for page in _resident_teleboat_pages(context):
        try:
            current_url = page.url or ""
        except Exception:  # noqa: BLE001
            current_url = ""

        try:
            needs_navigation = force_base_url or _is_session_timeout_page(page) or _visible_exists(page, LOGIN_FORM_SELECTORS)
        except Exception:  # noqa: BLE001
            needs_navigation = force_base_url

        try:
            if needs_navigation:
                page.goto(BASE_URL, wait_until="domcontentloaded", timeout=15_000)
                _settle(page, milliseconds=700)
                continue

            if current_url:
                page.reload(wait_until="domcontentloaded", timeout=10_000)
                _settle(page, milliseconds=700)
        except Exception:  # noqa: BLE001
            if needs_navigation:
                continue
            try:
                page.goto(BASE_URL, wait_until="domcontentloaded", timeout=15_000)
                _settle(page, milliseconds=700)
            except Exception:  # noqa: BLE001
                continue


def _activate_resident_ready_page(context, *, timeout_seconds: int = 6) -> Page | None:
    deadline = time.time() + max(1, timeout_seconds)
    refreshed = False
    forced_base_url = False
    while time.time() < deadline:
        ready_page = _find_ready_resident_page(context)
        if ready_page is not None:
            return _cleanup_resident_pages(context, preferred_page=ready_page)
        remaining_seconds = deadline - time.time()
        if not refreshed and remaining_seconds > 1:
            _refresh_resident_pages(context, force_base_url=False)
            refreshed = True
            continue
        if not forced_base_url and remaining_seconds > 1:
            _refresh_resident_pages(context, force_base_url=True)
            forced_base_url = True
            continue
        time.sleep(0.5)
    ready_page = _find_ready_resident_page(context)
    if ready_page is not None:
        return _cleanup_resident_pages(context, preferred_page=ready_page)
    return None


def _open_bet_top(page: Page, *, force_navigation: bool = False) -> str:
    current_url = page.url or ""
    if not _recover_session_timeout_page(page):
        raise _session_timeout_error()
    if not force_navigation and "/tohyo-ap-pctohyo-web/service/bet/top/" in current_url:
        if _session_is_ready(page):
            return current_url

    for selector in (
        'text="投票"',
        "a:has-text('投票')",
        "button:has-text('投票')",
        'text="BOAT RACE"',
        "a:has-text('BOAT RACE')",
    ):
        locator = page.locator(selector).first
        if _count(locator) == 0:
            continue
        try:
            locator.click(timeout=2_000)
            _settle(page, milliseconds=700)
            if _is_session_timeout_page(page):
                raise _session_timeout_error()
            if _session_is_ready(page):
                return page.url or current_url
        except Exception:  # noqa: BLE001
            continue

    for url in (BET_TOP_URL,):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=15_000)
            _settle(page, milliseconds=700)
            if _is_session_timeout_page(page):
                raise _session_timeout_error()
            if _session_is_ready(page):
                return page.url or url
        except Exception:  # noqa: BLE001
            continue

    raise TeleboatError("Teleboat ログイン後のトップ画面へ移動できませんでした")


def _fill_login_form(page: Page, credentials: TeleboatCredentials) -> None:
    _fill_first(
        page,
        [
            "#memberNo",
            "input[title='加入者番号']",
            "input[aria-label='加入者番号']",
            "input[name='memberNo']",
            "input[name*='kaiin']",
            "input[name*='subscriber']",
            "input[type='text']",
        ],
        credentials.subscriber_no,
        description="加入者番号",
    )
    _fill_first(
        page,
        [
            "#pin",
            "input[title='暗証番号']",
            "input[aria-label='暗証番号']",
            "input[name='pin']",
            "input[name*='pin']",
            "input[name*='ansho']",
            "input[inputmode='numeric']",
        ],
        credentials.pin,
        description="暗証番号",
    )
    _fill_first(
        page,
        [
            "#authPassword",
            "input[title='認証用パスワード']",
            "input[aria-label='認証用パスワード']",
            "input[name='authPassword']",
            "input[name*='password']",
            "input[type='password']",
        ],
        credentials.auth_password,
        description="認証用パスワード",
    )

    if _exists(page, ('text="ログイン情報を保持する"',)):
        try:
            _click_first(
                page,
                [
                    "label[for='isKeepLoginInfo']",
                    "#isKeepLoginInfo",
                    "label:has-text('ログイン情報を保持する')",
                    "text='ログイン情報を保持する'",
                ],
                description="ログイン情報保持チェック",
                timeout_ms=1_500,
            )
        except TeleboatError:
            pass


def _click_login_button(page: Page) -> None:
    _click_first(
        page,
        [
            "#loginButton",
            "a.btn-login",
            "button:has-text('ログイン')",
            "input[value='ログインする']",
            "input[value='ログイン']",
            "text='ログイン'",
        ],
        description="ログインボタン",
    )


def _wait_for_login_ready(
    page: Page,
    *,
    timeout_seconds: int,
    allow_manual_completion: bool,
    setup_mode: bool,
) -> str:
    deadline = time.time() + max(10, timeout_seconds)
    manual_auth_seen = False
    while time.time() < deadline:
        _settle(page, milliseconds=500)
        if _session_is_ready(page):
            return "logged_in"
        if _requires_manual_auth(page):
            manual_auth_seen = True
            if not allow_manual_completion:
                break
        page.wait_for_timeout(1_000)

    if manual_auth_seen:
        if setup_mode and allow_manual_completion:
            raise TeleboatPreparationPending(
                "Teleboat セッション準備中です。reCAPTCHA または追加認証が表示されている可能性があります。"
                " 表示されたブラウザでログインを完了し、準備完了メッセージが出るまで待ってください。"
            )
        raise TeleboatError("Teleboat ログインに失敗しました。reCAPTCHA または追加認証が必要な可能性があります。")
    if setup_mode and allow_manual_completion:
        raise TeleboatPreparationPending(
            "Teleboat セッション準備を開始しました。表示されたブラウザで手動ログイン後、ブラウザを閉じてから `Teleboat ログイン確認` を実行してください。"
        )
    raise TeleboatError("Teleboat ログインに失敗しました。ログイン後のトップ画面を確認できませんでした。")


def _ensure_login(
    page: Page,
    credentials: TeleboatCredentials,
    *,
    login_timeout_seconds: int,
    allow_manual_completion: bool,
) -> str:
    page.goto(BASE_URL, wait_until="domcontentloaded")
    _settle(page)

    if _session_is_ready(page):
        return "reused_session"

    _fill_login_form(page, credentials)
    _click_login_button(page)
    return _wait_for_login_ready(
        page,
        timeout_seconds=login_timeout_seconds,
        allow_manual_completion=allow_manual_completion,
        setup_mode=False,
    )


def _stadium_name(stadium_code: str, fallback: str | None) -> str:
    normalized_code = str(stadium_code).zfill(2)
    return STADIUM_CODE_TO_NAME.get(normalized_code, str(fallback or normalized_code))


def _select_race(page: Page, *, stadium_code: str, stadium_name: str | None, race_no: int) -> None:
    _open_bet_top(page)
    resolved_name = _stadium_name(stadium_code, stadium_name)
    race_label = f"{int(race_no)}R"

    for attempt in range(2):
        try:
            _clear_bet_top_click_obstructions(page)
            _settle(page, milliseconds=250)
            _click_first(
                page,
                [
                    f"text=\"{resolved_name}\"",
                    f"a:has-text('{resolved_name}')",
                    f"button:has-text('{resolved_name}')",
                ],
                description=f"レース場({resolved_name})",
                timeout_ms=8_000,
            )
            _settle(page)

            _clear_bet_top_click_obstructions(page)
            _settle(page, milliseconds=250)
            _click_first(
                page,
                [
                    f"text=\"{race_label}\"",
                    f"a:has-text('{race_label}')",
                    f"button:has-text('{race_label}')",
                ],
                description=f"レース({race_label})",
                timeout_ms=8_000,
            )
            _settle(page)
            return
        except TeleboatError:
            if attempt == 0:
                _clear_bet_top_click_obstructions(page)
                _open_bet_top(page, force_navigation=True)
                continue
            raise


def _select_group_value(page: Page, *, group_label: str, value_label: str) -> None:
    group_candidates = [
        f"text=\"{group_label}\"",
        f"label:has-text('{group_label}')",
        f"th:has-text('{group_label}')",
        f"td:has-text('{group_label}')",
    ]
    value_candidates = [
        f"text=\"{value_label}\"",
        f"button:has-text('{value_label}')",
        f"a:has-text('{value_label}')",
        f"label:has-text('{value_label}')",
    ]

    for group_selector in group_candidates:
        group_locator = page.locator(group_selector).first
        if _count(group_locator) == 0:
            continue
        for ancestor_depth in (1, 2, 3):
            container = group_locator.locator(
                f"xpath=ancestor::*[self::div or self::section or self::table or self::tr or self::td][{ancestor_depth}]"
            )
            if _count(container) == 0:
                continue
            for value_selector in value_candidates:
                target = container.locator(value_selector).first
                if _count(target) == 0:
                    continue
                try:
                    target.click(timeout=3_000)
                    return
                except Exception:  # noqa: BLE001
                    continue

    all_matches = page.locator(f"text=\"{value_label}\"")
    if _count(all_matches) > 0:
        try:
            all_matches.first.click(timeout=3_000)
            return
        except Exception as exc:  # noqa: BLE001
            raise TeleboatError(f"{group_label} の {value_label} を選べませんでした: {exc}") from exc

    raise TeleboatError(f"{group_label} の {value_label} を選ぶ要素が見つかりません")


def _select_regular_value(page: Page, *, column_index: int, token: str) -> None:
    normalized = token.strip().upper()
    if not normalized or normalized == "ALL":
        raise TeleboatError(f"通常投票では使えない組番です: {token}")

    selector = f"#regbtn_{normalized}_{int(column_index)}"
    _click_first(
        page,
        [
            f"{selector} a",
            selector,
        ],
        description=f"通常投票 {column_index}列 {normalized}",
        timeout_ms=3_000,
    )
    _settle(page, milliseconds=250)


def _select_regular_value(page: Page, *, column_index: int, token: str) -> None:
    normalized = token.strip().upper()
    if not normalized or normalized == "ALL":
        raise TeleboatError(f"騾壼ｸｸ謚慕･ｨ縺ｧ縺ｯ菴ｿ縺医↑縺・ｵ・分縺ｧ縺・ {token}")

    selector = f"#regbtn_{normalized}_{int(column_index)}"
    _click_regular_value(
        page,
        selector=selector,
        description=f"騾壼ｸｸ謚慕･ｨ {column_index}蛻・{normalized}",
        timeout_ms=4_000,
    )
    _settle(page, milliseconds=250)


def _select_method_and_bet_type(
    page: Page,
    *,
    method_label: str,
    bet_type_label: str,
    method_selector: str | None = None,
    bet_type_selector: str | None = None,
) -> None:
    method_candidates = [
        method_selector or "",
        f"{method_selector} a" if method_selector else "",
        METHOD_SELECTOR_MAP.get(method_label, ""),
        f"text=\"{method_label}\"",
        f"button:has-text('{method_label}')",
        f"a:has-text('{method_label}')",
    ]
    if not _wait_for_any_selector(page, method_candidates, timeout_ms=5_000):
        raise TeleboatError(f"投票方法({method_label}) に使える要素が見つかりません")
    _click_first(
        page,
        method_candidates,
        description=f"投票方法({method_label})",
        timeout_ms=5_000,
    )
    _settle(page, milliseconds=500)
    bet_type_candidates = [
        bet_type_selector or "",
        f"{bet_type_selector} a" if bet_type_selector else "",
        BET_TYPE_SELECTOR_MAP.get(bet_type_label, ""),
        f"text=\"{bet_type_label}\"",
        f"button:has-text('{bet_type_label}')",
        f"a:has-text('{bet_type_label}')",
    ]
    if not _wait_for_any_selector(page, bet_type_candidates, timeout_ms=5_000):
        raise TeleboatError(f"勝式({bet_type_label}) に使える要素が見つかりません")
    _click_first(
        page,
        bet_type_candidates,
        description=f"勝式({bet_type_label})",
        timeout_ms=5_000,
    )
    _settle(page, milliseconds=500)


def _fill_amount(page: Page, amount: int) -> None:
    normalized_amount = max(0, int(amount))
    # On the bet list screen the UI appends "00円", so entering "1" means 100 yen.
    entry_units = max(1, normalized_amount // 100) if normalized_amount > 0 else 0
    value = str(entry_units)
    selectors = [
        "#amount",
        "input[title*='購入金額']",
        "input[aria-label*='購入金額']",
        "input[name*='kingaku']",
        "input[name*='amount']",
        "input[name*='money']",
        "input[inputmode='numeric']",
    ]
    try:
        _fill_first(page, selectors, value, description="購入金額", timeout_ms=2_500)
        return
    except TeleboatError:
        pass

    numeric_inputs = page.locator("input[type='text'], input[type='tel'], input[type='number']")
    count = _count(numeric_inputs)
    for index in range(max(0, count - 3), count):
        locator = numeric_inputs.nth(index)
        try:
            locator.fill(value, timeout=1_500)
            return
        except Exception:  # noqa: BLE001
            continue

    raise TeleboatError("購入金額の入力欄を特定できませんでした")


def _current_confirmation_total_amount(page: Page) -> int:
    for selector in ("#betconfTotalBetAmount", "#totalAmount", ".confirmationBox1 strong"):
        locator = page.locator(selector).first
        if _count(locator) == 0:
            continue
        value = _read_int_from_locator(locator)
        if value is not None:
            return value
    return 0


def _select_formation_value(page: Page, *, column_index: int, token: str) -> None:
    normalized = token.strip().upper()
    if normalized == "ALL":
        selectors = [
            f".combiAll.forma{column_index} a",
            f".combiAll.forma{column_index}",
        ]
    else:
        selectors = [
            f".combiForma.x{normalized}.y{column_index} a",
            f".combiForma.x{normalized}.y{column_index}",
        ]

    _click_first(
        page,
        selectors,
        description=f"フォーメーション {column_index}着={normalized}",
        timeout_ms=3_000,
    )
    _settle(page, milliseconds=250)


def _confirm_combination_selection(
    page: Page,
    *,
    method_label: str,
    method_key: str | None = None,
    data_dir: Path,
    debug_prefix: str,
) -> int:
    confirm_selector_map = {
        "ボックス投票": "#combiConfirmBtnBox",
        "フォーメーション投票": "#combiConfirmBtnForma",
    }
    confirm_selector = COMBINATION_CONFIRM_SELECTOR_BY_METHOD_KEY.get(method_key or "", "") or confirm_selector_map.get(method_label)
    if not confirm_selector:
        return max(1, _current_combination_count(page))

    deadline = time.time() + 5
    while time.time() < deadline:
        count = _current_combination_count(page)
        if count > 0:
            return count
        if _button_is_enabled(page, confirm_selector):
            _click_first(
                page,
                [confirm_selector, f"{confirm_selector} a"],
                description="組合せ確認",
                timeout_ms=3_000,
            )
            _settle(page, milliseconds=500)
        page.wait_for_timeout(250)

    _raise_preparation_error(
        page,
        data_dir=data_dir,
        debug_prefix=debug_prefix,
        message="組合せ確認まで進みませんでした",
        details={
            "method_label": method_label,
            "combination_count": _current_combination_count(page),
            "confirm_enabled": _button_is_enabled(page, confirm_selector),
        },
    )


def _wait_for_betlist_update(
    page: Page,
    *,
    previous_total_amount: int,
    previous_bet_count: int,
    expected_increment: int,
    data_dir: Path,
    debug_prefix: str,
) -> None:
    deadline = time.time() + 8
    while time.time() < deadline:
        total_amount = _current_total_amount(page)
        total_bets = _current_total_bet_count(page)
        if total_amount >= previous_total_amount + expected_increment and total_bets > previous_bet_count:
            return
        page.wait_for_timeout(250)

    _raise_preparation_error(
        page,
        data_dir=data_dir,
        debug_prefix=debug_prefix,
        message="ベットリストへの追加が反映されませんでした",
        details={
            "previous_total_amount": previous_total_amount,
            "current_total_amount": _current_total_amount(page),
            "previous_bet_count": previous_bet_count,
            "current_bet_count": _current_total_bet_count(page),
            "expected_increment": expected_increment,
        },
    )


def _add_intent_to_bet_list(
    page: Page,
    *,
    bet_type: str,
    combo: str,
    amount: int,
    data_dir: Path,
    debug_prefix: str,
) -> int:
    bet_type_label = BET_TYPE_TO_LABEL.get(str(bet_type).lower())
    if not bet_type_label:
        raise TeleboatError(f"未対応の券種です: {bet_type}")

    parts = [part.strip().upper() for part in str(combo).split("-") if part.strip()]
    if not parts:
        raise TeleboatError(f"組番の形式が不正です: {combo}")

    previous_total_amount = _current_total_amount(page)
    previous_bet_count = _current_total_bet_count(page)
    method_label = "フォーメーション投票" if "ALL" in parts else "通常投票"
    _select_method_and_bet_type(page, method_label=method_label, bet_type_label=bet_type_label)

    if method_label == "通常投票":
        for index, token in enumerate(parts, start=1):
            _select_regular_value(page, column_index=index, token=token)
        combination_count = 1
    else:
        for index, token in enumerate(parts, start=1):
            _select_formation_value(page, column_index=index, token=token)
        combination_count = _confirm_combination_selection(
            page,
            method_label=method_label,
            data_dir=data_dir,
            debug_prefix=f"{debug_prefix}_combination",
        )

    _fill_amount(page, amount)
    add_button_map = {
        "通常投票": "#regAmountBtn",
        "ボックス投票": "#boxAmountBtn",
        "フォーメーション投票": "#formaAmountBtn",
    }
    add_button_selector = add_button_map.get(method_label, "#formaAmountBtn")
    if not _button_is_enabled(page, add_button_selector):
        _raise_preparation_error(
            page,
            data_dir=data_dir,
            debug_prefix=f"{debug_prefix}_betlist_disabled",
            message="ベットリスト追加ボタンが有効化されませんでした",
            details={
                "method_label": method_label,
                "combination_count": combination_count,
                "amount": amount,
                "button_selector": add_button_selector,
            },
        )

    _click_first(
        page,
        [
            add_button_selector,
            f"{add_button_selector} a",
            "text=\"ベットリストに追加\"",
            "button:has-text('ベットリストに追加')",
            "input[value='ベットリストに追加']",
        ],
        description="ベットリストに追加",
        timeout_ms=8_000,
    )
    _settle(page, milliseconds=500)
    _wait_for_betlist_update(
        page,
        previous_total_amount=previous_total_amount,
        previous_bet_count=previous_bet_count,
        expected_increment=combination_count * amount,
        data_dir=data_dir,
        debug_prefix=f"{debug_prefix}_betlist_update",
    )
    return combination_count


def _add_intent_to_bet_list(
    page: Page,
    *,
    bet_type: str,
    combo: str,
    amount: int,
    data_dir: Path,
    debug_prefix: str,
) -> int:
    bet_type_label = BET_TYPE_TO_LABEL.get(str(bet_type).lower())
    if not bet_type_label:
        raise TeleboatError(f"譛ｪ蟇ｾ蠢懊・蛻ｸ遞ｮ縺ｧ縺・ {bet_type}")

    parts = [part.strip().upper() for part in str(combo).split("-") if part.strip()]
    if not parts:
        raise TeleboatError(f"邨・分縺ｮ蠖｢蠑上′荳肴ｭ｣縺ｧ縺・ {combo}")

    previous_total_amount = _current_total_amount(page)
    previous_bet_count = _current_total_bet_count(page)
    method_label = "繝輔か繝ｼ繝｡繝ｼ繧ｷ繝ｧ繝ｳ謚慕･ｨ" if "ALL" in parts else "騾壼ｸｸ謚慕･ｨ"

    try:
        _select_method_and_bet_type(page, method_label=method_label, bet_type_label=bet_type_label)

        if method_label == "騾壼ｸｸ謚慕･ｨ":
            for index, token in enumerate(parts, start=1):
                _select_regular_value(page, column_index=index, token=token)
            combination_count = 1
        else:
            for index, token in enumerate(parts, start=1):
                _select_formation_value(page, column_index=index, token=token)
            combination_count = _confirm_combination_selection(
                page,
                method_label=method_label,
                data_dir=data_dir,
                debug_prefix=f"{debug_prefix}_combination",
            )

        _fill_amount(page, amount)
    except TeleboatExecutionError:
        raise
    except TeleboatError as exc:
        _raise_preparation_error(
            page,
            data_dir=data_dir,
            debug_prefix=f"{debug_prefix}_selection",
            message=str(exc),
            details={
                "bet_type": bet_type,
                "bet_type_label": bet_type_label,
                "combo": combo,
                "parts": parts,
                "amount": amount,
                "method_label": method_label,
                "current_url": page.url or "",
            },
        )

    add_button_map = {
        "騾壼ｸｸ謚慕･ｨ": "#regAmountBtn",
        "繝懊ャ繧ｯ繧ｹ謚慕･ｨ": "#boxAmountBtn",
        "繝輔か繝ｼ繝｡繝ｼ繧ｷ繝ｧ繝ｳ謚慕･ｨ": "#formaAmountBtn",
    }
    add_button_selector = add_button_map.get(method_label, "#formaAmountBtn")
    if not _button_is_enabled(page, add_button_selector):
        _raise_preparation_error(
            page,
            data_dir=data_dir,
            debug_prefix=f"{debug_prefix}_betlist_disabled",
            message="繝吶ャ繝医Μ繧ｹ繝郁ｿｽ蜉繝懊ち繝ｳ縺梧怏蜉ｹ蛹悶＆繧後∪縺帙ｓ縺ｧ縺励◆",
            details={
                "method_label": method_label,
                "combination_count": combination_count,
                "amount": amount,
                "button_selector": add_button_selector,
            },
        )

    _click_first(
        page,
        [
            add_button_selector,
            f"{add_button_selector} a",
            "text=\"繝吶ャ繝医Μ繧ｹ繝医↓霑ｽ蜉\"",
            "button:has-text('繝吶ャ繝医Μ繧ｹ繝医↓霑ｽ蜉')",
            "input[value='繝吶ャ繝医Μ繧ｹ繝医↓霑ｽ蜉']",
        ],
        description="繝吶ャ繝医Μ繧ｹ繝医↓霑ｽ蜉",
        timeout_ms=8_000,
    )
    _settle(page, milliseconds=500)
    _wait_for_betlist_update(
        page,
        previous_total_amount=previous_total_amount,
        previous_bet_count=previous_bet_count,
        expected_increment=combination_count * amount,
        data_dir=data_dir,
        debug_prefix=f"{debug_prefix}_betlist_update",
    )
    return combination_count


def _add_intent_to_bet_list(
    page: Page,
    *,
    bet_type: str,
    combo: str,
    amount: int,
    data_dir: Path,
    debug_prefix: str,
) -> int:
    bet_type_label = BET_TYPE_TO_LABEL.get(str(bet_type).lower())
    if not bet_type_label:
        raise TeleboatError(f"未対応の券種です: {bet_type}")

    parts = [part.strip().upper() for part in str(combo).split("-") if part.strip()]
    if not parts:
        raise TeleboatError(f"組番の形式が不正です: {combo}")

    previous_total_amount = _current_total_amount(page)
    previous_bet_count = _current_total_bet_count(page)
    method_key = "formation" if "ALL" in parts else "regular"
    method_label = "フォーメーション投票" if method_key == "formation" else "通常投票"
    method_selector = METHOD_SELECTOR_BY_KEY.get(method_key)
    bet_type_selector = BET_TYPE_SELECTOR_BY_CODE.get(str(bet_type).lower())

    try:
        _select_method_and_bet_type(
            page,
            method_label=method_label,
            bet_type_label=bet_type_label,
            method_selector=method_selector,
            bet_type_selector=bet_type_selector,
        )

        if method_key == "regular":
            for index, token in enumerate(parts, start=1):
                _select_regular_value(page, column_index=index, token=token)
            combination_count = 1
        else:
            for index, token in enumerate(parts, start=1):
                _select_formation_value(page, column_index=index, token=token)
            combination_count = _confirm_combination_selection(
                page,
                method_label=method_label,
                method_key=method_key,
                data_dir=data_dir,
                debug_prefix=f"{debug_prefix}_combination",
            )

        _fill_amount(page, amount)
    except TeleboatExecutionError:
        raise
    except TeleboatError as exc:
        _raise_preparation_error(
            page,
            data_dir=data_dir,
            debug_prefix=f"{debug_prefix}_selection",
            message=str(exc),
            details={
                "bet_type": bet_type,
                "bet_type_label": bet_type_label,
                "combo": combo,
                "parts": parts,
                "amount": amount,
                "method_key": method_key,
                "method_label": method_label,
                "method_selector": method_selector,
                "bet_type_selector": bet_type_selector,
                "current_url": page.url or "",
            },
        )

    add_button_selector = ADD_BUTTON_SELECTOR_BY_METHOD_KEY.get(method_key, "#formaAmountBtn")
    if not _button_is_enabled(page, add_button_selector):
        _raise_preparation_error(
            page,
            data_dir=data_dir,
            debug_prefix=f"{debug_prefix}_betlist_disabled",
            message="ベットリスト追加ボタンが有効化されませんでした",
            details={
                "method_key": method_key,
                "method_label": method_label,
                "combination_count": combination_count,
                "amount": amount,
                "button_selector": add_button_selector,
            },
        )

    _click_first(
        page,
        [
            add_button_selector,
            f"{add_button_selector} a",
            "text=\"ベットリストに追加\"",
            "button:has-text('ベットリストに追加')",
            "input[value='ベットリストに追加']",
        ],
        description="ベットリストに追加",
        timeout_ms=8_000,
    )
    _settle(page, milliseconds=500)
    _wait_for_betlist_update(
        page,
        previous_total_amount=previous_total_amount,
        previous_bet_count=previous_bet_count,
        expected_increment=combination_count * amount,
        data_dir=data_dir,
        debug_prefix=f"{debug_prefix}_betlist_update",
    )
    return combination_count


def _open_confirmation(page: Page, *, data_dir: Path, debug_prefix: str) -> None:
    if not _button_is_enabled(page, ".btnSubmit"):
        _raise_preparation_error(
            page,
            data_dir=data_dir,
            debug_prefix=f"{debug_prefix}_submit_disabled",
            message="投票入力完了ボタンが有効になっていません",
            details={
                "total_bet_count": _current_total_bet_count(page),
                "total_amount": _current_total_amount(page),
            },
        )

    _click_first(
        page,
        [
            ".btnSubmit a",
            "text=\"投票入力完了\"",
            "text=\"投票確認完了\"",
            "button:has-text('投票入力完了')",
            "button:has-text('投票確認完了')",
            "input[value='投票入力完了']",
            "input[value='投票確認完了']",
        ],
        description="投票確認画面へ進む",
        timeout_ms=8_000,
    )
    _settle(page)

    deadline = time.time() + 8
    while time.time() < deadline:
        current_url = page.url or ""
        if "/service/bet/betconf" in current_url:
            return
        if _exists(
            page,
            (
                "input[name*='vote']",
                "input[title='投票用パスワード']",
                'text="投票する"',
            ),
        ):
            return
        page.wait_for_timeout(250)

    _raise_preparation_error(
        page,
        data_dir=data_dir,
        debug_prefix=f"{debug_prefix}_confirm_page",
        message="確認画面への遷移を確認できませんでした",
        details={"current_url": page.url or ""},
    )


def _submit_vote(
    page: Page,
    *,
    vote_password: str,
    total_amount: int | None = None,
    data_dir: Path | None = None,
    debug_prefix: str | None = None,
) -> list[str]:
    _prefill_confirmation_inputs(
        page,
        vote_password=vote_password,
        total_amount=total_amount,
        data_dir=data_dir,
        debug_prefix=debug_prefix,
    )

    dialog_seen: list[str] = []

    def _dialog_handler(dialog) -> None:
        dialog_seen.append(dialog.message)
        dialog.accept()

    page.on("dialog", _dialog_handler)
    try:
        _click_first(
            page,
            [
                "text=\"投票する\"",
                "button:has-text('投票する')",
                "input[value='投票する']",
            ],
            description="投票する",
            timeout_ms=8_000,
        )
        page.wait_for_timeout(700)
        if _exists(page, ('text="OK"', "button:has-text('OK')", "input[value='OK']")):
            _click_first(
                page,
                [
                    'text="OK"',
                    "button:has-text('OK')",
                    "input[value='OK']",
                ],
                description="最終OK",
                timeout_ms=5_000,
            )
        _settle(page)
    finally:
        page.remove_listener("dialog", _dialog_handler)
    return dialog_seen


def _prefill_confirmation_inputs(
    page: Page,
    *,
    vote_password: str,
    total_amount: int | None = None,
    data_dir: Path | None = None,
    debug_prefix: str | None = None,
) -> int:
    confirmation_total_amount = int(total_amount) if total_amount is not None else _current_confirmation_total_amount(page)
    if confirmation_total_amount > 0:
        _fill_first(
            page,
            [
                "input[name='betAmount']",
                "#betconfForm #amount",
                "input[title='購入金額']",
                "input[aria-label='購入金額']",
            ],
            str(confirmation_total_amount),
            description="確認画面の購入金額",
        )

    _fill_confirmation_vote_password(
        page,
        vote_password=vote_password,
        data_dir=data_dir,
        debug_prefix=debug_prefix,
    )
    return confirmation_total_amount


def _wait_for_manual_submit(page: Page, *, timeout_seconds: int) -> bool:
    deadline = time.time() + max(10, timeout_seconds)
    while time.time() < deadline:
        if _exists(page, ('text="投票結果"', 'text="同じ場で投票する"', 'text="契約番号"')):
            return True
        page.wait_for_timeout(1_000)
    return False


def _wait_for_manual_submit_or_raise(
    page: Page,
    *,
    timeout_seconds: int,
    data_dir: Path,
    debug_prefix: str,
) -> bool:
    deadline = time.time() + max(10, timeout_seconds)
    dialog_seen: list[str] = []

    def _dialog_handler(dialog) -> None:
        dialog_seen.append(dialog.message)
        dialog.accept()

    page.on("dialog", _dialog_handler)
    try:
        while time.time() < deadline:
            _raise_if_insufficient_funds(
                page,
                data_dir=data_dir,
                debug_prefix=debug_prefix,
                dialog_messages=dialog_seen,
            )
            dialog_seen.clear()
            if _exists(page, VOTE_SUCCESS_SELECTORS) or _extract_contract_no(page):
                return True
            page.wait_for_timeout(1_000)
    finally:
        page.remove_listener("dialog", _dialog_handler)
    return False


def _wait_for_submit_outcome(
    page: Page,
    *,
    data_dir: Path,
    debug_prefix: str,
    dialog_messages: Iterable[str],
) -> None:
    deadline = time.time() + 15
    while time.time() < deadline:
        _raise_if_insufficient_funds(
            page,
            data_dir=data_dir,
            debug_prefix=debug_prefix,
            dialog_messages=dialog_messages,
        )
        if _exists(page, VOTE_SUCCESS_SELECTORS) or _extract_contract_no(page):
            return
        page.wait_for_timeout(500)

    _raise_if_insufficient_funds(
        page,
        data_dir=data_dir,
        debug_prefix=debug_prefix,
        dialog_messages=dialog_messages,
    )


def _raise_if_session_timeout(page: Page) -> None:
    if not _recover_session_timeout_page(page):
        raise _session_timeout_error()


def _lookup_last_contract(page: Page) -> str | None:
    if _extract_contract_no(page):
        return _extract_contract_no(page)

    try:
        _click_first(
            page,
            [
                'text="照会"',
                "a:has-text('照会')",
                "button:has-text('照会')",
            ],
            description="照会メニュー",
            timeout_ms=3_000,
        )
        _settle(page, milliseconds=500)
        _click_first(
            page,
            [
                'text="直前の契約を見る"',
                "a:has-text('直前の契約を見る')",
                "button:has-text('直前の契約を見る')",
            ],
            description="直前の契約を見る",
            timeout_ms=5_000,
        )
        _settle(page)
    except TeleboatError:
        return None
    return _extract_contract_no(page)


class TeleboatClient:
    def __init__(self, *, data_dir: Path, settings: dict[str, Any]) -> None:
        self._data_dir = data_dir
        self._settings = settings
        user_data_dir = Path(str(settings.get("teleboat_user_data_dir", data_dir / "playwright_user_data")))
        user_data_dir.mkdir(parents=True, exist_ok=True)
        self._user_data_dir = user_data_dir
        self._storage_state_path = _teleboat_storage_state_path(data_dir)
        self._saved_login_form_only = _looks_like_saved_login_form_only(user_data_dir)
        self._manual_action_timeout_seconds = int(settings.get("manual_action_timeout_seconds", 180))
        self._login_timeout_seconds = int(settings.get("login_timeout_seconds", 120))
        self._headless = bool(settings.get("real_headless", False))
        self._setup_mode = bool(settings.get("teleboat_setup_mode", False))
        self._resident_browser = bool(settings.get("teleboat_resident_browser", True)) and not self._headless
        self._resident_debug_port = int(settings.get("teleboat_resident_debug_port", 9333))
        self._use_persistent_context = False
        self._connected_to_resident_browser = False
        self._playwright = None
        self._browser = None
        self._context = None
        self._page: Page | None = None
        self._credentials: TeleboatCredentials | None = None

    def __enter__(self) -> "TeleboatClient":
        self._playwright = sync_playwright().start()
        self._use_persistent_context = (self._setup_mode or not self._storage_state_path.exists()) and not self._resident_browser
        try:
            if self._resident_browser:
                self._connect_to_resident_browser()
            elif self._use_persistent_context:
                self._context = self._playwright.chromium.launch_persistent_context(
                    user_data_dir=str(self._user_data_dir),
                    headless=self._headless,
                    viewport={"width": 1600, "height": 1100},
                )
            else:
                self._browser = self._playwright.chromium.launch(headless=self._headless)
                context_kwargs: dict[str, Any] = {
                    "viewport": {"width": 1600, "height": 1100},
                }
                if self._storage_state_path.exists():
                    context_kwargs["storage_state"] = str(self._storage_state_path)
                self._context = self._browser.new_context(**context_kwargs)
        except PlaywrightError as exc:
            if self._browser is not None:
                self._browser.close()
                self._browser = None
            if self._playwright is not None:
                self._playwright.stop()
                self._playwright = None
            lock_paths = _profile_lock_paths(self._user_data_dir)
            if self._use_persistent_context and ("launch_persistent_context" in str(exc) or "browser has been closed" in str(exc)):
                detail = ""
                if lock_paths:
                    detail = " lock=" + ", ".join(path.name for path in lock_paths)
                raise TeleboatError(
                    "Teleboat セッションを開けませんでした。同じ user data dir を使う Google Chrome for Testing / Playwright が起動中か、"
                    "前回の lock が残っています。ブラウザを閉じてから再度実行してください。"
                    f"{detail}"
                ) from exc
            raise
        if self._connected_to_resident_browser:
            self._page = _cleanup_resident_pages(self._context)
        else:
            self._page = _pick_teleboat_page(self._context)
        return self

    def _connect_to_resident_browser(self) -> None:
        if self._playwright is None:
            raise TeleboatError("Playwright が初期化されていません")

        port = self._resident_debug_port
        executable_path = self._playwright.chromium.executable_path
        if not _is_port_open(port):
            lock_paths = _profile_lock_paths(self._user_data_dir)
            if lock_paths:
                detail = " lock=" + ", ".join(path.name for path in lock_paths)
            else:
                detail = ""
            process = _launch_resident_browser(
                executable_path=executable_path,
                user_data_dir=self._user_data_dir,
                port=port,
            )
            if not _wait_for_port(port, timeout_seconds=20):
                raise TeleboatError(
                    "Teleboat 常駐ブラウザを起動できませんでした。Google Chrome for Testing の起動に失敗した可能性があります。"
                    f"{detail}"
                )
            _record_resident_browser_state(
                self._data_dir,
                status="running",
                port=port,
                user_data_dir=self._user_data_dir,
                pid=process.pid,
                executable_path=executable_path,
                message="Teleboat 常駐ブラウザを起動しました。",
            )
        else:
            _record_resident_browser_state(
                self._data_dir,
                status="running",
                port=port,
                user_data_dir=self._user_data_dir,
                executable_path=executable_path,
                message="Teleboat 常駐ブラウザへ接続します。",
            )

        self._browser = self._playwright.chromium.connect_over_cdp(_resident_debug_url(port))
        self._connected_to_resident_browser = True
        if not self._browser.contexts:
            raise TeleboatError("Teleboat 常駐ブラウザへ接続できましたが、利用可能な context がありません。")
        self._context = self._browser.contexts[0]

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._context is not None and not self._connected_to_resident_browser:
            self._context.close()
        if self._browser is not None and not self._connected_to_resident_browser:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()

    @property
    def page(self) -> Page:
        if self._page is None:
            raise TeleboatError("Playwright page が初期化されていません")
        return self._page

    def _save_storage_state(self) -> None:
        if self._context is None:
            return
        self._storage_state_path.parent.mkdir(parents=True, exist_ok=True)
        self._context.storage_state(path=str(self._storage_state_path))

    def _record_session(self, *, status: str, message: str, session_state: str | None = None, refresh_validity: bool = False) -> None:
        _record_teleboat_session_state(
            self._data_dir,
            status=status,
            message=message,
            user_data_dir=self._user_data_dir,
            session_state=session_state,
            refresh_validity=refresh_validity,
        )

    def ensure_session(self) -> str:
        page = self.page
        if self._connected_to_resident_browser and self._context is not None:
            resident_ready_page = _activate_resident_ready_page(self._context, timeout_seconds=3)
            if resident_ready_page is not None:
                self._page = resident_ready_page
                page = resident_ready_page
        _settle(page)
        try:
            _recover_timeout_or_raise(page)
        except TeleboatError as exc:
            self._record_session(status="login_required", message=str(exc), session_state="login_required")
            raise
        if _session_is_ready(page):
            try:
                _open_bet_top(page)
            except TeleboatError:
                pass
            try:
                _raise_if_session_timeout(page)
            except TeleboatError as exc:
                self._record_session(status="login_required", message=str(exc), session_state="login_required")
                raise
            self._save_storage_state()
            self._record_session(
                status="verified",
                message="Teleboat 保存セッションを再利用できました。",
                session_state="reused_session",
                refresh_validity=False,
            )
            return "reused_session"

        page.goto(BASE_URL, wait_until="domcontentloaded")
        _settle(page)
        if self._connected_to_resident_browser and self._context is not None:
            resident_ready_page = _activate_resident_ready_page(self._context, timeout_seconds=5)
            if resident_ready_page is not None:
                self._page = resident_ready_page
                page = resident_ready_page
        try:
            _recover_timeout_or_raise(page)
        except TeleboatError as exc:
            self._record_session(status="login_required", message=str(exc), session_state="login_required")
            raise
        if _session_is_ready(page):
            try:
                _open_bet_top(page)
            except TeleboatError:
                pass
            try:
                _raise_if_session_timeout(page)
            except TeleboatError as exc:
                self._record_session(status="login_required", message=str(exc), session_state="login_required")
                raise
            self._save_storage_state()
            self._record_session(
                status="verified",
                message="Teleboat 保存セッションを再利用できました。",
                session_state="reused_session",
                refresh_validity=False,
            )
            return "reused_session"

        if self._credentials is None:
            self._credentials = load_credentials(require_vote_password=False)
        try:
            session_state = _ensure_login(
                page,
                self._credentials,
                login_timeout_seconds=self._login_timeout_seconds,
                allow_manual_completion=not self._headless,
            )
        except TeleboatError as exc:
            payload = load_teleboat_session_state(self._data_dir)
            hint = _format_session_hint(payload)
            message = str(exc)
            if hint:
                message = f"{message} / {hint} / `Teleboat セッション準備` をやり直してください。"
            if (not self._storage_state_path.exists()) and self._saved_login_form_only:
                message = (
                    f"{message} / `ログイン情報を保持する(7日間有効)` で残っているのは入力補助 cookie のみで、"
                    "ログイン済みセッション自体は再利用できていない可能性があります。"
                )
            self._record_session(status="login_required", message=message, session_state="login_required")
            raise TeleboatError(message) from exc

        if self._connected_to_resident_browser and self._context is not None:
            resident_ready_page = _activate_resident_ready_page(
                self._context,
                timeout_seconds=max(3, self._login_timeout_seconds // 2),
            )
            if resident_ready_page is not None:
                self._page = resident_ready_page
                page = resident_ready_page

        try:
            _open_bet_top(page)
        except TeleboatError:
            pass
        try:
            _recover_timeout_or_raise(page)
        except TeleboatError as exc:
            self._record_session(status="login_required", message=str(exc), session_state="login_required")
            raise
        self._save_storage_state()
        self._record_session(
            status="verified",
            message="Teleboat セッション確認が完了しました。",
            session_state=session_state,
            refresh_validity=(session_state == "logged_in"),
        )
        return session_state

    def prepare_session(self) -> str:
        if self._headless:
            raise TeleboatConfigurationError("Teleboat セッション準備は headless=False で実行してください。")

        self._record_session(
            status="preparing",
            message="Teleboat 常駐ブラウザを開きました。必要に応じて手動ログインを完了してください。",
            session_state="preparing",
            refresh_validity=False,
        )
        page = self.page
        if self._connected_to_resident_browser and self._context is not None:
            resident_ready_page = _activate_resident_ready_page(self._context, timeout_seconds=3)
            if resident_ready_page is not None:
                self._page = resident_ready_page
                page = resident_ready_page
        _settle(page)
        try:
            _recover_timeout_or_raise(page)
        except TeleboatError as exc:
            self._record_session(status="login_required", message=str(exc), session_state="login_required")
            raise
        if _session_is_ready(page):
            try:
                _open_bet_top(page)
            except TeleboatError:
                pass
            try:
                _raise_if_session_timeout(page)
            except TeleboatError as exc:
                self._record_session(status="login_required", message=str(exc), session_state="login_required")
                raise
            self._save_storage_state()
            self._record_session(
                status="prepared",
                message="Teleboat セッションはすでに有効です。",
                session_state="reused_session",
                refresh_validity=True,
            )
            return "reused_session"

        page.goto(BASE_URL, wait_until="domcontentloaded")
        _settle(page)
        if self._connected_to_resident_browser and self._context is not None:
            resident_ready_page = _activate_resident_ready_page(self._context, timeout_seconds=5)
            if resident_ready_page is not None:
                self._page = resident_ready_page
                page = resident_ready_page
        try:
            _recover_timeout_or_raise(page)
        except TeleboatError as exc:
            self._record_session(status="login_required", message=str(exc), session_state="login_required")
            raise
        if _session_is_ready(page):
            try:
                _open_bet_top(page)
            except TeleboatError:
                pass
            try:
                _raise_if_session_timeout(page)
            except TeleboatError as exc:
                self._record_session(status="login_required", message=str(exc), session_state="login_required")
                raise
            self._save_storage_state()
            self._record_session(
                status="prepared",
                message="Teleboat セッションはすでに有効です。",
                session_state="reused_session",
                refresh_validity=True,
            )
            return "reused_session"

        if self._credentials is None:
            self._credentials = load_credentials(require_vote_password=False)

        _fill_login_form(page, self._credentials)
        try:
            _click_login_button(page)
        except TeleboatError:
            # 手動ログイン画面の差分で自動クリックできなくても、表示ブラウザ上で継続できるようにする。
            pass
        try:
            session_state = _wait_for_login_ready(
                page,
                timeout_seconds=max(self._login_timeout_seconds, self._manual_action_timeout_seconds),
                allow_manual_completion=True,
                setup_mode=True,
            )
        except TeleboatPreparationPending as exc:
            self._record_session(
                status="pending_verification",
                message=str(exc),
                session_state="pending_verification",
                refresh_validity=False,
            )
            raise
        except TeleboatError as exc:
            self._record_session(status="login_required", message=str(exc), session_state="login_required")
            raise

        if self._connected_to_resident_browser and self._context is not None:
            resident_ready_page = _activate_resident_ready_page(
                self._context,
                timeout_seconds=max(3, self._manual_action_timeout_seconds),
            )
            if resident_ready_page is not None:
                self._page = resident_ready_page
                page = resident_ready_page

        try:
            _open_bet_top(page)
        except TeleboatError:
            pass
        try:
            _recover_timeout_or_raise(page)
        except TeleboatError as exc:
            self._record_session(status="login_required", message=str(exc), session_state="login_required")
            raise
        self._save_storage_state()
        self._record_session(
            status="prepared",
            message=f"Teleboat 常駐セッションを準備しました。ログイン情報保持は {SESSION_KEEP_LOGIN_DAYS} 日想定です。",
            session_state=session_state,
            refresh_validity=True,
        )
        return session_state

    def current_purchase_limit(self) -> int | None:
        self.ensure_session()
        page = self.page
        _open_bet_top(page)
        return _current_purchase_limit_amount(page)

    def _prepare_target_for_submission(
        self,
        *,
        target,
        intents: list[Any],
        require_vote_password: bool,
    ) -> tuple[str, int]:
        if self._credentials is None:
            self._credentials = load_credentials(require_vote_password=require_vote_password)
        elif require_vote_password and not self._credentials.vote_password:
            self._credentials = load_credentials(require_vote_password=True)

        session_state = self.ensure_session()
        page = self.page

        _select_race(
            page,
            stadium_code=target.stadium_code,
            stadium_name=target.stadium_name,
            race_no=target.race_no,
        )

        prepared_units = 0
        for intent in intents:
            prepared_units += _add_intent_to_bet_list(
                page,
                bet_type=intent.bet_type,
                combo=intent.combo,
                amount=int(intent.amount),
                data_dir=self._data_dir,
                debug_prefix=f"{target.race_id}_{intent.combo.replace('-', '_')}",
            )

        _open_confirmation(page, data_dir=self._data_dir, debug_prefix=f"{target.race_id}_confirm")
        return session_state, prepared_units

    def prepare_target_confirmation(self, *, target, intents: list[Any]) -> TeleboatResult:
        session_state, prepared_units = self._prepare_target_for_submission(
            target=target,
            intents=intents,
            require_vote_password=False,
        )
        screenshot_path, html_path = _save_debug_artifacts(
            self.page,
            prefix=f"{target.race_id}_manual_confirm_ready",
            data_dir=self._data_dir,
        )
        return TeleboatResult(
            execution_status="prepared_confirmation",
            message="確認画面まで到達しました",
            screenshot_path=screenshot_path,
            html_path=html_path,
            details={"session_state": session_state, "prepared_units": prepared_units},
        )

    def prepare_target_confirmation_prefill(self, *, target, intents: list[Any]) -> TeleboatResult:
        session_state, prepared_units = self._prepare_target_for_submission(
            target=target,
            intents=intents,
            require_vote_password=True,
        )
        confirmation_total_amount = _prefill_confirmation_inputs(
            self.page,
            vote_password=self._credentials.vote_password,
            total_amount=_current_confirmation_total_amount(self.page),
            data_dir=self._data_dir,
            debug_prefix=f"{target.race_id}_confirm_prefill",
        )
        return TeleboatResult(
            execution_status="prepared_confirmation_prefilled",
            message="確認画面で購入金額と投票用パスワードを入力しました。投票するは未実行です。",
            details={
                "session_state": session_state,
                "prepared_units": prepared_units,
                "confirmation_total_amount": confirmation_total_amount,
            },
        )

    def place_target(self, *, target, intents: list[Any], mode: str) -> TeleboatResult:
        if mode not in {"assist_real", "armed_real"}:
            raise TeleboatError(f"実投票ではない mode が指定されました: {mode}")

        session_state, prepared_units = self._prepare_target_for_submission(
            target=target,
            intents=intents,
            require_vote_password=(mode == "armed_real"),
        )
        page = self.page

        if mode == "assist_real":
            confirmation_total_amount = _prefill_confirmation_inputs(
                page,
                vote_password=self._credentials.vote_password,
                total_amount=_current_confirmation_total_amount(page),
                data_dir=self._data_dir,
                debug_prefix=f"{target.race_id}_assist",
            )
            screenshot_path, html_path = _save_debug_artifacts(
                page,
                prefix=f"{target.race_id}_assist_confirm",
                data_dir=self._data_dir,
            )
            submitted = _wait_for_manual_submit_or_raise(
                page,
                timeout_seconds=self._manual_action_timeout_seconds,
                data_dir=self._data_dir,
                debug_prefix=f"{target.race_id}_assist",
            )
            contract_no = _lookup_last_contract(page) if submitted else None
            return TeleboatResult(
                execution_status="submitted" if submitted else "assist_timeout",
                message="手動確認で投票結果を確認しました" if submitted else "確認画面での手動操作待ちがタイムアウトしました",
                contract_no=contract_no,
                screenshot_path=screenshot_path,
                html_path=html_path,
                details={
                    "mode": mode,
                    "session_state": session_state,
                    "prepared_units": prepared_units,
                    "confirmation_total_amount": confirmation_total_amount,
                },
            )

        dialog_messages = _submit_vote(
            page,
            vote_password=self._credentials.vote_password,
            total_amount=_current_confirmation_total_amount(page),
            data_dir=self._data_dir,
            debug_prefix=f"{target.race_id}_armed",
        )
        _wait_for_submit_outcome(
            page,
            data_dir=self._data_dir,
            debug_prefix=f"{target.race_id}_armed",
            dialog_messages=dialog_messages,
        )
        screenshot_path, html_path = _save_debug_artifacts(
            page,
            prefix=f"{target.race_id}_armed_result",
            data_dir=self._data_dir,
        )
        contract_no = _lookup_last_contract(page)
        return TeleboatResult(
            execution_status="submitted",
            message="自動投票を実行しました",
            contract_no=contract_no,
            screenshot_path=screenshot_path,
            html_path=html_path,
            details={"mode": mode, "session_state": session_state, "prepared_units": prepared_units},
        )
