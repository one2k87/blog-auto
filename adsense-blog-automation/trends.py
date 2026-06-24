"""
trends.py
- 핫이슈 키워드: Google Trends 일일 인기 검색어 RSS에서 수집 (API 키 불필요, 무료)
- 세분화(롱테일) 키워드: LLM으로 검색량은 적지만 경쟁이 약한 초세부 how-to 주제 생성
"""

import re
import html
import random
import urllib.request
import xml.etree.ElementTree as ET

# Google Trends "Trending now" RSS 피드 (공식, 무료)
TRENDS_RSS = "https://trends.google.com/trending/rss?geo={geo}"

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def fetch_hot_keywords(geo="KR", limit=5):
    """Google Trends RSS에서 오늘의 인기 검색어 상위 limit개를 가져온다."""
    url = TRENDS_RSS.format(geo=geo)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[trends] RSS 수집 실패({geo}): {e} -> 폴백 사용")
        return _fallback_hot(geo, limit)

    items = []
    try:
        root = ET.fromstring(raw)
        ns = {"ht": "https://trends.google.com/trending/rss"}
        for item in root.iter("item"):
            title_el = item.find("title")
            if title_el is None or not title_el.text:
                continue
            title = html.unescape(title_el.text.strip())
            traffic_el = item.find("ht:approx_traffic", ns)
            traffic = traffic_el.text if traffic_el is not None else ""
            # 관련 뉴스 제목 몇 개를 컨텍스트로 모아둔다
            news = []
            for n in item.findall("ht:news_item", ns):
                t = n.find("ht:news_item_title", ns)
                link = n.find("ht:news_item_url", ns)
                if t is not None and t.text:
                    news.append({
                        "title": html.unescape(t.text.strip()),
                        "url": link.text.strip() if link is not None and link.text else "",
                    })
            items.append({"keyword": title, "traffic": traffic, "news": news})
            if len(items) >= limit:
                break
    except Exception as e:
        print(f"[trends] RSS 파싱 실패: {e} -> 폴백 사용")
        return _fallback_hot(geo, limit)

    if not items:
        return _fallback_hot(geo, limit)
    return items


def _fallback_hot(geo, limit):
    """RSS가 막혔을 때를 위한 최소 폴백(LLM이 채우도록 빈 키워드 반환)."""
    return [{"keyword": "", "traffic": "", "news": []} for _ in range(limit)]


# 세분화 주제를 뽑을 시드 카테고리 (검색량 적지만 의도 명확 = AdSense 친화적)
NICHE_SEED_CATEGORIES = [
    "프린터/스캐너 드라이버 설치 및 오류 해결",
    "특정 가전제품 모델 설정 및 초기화 방법",
    "소프트웨어 특정 버전 설치/호환성 문제 해결",
    "공유기/네트워크 장비 모델별 설정",
    "자동차 특정 모델 경고등/정비 방법",
    "엑셀/한글/오피스 특정 기능 단축키와 오류",
    "스마트폰 특정 모델 숨은 기능/설정",
    "게임/앱 특정 오류 코드 해결",
    "키보드/마우스/주변기기 펌웨어 및 매크로",
    "윈도우/맥 특정 에러 메시지 해결",
]


def build_niche_prompt(count=5, lang="ko"):
    """LLM에게 초세부 롱테일 주제 count개를 뽑게 하는 프롬프트."""
    seeds = random.sample(NICHE_SEED_CATEGORIES, k=min(5, len(NICHE_SEED_CATEGORIES)))
    seeds_text = "\n".join(f"- {s}" for s in seeds)
    return f"""당신은 SEO 롱테일 키워드 전략가입니다.
검색량은 많지 않지만 의도가 매우 분명하고 경쟁이 약한 '초세부 how-to' 블로그 주제를 정확히 {count}개 추천하세요.

좋은 예시: "엡손 L3150 프린터 드라이버 윈도우11 설치 방법", "아이패드 9세대 화면 분할 끄는 법", "오류 코드 0x80070643 윈도우 업데이트 해결"

조건:
- 특정 브랜드/모델명/버전/오류코드처럼 구체적인 식별자를 반드시 포함
- 정보성 키워드(설치/설정/해결/방법/오류)로 끝나는 형태
- 서로 다른 분야로 분산

참고할 분야 시드:
{seeds_text}

출력은 줄바꿈으로 구분된 {count}개의 주제 문장만. 번호/설명/따옴표 없이."""


def parse_niche_keywords(text, count=5):
    """LLM 응답 텍스트에서 주제 라인을 정리해 리스트로."""
    lines = []
    for line in text.splitlines():
        line = line.strip()
        line = re.sub(r"^[\-\*\d\.\)\s\"']+", "", line).strip().strip('"').strip()
        if line:
            lines.append(line)
    return [{"keyword": k, "traffic": "롱테일", "news": []} for k in lines[:count]]


if __name__ == "__main__":
    for kw in fetch_hot_keywords("KR", 5):
        print("HOT:", kw["keyword"], "|", kw["traffic"], "| news:", len(kw["news"]))
