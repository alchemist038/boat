import sys
import os
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import SessionLocal, TargetRace, BetHistory
from app.logics.logic_125 import Logic125
from app.logics.logic_c2 import LogicC2
from app.utils.scraper import fetch_live_info

def main():
    print(f"[{datetime.now()}] 直前判定処理開始...")
    session = SessionLocal()
    
    # 利用可能なロジックのマッピング
    logic_map = {
        "125_line_provisional": Logic125(),
        "c2_provisional_v1": LogicC2()
    }

    # 本日の抽出済みレースを取得
    today = datetime.now().strftime("%Y-%m-%d")
    targets = session.query(TargetRace).filter(TargetRace.date == today).all()

    if not targets:
        print("判定対象のレースが見つかりませんでした。")
        session.close()
        return

    for target in targets:
        # 重複チェック: 既に判定済みの場合はスキップ
        exists = session.query(BetHistory).filter(BetHistory.target_race_id == target.id).first()
        if exists:
            continue

        logic = logic_map.get(target.logic_name)
        if not logic:
            print(f"  [ERROR] ロジック '{target.logic_name}' が見つかりません。")
            continue

        print(f"  [TARGET] {target.stadium_code}#{target.race_no} (Logic: {target.logic_name})")

        # 直前情報取得 (Scraper)
        live_info = fetch_live_info(target.stadium_code, target.race_no)

        # 判定に必要な詳細情報を再構築（不足情報を補完）
        from app.utils.scraper import fetch_race_card
        race_info = fetch_race_card(target.stadium_code, target.race_no)
        if not race_info:
            race_info = {"stadium_code": target.stadium_code, "race_no": target.race_no}

        # 直前判定実行
        if logic.just_in_time_check(race_info, live_info):
            print("    -> [GO] 条件一致！買い目を生成します。")
            bets = logic.build_bet(race_info, live_info)
            for bet in bets:
                history = BetHistory(
                    target_race_id=target.id,
                    status="GO",
                    bet_type=bet["bet_type"],
                    combo=bet["combo"],
                    amount=bet["amount"],
                    is_air_bet=True
                )
                session.add(history)
        else:
            print("    -> [SKIP] 条件不一致。")
            history = BetHistory(
                target_race_id=target.id,
                status="SKIP",
                reason="Just-in-time check failed"
            )
            session.add(history)

    session.commit()
    session.close()
    print(f"[{datetime.now()}] 直前判定・履歴保存完了。")

if __name__ == "__main__":
    main()
