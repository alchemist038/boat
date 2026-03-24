from __future__ import annotations

import importlib.util
import json
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any

from playwright.sync_api import Page, sync_playwright

from app.core.fresh_flow import (
    FlowStepType,
    FreshExecutorPolicy,
    RealExecutionMode,
    SessionStrategy,
    build_real_execution_steps,
    should_keep_session,
)
from app.core.fresh_settings import SHARED_LIVE_TRIGGER_ROOT

FRESH_SYSTEM_ROOT = Path(__file__).resolve().parents[2]
LEGACY_TELEBOAT_PATH = SHARED_LIVE_TRIGGER_ROOT / "auto_system" / "app" / "core" / "teleboat.py"


def _load_legacy_teleboat_module() -> ModuleType:
    module_name = "live_trigger_legacy_teleboat"
    cached = sys.modules.get(module_name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(module_name, LEGACY_TELEBOAT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load legacy teleboat module: {LEGACY_TELEBOAT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


LEGACY = _load_legacy_teleboat_module()
STADIUM_CODE_TO_NAME = dict(getattr(LEGACY, "STADIUM_CODE_TO_NAME", {}))
TELEGRAM_STATE_FILENAME = "telegram_state.json"


def get_legacy_teleboat_module() -> ModuleType:
    return LEGACY


@dataclass
class FreshExecutionTrace:
    planned_steps: list[str] = field(default_factory=list)
    completed_steps: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def policy_from_settings(settings: dict[str, Any] | None) -> FreshExecutorPolicy:
    payload = dict(settings or {})
    strategy_raw = str(payload.get("real_session_strategy", SessionStrategy.FRESH_PER_EXECUTION.value)).strip().lower()
    try:
        strategy = SessionStrategy(strategy_raw)
    except ValueError:
        strategy = SessionStrategy.FRESH_PER_EXECUTION
    return FreshExecutorPolicy(
        session_strategy=strategy,
        reuse_when_next_real_within_seconds=max(
            0,
            int(payload.get("reuse_when_next_real_within_seconds", 180)),
        ),
        post_login_settle_seconds=max(
            1,
            int(payload.get("post_login_settle_seconds", 10)),
        ),
        top_stable_confirm_seconds=max(
            1,
            int(payload.get("top_stable_confirm_seconds", 3)),
        ),
        logout_after_execution=bool(payload.get("logout_after_execution", True)),
        close_browser_after_execution=bool(payload.get("close_browser_after_execution", True)),
    )


class FreshTeleboatExecutor:
    def __init__(
        self,
        *,
        data_dir: Path,
        settings: dict[str, Any] | None = None,
        policy: FreshExecutorPolicy | None = None,
    ) -> None:
        self._data_dir = Path(data_dir)
        self._settings = dict(settings or {})
        self._policy = policy or policy_from_settings(self._settings)
        self._headless = bool(self._settings.get("headless", False))
        self._login_timeout_seconds = max(30, int(self._settings.get("login_timeout_seconds", 120)))
        self._manual_action_timeout_seconds = max(30, int(self._settings.get("manual_action_timeout_seconds", 180)))
        self._playwright = None
        self._browser = None
        self._context = None
        self._page: Page | None = None
        self._credentials = None
        self._trace = FreshExecutionTrace()

    def __enter__(self) -> "FreshTeleboatExecutor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @property
    def page(self) -> Page:
        if self._page is None:
            raise LEGACY.TeleboatError("Fresh executor page is not ready.")
        return self._page

    @property
    def trace(self) -> FreshExecutionTrace:
        return self._trace

    def _reset_trace(self, *, planned_steps: list[str] | None = None) -> None:
        self._trace = FreshExecutionTrace(planned_steps=list(planned_steps or []))

    def _record_step(self, step: FlowStepType) -> None:
        value = step.value
        if value not in self._trace.completed_steps:
            self._trace.completed_steps.append(value)

    def _warn(self, message: str) -> None:
        self._trace.warnings.append(str(message))

    def _safe_url(self, page: Page | None) -> str:
        if page is None:
            return ""
        try:
            return page.url or ""
        except Exception:  # noqa: BLE001
            return ""

    def _page_is_closed(self, page: Page | None) -> bool:
        if page is None:
            return True
        try:
            return page.is_closed()
        except Exception:  # noqa: BLE001
            return True

    def _all_pages(self) -> list[Page]:
        if self._context is None:
            return []
        pages: list[Page] = []
        for page in list(self._context.pages):
            if self._page_is_closed(page):
                continue
            pages.append(page)
        return pages

    def _page_score(self, page: Page) -> int:
        score = 0
        current_url = self._safe_url(page)
        if "ib.mbrace.or.jp" in current_url:
            score += 10
        if "/service/bet/top/" in current_url:
            score += 50
        elif "/service/bet/" in current_url:
            score += 25
        try:
            if LEGACY._session_is_ready(page):
                score += 100
        except Exception:  # noqa: BLE001
            pass
        try:
            if LEGACY._visible_exists(page, LEGACY.LOGIN_FORM_SELECTORS):
                score -= 40
        except Exception:  # noqa: BLE001
            pass
        try:
            if LEGACY._is_session_timeout_page(page):
                score -= 100
        except Exception:  # noqa: BLE001
            pass
        return score

    def _ordered_pages(self) -> list[Page]:
        pages = self._all_pages()
        pages.sort(key=self._page_score, reverse=True)
        return pages

    def _find_ready_page(self) -> Page | None:
        for page in self._ordered_pages():
            try:
                if LEGACY._session_is_ready(page):
                    return page
            except Exception:  # noqa: BLE001
                continue
        return None

    def _manual_auth_visible(self) -> bool:
        for page in self._ordered_pages():
            try:
                if LEGACY._requires_manual_auth(page):
                    return True
            except Exception:  # noqa: BLE001
                continue
        return False

    def _ensure_browser_started(self) -> None:
        if self._context is not None:
            return
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self._headless)
        self._context = self._browser.new_context(viewport={"width": 1600, "height": 1100})
        self._page = self._context.new_page()
        self._record_step(FlowStepType.START_BROWSER)

    def _ensure_credentials(self, *, require_vote_password: bool) -> Any:
        if self._credentials is None:
            self._credentials = LEGACY.load_credentials(require_vote_password=require_vote_password)
            return self._credentials
        if require_vote_password and not getattr(self._credentials, "vote_password", ""):
            self._credentials = LEGACY.load_credentials(require_vote_password=True)
        return self._credentials

    def _close_extra_pages(self, *, preserve: Page) -> int:
        closed = 0
        for page in list(self._all_pages()):
            if page is preserve:
                continue
            try:
                page.close()
                closed += 1
            except Exception:  # noqa: BLE001
                continue
        return closed

    def _converge_to_top_page(self, page: Page) -> Page:
        closed = self._close_extra_pages(preserve=page)
        self._record_step(FlowStepType.CLOSE_LOGIN_TABS)
        if closed:
            self._warn(f"Closed {closed} extra page(s) after login.")
        LEGACY._open_bet_top(page)
        LEGACY._settle(page, milliseconds=700)
        self._page = page
        self._record_step(FlowStepType.CAPTURE_TOP_PAGE)
        return page

    def _reconnect_existing_ready_page(self) -> str | None:
        ready_page = self._find_ready_page()
        if ready_page is None and not self._page_is_closed(self._page):
            try:
                LEGACY._open_bet_top(self.page, force_navigation=True)
                if LEGACY._session_is_ready(self.page):
                    ready_page = self.page
            except Exception:  # noqa: BLE001
                ready_page = None
        if ready_page is None:
            return None
        self._converge_to_top_page(ready_page)
        return "reused_session"

    def _normalize_datetime(self, value: Any) -> datetime | None:
        if value is None:
            return None

        parsed: datetime | None
        if isinstance(value, datetime):
            parsed = value
        else:
            text = str(value).strip()
            if not text:
                return None
            parsed = None
            candidates = [text]
            if text.endswith("Z"):
                candidates.append(text[:-1] + "+00:00")
            for candidate in candidates:
                try:
                    parsed = datetime.fromisoformat(candidate)
                    break
                except ValueError:
                    continue
            if parsed is None:
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M"):
                    try:
                        parsed = datetime.strptime(text, fmt)
                        break
                    except ValueError:
                        continue
        if parsed is None:
            return None
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone().replace(tzinfo=None)
        return parsed

    def _target_deadline_at(self, target: Any) -> datetime | None:
        return self._normalize_datetime(getattr(target, "deadline_at", None))

    def _wait_for_top_page(self, *, login_started_at: float) -> Page:
        minimum_ready_at = login_started_at + self._policy.post_login_settle_seconds
        stable_candidate: Page | None = None
        stable_since: float | None = None
        deadline = login_started_at + max(
            self._login_timeout_seconds,
            self._policy.post_login_settle_seconds + self._policy.top_stable_confirm_seconds,
        )
        manual_auth_seen = False

        while time.time() < deadline:
            candidate = self._find_ready_page()
            if candidate is None:
                stable_candidate = None
                stable_since = None
                manual_auth_seen = manual_auth_seen or self._manual_auth_visible()
                time.sleep(1)
                continue

            now = time.time()
            if stable_candidate is not candidate:
                stable_candidate = candidate
                stable_since = now
            elif stable_since is not None:
                stable_enough = (now - stable_since) >= self._policy.top_stable_confirm_seconds
                settle_elapsed = now >= minimum_ready_at
                if stable_enough and settle_elapsed:
                    self._record_step(FlowStepType.WAIT_TOP_STABLE)
                    return self._converge_to_top_page(candidate)
            time.sleep(1)

        if manual_auth_seen:
            raise LEGACY.TeleboatError(
                "Fresh executor login did not finish automatically. Manual auth may still be pending."
            )
        raise LEGACY.TeleboatError("Fresh executor could not capture a stable top page after login.")

    def has_active_session(self) -> bool:
        try:
            return self._find_ready_page() is not None
        except Exception:  # noqa: BLE001
            return False

    def login(self, *, require_vote_password: bool = False) -> str:
        self._ensure_browser_started()
        existing_state = self._reconnect_existing_ready_page()
        if existing_state is not None:
            return existing_state

        credentials = self._ensure_credentials(require_vote_password=require_vote_password)
        page = self.page
        page.goto(LEGACY.BASE_URL, wait_until="domcontentloaded")
        LEGACY._settle(page)
        self._record_step(FlowStepType.OPEN_LOGIN_PAGE)

        if LEGACY._session_is_ready(page):
            self._record_step(FlowStepType.WAIT_TOP_STABLE)
            self._converge_to_top_page(page)
            return "reused_session"

        LEGACY._fill_login_form(page, credentials)
        login_started_at = time.time()
        LEGACY._click_login_button(page)
        self._record_step(FlowStepType.SUBMIT_LOGIN)
        self._wait_for_top_page(login_started_at=login_started_at)
        return "logged_in"

    def login_only(self) -> Any:
        self._reset_trace(
            planned_steps=[
                FlowStepType.START_BROWSER.value,
                FlowStepType.OPEN_LOGIN_PAGE.value,
                FlowStepType.SUBMIT_LOGIN.value,
                FlowStepType.WAIT_TOP_STABLE.value,
                FlowStepType.CLOSE_LOGIN_TABS.value,
                FlowStepType.CAPTURE_TOP_PAGE.value,
            ]
        )
        session_state = self.login(require_vote_password=False)
        screenshot_path, html_path = LEGACY._save_debug_artifacts(
            self.page,
            prefix="fresh_login_top",
            data_dir=self._data_dir,
        )
        return LEGACY.TeleboatResult(
            execution_status="logged_in",
            message="Fresh executor login completed.",
            screenshot_path=screenshot_path,
            html_path=html_path,
            details=self._base_details(session_state=session_state),
        )

    def _prepare_target_for_submission(
        self,
        *,
        target: Any,
        intents: list[Any],
        require_vote_password: bool,
    ) -> tuple[str, int]:
        session_state = self.login(require_vote_password=require_vote_password)
        page = self.page

        self._record_step(FlowStepType.SELECT_RACE)
        LEGACY._select_race(
            page,
            stadium_code=target.stadium_code,
            stadium_name=target.stadium_name,
            race_no=target.race_no,
        )

        prepared_units = 0
        self._record_step(FlowStepType.BUILD_BET_LIST)
        for intent in intents:
            prepared_units += LEGACY._add_intent_to_bet_list(
                page,
                bet_type=intent.bet_type,
                combo=intent.combo,
                amount=int(intent.amount),
                data_dir=self._data_dir,
                debug_prefix=f"{target.race_id}_{str(intent.combo).replace('-', '_')}",
            )

        self._record_step(FlowStepType.OPEN_CONFIRMATION)
        LEGACY._open_confirmation(
            page,
            data_dir=self._data_dir,
            debug_prefix=f"{target.race_id}_fresh_confirm",
        )
        return session_state, prepared_units

    def prepare_target_confirmation(self, *, target: Any, intents: list[Any], prefill: bool) -> Any:
        planned_steps = [
            FlowStepType.START_BROWSER.value,
            FlowStepType.OPEN_LOGIN_PAGE.value,
            FlowStepType.SUBMIT_LOGIN.value,
            FlowStepType.WAIT_TOP_STABLE.value,
            FlowStepType.CLOSE_LOGIN_TABS.value,
            FlowStepType.CAPTURE_TOP_PAGE.value,
            FlowStepType.SELECT_RACE.value,
            FlowStepType.BUILD_BET_LIST.value,
            FlowStepType.OPEN_CONFIRMATION.value,
        ]
        if prefill:
            planned_steps.append(FlowStepType.PREFILL_CONFIRMATION.value)
        self._reset_trace(planned_steps=planned_steps)

        session_state, prepared_units = self._prepare_target_for_submission(
            target=target,
            intents=intents,
            require_vote_password=prefill,
        )

        details = self._base_details(
            session_state=session_state,
            prepared_units=prepared_units,
            race_id=target.race_id,
        )

        if prefill:
            self._record_step(FlowStepType.PREFILL_CONFIRMATION)
            total_amount = LEGACY._prefill_confirmation_inputs(
                self.page,
                vote_password=self._ensure_credentials(require_vote_password=True).vote_password,
                total_amount=LEGACY._current_confirmation_total_amount(self.page),
            )
            details["confirmation_total_amount"] = total_amount
            self._sync_trace_details(details)

        screenshot_path, html_path = LEGACY._save_debug_artifacts(
            self.page,
            prefix=f"{target.race_id}_fresh_confirmation",
            data_dir=self._data_dir,
        )
        return LEGACY.TeleboatResult(
            execution_status="prepared_confirmation_prefilled" if prefill else "prepared_confirmation",
            message="Fresh executor confirmation page is ready.",
            screenshot_path=screenshot_path,
            html_path=html_path,
            details=self._sync_trace_details(details),
        )

    def _base_details(self, **extra: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "planned_steps": list(self._trace.planned_steps),
            "completed_steps": list(self._trace.completed_steps),
            "warnings": list(self._trace.warnings),
            "current_url": self._safe_url(self._page),
        }
        payload.update(extra)
        return payload

    def _sync_trace_details(self, details: dict[str, Any]) -> dict[str, Any]:
        details["planned_steps"] = list(self._trace.planned_steps)
        details["completed_steps"] = list(self._trace.completed_steps)
        details["warnings"] = list(self._trace.warnings)
        details["current_url"] = self._safe_url(self._page)
        return details

    def _telegram_enabled(self) -> bool:
        token = str(self._settings.get("telegram_bot_token") or "").strip()
        chat_id = str(self._settings.get("telegram_chat_id") or "").strip()
        return bool(self._settings.get("telegram_enabled")) and bool(token) and bool(chat_id)

    def _telegram_state_path(self) -> Path:
        return self._data_dir / TELEGRAM_STATE_FILENAME

    def _load_telegram_state(self) -> dict[str, Any]:
        path = self._telegram_state_path()
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {}

    def _save_telegram_state(self, state: dict[str, Any]) -> None:
        self._telegram_state_path().write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _telegram_request(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        token = str(self._settings.get("telegram_bot_token") or "").strip()
        if not token:
            raise RuntimeError("telegram bot token is not configured")
        request = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/{method}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))

    def _consume_telegram_assist_action(self, *, race_id: str) -> dict[str, Any] | None:
        if not self._telegram_enabled():
            return None

        state = self._load_telegram_state()
        payload: dict[str, Any] = {}
        last_update_id = state.get("last_update_id")
        if isinstance(last_update_id, int):
            payload["offset"] = last_update_id + 1

        response = self._telegram_request("getUpdates", payload)
        updates = list(response.get("result") or [])
        if not updates:
            return None

        max_update_id = last_update_id if isinstance(last_update_id, int) else None
        matched: dict[str, Any] | None = None
        for item in updates:
            update_id = item.get("update_id")
            if isinstance(update_id, int):
                max_update_id = update_id if max_update_id is None else max(max_update_id, update_id)
            callback = item.get("callback_query") or {}
            data = str(callback.get("data") or "")
            if ":" not in data:
                continue
            action, callback_race_id = data.split(":", 1)
            if callback_race_id != race_id:
                continue
            if action not in {"approve", "reject"}:
                continue
            matched = {
                "action": action,
                "callback_id": callback.get("id"),
                "message_id": (callback.get("message") or {}).get("message_id"),
                "message_chat_id": ((callback.get("message") or {}).get("chat") or {}).get("id"),
                "username": (callback.get("from") or {}).get("username"),
                "update_id": update_id,
            }
            break

        if max_update_id is not None:
            state["last_update_id"] = max_update_id
            self._save_telegram_state(state)

        if matched is None:
            return None

        callback_id = matched.get("callback_id")
        answer_text = "承認を受け付けました。" if matched["action"] == "approve" else "却下を受け付けました。"
        try:
            if callback_id:
                self._telegram_request(
                    "answerCallbackQuery",
                    {"callback_query_id": callback_id, "text": answer_text, "show_alert": False},
                )
        except Exception as exc:  # noqa: BLE001
            self._warn(f"Failed to answer Telegram callback: {exc}")

        try:
            message_id = matched.get("message_id")
            message_chat_id = matched.get("message_chat_id")
            if message_id is not None and message_chat_id is not None:
                self._telegram_request(
                    "editMessageReplyMarkup",
                    {
                        "chat_id": message_chat_id,
                        "message_id": message_id,
                        "reply_markup": {"inline_keyboard": []},
                    },
                )
        except Exception as exc:  # noqa: BLE001
            self._warn(f"Failed to clear Telegram buttons: {exc}")

        return matched

    def _wait_for_assist_submit(
        self,
        *,
        page: Page,
        target: Any,
        data_dir: Path,
        debug_prefix: str,
    ) -> dict[str, Any]:
        deadline_at = self._target_deadline_at(target)
        if deadline_at is None:
            wait_until_at = datetime.now() + timedelta(seconds=self._manual_action_timeout_seconds)
            wait_mode = "manual_timeout"
        else:
            wait_until_at = deadline_at
            wait_mode = "deadline_at"

        dialog_seen: list[str] = []

        def _dialog_handler(dialog) -> None:
            dialog_seen.append(dialog.message)
            dialog.accept()

        page.on("dialog", _dialog_handler)
        try:
            while True:
                LEGACY._raise_if_insufficient_funds(
                    page,
                    data_dir=data_dir,
                    debug_prefix=debug_prefix,
                    dialog_messages=dialog_seen,
                )
                dialog_seen.clear()
                telegram_action = self._consume_telegram_assist_action(race_id=str(getattr(target, "race_id", "")))
                if telegram_action is not None:
                    if telegram_action["action"] == "approve":
                        dialog_messages = LEGACY._submit_vote(
                            page,
                            vote_password=self._ensure_credentials(require_vote_password=True).vote_password,
                            total_amount=LEGACY._current_confirmation_total_amount(page),
                        )
                        LEGACY._wait_for_submit_outcome(
                            page,
                            data_dir=data_dir,
                            debug_prefix=f"{debug_prefix}_approved",
                            dialog_messages=dialog_messages,
                        )
                        return {
                            "submitted": True,
                            "assist_wait_mode": wait_mode,
                            "assist_wait_until_at": wait_until_at.isoformat(timespec="seconds"),
                            "assist_deadline_at": deadline_at.isoformat(timespec="seconds") if deadline_at else None,
                            "terminal_reason": "telegram_approved",
                            "approval_source": "telegram",
                            "approval_username": telegram_action.get("username"),
                        }
                    return {
                        "submitted": False,
                        "assist_wait_mode": wait_mode,
                        "assist_wait_until_at": wait_until_at.isoformat(timespec="seconds"),
                        "assist_deadline_at": deadline_at.isoformat(timespec="seconds") if deadline_at else None,
                        "terminal_reason": "telegram_rejected",
                        "approval_source": "telegram",
                        "approval_username": telegram_action.get("username"),
                    }
                if LEGACY._exists(page, LEGACY.VOTE_SUCCESS_SELECTORS) or LEGACY._extract_contract_no(page):
                    return {
                        "submitted": True,
                        "assist_wait_mode": wait_mode,
                        "assist_wait_until_at": wait_until_at.isoformat(timespec="seconds"),
                        "assist_deadline_at": deadline_at.isoformat(timespec="seconds") if deadline_at else None,
                        "terminal_reason": "submitted",
                        "approval_source": "manual",
                    }
                if datetime.now() >= wait_until_at:
                    break
                page.wait_for_timeout(1_000)
        finally:
            page.remove_listener("dialog", _dialog_handler)

        return {
            "submitted": False,
            "assist_wait_mode": wait_mode,
            "assist_wait_until_at": wait_until_at.isoformat(timespec="seconds"),
            "assist_deadline_at": deadline_at.isoformat(timespec="seconds") if deadline_at else None,
            "terminal_reason": "deadline_passed" if deadline_at is not None else "manual_timeout",
        }

    def wait_for_telegram_approval_test(
        self,
        *,
        race_id: str,
        timeout_seconds: int | None = None,
    ) -> Any:
        wait_seconds = max(5, int(timeout_seconds or self._manual_action_timeout_seconds))
        wait_until_at = datetime.now() + timedelta(seconds=wait_seconds)
        self._reset_trace(planned_steps=[FlowStepType.WAIT_MANUAL_SUBMIT.value])
        while datetime.now() < wait_until_at:
            telegram_action = self._consume_telegram_assist_action(race_id=race_id)
            if telegram_action is not None:
                action = str(telegram_action["action"])
                username = telegram_action.get("username")
                if action == "approve":
                    self._record_step(FlowStepType.WAIT_MANUAL_SUBMIT)
                    return LEGACY.TeleboatResult(
                        execution_status="telegram_approved_test",
                        message="Telegram approval test received an approve action.",
                        details=self._sync_trace_details(
                            {
                                "race_id": race_id,
                                "approval_source": "telegram",
                                "approval_username": username,
                                "terminal_reason": "telegram_approved_test",
                            }
                        ),
                    )
                self._record_step(FlowStepType.WAIT_MANUAL_SUBMIT)
                return LEGACY.TeleboatResult(
                    execution_status="telegram_rejected_test",
                    message="Telegram approval test received a reject action.",
                    details=self._sync_trace_details(
                        {
                            "race_id": race_id,
                            "approval_source": "telegram",
                            "approval_username": username,
                            "terminal_reason": "telegram_rejected_test",
                        }
                    ),
                )
            time.sleep(1)

        return LEGACY.TeleboatResult(
            execution_status="telegram_timeout_test",
            message="Telegram approval test timed out without a callback.",
            details=self._sync_trace_details(
                {
                    "race_id": race_id,
                    "terminal_reason": "telegram_timeout_test",
                    "assist_wait_until_at": wait_until_at.isoformat(timespec="seconds"),
                }
            ),
        )

    def logout(self) -> bool:
        candidates: list[Page] = []
        primary = self._find_ready_page() or self._page
        if primary is not None and not self._page_is_closed(primary):
            candidates.append(primary)
        for candidate in self._ordered_pages():
            if candidate in candidates or self._page_is_closed(candidate):
                continue
            candidates.append(candidate)
        if not candidates:
            return False

        logout_selectors = [
            "#logout a",
            "#logout",
            "#errorLogout",
            'text="ログアウト"',
            "a:has-text('ログアウト')",
            "button:has-text('ログアウト')",
        ]
        logout_confirm_selectors = [
            "#ok",
            "#errorLogout",
            'text="OK"',
            "button:has-text('OK')",
            "a:has-text('OK')",
        ]
        last_error: Exception | None = None
        page: Page | None = None
        for candidate in candidates:
            for should_open_top in (False, True):
                if should_open_top:
                    try:
                        LEGACY._open_bet_top(candidate)
                    except Exception as exc:  # noqa: BLE001
                        last_error = exc
                        continue
                try:
                    LEGACY._click_first(
                        candidate,
                        logout_selectors,
                        description="logout",
                        timeout_ms=5_000,
                    )
                    page = candidate
                    break
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    continue
            if page is not None:
                break

        if page is None:
            if last_error is not None:
                raise last_error
            raise LEGACY.TeleboatError("logout に使える要素が見つかりません")

        self._record_step(FlowStepType.LOGOUT)

        confirm_deadline = time.time() + 5
        confirm_error: Exception | None = None
        while time.time() < confirm_deadline:
            popup_visible = False
            try:
                popup_visible = LEGACY._exists(page, logout_confirm_selectors)
            except Exception as exc:  # noqa: BLE001
                confirm_error = exc
                popup_visible = False
            if popup_visible:
                try:
                    LEGACY._click_first(
                        page,
                        logout_confirm_selectors,
                        description="logout_confirm",
                        timeout_ms=3_000,
                    )
                    break
                except Exception as exc:  # noqa: BLE001
                    confirm_error = exc
            if self._page_is_closed(page):
                break
            time.sleep(0.25)

        deadline = time.time() + 10
        while time.time() < deadline:
            for candidate in self._ordered_pages():
                try:
                    if LEGACY._visible_exists(candidate, LEGACY.LOGIN_FORM_SELECTORS):
                        self._page = candidate
                        self._close_extra_pages(preserve=candidate)
                        return True
                except Exception:  # noqa: BLE001
                    continue
            time.sleep(0.5)

        if self._context is None:
            return True

        try:
            verify_page = self._context.new_page()
            verify_page.goto(LEGACY.BASE_URL, wait_until="domcontentloaded", timeout=15_000)
            LEGACY._settle(verify_page, milliseconds=700)
            if LEGACY._visible_exists(verify_page, LEGACY.LOGIN_FORM_SELECTORS):
                self._page = verify_page
                self._close_extra_pages(preserve=verify_page)
                return True
            try:
                verify_page.close()
            except Exception:  # noqa: BLE001
                pass
        except Exception as exc:  # noqa: BLE001
            confirm_error = confirm_error or exc

        if confirm_error is not None:
            raise LEGACY.TeleboatError(f"Fresh executor logout did not reach the login screen: {confirm_error}")
        raise LEGACY.TeleboatError("Fresh executor logout did not reach the login screen.")

    def execute_target(
        self,
        *,
        target: Any,
        intents: list[Any],
        mode: RealExecutionMode | str,
        next_real_target_in_seconds: int | None = None,
    ) -> Any:
        normalized_mode = mode if isinstance(mode, RealExecutionMode) else RealExecutionMode(str(mode).strip().lower())
        self._reset_trace(
            planned_steps=[step.step.value for step in build_real_execution_steps(
                normalized_mode,
                next_real_target_in_seconds=next_real_target_in_seconds,
                policy=self._policy,
            )]
        )

        session_state, prepared_units = self._prepare_target_for_submission(
            target=target,
            intents=intents,
            require_vote_password=True,
        )
        page = self.page
        details = self._base_details(
            mode=normalized_mode.value,
            session_state=session_state,
            prepared_units=prepared_units,
            race_id=target.race_id,
        )

        if normalized_mode == RealExecutionMode.ASSIST_REAL:
            self._record_step(FlowStepType.PREFILL_CONFIRMATION)
            confirmation_total_amount = LEGACY._prefill_confirmation_inputs(
                page,
                vote_password=self._ensure_credentials(require_vote_password=True).vote_password,
                total_amount=LEGACY._current_confirmation_total_amount(page),
            )
            details["confirmation_total_amount"] = confirmation_total_amount
            deadline_at = self._target_deadline_at(target)
            if deadline_at is not None:
                details["assist_deadline_at"] = deadline_at.isoformat(timespec="seconds")
            screenshot_path, html_path = LEGACY._save_debug_artifacts(
                page,
                prefix=f"{target.race_id}_fresh_assist_confirm",
                data_dir=self._data_dir,
            )
            self._record_step(FlowStepType.WAIT_MANUAL_SUBMIT)
            wait_result = self._wait_for_assist_submit(
                page=page,
                target=target,
                data_dir=self._data_dir,
                debug_prefix=f"{target.race_id}_fresh_assist",
            )
            details.update({k: v for k, v in wait_result.items() if k != "submitted"})
            if not wait_result.get("submitted"):
                rejected = wait_result.get("terminal_reason") == "telegram_rejected"
                expired_screenshot_path, expired_html_path = LEGACY._save_debug_artifacts(
                    page,
                    prefix=(
                        f"{target.race_id}_fresh_assist_rejected"
                        if rejected
                        else f"{target.race_id}_fresh_assist_window_closed"
                    ),
                    data_dir=self._data_dir,
                )
                details["cleanup_status"] = "assist_rejected" if rejected else "assist_window_closed"
                details.update(self._finalize_after_assist_window_close())
                return LEGACY.TeleboatResult(
                    execution_status="assist_window_closed",
                    message=(
                        "Fresh executor assist mode was rejected via Telegram approval."
                        if rejected
                        else "Fresh executor assist mode closed the session after the vote window passed without manual submit."
                    ),
                    screenshot_path=expired_screenshot_path or screenshot_path,
                    html_path=expired_html_path or html_path,
                    details=self._sync_trace_details(details),
                )

            self._record_step(FlowStepType.WAIT_RESULT)
            contract_no = LEGACY._lookup_last_contract(page)
            cleanup_details = self._finalize_after_success(next_real_target_in_seconds=next_real_target_in_seconds)
            details.update(cleanup_details)
            return LEGACY.TeleboatResult(
                execution_status="submitted",
                message="Fresh executor assist mode observed a completed vote.",
                contract_no=contract_no,
                screenshot_path=screenshot_path,
                html_path=html_path,
                details=self._sync_trace_details(details),
            )

        self._record_step(FlowStepType.AUTO_SUBMIT)
        dialog_messages = LEGACY._submit_vote(
            page,
            vote_password=self._ensure_credentials(require_vote_password=True).vote_password,
            total_amount=LEGACY._current_confirmation_total_amount(page),
        )
        self._record_step(FlowStepType.WAIT_RESULT)
        LEGACY._wait_for_submit_outcome(
            page,
            data_dir=self._data_dir,
            debug_prefix=f"{target.race_id}_fresh_armed",
            dialog_messages=dialog_messages,
        )
        screenshot_path, html_path = LEGACY._save_debug_artifacts(
            page,
            prefix=f"{target.race_id}_fresh_armed_result",
            data_dir=self._data_dir,
        )
        contract_no = LEGACY._lookup_last_contract(page)
        cleanup_details = self._finalize_after_success(next_real_target_in_seconds=next_real_target_in_seconds)
        details.update(cleanup_details)
        return LEGACY.TeleboatResult(
            execution_status="submitted",
            message="Fresh executor armed mode submitted successfully.",
            contract_no=contract_no,
            screenshot_path=screenshot_path,
            html_path=html_path,
            details=self._sync_trace_details(details),
        )

    def _finalize_after_success(self, *, next_real_target_in_seconds: int | None) -> dict[str, Any]:
        details: dict[str, Any] = {}
        if should_keep_session(
            next_real_target_in_seconds=next_real_target_in_seconds,
            policy=self._policy,
        ):
            self._record_step(FlowStepType.KEEP_SESSION)
            details["session_reused_for_next_real"] = True
            return details

        details["session_reused_for_next_real"] = False
        if self._policy.logout_after_execution:
            try:
                details["logout_status"] = "completed" if self.logout() else "skipped"
            except Exception as exc:  # noqa: BLE001
                details["logout_status"] = "failed"
                details["logout_error"] = str(exc)
                self._warn(f"Logout failed: {exc}")

        if self._policy.close_browser_after_execution:
            self.close(record_step=True)
            details["browser_closed"] = True
        else:
            details["browser_closed"] = False
        return details

    def _finalize_after_assist_window_close(self) -> dict[str, Any]:
        details: dict[str, Any] = {
            "session_reused_for_next_real": False,
        }
        if self._policy.logout_after_execution:
            try:
                details["logout_status"] = "completed" if self.logout() else "skipped"
            except Exception as exc:  # noqa: BLE001
                details["logout_status"] = "failed"
                details["logout_error"] = str(exc)
                self._warn(f"Logout failed: {exc}")

        if self._policy.close_browser_after_execution:
            self.close(record_step=True)
            details["browser_closed"] = True
        else:
            details["browser_closed"] = False
        return details

    def close(self, *, record_step: bool = False) -> None:
        if record_step and self._context is not None:
            self._record_step(FlowStepType.CLOSE_BROWSER)
        if self._context is not None:
            try:
                self._context.close()
            except Exception:  # noqa: BLE001
                pass
            self._context = None
        if self._browser is not None:
            try:
                self._browser.close()
            except Exception:  # noqa: BLE001
                pass
            self._browser = None
        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception:  # noqa: BLE001
                pass
            self._playwright = None
        self._page = None
