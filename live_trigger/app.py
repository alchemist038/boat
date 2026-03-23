from __future__ import annotations

from datetime import date
from pathlib import Path
import json
import sys
import traceback

APP_ROOT = Path(__file__).resolve().parent
RUNTIME_ROOT = APP_ROOT / "runtime"
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

import pandas as pd
import streamlit as st
from streamlit.components.v1 import html as st_html
from streamlit.runtime.scriptrunner import get_script_run_ctx

from auto_system.app.core.bets import bet_point_count, bet_total_amount, build_bet_rows
from boat_race_data.client import BoatRaceClient
from boat_race_data.live_trigger import (
    build_watchlist_for_profiles,
    judge_air_bet,
    load_trigger_profiles,
    read_watchlist,
    record_air_bets,
    resolve_watchlist_for_profiles,
    run_air_bet_flow_cli,
)
from boat_race_data.logic_board import build_logic_board
from shared_contract import SHARED_BOX_ROOT
import random

PROFILE_ROOT = SHARED_BOX_ROOT
PLANS_ROOT = APP_ROOT / "plans"
RAW_ROOT = APP_ROOT / "raw"
WATCHLIST_ROOT = APP_ROOT / "watchlists"
READY_ROOT = APP_ROOT / "ready"
AIR_BET_LOG_FILE = APP_ROOT / "air_bet_log.csv"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_RACE_NO = 12
DEFAULT_SLEEP_SECONDS = 0.5
MAX_BET_PER_DAY = 10


def _normalize_air_bet_record(record: dict[str, object]) -> dict[str, object]:
    normalized = dict(record)
    if (
        "unit_amount" in normalized
        and "ticket_count" in normalized
        and "amount" in normalized
    ):
        return normalized

    logic_name = str(normalized.get("logic") or normalized.get("profile_id") or "")
    strategy_id = str(normalized.get("strategy_id") or logic_name)
    unit_amount = int(normalized.get("unit_amount", normalized.get("amount", 0)) or 0)
    bet_rows = build_bet_rows(
        strategy_id=strategy_id,
        profile_id=logic_name,
        amount=unit_amount,
        context=normalized,
    )
    if not bet_rows:
        normalized["unit_amount"] = unit_amount
        normalized["ticket_count"] = 1 if unit_amount > 0 else 0
        normalized["amount"] = unit_amount
        return normalized

    normalized["unit_amount"] = unit_amount
    normalized["ticket_count"] = sum(
        bet_point_count(bet_type=str(row["bet_type"]), combo=str(row["combo"]))
        for row in bet_rows
    )
    normalized["amount"] = sum(
        bet_total_amount(
            bet_type=str(row["bet_type"]),
            combo=str(row["combo"]),
            unit_amount=int(row["amount"]),
        )
        for row in bet_rows
    )
    return normalized

PROFILE_COLUMNS_JA = {
    "box_id": "BOX",
    "profile_id": "PROFILE",
    "strategy_id": "戦略",
    "display_name": "表示名",
    "enabled": "有効",
    "stadiums": "対象場",
    "watch_minutes_before_deadline": "監視開始(分前)",
    "description": "説明",
}

WATCHLIST_COLUMNS_JA = {
    "box_id": "BOX",
    "profile_id": "PROFILE",
    "strategy_id": "戦略",
    "race_id": "race_id",
    "race_date": "日付",
    "stadium_code": "場コード",
    "stadium_name": "場名",
    "race_no": "R",
    "meeting_title": "開催名",
    "race_title": "レース名",
    "deadline_time": "締切",
    "watch_start_time": "監視開始",
    "status": "状態",
    "pre_reason": "事前条件",
    "final_reason": "直前条件",
    "lane1_racer_name": "1号艇選手",
    "lane1_racer_class": "1号艇級別",
    "lane1_motor_place_rate": "1号艇モーター2連率",
    "lane1_motor_top3_rate": "1号艇モーター3連率",
    "lane1_exhibition_time": "1号艇展示",
    "lane1_exhibition_best_gap": "1号艇最速差",
    "lane2_exhibition_time": "2号艇展示",
    "lane3_exhibition_time": "3号艇展示",
    "lane1_start_exhibition_st": "1号艇ST展示",
    "min_other_start_exhibition_st": "他艇最小ST展示",
    "lane1_start_gap_over_rest": "1号艇ST差",
    "beforeinfo_fetched_at": "beforeinfo取得時刻",
}


def _profile_label(profile) -> str:
    status = "有効" if profile.enabled else "無効"
    return f"{profile.box_id} / {profile.display_name} ({status})"


def _profile_summary_rows(profiles: list) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for profile in profiles:
        rows.append(
            {
                "box_id": profile.box_id,
                "profile_id": profile.profile_id,
                "strategy_id": profile.strategy_id,
                "display_name": profile.display_name,
                "enabled": profile.enabled,
                "stadiums": ",".join(profile.stadiums) if profile.stadiums else "all",
                "watch_minutes_before_deadline": profile.watch_minutes_before_deadline,
                "description": profile.description,
            }
        )
    return rows


def _watchlist_frame(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    rows = read_watchlist(path)
    return pd.DataFrame(rows)


def _available_watchlists() -> list[Path]:
    if not WATCHLIST_ROOT.exists():
        return []
    return sorted(WATCHLIST_ROOT.glob("*.csv"), reverse=True)


def _available_ready_files() -> list[Path]:
    if not READY_ROOT.exists():
        return []
    return sorted(READY_ROOT.glob("*.csv"), reverse=True)


def _default_watchlist_name(target_date: date) -> str:
    return f"{target_date:%Y%m%d}_app_batch.csv"


def _matching_date_files(root: Path, target_date: date, *, suffix: str = ".csv") -> list[Path]:
    if not root.exists():
        return []
    prefix = f"{target_date:%Y%m%d}_"
    candidates = [
        path
        for path in root.glob("*.csv")
        if path.name.startswith(prefix) and path.name.endswith(suffix)
    ]
    return sorted(candidates, key=lambda path: (path.stat().st_mtime, path.name), reverse=True)


def _session_path(key: str) -> Path | None:
    raw = st.session_state.get(key)
    if not raw:
        return None
    path = Path(str(raw))
    if not path.exists():
        return None
    return path


def _set_watchlist_session(path: Path) -> None:
    rows = read_watchlist(path)
    st.session_state["watchlist_path"] = str(path)
    st.session_state["watchlist_count"] = len(rows)


def _set_ready_session(path: Path) -> None:
    rows = read_watchlist(path)
    ready_count = sum(1 for row in rows if str(row.get("status", "")).strip() == "trigger_ready")
    st.session_state["ready_path"] = str(path)
    st.session_state["resolve_ready_count"] = ready_count
    st.session_state["resolve_changed_rows"] = 0


def _restore_existing_outputs(target_date: date) -> None:
    if _session_path("watchlist_path") is None:
        watchlists = _matching_date_files(WATCHLIST_ROOT, target_date)
        if watchlists:
            _set_watchlist_session(watchlists[0])

    if _session_path("ready_path") is None:
        ready_files = _matching_date_files(READY_ROOT, target_date, suffix="_ready.csv")
        if ready_files:
            _set_ready_session(ready_files[0])


def _logic_display_name(profile) -> str:
    if profile is None:
        return "unknown"
    return str(profile.display_name or profile.profile_id)


def _logic_targets_for_watchlist(profiles: list, watchlist_path: Path | None) -> list[dict[str, object]]:
    profile_map = {profile.profile_id: profile for profile in profiles}
    targets: list[dict[str, object]] = []
    seen: set[str] = set()

    if watchlist_path is not None and watchlist_path.exists():
        for row in read_watchlist(watchlist_path):
            logic_id = str(row.get("profile_id", "")).strip()
            if not logic_id or logic_id in seen:
                continue
            profile = profile_map.get(logic_id)
            targets.append(
                {
                    "logic_id": logic_id,
                    "label": _logic_display_name(profile) if profile is not None else logic_id,
                    "default_enabled": bool(profile.enabled) if profile is not None else True,
                }
            )
            seen.add(logic_id)

    if targets:
        return targets

    for profile in profiles:
        if not profile.enabled:
            continue
        targets.append(
            {
                "logic_id": str(profile.profile_id),
                "label": _logic_display_name(profile),
                "default_enabled": True,
            }
        )
    return targets


def _rename_columns(frame: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    columns = [column for column in mapping if column in frame.columns]
    if not columns:
        return frame
    return frame.loc[:, columns].rename(columns={column: mapping[column] for column in columns})


def _render_exception(message: str, exc: Exception) -> None:
    st.error(message)
    with st.expander("詳細"):
        st.code("".join(traceback.format_exception(exc)), language="text")


def _resolve_profile_path(box_id: str, profile_id: str) -> Path | None:
    """プロファイルの JSON パスを特定する。"""
    box_dir = PROFILE_ROOT / box_id / "profiles"
    if not box_dir.exists():
        return None
    for path in box_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("profile_id") == profile_id:
                return path
        except Exception:
            continue
    return None


def _save_profile_enabled(path: Path, profile_id: str, enabled: bool) -> tuple[bool, str]:
    """JSON ファイルの enabled フィールドのみを更新する。"""
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
        if content.get("profile_id") != profile_id:
            return False, f"Profile ID 不一致: {profile_id} != {content.get('profile_id')}"

        old_enabled = content.get("enabled", True)
        if old_enabled == enabled:
            return True, "変更なし"

        content["enabled"] = enabled
        path.write_text(json.dumps(content, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return True, f"成功: {path.name} ({old_enabled} -> {enabled})"
    except Exception as exc:
        return False, f"失敗: {exc}"


def main() -> None:
    st.set_page_config(
        page_title="BOAT Live Trigger",
        layout="wide",
    )
    st.title("BOAT Live Trigger")
    st.caption("予定確認、翌日候補抽出、直前判定を1画面で扱うためのローカルアプリです。")

    if "air_bet_history" not in st.session_state:
        st.session_state["air_bet_history"] = []

    try:
        profiles = load_trigger_profiles(PROFILE_ROOT, include_disabled=True)
    except Exception as exc:
        _render_exception("BOX 設定の読み込みに失敗しました。", exc)
        return

    label_to_profile = {_profile_label(profile): profile for profile in profiles}
    enabled_labels = [label for label, profile in label_to_profile.items() if profile.enabled]
    profile_name_map = {profile.profile_id: _logic_display_name(profile) for profile in profiles}
    _restore_existing_outputs(date.today())

    with st.sidebar:
        st.header("BOX 一覧")
        profile_frame = pd.DataFrame(_profile_summary_rows(profiles))
        st.dataframe(
            _rename_columns(profile_frame, PROFILE_COLUMNS_JA),
            use_container_width=True,
            hide_index=True,
        )
        st.caption("batch 候補抽出は通常、有効 profile だけを対象にします。")

        st.divider()
        st.subheader("有効/無効の切替")
        for profile in profiles:
            p_key = f"toggle_{profile.box_id}_{profile.profile_id}"
            # 初期値設定
            if p_key not in st.session_state:
                st.session_state[p_key] = profile.enabled

            new_val = st.toggle(
                label=f"{profile.box_id} / {profile.display_name}",
                value=st.session_state[p_key],
                key=f"ui_{p_key}",
            )

            # 値が変更されたら保存
            if new_val != st.session_state[p_key]:
                path = _resolve_profile_path(profile.box_id, profile.profile_id)
                if path:
                    success, msg = _save_profile_enabled(path, profile.profile_id, new_val)
                    if success:
                        st.sidebar.success(msg)
                        st.sidebar.info(f"Path: {path}")
                        st.session_state[p_key] = new_val
                        # プロファイル再読み込みのためにリラン
                        st.rerun()
                    else:
                        st.sidebar.error(msg)
                else:
                    st.sidebar.error(f"パスの特定に失敗: {profile.profile_id}")

    board_tab, watchlist_tab, resolve_tab, air_bet_tab, stats_tab = st.tabs(
        ["予定ボード", "翌日候補抽出", "直前判定", "Air Bet", "成績管理"]
    )

    with board_tab:
        st.subheader("予定ボード")
        with st.form("board_form"):
            board_start_date = st.date_input("開始日", value=date.today())
            board_days = st.slider("表示日数", min_value=7, max_value=31, value=14)
            board_submitted = st.form_submit_button("予定ボードを作成")

        if board_submitted:
            try:
                with st.spinner("予定ボードを作成中..."):
                    outputs = build_logic_board(
                        start_date=board_start_date.isoformat(),
                        days=int(board_days),
                        profiles=profiles,
                        output_dir=PLANS_ROOT,
                        raw_root=RAW_ROOT,
                        timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
                    )
                st.session_state["board_html_path"] = str(outputs["logic_board_html"])
                st.session_state["board_md_path"] = str(outputs["logic_board_md"])
            except Exception as exc:
                _render_exception("予定ボードの作成に失敗しました。", exc)

        board_html_path = _session_path("board_html_path")
        board_md_path = _session_path("board_md_path")
        if board_html_path is not None:
            st.success(f"出力先: {board_html_path}")
            st_html(board_html_path.read_text(encoding="utf-8"), height=1200, scrolling=True)
        else:
            st.info("まず上のボタンで予定ボードを作成してください。")
        if board_md_path is not None:
            with st.expander("Markdown 表示"):
                st.code(board_md_path.read_text(encoding="utf-8"), language="markdown")

    with watchlist_tab:
        st.subheader("翌日候補抽出")
        with st.form("watchlist_form"):
            watchlist_date = st.date_input("対象日", value=date.today())
            selected_labels = st.multiselect(
                "使う profile",
                options=list(label_to_profile.keys()),
                default=enabled_labels,
            )
            watchlist_name = st.text_input("出力ファイル名", value=_default_watchlist_name(watchlist_date))
            watchlist_submitted = st.form_submit_button("候補を取得 / 再取得")

        existing_watchlists = _matching_date_files(WATCHLIST_ROOT, watchlist_date)
        if existing_watchlists:
            selected_existing_watchlist = st.selectbox(
                "既存 watchlist",
                options=existing_watchlists,
                index=0,
                format_func=lambda path: path.name,
                key=f"existing_watchlist_{watchlist_date:%Y%m%d}",
            )
            load_col, note_col = st.columns([1, 2])
            if load_col.button("既存データを読み込む", key=f"load_watchlist_{watchlist_date:%Y%m%d}"):
                _set_watchlist_session(selected_existing_watchlist)
                st.success(f"既存 watchlist を読み込みました: {selected_existing_watchlist.name}")
                st.rerun()
            note_col.caption("既存データで先に進めます。上のボタンは同じ日付のデータを取り直したいときだけ使います。")

        if watchlist_submitted:
            selected_profiles = [label_to_profile[label] for label in selected_labels]
            if not selected_profiles:
                st.warning("最低1つは profile を選んでください。")
            else:
                output_path = WATCHLIST_ROOT / watchlist_name
                try:
                    with st.spinner("候補抽出中..."):
                        row_count, path = build_watchlist_for_profiles(
                            race_date=watchlist_date.strftime("%Y%m%d"),
                            profiles=selected_profiles,
                            output_path=output_path,
                            raw_root=RAW_ROOT,
                            max_race_no=DEFAULT_MAX_RACE_NO,
                            sleep_seconds=DEFAULT_SLEEP_SECONDS,
                            timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
                        )
                    _set_watchlist_session(path)
                except Exception as exc:
                    _render_exception("翌日候補抽出に失敗しました。", exc)

        watchlist_path = _session_path("watchlist_path")
        if watchlist_path is not None:
            row_count = st.session_state.get("watchlist_count", 0)
            st.success(f"出力先: {watchlist_path} / {row_count}件")
            frame = _watchlist_frame(watchlist_path)
            if frame.empty:
                st.info("今回の条件では候補は 0 件でした。")
            else:
                st.dataframe(
                    _rename_columns(frame, WATCHLIST_COLUMNS_JA),
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            st.info("ここで翌日候補を作ると、watchlist CSV が保存されます。")

    with resolve_tab:
        st.subheader("直前判定")
        watchlist_files = _available_watchlists()
        if not watchlist_files:
            st.info("まだ watchlist CSV がありません。先に『候補を取得 / 再取得』を実行してください。")
            return

        default_index = 0
        current_path = _session_path("watchlist_path")
        if current_path is not None and current_path in watchlist_files:
            default_index = watchlist_files.index(current_path)

        with st.form("resolve_form"):
            selected_watchlist = st.selectbox(
                "watchlist ファイル",
                options=watchlist_files,
                index=default_index,
                format_func=lambda path: path.name,
            )
            logic_targets = _logic_targets_for_watchlist(profiles, selected_watchlist)
            logic_controls: dict[str, dict[str, object]] = {}
            resolve_name = st.text_input("出力ファイル名", value=f"{selected_watchlist.stem}_ready.csv")
            
            st.write("Air Bet 記録対象設定:")
            for target in logic_targets:
                logic_id = str(target["logic_id"])
                label = str(target["label"])
                default_enabled = bool(target["default_enabled"])
                state_suffix = logic_id.replace("-", "_")
                use_key = f"use_logic_{state_suffix}"
                amount_key = f"amt_logic_{state_suffix}"

                col1, col2 = st.columns([3, 2])
                use_logic = col1.checkbox(
                    label,
                    value=st.session_state.get(use_key, default_enabled),
                    key=use_key,
                )
                amount = col2.number_input(
                    f"金額 / {label}",
                    min_value=0,
                    value=int(st.session_state.get(amount_key, 100)),
                    step=100,
                    key=amount_key,
                )
                logic_controls[logic_id] = {
                    "label": label,
                    "use": use_logic,
                    "amount": int(amount),
                }

            resolve_submitted = st.form_submit_button("beforeinfo を見て判定 / 再取得")

        existing_ready_path = READY_ROOT / resolve_name
        if existing_ready_path.exists():
            load_col, note_col = st.columns([1, 2])
            if load_col.button("既存 ready を読み込む", key=f"load_ready_{selected_watchlist.stem}"):
                _set_ready_session(existing_ready_path)
                st.success(f"既存 ready を読み込みました: {existing_ready_path.name}")
                st.rerun()
            note_col.caption("同じ watchlist をそのまま使うなら、既存 ready を読み込めます。再判定したいときだけ上のボタンを使います。")

        if resolve_submitted:
            ready_path = READY_ROOT / resolve_name
            try:
                amount_by_logic = {
                    logic_id: int(control["amount"])
                    for logic_id, control in logic_controls.items()
                }

                with st.spinner("直前判定中..."):
                    changed_rows, ready_count = resolve_watchlist_for_profiles(
                        watchlist_path=selected_watchlist,
                        profiles=profiles,
                        raw_root=RAW_ROOT,
                        ready_output_path=ready_path,
                        sleep_seconds=DEFAULT_SLEEP_SECONDS,
                        timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
                    )
                _set_ready_session(ready_path)
                st.session_state["resolve_ready_count"] = ready_count
                st.session_state["resolve_changed_rows"] = changed_rows

                # 「GO」判定された行を Air Bet 履歴に追記
                ready_frame = _watchlist_frame(ready_path)
                if not ready_frame.empty and "status" in ready_frame.columns:
                    go_rows = ready_frame[ready_frame["status"] == "trigger_ready"]
                    if not go_rows.empty:
                        new_records = go_rows.to_dict("records")
                        valid_new_records = []
                        with BoatRaceClient(timeout_seconds=DEFAULT_TIMEOUT_SECONDS) as client:
                            for r in new_records:
                                logic_name = str(r.get("profile_id", "unknown"))
                                control = logic_controls.get(logic_name)
                                if control is None:
                                    rec_amount = 100
                                    logic_label = profile_name_map.get(logic_name, logic_name)
                                else:
                                    if not bool(control["use"]):
                                        continue
                                    rec_amount = int(amount_by_logic.get(logic_name, control["amount"]))
                                    logic_label = str(control["label"])
                                
                                if rec_amount <= 0:
                                    continue

                                # 3. 実際の的中判定と払戻 (実データ取得)
                                try:
                                    result_str, payout_val = judge_air_bet(r, client, RAW_ROOT)
                                    r["result"] = result_str
                                    r["payout"] = payout_val
                                except Exception as exc:
                                    r["result"] = "skip"
                                    r["payout"] = 0
                                    st.warning(f"結果取得失敗 (Race {r.get('race_id')}): {exc}")

                                bet_rows = build_bet_rows(
                                    strategy_id=str(r.get("strategy_id") or logic_name),
                                    profile_id=logic_name,
                                    amount=rec_amount,
                                    context=r,
                                )
                                r["unit_amount"] = rec_amount
                                r["ticket_count"] = sum(
                                    bet_point_count(bet_type=str(row["bet_type"]), combo=str(row["combo"]))
                                    for row in bet_rows
                                )
                                r["amount"] = sum(
                                    bet_total_amount(
                                        bet_type=str(row["bet_type"]),
                                        combo=str(row["combo"]),
                                        unit_amount=int(row["amount"]),
                                    )
                                    for row in bet_rows
                                )
                                r["logic"] = logic_name
                                r["logic_display"] = logic_label
                                valid_new_records.append(r)

                        if valid_new_records:
                            # 5. Persistent Air Bet Log (with results)
                            new_bets = record_air_bets(ready_path, AIR_BET_LOG_FILE, rows_with_results=valid_new_records)
                            if new_bets > 0:
                                st.toast(f"Air Bet ログに {new_bets} 件追記しました。", icon="✅")
                            elif ready_count > 0:
                                st.toast("既存の Air Bet ログと重複しているため追記をスキップしました。", icon="ℹ️")

                            # 6. Session History
                            if "air_bet_history" not in st.session_state:
                                st.session_state["air_bet_history"] = []
                            
                            current_count = len(st.session_state["air_bet_history"])
                            if current_count >= MAX_BET_PER_DAY:
                                st.warning(f"1日の上限回数 ({MAX_BET_PER_DAY}回) に達しているため、今回の判定結果 ({len(valid_new_records)}件) は Air Bet に記録されませんでした。")
                            else:
                                st.session_state["air_bet_history"].extend(valid_new_records)
                                if len(valid_new_records) < len(new_records):
                                    st.info(f"一部のロジックが OFF のため、{len(new_records) - len(valid_new_records)} 件の記録がスキップされました。")
            except Exception as exc:
                _render_exception("直前判定に失敗しました。", exc)

        ready_path = _session_path("ready_path")
        if ready_path is not None:
            changed_rows = st.session_state.get("resolve_changed_rows", 0)
            ready_count = st.session_state.get("resolve_ready_count", 0)
            st.success(f"出力先: {ready_path} / trigger_ready {ready_count}件 / 更新 {changed_rows}件")
            frame = _watchlist_frame(ready_path)
            if frame.empty:
                st.info("trigger_ready の行はまだありません。")
            else:
                    st.dataframe(
                        _rename_columns(frame, WATCHLIST_COLUMNS_JA),
                        use_container_width=True,
                        hide_index=True,
                    )

    with air_bet_tab:
        st.subheader("Air Bet")
        if st.button("履歴クリア"):
            st.session_state["air_bet_history"] = []
            st.rerun()
        col1, col2, col3 = st.columns(3)
        col1.metric("今日の Air Bet 数", "0 件")
        col2.metric("今日の的中数", "0 件")
        col3.metric("今日の収支", "±0 円")

        st.divider()
        st.subheader("Air Bet 履歴 (仮)")
        # セッションから連携データを取得して表示
        history_records = st.session_state.get("air_bet_history", [])
        if history_records:
            history_df = pd.DataFrame([_normalize_air_bet_record(record) for record in history_records])
            if "logic_display" not in history_df.columns:
                if "logic" in history_df.columns:
                    history_df["logic_display"] = history_df["logic"].map(profile_name_map).fillna(history_df["logic"])
                elif "profile_id" in history_df.columns:
                    history_df["logic_display"] = history_df["profile_id"].map(profile_name_map).fillna(history_df["profile_id"])
                else:
                    history_df["logic_display"] = "unknown"
            # 表示項目: 時刻 / 場 / レース / ロジック / 単価 / 点数 / 合計金額 / 結果 / 払戻 / 状態（GO）
            display_cols = [
                "deadline_time",
                "stadium_name",
                "race_no",
                "logic_display",
                "unit_amount",
                "ticket_count",
                "amount",
                "result",
                "payout",
                "status",
            ]
            available_cols = [c for c in display_cols if c in history_df.columns]
            df_to_show = history_df[available_cols].copy()
            df_to_show = df_to_show.rename(columns={
                "deadline_time": "時刻",
                "stadium_name": "場",
                "race_no": "レース",
                "logic_display": "ロジック",
                "unit_amount": "単価",
                "ticket_count": "点数",
                "amount": "合計金額",
                "result": "結果",
                "payout": "払戻",
                "status": "状態"
            })
            if "状態" in df_to_show.columns:
                df_to_show["状態"] = "GO"
            st.dataframe(df_to_show, use_container_width=True, hide_index=True)
        else:
            # データがない場合は空のテーブルを表示
            dummy_history = pd.DataFrame(
                columns=["時刻", "場", "レース", "ロジック", "単価", "点数", "合計金額", "結果", "払戻", "状態"]
            )
            st.dataframe(dummy_history, use_container_width=True, hide_index=True)

    with stats_tab:
        st.subheader("成績管理")
        # セッションから履歴を取得して件数と収支を算出
        history_data = [_normalize_air_bet_record(record) for record in st.session_state.get("air_bet_history", [])]
        bet_count = len(history_data)

        if isinstance(history_data, pd.DataFrame):
            total_spent = int(history_data["amount"].sum()) if "amount" in history_data.columns else 0
            total_payout = int(history_data["payout"].sum()) if "payout" in history_data.columns else 0
        else:
            total_spent = sum(int(r.get("amount", 0)) for r in history_data)
            total_payout = sum(int(r.get("payout", 0)) for r in history_data)
        
        total_balance = total_payout - total_spent

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("今日の Air Bet 数", f"{bet_count} 件")
        col2.metric("今日の的中数", f"{total_payout // 200 if bet_count > 0 else 0} 件") # 簡略的な表示
        col3.metric("今日の収支", f"{total_balance:+d} 円")
        col4.metric("回収率", f"{(total_payout / total_spent * 100):.1f}%" if total_spent > 0 else "0.0%")

        st.divider()
        st.subheader("ロジック別成績 (仮)")
        
        if bet_count > 0:
            # 履歴を DataFrame として読み込み
            df = pd.DataFrame(history_data)
            # logic がない場合は unknown に置換
            if "logic" not in df.columns:
                df["logic"] = "unknown"
            else:
                df["logic"] = df["logic"].fillna("unknown")
            if "logic_display" not in df.columns:
                df["logic_display"] = df["logic"].map(profile_name_map).fillna(df["logic"])
            
            # 必要なカラムの存在確認と初期化
            for col in ["amount", "payout", "result"]:
                if col not in df.columns:
                    df[col] = 0 if col != "result" else "lose"

            # ロジックごとにグループ化して集計
            stats_df = df.groupby("logic_display").apply(lambda x: pd.Series({
                "レース数": len(x),
                "的中数": (x["result"] == "win").sum(),
                "収支": (x["payout"] - x["amount"]).sum()
            }), include_groups=False).reset_index().rename(columns={"logic_display": "ロジック"})
            
            st.dataframe(stats_df, use_container_width=True, hide_index=True)
        else:
            # 将来的にロジック別成績を表示するための空テーブル
            dummy_stats = pd.DataFrame(
                columns=["ロジック", "レース数", "的中数", "収支"]
            )
            st.dataframe(dummy_stats, use_container_width=True, hide_index=True)

        st.info("将来の統合用プレースホルダです。")


if __name__ == "__main__":
    if get_script_run_ctx() is None:
        # CLI 実行モード
        ready_path = READY_ROOT / "latest.csv"
        log_path = AIR_BET_LOG_FILE
        raw_root = RAW_ROOT
        run_air_bet_flow_cli(ready_path, log_path, raw_root)
    else:
        main()
