from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUTO_SYSTEM_ROOT = ROOT / "live_trigger" / "auto_system"

for module_name in [name for name in list(sys.modules) if name == "app" or name.startswith("app.")]:
    sys.modules.pop(module_name, None)

for import_root in (ROOT, AUTO_SYSTEM_ROOT):
    import_text = str(import_root)
    while import_text in sys.path:
        sys.path.remove(import_text)
    sys.path.insert(0, import_text)

import app.core.teleboat as teleboat


class FakePage:
    def __init__(self, url: str = "https://example.invalid/service/bet/betconf") -> None:
        self.url = url
        self.wait_calls: list[int] = []

    def wait_for_timeout(self, timeout_ms: int) -> None:
        self.wait_calls.append(timeout_ms)


def test_prefill_confirmation_inputs_retries_vote_password_field(monkeypatch) -> None:
    page = FakePage()
    call_count = {"value": 0}

    monkeypatch.setattr(teleboat, "_raise_if_session_timeout", lambda page: None)
    monkeypatch.setattr(teleboat, "_settle", lambda page, milliseconds=700: None)

    def fake_fill_first(page, selectors, value, *, description, timeout_ms=5_000):
        if description != "投票用パスワード":
            return "amount"
        call_count["value"] += 1
        if call_count["value"] < 3:
            raise teleboat.TeleboatError("投票用パスワード の入力欄が見つかりません")
        return "password"

    monkeypatch.setattr(teleboat, "_fill_first", fake_fill_first)

    confirmation_total_amount = teleboat._prefill_confirmation_inputs(
        page,
        vote_password="secret",
        total_amount=0,
        data_dir=Path("C:/tmp"),
        debug_prefix="race123",
    )

    assert confirmation_total_amount == 0
    assert call_count["value"] == 3
    assert page.wait_calls == [10_000, 10_000]


def test_prefill_confirmation_inputs_saves_artifacts_after_vote_password_retries(monkeypatch, tmp_path: Path) -> None:
    page = FakePage(url="https://example.invalid/not-ready")
    saved: list[tuple[str, Path]] = []

    monkeypatch.setattr(teleboat, "_raise_if_session_timeout", lambda page: None)
    monkeypatch.setattr(teleboat, "_settle", lambda page, milliseconds=700: None)

    def fake_fill_first(page, selectors, value, *, description, timeout_ms=5_000):
        raise teleboat.TeleboatError("投票用パスワード の入力欄が見つかりません")

    def fake_save_debug_artifacts(page, *, prefix, data_dir):
        saved.append((prefix, data_dir))
        return ("shot.png", "page.html")

    monkeypatch.setattr(teleboat, "_fill_first", fake_fill_first)
    monkeypatch.setattr(teleboat, "_save_debug_artifacts", fake_save_debug_artifacts)

    with pytest.raises(teleboat.TeleboatExecutionError) as excinfo:
        teleboat._prefill_confirmation_inputs(
            page,
            vote_password="secret",
            total_amount=0,
            data_dir=tmp_path,
            debug_prefix="race123",
        )

    assert str(excinfo.value) == "投票用パスワード の入力欄が見つかりません"
    assert excinfo.value.screenshot_path == "shot.png"
    assert excinfo.value.html_path == "page.html"
    assert excinfo.value.details == {
        "current_url": "https://example.invalid/not-ready",
        "retry_attempts": 3,
        "retry_wait_ms": 10_000,
    }
    assert saved == [("race123_vote_password_missing", tmp_path)]
    assert page.wait_calls == [10_000, 10_000, 10_000]
