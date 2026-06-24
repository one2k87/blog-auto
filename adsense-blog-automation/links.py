"""
links.py - 주제별 '실제로 존재하는' 참고 링크 1~2개를 검색해서 가져온다.
LLM이 만든 가짜 URL 대신 검색 결과의 진짜 링크를 쓰기 위함.
설치: pip install ddgs   (DuckDuckGo 검색, API 키 불필요)
검색 모듈이 없거나 실패하면 빈 리스트를 반환하고, generator가 안전하게 처리한다.
"""


def find_reference_links(query, max_results=2):
    """주어진 검색어로 실제 웹 링크 목록을 반환. [{title, url}]"""
    results = []
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results * 2):
                url = r.get("href") or r.get("url") or ""
                title = r.get("title") or ""
                if url.startswith("http"):
                    results.append({"title": title.strip(), "url": url.strip()})
                if len(results) >= max_results:
                    break
    except Exception as e:
        print(f"[links] 검색 실패('{query}'): {e}")
    return results
