import sys
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.core.database import SessionLocal, BetHistory

# 環境変数の読み込み
load_dotenv()
SUBSCRIBER_NO = os.getenv("TELEBOAT_SUBSCRIBER_NO")
PIN = os.getenv("TELEBOAT_PIN")
PASSWORD = os.getenv("TELEBOAT_PASSWORD")

def execute_bet(page, bet):
    """投票実行ロジック (Air Bet / Real Bet 兼用)"""
    if bet.is_air_bet:
        print(f"    [AIR BET] 仮想投票として処理しました: {bet.combo} ({bet.amount}円)")
        return True

    # --- リアルマネー投票処理 (Playwright) ---
    try:
        if not all([SUBSCRIBER_NO, PIN, PASSWORD]):
            print("    [ERROR] .env にテレボートの認証情報が設定されていません。")
            return False

        print("    [REAL BET] テレボートにログインします...")
        page.goto("https://ib.mbrace.or.jp/") # テレボートPC版URL
        
        # ログイン情報の入力 (※実際のセレクタに合わせて今後微調整が必要な場合があります)
        page.fill("input[title='加入者番号']", SUBSCRIBER_NO)
        page.fill("input[title='暗証番号']", PIN)
        page.fill("input[title='認証用パスワード']", PASSWORD)
        page.click("a.btn-login") # ログインボタン
        
        # 画面遷移待ち
        page.wait_for_load_state("networkidle")
        time.sleep(2) # 安定稼働のためのバッファ
        
        print(f"    [REAL BET] ログイン成功. 投票処理を実行(モック): {bet.combo} ({bet.amount}円)")
        # TODO: 実際の買い目選択と投票確定のクリック処理をここに追加
        
        return True
    except Exception as e:
        print(f"    [ERROR] 投票処理中にエラーが発生しました: {e}")
        return False

def main(headless: bool = True):
    print(f"[{datetime.now()}] 投票処理(Executor)を開始...")
    session = SessionLocal()
    
    # 処理対象の買い目を取得
    pending_bets = session.query(BetHistory).filter(
        BetHistory.status == "GO"
    ).all()

    if not pending_bets:
        print("実行待ちの投票データはありません。")
        session.close()
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        for bet in pending_bets:
            print(f"  [TARGET] TargetRaceID: {bet.target_race_id}, Type: {bet.bet_type}, Combo: {bet.combo}")
            
            success = execute_bet(page, bet)
            
            if success:
                bet.status = "BET_PLACED"
            else:
                bet.status = "ERROR"
            
            session.commit()
            
        browser.close()
    
    session.close()
    print(f"[{datetime.now()}] 投票処理が完了しました。")

if __name__ == "__main__":
    main(headless=True)
