from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from live_trigger_cli import runtime

PID_FILE = runtime.data_dir() / "auto_loop.pid"
AUTO_REFRESH_INTERVAL_SECONDS = 5

EXECUTION_MODE_LABELS = {
    "air": "Air",
    "assist_real": "Assist Real",
    "armed_real": "Armed Real",
}

REAL_STRATEGY_LABELS = {
    "fresh_per_execution": "毎回ログイン",
    "burst_reuse": "直近セッション再利用",
}

STATUS_LABELS = {
    "imported": "取り込み済み",
    "monitoring": "監視中",
    "checked_waiting": "待機判定",
    "waiting_market": "市場待ち",
    "checked_go": "GO",
    "intent_created": "Intent作成済み",
    "checked_skip": "見送り",
    "air_bet_logged": "Air記録済み",
    "real_bet_placed": "実投票完了",
    "expired": "締切超過",
    "error": "エラー",
    "withdrawn": "watchlist除外",
    "pending": "未実行",
    "executed": "実行済み",
    "cancelled": "取消",
    "insufficient_funds": "残高不足",
    "assist_timeout": "Assist確認切れ",
    "assist_window_closed": "Assist締切超過",
    "logged": "記録済み",
    "submitted": "送信完了",
}


st.set_page_config(page_title="Live Trigger CLI UI", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        color: #f5f7fb;
        background:
            radial-gradient(circle at top left, rgba(29, 78, 137, 0.24), transparent 28%),
            radial-gradient(circle at top right, rgba(203, 143, 33, 0.18), transparent 24%),
            linear-gradient(180deg, #04070b 0%, #0a1018 42%, #111822 100%);
    }
    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 2rem;
        max-width: 1300px;
    }
    .stApp h1,
    .stApp h2,
    .stApp h3,
    .stApp h4,
    .stApp h5,
    .stApp h6 {
        color: #f8fbff !important;
    }
    .stApp, .stApp p, .stApp label, .stApp span, .stApp div {
        color: inherit;
    }
    .cli-hero {
        background: linear-gradient(135deg, #08111a 0%, #113a58 48%, #9d6c08 100%);
        color: #ffffff;
        border-radius: 22px;
        padding: 1.25rem 1.4rem;
        margin-bottom: 1rem;
        box-shadow: 0 18px 44px rgba(0, 0, 0, 0.35);
    }
    .cli-hero * {
        color: #ffffff !important;
    }
    .cli-note {
        background: rgba(12, 18, 28, 0.88);
        border: 1px solid rgba(115, 145, 173, 0.18);
        border-radius: 16px;
        padding: 0.95rem 1rem;
        margin-bottom: 0.8rem;
        box-shadow: 0 10px 26px rgba(0, 0, 0, 0.22);
    }
    .cli-note code {
        color: #b5ffcd !important;
        background: #08111a;
        border-radius: 8px;
        padding: 0.12rem 0.35rem;
    }
    div[data-testid="stMetric"] {
        background: rgba(10, 16, 24, 0.9);
        border: 1px solid rgba(115, 145, 173, 0.18);
        border-radius: 18px;
        padding: 0.9rem 1rem;
        box-shadow: 0 10px 28px rgba(0, 0, 0, 0.22);
    }
    div[data-testid="stMetricLabel"] p {
        color: #a6b7c9 !important;
        font-weight: 600;
    }
    div[data-testid="stMetricValue"] {
        color: #f7fbff !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.35rem;
    }
    .stTabs [data-baseweb="tab"] {
        background: rgba(12, 18, 28, 0.86);
        border-radius: 12px 12px 0 0;
        color: #a2b5c8;
        padding: 0.55rem 0.9rem 0.7rem;
        border: 1px solid rgba(115, 145, 173, 0.14);
    }
    .stTabs [aria-selected="true"] {
        color: #ffffff !important;
        background: rgba(18, 48, 73, 0.96) !important;
        border-bottom: 3px solid #f3b23a !important;
        font-weight: 700;
    }
    div[data-testid="stForm"],
    div[data-testid="stDataFrame"],
    div[data-testid="stCodeBlock"],
    div[data-testid="stAlert"] {
        border-radius: 16px;
    }
    div[data-testid="stForm"],
    div[data-testid="stDataFrame"],
    div[data-testid="stCodeBlock"],
    div[data-testid="stAlert"],
    div[data-testid="stJson"] {
        background: rgba(10, 16, 24, 0.86);
        border: 1px solid rgba(115, 145, 173, 0.14);
    }
    .stTextInput label,
    .stTextArea label,
    .stDateInput label,
    .stNumberInput label,
    .stSelectbox label,
    .stCheckbox label,
    .stRadio label {
        color: #dbe7f2 !important;
    }
    .stTextInput input,
    .stTextArea textarea,
    .stDateInput input,
    .stNumberInput input {
        color: #f8fbff !important;
        background: #121923 !important;
        border: 1px solid rgba(115, 145, 173, 0.2) !important;
    }
    div[data-baseweb="base-input"] > div,
    div[data-baseweb="select"] > div,
    div[data-baseweb="textarea"] > div {
        background: #121923 !important;
        color: #f8fbff !important;
        border-color: rgba(115, 145, 173, 0.2) !important;
    }
    div[data-baseweb="select"] * {
        color: #f8fbff !important;
    }
    .stButton > button,
    .stDownloadButton > button {
        border-radius: 12px;
        border: 1px solid rgba(115, 145, 173, 0.2);
        background: linear-gradient(180deg, #161d28 0%, #0f141d 100%);
        color: #f8fbff;
    }
    .stButton > button:hover,
    .stDownloadButton > button:hover {
        border-color: rgba(243, 178, 58, 0.45);
        color: #ffffff;
    }
    div[data-testid="stCodeBlock"] pre,
    div[data-testid="stCodeBlock"] code,
    div[data-testid="stJson"] pre,
    div[data-testid="stJson"] code {
        color: #f8fbff !important;
        background: #0a1018 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _notify_success(payload: dict[str, Any], *, label: str) -> None:
    st.success(f"{label} を実行しました。")
    st.json(payload)


def _notify_error(exc: Exception) -> None:
    st.error(str(exc))


def _apply_auto_refresh(enabled: bool, *, interval_seconds: int = AUTO_REFRESH_INTERVAL_SECONDS) -> None:
    interval_ms = max(1, int(interval_seconds)) * 1000
    if enabled:
        script = f"""
        <script>
        const parentWindow = window.parent;
        if (parentWindow.__liveTriggerCliRefreshTimer) {{
            clearTimeout(parentWindow.__liveTriggerCliRefreshTimer);
        }}
        parentWindow.__liveTriggerCliRefreshTimer = setTimeout(() => {{
            parentWindow.location.reload();
        }}, {interval_ms});
        </script>
        """
    else:
        script = """
        <script>
        const parentWindow = window.parent;
        if (parentWindow.__liveTriggerCliRefreshTimer) {
            clearTimeout(parentWindow.__liveTriggerCliRefreshTimer);
            parentWindow.__liveTriggerCliRefreshTimer = null;
        }
        </script>
        """
    components.html(script, height=0)


def _pid_is_running(pid: int | None) -> bool:
    if pid is None or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _read_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def _write_pid(pid: int) -> None:
    PID_FILE.write_text(str(pid), encoding="utf-8")


def _clear_pid_if_stale() -> None:
    pid = _read_pid()
    if pid is not None and not _pid_is_running(pid):
        PID_FILE.unlink(missing_ok=True)


def _tail_log(path: Path, *, lines: int = 80) -> str:
    if not path.exists():
        return ""
    content = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    return "\n".join(content[-lines:])


def _read_query(query: str, params: tuple[Any, ...] = ()) -> pd.DataFrame:
    if not runtime.db_path().exists():
        return pd.DataFrame()
    connection = sqlite3.connect(runtime.db_path(), timeout=2.0)
    connection.execute("PRAGMA busy_timeout = 2000")
    connection.execute("PRAGMA query_only = ON")
    try:
        return pd.read_sql_query(query, connection, params=params)
    except Exception:
        return pd.DataFrame()
    finally:
        connection.close()


def _load_summary() -> tuple[dict[str, Any], str | None]:
    try:
        return runtime.latest_summary(), None
    except Exception as exc:
        return {"targets_by_status": {}, "intents_by_status": {}}, str(exc)


def _status_text(value: Any) -> str:
    text = str(value or "")
    return STATUS_LABELS.get(text, text)


def _mode_text(value: Any) -> str:
    text = str(value or "")
    return EXECUTION_MODE_LABELS.get(text, text)


def _parse_datetime_text(text: str) -> datetime | None:
    value = text.strip()
    if not value:
        return None
    for candidate in (value, value[:-1] + "+00:00" if value.endswith("Z") else None):
        if not candidate:
            continue
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone().replace(tzinfo=None)
            return parsed
        except ValueError:
            continue
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
    ):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError("as_of は YYYY-MM-DD HH:MM[:SS] 形式で入力してください。")


def _profile_frame(settings: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    profiles = runtime.load_runtime_profiles(include_disabled=True)
    for profile in profiles:
        rows.append(
            {
                "profile_id": profile.profile_id,
                "display_name": profile.display_name,
                "box_id": profile.box_id,
                "enabled": runtime.profile_enabled(settings, profile.profile_id),
                "amount": runtime.profile_amount(settings, profile.profile_id),
                "runtime_profile_enabled": bool(profile.enabled),
            }
        )
    return pd.DataFrame(rows)


def _latest_targets_frame(limit: int = 200) -> pd.DataFrame:
    frame = _read_query(
        """
        SELECT
            race_id,
            race_date,
            stadium_code,
            stadium_name,
            race_no,
            profile_id,
            strategy_id,
            deadline_at,
            status,
            row_status,
            last_reason,
            updated_at
        FROM target_races
        ORDER BY updated_at DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    )
    if frame.empty:
        return frame
    frame["場"] = frame["stadium_code"] + " " + frame["stadium_name"].fillna("")
    frame["状態"] = frame["status"].map(_status_text)
    frame["判定"] = frame["row_status"].map(_status_text)
    return frame[
        [
            "race_id",
            "race_date",
            "場",
            "race_no",
            "profile_id",
            "strategy_id",
            "deadline_at",
            "状態",
            "判定",
            "last_reason",
            "updated_at",
        ]
    ]


def _latest_intents_frame(limit: int = 200) -> pd.DataFrame:
    frame = _read_query(
        """
        SELECT
            bet_intents.id,
            bet_intents.target_race_id,
            target_races.race_id,
            target_races.profile_id,
            target_races.strategy_id,
            bet_intents.execution_mode,
            bet_intents.status,
            bet_intents.bet_type,
            bet_intents.combo,
            bet_intents.amount,
            bet_intents.created_at
        FROM bet_intents
        JOIN target_races ON target_races.id = bet_intents.target_race_id
        ORDER BY bet_intents.created_at DESC, bet_intents.id DESC
        LIMIT ?
        """,
        (limit,),
    )
    if frame.empty:
        return frame
    frame["実行モード"] = frame["execution_mode"].map(_mode_text)
    frame["状態"] = frame["status"].map(_status_text)
    return frame[
        [
            "id",
            "race_id",
            "profile_id",
            "strategy_id",
            "bet_type",
            "combo",
            "amount",
            "実行モード",
            "状態",
            "created_at",
        ]
    ]


def _latest_executions_frame(limit: int = 200) -> pd.DataFrame:
    frame = _read_query(
        """
        SELECT
            bet_executions.id,
            target_races.race_id,
            target_races.profile_id,
            bet_executions.execution_mode,
            bet_executions.execution_status,
            bet_executions.executed_at,
            bet_executions.seconds_before_deadline,
            bet_executions.contract_no,
            bet_executions.screenshot_path,
            bet_executions.error_message
        FROM bet_executions
        JOIN target_races ON target_races.id = bet_executions.target_race_id
        ORDER BY bet_executions.executed_at DESC, bet_executions.id DESC
        LIMIT ?
        """,
        (limit,),
    )
    if frame.empty:
        return frame
    frame["実行モード"] = frame["execution_mode"].map(_mode_text)
    frame["状態"] = frame["execution_status"].map(_status_text)
    return frame[
        [
            "id",
            "race_id",
            "profile_id",
            "実行モード",
            "状態",
            "executed_at",
            "seconds_before_deadline",
            "contract_no",
            "screenshot_path",
            "error_message",
        ]
    ]


def _latest_events_frame(limit: int = 200) -> pd.DataFrame:
    return _read_query(
        """
        SELECT
            event_at,
            event_type,
            target_race_id,
            intent_id,
            message,
            details_json
        FROM execution_events
        ORDER BY event_at DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    )


def _latest_session_events_frame(limit: int = 120) -> pd.DataFrame:
    return _read_query(
        """
        SELECT
            event_at,
            event_type,
            message,
            details_json
        FROM session_events
        ORDER BY event_at DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    )


def _parse_bet_lines(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split(":", 2)
        if len(parts) != 3:
            raise ValueError(f"ベット行の形式が不正です: {line}")
        bet_type, combo, amount_text = parts
        rows.append(
            {
                "bet_type": bet_type.strip(),
                "combo": combo.strip(),
                "amount": int(amount_text),
            }
        )
    return rows


def _spawn_auto_loop() -> int:
    runtime.initialize_runtime()
    existing_pid = _read_pid()
    if _pid_is_running(existing_pid):
        return int(existing_pid)
    creationflags = 0
    creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0)
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        value
        for value in (
            str(REPO_ROOT),
            str(REPO_ROOT / "src"),
            env.get("PYTHONPATH", ""),
        )
        if value
    )
    process = subprocess.Popen(
        [sys.executable, "-m", "live_trigger_cli", "auto-loop"],
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        close_fds=True,
        creationflags=creationflags,
        env=env,
    )
    deadline = time.time() + 3.0
    while time.time() < deadline:
        running_pid = _read_pid()
        if _pid_is_running(running_pid):
            return int(running_pid)
        if process.poll() is not None:
            break
        time.sleep(0.1)
    _write_pid(process.pid)
    return int(process.pid)


def _save_profile_table(edited: pd.DataFrame, current_settings: dict[str, Any]) -> dict[str, Any]:
    profile_amount_updates = {
        str(row["profile_id"]): int(row["amount"])
        for _, row in edited.iterrows()
    }
    enabled_profiles = [str(row["profile_id"]) for _, row in edited.iterrows() if bool(row["enabled"])]
    disabled_profiles = [str(row["profile_id"]) for _, row in edited.iterrows() if not bool(row["enabled"])]
    return runtime.configure_runtime(
        execution_mode=current_settings["execution_mode"],
        setting_overrides={
            "system_running": current_settings["system_running"],
            "poll_seconds": current_settings["poll_seconds"],
            "check_window_start_minutes": current_settings["check_window_start_minutes"],
            "check_window_end_minutes": current_settings["check_window_end_minutes"],
            "default_bet_amount": current_settings["default_bet_amount"],
            "real_headless": current_settings["real_headless"],
            "stop_on_insufficient_funds": current_settings["stop_on_insufficient_funds"],
            "manual_action_timeout_seconds": current_settings["manual_action_timeout_seconds"],
            "login_timeout_seconds": current_settings["login_timeout_seconds"],
            "real_session_strategy": current_settings["real_session_strategy"],
            "reuse_when_next_real_within_seconds": current_settings["reuse_when_next_real_within_seconds"],
            "post_login_settle_seconds": current_settings["post_login_settle_seconds"],
            "top_stable_confirm_seconds": current_settings["top_stable_confirm_seconds"],
            "logout_after_execution": current_settings["logout_after_execution"],
            "close_browser_after_execution": current_settings["close_browser_after_execution"],
        },
        profile_amount_updates=profile_amount_updates,
        enabled_profiles=enabled_profiles,
        disabled_profiles=disabled_profiles,
    )


def _profile_generation_summary() -> dict[str, Any]:
    profiles = runtime.load_runtime_profiles(include_disabled=True)
    return {
        "shared_profiles": [profile.profile_id for profile in profiles if profile.source_kind == "shared"],
        "local_profiles": [profile.profile_id for profile in profiles if profile.source_kind == "local"],
        "raw_root": str(runtime.raw_root()),
    }


_clear_pid_if_stale()
settings = runtime.load_settings()
summary, summary_warning = _load_summary()
pid = _read_pid()
loop_running = _pid_is_running(pid)
generation_summary = _profile_generation_summary()

if "ui_auto_refresh" not in st.session_state:
    st.session_state["ui_auto_refresh"] = True

refresh_cols = st.columns([1.1, 2.4, 1.5])
auto_refresh_enabled = refresh_cols[0].toggle(
    "5秒自動更新",
    key="ui_auto_refresh",
    help="状態表示を5秒ごとに更新します。設定入力や手動テスト中は OFF 推奨です。",
)
refresh_cols[1].caption(
    "loop 状態や summary を 5 秒ごとに読み直します。入力中に邪魔なときは OFF にしてください。"
)
refresh_cols[2].caption(f"最終描画: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
_apply_auto_refresh(bool(auto_refresh_enabled))

st.markdown(
    """
    <div class="cli-hero">
      <h2 style="margin:0 0 0.35rem 0;">Live Trigger CLI UI</h2>
      <div style="font-size:1rem;">
        既存ラインを触らずに、CLI 主導の新ベットラインを UI から管理する画面です。
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

top = st.columns(5)
top[0].metric("実行モード", EXECUTION_MODE_LABELS.get(settings["execution_mode"], settings["execution_mode"]))
top[1].metric("system_running", "ON" if settings["system_running"] else "OFF")
top[2].metric("loop PID", str(pid) if loop_running else "-")
top[3].metric("targets", str(sum(summary.get("targets_by_status", {}).values())))
top[4].metric("pending intents", str(summary.get("intents_by_status", {}).get("pending", 0)))

st.markdown(
    """
    <div class="cli-note">
      shared <code>boxes/watchlists/raw</code> を読み込む新ラインです。
      <code>settings.json/system.db/auto_run.log</code> はこの新ライン専用です。
    </div>
    """,
    unsafe_allow_html=True,
)

tab_overview, tab_settings, tab_actions, tab_manual, tab_data = st.tabs(
    ["概要", "設定", "実行", "手動テスト", "データ"]
)

with tab_overview:
    if summary_warning:
        st.warning(f"概要集計を一時的に読めませんでした: {summary_warning}")
    st.info(
        "\n".join(
            [
                "使い方の最短手順",
                "1. 設定 で execution_mode と profile の enabled / amount を決める",
                "2. 実行 で対象日を入れて sync-watchlists を押す",
                "3. evaluate-targets で GO 判定と intent を作る",
                "4. execute-bets で air / real を実行する。まとめてやるなら run-cycle",
                "5. まずは 手動テスト の confirm_only で確認画面まで試す",
            ]
        )
    )
    col1, col2 = st.columns([1.2, 1.0])
    with col1:
        st.subheader("状態サマリー")
        st.json(summary)
        st.subheader("このラインが生成する profile")
        st.write(
            {
                "shared_profiles": generation_summary["shared_profiles"],
                "local_profiles": generation_summary["local_profiles"],
                "raw_root": generation_summary["raw_root"],
            }
        )
        st.caption(
            "sync-watchlists は shared watchlist CSV を読むのではなく、shared BOX と local BOX をもとに "
            "このライン自身の raw キャッシュへ racelist を集めて候補を生成します。"
        )
    with col2:
        st.subheader("ループ状態")
        st.write(f"PIDファイル: `{PID_FILE}`")
        if loop_running:
            st.success(f"auto-loop は PID `{pid}` で起動中です。")
        elif pid is not None:
            st.warning("PIDファイルは残っていますが、プロセスは動いていません。")
        else:
            st.info("auto-loop は起動していません。")

    st.subheader("最新ターゲット")
    latest_targets = _latest_targets_frame(limit=20)
    if latest_targets.empty:
        st.info("まだ target はありません。")
    else:
        st.dataframe(latest_targets, width="stretch", hide_index=True)

    st.subheader("ログ末尾")
    log_text = _tail_log(runtime.auto_run_log_path(), lines=60)
    if log_text:
        st.code(log_text, language="text")
    else:
        st.caption("まだログはありません。")

with tab_settings:
    st.subheader("基本設定")
    with st.form("settings_form"):
        col1, col2, col3 = st.columns(3)
        execution_mode = col1.selectbox(
            "実行モード",
            options=list(runtime.VALID_EXECUTION_MODES),
            index=list(runtime.VALID_EXECUTION_MODES).index(settings["execution_mode"]),
            format_func=lambda value: EXECUTION_MODE_LABELS.get(value, value),
        )
        system_running = col2.checkbox("system_running", value=bool(settings["system_running"]))
        real_headless = col3.checkbox("headless", value=bool(settings["real_headless"]))

        col4, col5, col6 = st.columns(3)
        poll_seconds = col4.number_input("poll_seconds", min_value=5, value=int(settings["poll_seconds"]), step=5)
        window_start = col5.number_input(
            "監視開始までの分",
            min_value=1,
            value=int(settings["check_window_start_minutes"]),
            step=1,
        )
        window_end = col6.number_input(
            "監視終了までの分",
            min_value=0,
            value=int(settings["check_window_end_minutes"]),
            step=1,
        )

        col7, col8, col9 = st.columns(3)
        default_bet_amount = col7.number_input(
            "default_bet_amount",
            min_value=0,
            value=int(settings["default_bet_amount"]),
            step=100,
        )
        manual_timeout = col8.number_input(
            "manual_action_timeout_seconds",
            min_value=30,
            value=int(settings["manual_action_timeout_seconds"]),
            step=30,
        )
        login_timeout = col9.number_input(
            "login_timeout_seconds",
            min_value=30,
            value=int(settings["login_timeout_seconds"]),
            step=30,
        )

        col10, col11, col12 = st.columns(3)
        session_strategy = col10.selectbox(
            "real_session_strategy",
            options=list(runtime.VALID_REAL_SESSION_STRATEGIES),
            index=list(runtime.VALID_REAL_SESSION_STRATEGIES).index(settings["real_session_strategy"]),
            format_func=lambda value: REAL_STRATEGY_LABELS.get(value, value),
        )
        reuse_seconds = col11.number_input(
            "reuse_when_next_real_within_seconds",
            min_value=0,
            value=int(settings["reuse_when_next_real_within_seconds"]),
            step=30,
        )
        post_login_settle = col12.number_input(
            "post_login_settle_seconds",
            min_value=1,
            value=int(settings["post_login_settle_seconds"]),
            step=1,
        )

        col13, col14, col15 = st.columns(3)
        top_stable = col13.number_input(
            "top_stable_confirm_seconds",
            min_value=1,
            value=int(settings["top_stable_confirm_seconds"]),
            step=1,
        )
        stop_on_funds = col14.checkbox(
            "残高不足で停止",
            value=bool(settings["stop_on_insufficient_funds"]),
        )
        logout_after_execution = col15.checkbox(
            "実行後にログアウト",
            value=bool(settings["logout_after_execution"]),
        )
        close_browser_after_execution = st.checkbox(
            "実行後にブラウザを閉じる",
            value=bool(settings["close_browser_after_execution"]),
        )
        st.caption("Telegram GO 通知")
        tg_col1, tg_col2 = st.columns(2)
        telegram_enabled = tg_col1.checkbox(
            "Telegram 通知を有効化",
            value=bool(settings.get("telegram_enabled", False)),
        )
        telegram_go_notifications = tg_col2.checkbox(
            "GO 通知を送る",
            value=bool(settings.get("telegram_go_notifications", True)),
        )
        telegram_token = st.text_input(
            "telegram_bot_token",
            value=str(settings.get("telegram_bot_token", "")),
            type="password",
            help="未入力なら LIVE_TRIGGER_TELEGRAM_BOT_TOKEN / TELEGRAM_BOT_TOKEN を使います。",
        )
        telegram_chat_id = st.text_input(
            "telegram_chat_id",
            value=str(settings.get("telegram_chat_id", "")),
            help="未入力なら LIVE_TRIGGER_TELEGRAM_CHAT_ID / TELEGRAM_CHAT_ID を使います。",
        )

        save_basic = st.form_submit_button("基本設定を保存", width="stretch")
        if save_basic:
            try:
                result = runtime.configure_runtime(
                    execution_mode=execution_mode,
                    setting_overrides={
                        "system_running": system_running,
                        "poll_seconds": int(poll_seconds),
                        "check_window_start_minutes": int(window_start),
                        "check_window_end_minutes": int(window_end),
                        "default_bet_amount": int(default_bet_amount),
                        "real_headless": real_headless,
                        "stop_on_insufficient_funds": stop_on_funds,
                        "manual_action_timeout_seconds": int(manual_timeout),
                        "login_timeout_seconds": int(login_timeout),
                        "real_session_strategy": session_strategy,
                        "reuse_when_next_real_within_seconds": int(reuse_seconds),
                        "post_login_settle_seconds": int(post_login_settle),
                        "top_stable_confirm_seconds": int(top_stable),
                        "logout_after_execution": logout_after_execution,
                        "close_browser_after_execution": close_browser_after_execution,
                        "telegram_enabled": telegram_enabled,
                        "telegram_go_notifications": telegram_go_notifications,
                        "telegram_bot_token": telegram_token,
                        "telegram_chat_id": telegram_chat_id,
                    },
                )
                _notify_success(result, label="基本設定")
            except Exception as exc:  # noqa: BLE001
                _notify_error(exc)

    st.subheader("Profile ごとの有効化と金額")
    profile_frame = _profile_frame(runtime.load_settings())
    edited_profiles = st.data_editor(
        profile_frame,
        width="stretch",
        hide_index=True,
        num_rows="fixed",
        column_config={
            "profile_id": st.column_config.TextColumn("profile_id", disabled=True),
            "display_name": st.column_config.TextColumn("display_name", disabled=True),
            "box_id": st.column_config.TextColumn("box_id", disabled=True),
            "enabled": st.column_config.CheckboxColumn("このラインで有効"),
            "amount": st.column_config.NumberColumn("金額", min_value=0, step=100),
            "runtime_profile_enabled": st.column_config.CheckboxColumn("shared profile有効", disabled=True),
        },
        key="live_trigger_cli_profile_editor",
    )
    if st.button("Profile設定を保存", width="stretch"):
        try:
            result = _save_profile_table(edited_profiles, runtime.load_settings())
            _notify_success(result, label="Profile設定")
        except Exception as exc:  # noqa: BLE001
            _notify_error(exc)

with tab_actions:
    st.subheader("即時実行")
    col1, col2 = st.columns([1.3, 1.0])
    with col1:
        race_date = st.text_input("対象日", value=datetime.now().strftime("%Y-%m-%d"))
    with col2:
        as_of_text = st.text_input("as_of 基準時刻", value="")

    st.info(
        f"{race_date} は新ライン自身が `125 / c2 / 4wind` を生成します。"
        " shared watchlist CSV が空でも問題ありません。"
    )
    st.caption("基本の順番は `sync-watchlists -> evaluate-targets -> execute-bets` です。まとめてやるなら `run-cycle` を使います。")

    try:
        as_of_value = _parse_datetime_text(as_of_text) if as_of_text.strip() else None
    except ValueError as exc:
        as_of_value = None
        st.error(str(exc))

    row1 = st.columns(4)
    if row1[0].button("sync-watchlists", width="stretch"):
        try:
            with st.spinner("新ライン用 watchlist を生成中..."):
                _notify_success(runtime.sync_watchlists(race_date=race_date), label="sync-watchlists")
        except Exception as exc:  # noqa: BLE001
            _notify_error(exc)
    if row1[1].button("evaluate-targets", width="stretch"):
        try:
            with st.spinner("beforeinfo と odds を評価中..."):
                _notify_success(runtime.evaluate_targets(race_date=race_date, as_of=as_of_value), label="evaluate-targets")
        except Exception as exc:  # noqa: BLE001
            _notify_error(exc)
    if row1[2].button("execute-bets", width="stretch"):
        try:
            with st.spinner("pending intents を実行中..."):
                _notify_success(runtime.execute_bets(race_date=race_date, as_of=as_of_value), label="execute-bets")
        except Exception as exc:  # noqa: BLE001
            _notify_error(exc)
    if row1[3].button("run-cycle", width="stretch"):
        try:
            with st.spinner("1 サイクル実行中..."):
                _notify_success(runtime.run_cycle(race_date=race_date, as_of=as_of_value), label="run-cycle")
        except Exception as exc:  # noqa: BLE001
            _notify_error(exc)

    st.subheader("ループ制御")
    loop_cols = st.columns(3)
    if loop_cols[0].button("system_running を ON", width="stretch"):
        try:
            _notify_success(runtime.configure_runtime(setting_overrides={"system_running": True}), label="system_running ON")
        except Exception as exc:  # noqa: BLE001
            _notify_error(exc)
    if loop_cols[1].button("system_running を OFF", width="stretch"):
        try:
            _notify_success(runtime.configure_runtime(setting_overrides={"system_running": False}), label="system_running OFF")
        except Exception as exc:  # noqa: BLE001
            _notify_error(exc)
    if loop_cols[2].button("auto-loop を起動", width="stretch"):
        try:
            if loop_running:
                st.warning(f"auto-loop はすでに PID `{pid}` で起動中です。")
            else:
                runtime.configure_runtime(setting_overrides={"system_running": True})
                started_pid = _spawn_auto_loop()
                st.success(f"auto-loop を PID `{started_pid}` で起動しました。")
        except Exception as exc:  # noqa: BLE001
            _notify_error(exc)

    st.caption("注意: auto-loop はこの新ライン専用です。既存ラインの loop や DB には触れません。")

with tab_manual:
    st.subheader("Teleboat 手動テスト")
    st.caption("既存の fresh executor を流用しつつ、この新ラインの設定値で疎通テストします。")

    form_col1, form_col2, form_col3 = st.columns(3)
    test_mode = form_col1.selectbox(
        "test_mode",
        options=["login_only", "confirm_only", "confirm_prefill", "assist_real", "armed_real"],
    )
    stadium_code = form_col2.text_input("stadium_code", value="01")
    race_no = form_col3.number_input("race_no", min_value=1, max_value=12, value=12, step=1)

    bet_lines = st.text_area(
        "ベット内容",
        value="trifecta:1-2-5:100\ntrifecta:2-ALL-ALL:100",
        help="1行に1ベット。形式は BET_TYPE:COMBO:AMOUNT",
        height=120,
    )

    row = st.columns(3)
    cleanup_after_test = row[0].checkbox("cleanup_after_test", value=True)
    hold_open_seconds = row[1].number_input("hold_open_seconds", min_value=0, value=0, step=5)
    next_real_target = row[2].number_input("next_real_target_in_seconds", min_value=0, value=0, step=30)

    manual_settings_row = st.columns(3)
    manual_headless = manual_settings_row[0].checkbox("headless override", value=False)
    manual_timeout = manual_settings_row[1].number_input("manual timeout", min_value=30, value=180, step=30)
    login_timeout = manual_settings_row[2].number_input("login timeout", min_value=30, value=120, step=30)

    if st.button("手動テストを実行", width="stretch"):
        try:
            payload: dict[str, Any] = {
                "test_mode": test_mode,
                "cleanup_after_test": cleanup_after_test,
                "hold_open_seconds": int(hold_open_seconds),
                "settings": {
                    "real_headless": manual_headless,
                    "manual_action_timeout_seconds": int(manual_timeout),
                    "login_timeout_seconds": int(login_timeout),
                },
            }
            if int(next_real_target) > 0:
                payload["next_real_target_in_seconds"] = int(next_real_target)
            if test_mode != "login_only":
                payload["stadium_code"] = stadium_code
                payload["race_no"] = int(race_no)
                payload["bets"] = _parse_bet_lines(bet_lines)
            with st.spinner("Teleboat 手動テストを実行中..."):
                result = runtime.run_manual_test(payload)
            if result.get("ok"):
                st.success("手動テストが完了しました。")
            else:
                st.error("手動テストでエラーが発生しました。")
            st.json(result)
        except Exception as exc:  # noqa: BLE001
            _notify_error(exc)

with tab_data:
    subtab1, subtab2, subtab3, subtab4, subtab5 = st.tabs(
        ["Targets", "Intents", "Executions", "Events", "Session"]
    )
    with subtab1:
        frame = _latest_targets_frame()
        if frame.empty:
            st.info("target はまだありません。")
        else:
            st.dataframe(frame, width="stretch", hide_index=True)
    with subtab2:
        frame = _latest_intents_frame()
        if frame.empty:
            st.info("intent はまだありません。")
        else:
            st.dataframe(frame, width="stretch", hide_index=True)
    with subtab3:
        frame = _latest_executions_frame()
        if frame.empty:
            st.info("execution はまだありません。")
        else:
            st.dataframe(frame, width="stretch", hide_index=True)
    with subtab4:
        frame = _latest_events_frame()
        if frame.empty:
            st.info("event はまだありません。")
        else:
            st.dataframe(frame, width="stretch", hide_index=True)
    with subtab5:
        frame = _latest_session_events_frame()
        if frame.empty:
            st.info("session event はまだありません。")
        else:
            st.dataframe(frame, width="stretch", hide_index=True)
