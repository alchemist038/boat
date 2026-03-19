import sys
import os
import json
import time
from datetime import datetime

# プロジェクトルート (boat_auto_system) をパスに追加 (3階層上)
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import SessionLocal, TargetRace
from app.logics.logic_125 import Logic125
from app.logics.logic_c2 import LogicC2
from app.utils.scraper import fetch_race_card

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "settings.json")

def load_active_logics():
    if not os.path.exists(SETTINGS_FILE):
        return {"125_line_provisional": True, "c2_provisional_v1": True}
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        settings = json.load(f)
        return settings.get("active_logics", {})

def main():
    print(f"[{datetime.now()}] 本番用事前抽出処理開始...")
    session = SessionLocal()
    
    # settings.json から有効なロジックのみをロードしてインスタンス化
    active_flags = load_active_logics()
    logics = []
    if active_flags.get("125_line_provisional", True):
        logics.append(Logic125())
    if active_flags.get("c2_provisional_v1", True):
        logics.append(LogicC2())

    if not logics:
        print("有効なロジックが設定されていません。処理を終了します。")
        session.close()
        return

    print(f"  [INFO] 稼働ロジック: {[l.logic_name for l in logics]}")
    
    total_found = 0

    for s_id in range(1, 25):
        stadium_code = f"{s_id:02}"
        print(f"  [SCAN] Stadium: {stadium_code} をチェック中...")
        for race_no in range(1, 13):
            # 本番データ取得 (サーバー負荷軽減のため1秒待機)
            race_info = fetch_race_card(stadium_code, race_no)
            time.sleep(1)
            
            if race_info is None:
                continue
                
            for logic in logics:
                if logic.pre_check(race_info):
                    # 重複チェック (同一の日付、場、レース、ロジックがある場合はスキップ)
                    exists = session.query(TargetRace).filter(
                        TargetRace.date == race_info["date"],
                        TargetRace.stadium_code == stadium_code,
                        TargetRace.race_no == race_no,
                        TargetRace.logic_name == logic.logic_name
                    ).first()

                    if exists:
                        # print(f"  [SKIP] {stadium_code}#{race_no} (Logic: {logic.logic_name}) は既に存在します。")
                        continue

                    print(f"  [FOUND] {stadium_code}#{race_no} -> Logic: {logic.logic_name}")
                    target = TargetRace(
                        date=race_info["date"],
                        stadium_code=stadium_code,
                        race_no=race_no,
                        logic_name=logic.logic_name
                    )
                    session.add(target)
                    total_found += 1

    session.commit()
    session.close()
    print(f"[{datetime.now()}] 事前抽出処理完了。新規登録: {total_found}件")

if __name__ == "__main__":
    main()
