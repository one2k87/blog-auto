"""
topics.py - '카테고리 집중' 주제 엔진 (미니사이트 전략).

전략(참고 자료 기반):
- 고단가 카테고리 1개에 집중해 관련 글 다발(topic cluster)을 만든다.
- 두 갈래로 주제를 뽑는다:
    long   = 저경쟁 롱테일. 많은 사람이 다루지 않아 신생 블로그도 상위노출 쉬움 + 고단가.
    season = '이제 뜰' 시즌/이벤트 키워드를 2~4주 미리 선점(검색 반영에 1~2주 걸리므로).
- 이미 다룬 주제는 제외(중복 방지)하여 카테고리를 계속 채워 나간다.

LLM으로 주제를 생성하되, 히스토리(과거 발행 제목)를 프롬프트에 넣어 겹치지 않게 한다.
"""

import re
from datetime import date

# 시즌 선점 힌트: '지금 달'이 아니라 '1~2달 뒤 검색이 붙는' 주제를 노린다.
_SEASON_HINT = {
    1: "설 연휴 자금·연말정산 환급·새해 재테크 계획",
    2: "연말정산 추가납부·봄 이사 대출·전세자금",
    3: "종합소득세 준비·신학기 자녀 보험·봄 이사 자금",
    4: "5월 종합소득세 신고·근로장려금 신청·가정의 달 지출관리",
    5: "종합소득세 신고 마감·여름 휴가 적금·자동차세 연납",
    6: "여름 휴가 경비 마련·장마철 자동차보험·반기 결산 재테크",
    7: "휴가철 환전·해외여행 카드·하반기 재테크 점검",
    8: "추석 상여·명절 자금·연금저축 중간점검",
    9: "추석 연휴 자금·연말정산 미리보기·4분기 투자",
    10: "연말정산 세액공제 준비·김장/난방비 절약·연금 납입 한도",
    11: "연말정산 몰아넣기·연말 카드 실적·내년 재테크 계획",
    12: "연말정산 최종 점검·새해 예산·1월 만기 적금",
}


def season_focus(today=None):
    today = today or date.today()
    nxt = today.month % 12 + 1          # 다음 달(2~4주 뒤 검색 반영 타이밍)
    return nxt, _SEASON_HINT.get(nxt, "")


def build_topic_prompt(category, category_desc, kind, count, exclude=None, today=None):
    exclude = exclude or []
    ex_text = "\n".join(f"- {t}" for t in exclude[:60]) or "(없음)"

    common = f"""당신은 '{category}' 카테고리에 집중하는 애드센스 수익형 블로그의 주제 기획자입니다.
이 블로그는 '{category}' 미니사이트로 운영되며, 아래 세부 분야를 다룹니다:
{category_desc}

[반드시 지킬 원칙]
- 모두 '{category}' 카테고리 안의 주제여야 한다(카테고리 이탈 금지).
- 광고 단가가 높은 세부 키워드를 노린다.
- 아래 '이미 다룬 주제'와 겹치거나 매우 비슷하면 안 된다(새로운 각도로):
{ex_text}
- 각 주제는 검색 의도가 분명한 정보형(방법/비교/조건/신청/추천/후기 형태).
"""

    if kind == "season":
        nxt, hint = season_focus(today)
        extra = f"""[이번 배치 = 시즌 선점]
- '지금 뜨는' 게 아니라 '{nxt}월에 검색이 붙을' 주제를 지금 미리 잡는다(2~4주 선점).
- 참고 시즌 맥락: {hint}
- 계절/제도 일정/연례 이벤트와 '{category}'를 결합한 구체적 주제.
"""
    else:
        extra = """[이번 배치 = 저경쟁 롱테일]
- 검색량은 아주 많지 않아도 '경쟁이 약해 상위노출이 쉬운' 구체적 주제.
- 특정 조건/대상/금액/상품명처럼 좁고 명확한 롱테일(예: "무직자 소액 비상금 대출 조건", "청년 주택청약 소득공제 한도").
- 많은 블로그가 이미 도배한 광범위 키워드(예: 그냥 "대출", "신용카드 추천")는 피한다.
"""

    return common + extra + f"""
출력은 줄바꿈으로 구분된 한국어 주제 문장 정확히 {count}개만. 번호/설명/따옴표 없이.
각 주제는 그대로 블로그 제목 키워드로 쓸 수 있게 구체적으로."""


def classify_topics(items, category, chat, llm_cfg, today=None):
    """
    각 후보 주제를 '저경쟁(long)' vs '시즌(season)'으로 지속 판별한다.
    - 시즌: 특정 시기/계절/연례 일정과 결합돼 앞으로 검색이 몰릴 주제.
    - 저경쟁: 시기와 무관하게 1년 내내 꾸준하고 경쟁이 약한 롱테일.
    각 item에 lane_ai, lane_reason, season_month 를 채운다.
    """
    import json as _json
    import re as _re
    if not items:
        return items
    lst = "\n".join(f"{i+1}. {it['keyword']}" for i, it in enumerate(items))
    today = today or date.today()
    prompt = f"""'{category}' 블로그 주제들을 두 부류로 분류하세요. 오늘은 {today.year}년 {today.month}월입니다.

- season: 특정 시기/계절/연례 일정(연말정산, 종소세, 명절, 청약 일정 등)과 묶여 곧 검색이 몰릴 주제.
- long: 시기와 무관하게 1년 내내 꾸준하고 경쟁이 약한 롱테일 주제.

주제 목록:
{lst}

각 주제를 아래 JSON 배열로만 출력(설명 없이):
[{{"n":1,"lane":"long|season","month":0,"reason":"짧은 근거"}}, ...]
month는 season일 때 검색이 붙을 달(1~12), long이면 0."""
    try:
        raw = chat(prompt, llm_cfg, max_tokens=700, temperature=0.2)
        raw = _re.sub(r"^```[a-zA-Z]*|```$", "", (raw or "").strip()).strip()
        m = _re.search(r"\[.*\]", raw, _re.DOTALL)
        arr = _json.loads(m.group(0)) if m else []
        by_n = {int(x.get("n", 0)): x for x in arr}
        for i, it in enumerate(items):
            x = by_n.get(i + 1, {})
            it["lane_ai"] = x.get("lane", "")
            it["lane_reason"] = x.get("reason", "")
            it["season_month"] = x.get("month", 0)
    except Exception as e:
        print(f"[classify] 판별 실패(무시): {e}")
    return items


def split_by_lane(items, want, other_pool=None):
    """판별 결과(lane_ai)가 want('long'/'season')인 것 우선, 부족하면 나머지로 채움."""
    match = [x for x in items if x.get("lane_ai") == want]
    rest = [x for x in items if x.get("lane_ai") != want]
    return match, rest


def parse_topics(text, count):
    out = []
    seen = set()
    for line in (text or "").splitlines():
        line = re.sub(r"^[\-\*\d\.\)\s\"'·•]+", "", line.strip()).strip().strip('"').strip()
        key = re.sub(r"\s+", "", line)
        if line and key not in seen:
            seen.add(key)
            out.append({"keyword": line, "news": []})
        if len(out) >= count:
            break
    return out
