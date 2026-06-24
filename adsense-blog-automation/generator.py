"""
generator.py - 키워드 1개를 받아 SEO 블로그 글(HTML)을 생성.
- languages 설정에 따라 한국어/영어 버전 생성
- 본문에 실제 참고 링크 1~2개 삽입
- 결과는 dict: title, meta, html, tags, links, lang
"""

import json
import re
from llm import chat
from links import find_reference_links

SYSTEM = (
    "당신은 구글 애드센스 승인과 SEO에 최적화된 글을 쓰는 전문 블로거입니다. "
    "독자에게 실질적으로 유용하고, 단계별로 구체적이며, 정확한 정보를 제공합니다. "
    "AI가 쓴 티가 나지 않게 자연스럽고 신뢰감 있는 문체로 작성합니다."
)

LANG_LABEL = {"ko": "한국어", "en": "English"}


def _article_prompt(keyword, lang, kind, links, context_news):
    label = LANG_LABEL.get(lang, lang)
    link_lines = "\n".join(f"- {l['title']}: {l['url']}" for l in links) or "(없음)"
    news_lines = "\n".join(f"- {n['title']}" for n in context_news[:4]) or "(없음)"

    kind_hint = (
        "최신 트렌드/이슈를 다루는 시의성 있는 정보 글"
        if kind == "hot"
        else "특정 모델/버전/오류를 해결하는 구체적인 how-to 가이드"
    )

    return f"""아래 주제로 {label} 블로그 글을 작성하세요.

주제(키워드): {keyword}
글 유형: {kind_hint}

관련 뉴스/맥락(참고용, 사실 확인은 필수):
{news_lines}

본문에 자연스럽게 녹여 넣을 실제 참고 링크(아래 URL을 그대로 <a href> 로 사용):
{link_lines}

작성 규칙:
1. H1 제목은 클릭을 부르는 SEO 제목. 키워드 포함.
2. 도입부 2~3문장으로 검색 의도에 바로 답한다.
3. <h2>/<h3> 소제목으로 구조화. 본문 800~1500단어.
4. how-to면 번호 매긴 단계(<ol><li>)로 설명.
5. 위에 제공된 참고 링크가 있으면 본문 중 자연스러운 위치에 <a href="URL" target="_blank" rel="noopener">앵커텍스트</a> 형태로 1~2개 삽입. 링크가 (없음)이면 넣지 말 것. URL을 절대 지어내지 말 것.
6. 마지막에 간단한 FAQ 2~3개(<h2>자주 묻는 질문</h2>).
7. 광고 배치를 고려해 문단을 적당히 나눈다.

반드시 아래 JSON 형식으로만 출력(코드블록 없이):
{{
  "title": "SEO 제목",
  "meta": "150자 이내 메타 설명",
  "tags": ["태그1","태그2","태그3","태그4","태그5"],
  "html": "<h1>...</h1> ... 전체 본문 HTML ..."
}}"""


def _extract_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    # 파싱 실패 시 통째로 본문 취급
    return {"title": "", "meta": "", "tags": [], "html": text}


def generate_article(keyword, kind, llm_cfg, languages=("ko",), context_news=None):
    """키워드 하나에 대해 언어별 글을 생성해 리스트로 반환."""
    context_news = context_news or []
    # 참고 링크 검색 (실제 URL)
    links = find_reference_links(keyword, max_results=2)

    articles = []
    for lang in languages:
        prompt = _article_prompt(keyword, lang, kind, links, context_news)
        raw = chat(prompt, llm_cfg, system=SYSTEM, max_tokens=4000, temperature=0.75)
        data = _extract_json(raw)
        articles.append({
            "keyword": keyword,
            "kind": kind,            # "hot" 또는 "niche"
            "lang": lang,
            "title": data.get("title") or keyword,
            "meta": data.get("meta", ""),
            "tags": data.get("tags", []),
            "html": data.get("html", ""),
            "links": links,
        })
    return articles
