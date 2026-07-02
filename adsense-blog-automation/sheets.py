"""
sheets.py - 생성/게시 결과를 Google Sheets에 한 줄씩 기록.
서비스 계정(JSON 키)으로 인증. 시트는 서비스 계정 이메일과 '공유'되어 있어야 함.
설치: pip install gspread google-auth
config에 sheets 설정이 없으면 조용히 건너뛴다.
"""

from datetime import datetime

HEADER = ["날짜", "유형", "언어", "키워드", "월검색량", "경쟁도", "꾸준함",
          "제목", "상태", "게시URL", "참고링크"]


def log_rows(articles, sheets_cfg):
    """articles 각 항목을 시트에 append. 실패해도 전체 파이프라인은 계속."""
    if not sheets_cfg or not sheets_cfg.get("enabled"):
        return
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file(
            sheets_cfg["service_account_file"], scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(sheets_cfg["spreadsheet_id"])
        ws = sh.sheet1

        if ws.row_count == 0 or not ws.get_all_values():
            ws.append_row(HEADER)
        elif ws.row_values(1) != HEADER:
            ws.insert_row(HEADER, 1)

        today = datetime.now().strftime("%Y-%m-%d %H:%M")
        rows = []
        for a in articles:
            links = " | ".join(l["url"] for l in a.get("links", []))
            rows.append([
                today,
                "높은경쟁력" if a["kind"] == "hot" else "낮은경쟁력",
                a["lang"],
                a["keyword"],
                (a.get("volume") if a.get("volume") is not None
                 else (f"관심도 {a.get('interest')}" if a.get("interest") is not None else "미측정")),
                a.get("competition", ""),
                a.get("steadiness", ""),
                a["title"],
                a.get("status", "생성됨"),
                a.get("post_url", ""),
                links,
            ])
        ws.append_rows(rows, value_input_option="USER_ENTERED")
        print(f"[sheets] {len(rows)}행 기록 완료")
    except Exception as e:
        print(f"[sheets] 기록 실패(무시하고 계속): {e}")
