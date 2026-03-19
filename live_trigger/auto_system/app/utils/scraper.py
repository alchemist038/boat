import requests
import time
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
from datetime import datetime

def fetch_live_info(stadium_code: str, race_no: int) -> Dict[str, Any]:
    """
    ボートレース公式の直前情報ページから展示データを取得する。
    """
    stadium_code_str = str(stadium_code).zfill(2)
    race_no_str = str(race_no)
    
    url = f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?jcd={stadium_code_str}&hd=&rno={race_no_str}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    for attempt in range(3):
        try:
            response = requests.get(url, headers=headers, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            
            live_info = {"entries": []}
            tbody_list = soup.find_all("tbody", class_="is-fs12")
            
            if len(tbody_list) < 2:
                return live_info
                
            target_tbody = tbody_list[1]
            rows = target_tbody.find_all("tr")
            
            for i in range(6):
                if i >= len(rows):
                    break
                
                cols = rows[i].find_all("td")
                if len(cols) >= 7:
                    try:
                        ex_time_str = cols[2].text.strip()
                        ex_time = float(ex_time_str) if ex_time_str else None
                        
                        st_str = cols[6].text.strip().replace('F', '').replace('L', '').strip()
                        st = float(st_str) if st_str and st_str != '-' else None
                        
                        live_info["entries"].append({
                            "lane": i + 1,
                            "ex_time": ex_time,
                            "st": st
                        })
                    except ValueError:
                        continue
                        
            return live_info

        except requests.exceptions.RequestException as e:
            if attempt < 2:
                print(f"  [RETRY] 直前情報の取得に失敗しました。再試行します ({attempt + 1}/3): {e}")
                time.sleep(2)
                continue
            print(f"  [ERROR] 直前情報の取得に失敗しました: {e}")
            return {"entries": []}
    return {"entries": []}

def fetch_race_card(stadium_code: str, race_no: int, date_str: str = None) -> Optional[Dict[str, Any]]:
    """
    ボートレース公式の出走表ページから選手級別等を取得する。
    """
    if not date_str:
        date_str = datetime.now().strftime("%Y%m%d")
    
    stadium_code_str = str(stadium_code).zfill(2)
    url = f"https://www.boatrace.jp/owpc/pc/race/racelist?rno={race_no}&jcd={stadium_code_str}&hd={date_str}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    for attempt in range(3):
        try:
            response = requests.get(url, headers=headers, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            
            # レースが存在するかチェック (番組未発表など)
            if "データがありません" in soup.text or "お探しのページは見つかりませんでした" in soup.text:
                return None

            race_card = {
                "date": f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}",
                "stadium_code": stadium_code_str,
                "race_no": race_no,
                "is_women": False,
                "entries": []
            }

            # 女子戦判定 (レディース、ヴィーナス、オール女子等のキーワード)
            title_text = soup.select_one(".heading2_titleName")
            if title_text:
                text = title_text.text
                if any(k in text for k in ["レディース", "ヴィーナス", "女子", "G3"]):
                    race_card["is_women"] = True

            # 選手データ取得
            # 出走表のテーブル構造から級別を抽出
            tbody_list = soup.find_all("tbody", class_="is-fs12")
            if not tbody_list:
                return None

            # 級別が含まれる列を特定してループ (通常6枠分)
            for i in range(min(len(tbody_list), 6)):
                tbody = tbody_list[i]
                # 級別のテキストは class="is-grade" や特定のネスト内にあることが多い
                grade_tag = tbody.find("span", class_="is-grade")
                grade = grade_tag.text.strip() if grade_tag else "B2"
                
                race_card["entries"].append({
                    "lane": i + 1,
                    "class": grade
                })

            if len(race_card["entries"]) < 6:
                return None

            return race_card

        except requests.exceptions.RequestException as e:
            if attempt < 2:
                print(f"  [RETRY] 出走表の取得に失敗しました。再試行します ({attempt + 1}/3): {e}")
                time.sleep(2)
                continue
            print(f"  [ERROR] 出走表の取得に失敗しました: {e}")
            return None
    return None
