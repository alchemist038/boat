import sys
import os
import streamlit as st
import pandas as pd
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

# プロジェクトルートのパスを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.core.database import SessionLocal, TargetRace, BetHistory

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "settings.json")

st.set_page_config(page_title="ボートレース自動運用システム", layout="wide")

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {"system_running": False, "active_logics": {}}
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)

def get_data():
    session = SessionLocal()
    try:
        # TargetRaceをPandasのDataFrameに変換
        targets = session.query(TargetRace).all()
        target_df = pd.DataFrame([{
            "ID": t.id, "日付": t.date, "場": t.stadium_code, "レース": t.race_no,
            "ロジック": t.logic_name, "抽出日時": t.created_at
        } for t in targets])

        # BetHistoryをPandasのDataFrameに変換
        bets = session.query(BetHistory).all()
        bet_df = pd.DataFrame([{
            "ID": b.id, "Target_ID": b.target_race_id, "状態": b.status,
            "券種": b.bet_type, "買い目": b.combo, "金額": b.amount,
            "Air Bet": b.is_air_bet, "更新日時": b.created_at
        } for b in bets])
        
        return target_df, bet_df
    finally:
        session.close()

def main():
    st.title("🚤 ボートレース自動購入＆検証システム")
    
    # サイドバー：コントロールパネル
    st.sidebar.header("⚙️ コントロールパネル")
    settings = load_settings()
    is_running = settings.get("system_running", False)
    
    if is_running:
        st.sidebar.success("状態: 稼働中 (Running)")
        if st.sidebar.button("⏹️ システム停止"):
            settings["system_running"] = False
            save_settings(settings)
            st.rerun()
    else:
        st.sidebar.error("状態: 停止中 (Stopped)")
        if st.sidebar.button("▶️ システム起動"):
            settings["system_running"] = True
            save_settings(settings)
            # auto_run.py をバックグラウンドで起動
            log_path = Path(__file__).resolve().parent / "data" / "auto_run.log"
            with open(log_path, "a", encoding="utf-8") as f:
                subprocess.Popen(
                    [sys.executable, "-u", "auto_run.py"],
                    cwd=os.path.dirname(os.path.abspath(__file__)),
                    stdout=f,
                    stderr=f
                )
            st.rerun()

    st.sidebar.divider()
    st.sidebar.subheader("ロジック稼働設定")
    active_logics = settings.get("active_logics", {})
    available_logics = {
        "125_line_provisional": "125 Line",
        "c2_provisional_v1": "C2 Provisional"
    }
    
    new_active_logics = {}
    changed = False
    for l_id, l_name in available_logics.items():
        is_active = active_logics.get(l_id, True)
        val = st.sidebar.checkbox(l_name, value=is_active, key=l_id)
        new_active_logics[l_id] = val
        if val != is_active:
            changed = True
            
    if changed:
        settings["active_logics"] = new_active_logics
        save_settings(settings)
        st.sidebar.info("ロジック設定を更新しました。")

    # メインコンテンツ
    target_df, bet_df = get_data()
    
    if st.button("🔄 データを最新に更新"):
        st.rerun()

    # --- サマリー表示 (今日と累計) ---
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # データの件数計算
    total_targets = len(target_df)
    today_targets = len(target_df[target_df["日付"] == today_str]) if not target_df.empty else 0
    
    total_bets = len(bet_df)
    today_bets = 0
    if not bet_df.empty:
        # 更新日時を確実にdatetimeに変換して今日の日付と比較
        today_bets = len(bet_df[pd.to_datetime(bet_df["更新日時"]).dt.date == datetime.now().date()])

    cols = st.columns(4)
    cols[0].metric("ターゲット総数", f"{total_targets} 件")
    cols[1].metric("本日のターゲット", f"{today_targets} 件")
    cols[2].metric("投票履歴総数", f"{total_bets} 件")
    cols[3].metric("本日の投票数", f"{today_bets} 件")

    st.divider()

    tab1, tab2 = st.tabs(["🎯 本日のターゲット一覧", "📊 投票履歴 (Bet History)"])

    with tab1:
        st.subheader("事前抽出されたレース一覧")
        if not target_df.empty:
            st.dataframe(target_df, use_container_width=True, hide_index=True)
        else:
            st.info("ターゲットレースはありません。")

    with tab2:
        st.subheader("直前判定 ＆ 投票結果")
        if not bet_df.empty:
            st.dataframe(bet_df, use_container_width=True, hide_index=True)
        else:
            st.info("投票履歴はまだありません。")

if __name__ == "__main__":
    main()
