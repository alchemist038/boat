from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

BASE_URL = "https://ib.mbrace.or.jp/"

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


def _load_env() -> None:
    root = Path(__file__).resolve().parents[2]
    live_trigger_root = root.parent
    for path in (live_trigger_root / ".env", root / ".env"):
        if path.exists():
            load_dotenv(path, override=False)
    load_dotenv(override=False)


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


def _fill_first(page: Page, selectors: Iterable[str], value: str, *, description: str, timeout_ms: int = 5_000) -> str:
    last_error: Exception | None = None
    for selector in selectors:
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


def _extract_contract_no(page: Page) -> str | None:
    try:
        body = page.locator("body").inner_text(timeout=3_000)
    except Exception:  # noqa: BLE001
        return None

    match = re.search(r"契約番号[^0-9]*([0-9]{6,})", body)
    if match:
        return match.group(1)
    return None


def _ensure_login(page: Page, credentials: TeleboatCredentials, *, login_timeout_seconds: int) -> str:
    page.goto(BASE_URL, wait_until="domcontentloaded")
    _settle(page)

    if _exists(page, ('text="マイページ"', 'text="照会"', 'text="ログアウト"')):
        return "reused_session"

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

    deadline = time.time() + max(10, login_timeout_seconds)
    while time.time() < deadline:
        _settle(page, milliseconds=500)
        if _exists(page, ('text="マイページ"', 'text="照会"', 'text="ログアウト"')):
            return "logged_in"
        if _exists(page, ('text="reCAPTCHA"', 'text="認証"', 'text="エラー"')):
            break

    raise TeleboatError("Teleboat ログインに失敗しました。reCAPTCHA または追加認証が必要な可能性があります。")


def _stadium_name(stadium_code: str, fallback: str | None) -> str:
    normalized_code = str(stadium_code).zfill(2)
    return STADIUM_CODE_TO_NAME.get(normalized_code, str(fallback or normalized_code))


def _select_race(page: Page, *, stadium_code: str, stadium_name: str | None, race_no: int) -> None:
    page.goto(BASE_URL, wait_until="domcontentloaded")
    _settle(page)
    resolved_name = _stadium_name(stadium_code, stadium_name)

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

    race_label = f"{int(race_no)}R"
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


def _select_method_and_bet_type(page: Page, *, method_label: str, bet_type_label: str) -> None:
    _click_first(
        page,
        [
            f"text=\"{method_label}\"",
            f"button:has-text('{method_label}')",
            f"a:has-text('{method_label}')",
        ],
        description=f"投票方法({method_label})",
    )
    _settle(page, milliseconds=500)
    _click_first(
        page,
        [
            f"text=\"{bet_type_label}\"",
            f"button:has-text('{bet_type_label}')",
            f"a:has-text('{bet_type_label}')",
        ],
        description=f"勝式({bet_type_label})",
    )
    _settle(page, milliseconds=500)


def _fill_amount(page: Page, amount: int) -> None:
    value = str(int(amount))
    selectors = [
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


def _add_intent_to_bet_list(page: Page, *, bet_type: str, combo: str, amount: int) -> None:
    bet_type_label = BET_TYPE_TO_LABEL.get(str(bet_type).lower())
    if not bet_type_label:
        raise TeleboatError(f"未対応の券種です: {bet_type}")

    parts = [part.strip().upper() for part in str(combo).split("-") if part.strip()]
    if not parts:
        raise TeleboatError(f"組番の形式が不正です: {combo}")

    method_label = "フォーメーション投票" if "ALL" in parts else "通常投票"
    _select_method_and_bet_type(page, method_label=method_label, bet_type_label=bet_type_label)

    if method_label == "通常投票":
        for index, token in enumerate(parts, start=1):
            _select_group_value(page, group_label=f"{index}着", value_label=token)
    else:
        for index, token in enumerate(parts, start=1):
            value_label = "全通り" if token == "ALL" else token
            _select_group_value(page, group_label=f"{index}着", value_label=value_label)

    _fill_amount(page, amount)
    _click_first(
        page,
        [
            "text=\"ベットリストに追加\"",
            "button:has-text('ベットリストに追加')",
            "input[value='ベットリストに追加']",
        ],
        description="ベットリストに追加",
        timeout_ms=8_000,
    )
    _settle(page, milliseconds=500)


def _open_confirmation(page: Page) -> None:
    _click_first(
        page,
        [
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


def _submit_vote(page: Page, *, vote_password: str) -> None:
    _fill_first(
        page,
        [
            "input[title='投票用パスワード']",
            "input[aria-label='投票用パスワード']",
            "input[name*='vote']",
            "input[name*='password']",
            "input[type='password']",
        ],
        vote_password,
        description="投票用パスワード",
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


def _wait_for_manual_submit(page: Page, *, timeout_seconds: int) -> bool:
    deadline = time.time() + max(10, timeout_seconds)
    while time.time() < deadline:
        if _exists(page, ('text="投票結果"', 'text="同じ場で投票する"', 'text="契約番号"')):
            return True
        page.wait_for_timeout(1_000)
    return False


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
        self._manual_action_timeout_seconds = int(settings.get("manual_action_timeout_seconds", 180))
        self._login_timeout_seconds = int(settings.get("login_timeout_seconds", 120))
        self._headless = bool(settings.get("real_headless", False))
        self._playwright = None
        self._context = None
        self._page: Page | None = None
        self._credentials: TeleboatCredentials | None = None

    def __enter__(self) -> "TeleboatClient":
        self._playwright = sync_playwright().start()
        self._context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self._user_data_dir),
            headless=self._headless,
            viewport={"width": 1600, "height": 1100},
        )
        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._context is not None:
            self._context.close()
        if self._playwright is not None:
            self._playwright.stop()

    @property
    def page(self) -> Page:
        if self._page is None:
            raise TeleboatError("Playwright page が初期化されていません")
        return self._page

    def ensure_session(self) -> str:
        page = self.page
        page.goto(BASE_URL, wait_until="domcontentloaded")
        _settle(page)
        if _exists(page, ('text="マイページ"', 'text="照会"', 'text="ログアウト"')):
            return "reused_session"

        if self._credentials is None:
            self._credentials = load_credentials(require_vote_password=False)
        return _ensure_login(
            page,
            self._credentials,
            login_timeout_seconds=self._login_timeout_seconds,
        )

    def place_target(self, *, target, intents: list[Any], mode: str) -> TeleboatResult:
        if mode not in {"assist_real", "armed_real"}:
            raise TeleboatError(f"実投票ではない mode が指定されました: {mode}")

        if self._credentials is None:
            self._credentials = load_credentials(require_vote_password=(mode == "armed_real"))
        elif mode == "armed_real" and not self._credentials.vote_password:
            self._credentials = load_credentials(require_vote_password=True)

        session_state = self.ensure_session()
        page = self.page

        _select_race(
            page,
            stadium_code=target.stadium_code,
            stadium_name=target.stadium_name,
            race_no=target.race_no,
        )

        for intent in intents:
            _add_intent_to_bet_list(
                page,
                bet_type=intent.bet_type,
                combo=intent.combo,
                amount=int(intent.amount),
            )

        _open_confirmation(page)

        if mode == "assist_real":
            screenshot_path, html_path = _save_debug_artifacts(
                page,
                prefix=f"{target.race_id}_assist_confirm",
                data_dir=self._data_dir,
            )
            submitted = _wait_for_manual_submit(
                page,
                timeout_seconds=self._manual_action_timeout_seconds,
            )
            contract_no = _lookup_last_contract(page) if submitted else None
            return TeleboatResult(
                execution_status="submitted" if submitted else "assist_timeout",
                message="手動確認で投票結果を確認しました" if submitted else "確認画面での手動操作待ちがタイムアウトしました",
                contract_no=contract_no,
                screenshot_path=screenshot_path,
                html_path=html_path,
                details={"mode": mode, "session_state": session_state},
            )

        _submit_vote(page, vote_password=self._credentials.vote_password)
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
            details={"mode": mode, "session_state": session_state},
        )
