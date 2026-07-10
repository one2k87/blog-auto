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
        today = today or date.today()
        m1 = today.month % 12 + 1          # 1개월 뒤
        m2 = (today.month + 1) % 12 + 1     # 2개월 뒤
        hint = _SEASON_HINT.get(m1, "")
        extra = f"""[이번 배치 = 시즌 선점 · 1~2개월 뒤 겨냥]
- 지금은 {today.year}년 {today.month}월. **{m1}월~{m2}월(=지금부터 1~2개월 뒤)에 검색이 오를 주제만** 고른다.
- 검색엔진 색인·상위노출에 몇 주 걸리므로, 딱 이 시점(1~2개월 뒤)을 노려 지금 미리 쓴다.
- ⚠️ 3개월 이상 먼 주제는 금지. (예: 지금 {today.month}월인데 11월 수능, 12월 연말정산처럼 먼 이벤트 ❌)
- 참고 시즌 맥락({m1}월경): {hint}
- 계절/제도 일정/연례 이벤트와 '{category}'를 결합하되, 시점이 {m1}~{m2}월인 것만.
"""
    else:
        extra = """[이번 배치 = 수익형 저경쟁(스위트스팟)]
- 핵심: '수익이 날 만큼 검색량은 있으면서(월 대략 1,000~30,000회 수준)', 대형 매체가 도배하지 않아 신생 블로그도 노려볼 만한 키워드.
- 검색이 거의 없는 초극소 키워드(월 수십~수백 회)는 피한다 → 트래픽·수익이 안 나옴.
- 반대로 너무 광범위한 대형 키워드(예: 그냥 "대출", "다이어트")도 피한다 → 상위노출 불가.
- 그 중간: 특정 대상/조건/상황을 담되 '실제로 찾는 사람이 꽤 있는' 롱테일.
  (좋은 예: "무직자 비상금 대출 조건", "연말정산 월세 세액공제 조건", "직장인 점심 다이어트 도시락")
  (나쁜 예: 너무 좁아 아무도 안 찾는 "○○동 △△은행 무직자 소액대출 후기" 류)
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


# 애드센스 정책 위반 소지가 큰 주제(자동 제외). 필요시 config로 확장 가능.
BLOCKLIST = [
    "성인", "야동", "포르노", "19금", "성인용품",
    "도박", "카지노", "토토", "베팅", "슬롯머신", "바카라", "사설",
    "마약", "대마", "총기", "무기", "폭탄", "해킹", "불법",
    "미성년", "청소년 유해",
    "확실히 낫는", "100% 완치", "즉효", "부작용 없이", "무조건 살빠지는",  # 과장 의료/효과
    "토렌트", "불법 다운로드", "크랙", "무료 스트리밍", "다시보기 링크",     # 저작권
    # 전쟁·분쟁·정치적 민감 이슈(애드센스 '충격적/민감한 콘텐츠' 위험 → 제외)
    "전쟁", "내전", "분쟁", "교전", "침공", "침략", "테러", "테러리스트",
    "무장", "군사충돌", "학살", "대량학살", "쿠데타", "폭동", "시위 진압",
    "인질", "포로", "난민", "핵전쟁", "미사일 발사", "공습", "휴전", "정전협정",
]


def is_blocked(keyword, extra=None):
    kw = str(keyword or "")
    words = BLOCKLIST + list(extra or [])
    return any(b and b in kw for b in words)


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
