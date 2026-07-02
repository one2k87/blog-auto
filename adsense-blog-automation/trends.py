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
    """
    '낮은 경쟁력(상록성)' 키워드 프롬프트. 언어별로 시장 기준이 다르다.
      lang="ko" → 한국 시장 기준, 한국어 주제
      lang="en" → 미국 시장 기준, 영어 주제
    정의: 검색량은 적지만(경쟁 약함) 계절/유행을 타지 않고 매달 꾸준히 검색되는 상록성 세부 주제.
    """
    seeds = random.sample(NICHE_SEED_CATEGORIES, k=min(5, len(NICHE_SEED_CATEGORIES)))

    if lang == "en":
        seeds_text = "\n".join(f"- {s}" for s in seeds)
        return f"""You are an SEO long-tail keyword strategist for the US market.
Suggest exactly {count} blog topics that satisfy ALL of the 'low-competition' conditions below.

[Low-competition definition]
- Low monthly search volume, so competition is weak → a brand-new blog can still rank.
- BUT the demand is evergreen: searched consistently every month, not tied to a season/trend/event.
- Very clear searcher intent (mostly 'fix a problem' or 'how to do X').

Good examples: "how to install epson l3150 driver on windows 11", "reset ipad 9th gen without password", "fix error 0x80070643 windows update"
Avoid (not evergreen): brand-new product launches, tax season, elections — anything that spikes only at a certain time.

[Format rules]
- Must include a specific identifier (brand/model/version/error code).
- Phrase as an informational query (install/setup/fix/how to/error).
- Spread across different domains.

Reference domain seeds (adapt to US market):
{seeds_text}

Output ONLY {count} topic lines separated by newlines. No numbering, no explanation, no quotes."""

    seeds_text = "\n".join(f"- {s}" for s in seeds)
    return f"""당신은 한국 시장 대상 SEO 롱테일 키워드 전략가입니다.
아래 '낮은 경쟁력' 조건을 모두 만족하는 한국어 블로그 주제를 정확히 {count}개 추천하세요.

[낮은 경쟁력의 정의]
- 검색량(월간 조회수)은 적어 경쟁이 약하다. → 신생 블로그도 상위 노출 가능.
- 그러나 유행·계절·이벤트를 타지 않고 '1년 내내 매달 꾸준히 일정하게' 검색된다(상록성/evergreen).
- 검색자의 의도가 매우 분명하다(대부분 '문제 해결' 또는 '방법 찾기').

좋은 예시: "엡손 L3150 프린터 드라이버 윈도우11 설치 방법", "아이패드 9세대 화면 분할 끄는 법", "오류 코드 0x80070643 윈도우 업데이트 해결"
피해야 할 예시(꾸준하지 않음): 특정 신제품 출시·연말정산·선거처럼 특정 시기에만 몰리는 주제.

[형식 조건]
- 특정 브랜드/모델명/버전/오류코드 같은 구체적 식별자를 반드시 포함
- 정보성 키워드(설치/설정/해결/방법/오류/사용법)로 끝나는 형태
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
