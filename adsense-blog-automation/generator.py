"""
generator.py - 키워드 1개를 받아 SEO 최적화된 블로그 글을 생성.

SEO 적용 요소:
- 포커스 키워드(focus keyphrase): 제목 앞부분, 첫 문단(첫 100단어), 소제목, 메타에 자연 배치
- 제목 50~60자, 메타설명 120~155자 권장
- URL 슬러그(영문 소문자-하이픈) 자동 생성
- H1 1개 + H2/H3 계층, 목차(TOC) 자동 삽입, 짧은 문단/리스트로 가독성↑
- 신뢰할 수 있는 외부 링크 + 이미지 alt 텍스트 제안
- FAQ 섹션 + 구글이 읽는 구조화 데이터(JSON-LD: BlogPosting + FAQPage) 자동 생성
"""

import json
import re
import html as html_mod
from llm import chat
from links import find_reference_links

SYSTEM = (
    "당신은 구글 검색 1페이지 노출과 애드센스 수익을 동시에 잡는 전문 SEO 카피라이터입니다. "
    "검색 의도(정보형/거래형)를 정확히 충족시키고, E-E-A-T(경험·전문성·권위·신뢰)를 드러내며, "
    "키워드를 억지로 반복하지 않고 자연스럽게 배치합니다. 사실이 불확실하면 단정하지 않습니다."
)

LANG_LABEL = {"ko": "한국어", "en": "English"}


def slugify(text, max_words=8):
    """영문/숫자 기반 SEO 슬러그. 한글은 제거되므로 LLM 슬러그를 우선 사용."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text).strip("-")
    return "-".join(text.split("-")[:max_words]) or "post"


def _article_prompt(keyword, lang, kind, links, context_news):
    label = LANG_LABEL.get(lang, lang)
    link_lines = "\n".join(f"- {l['title']}: {l['url']}" for l in links) or "(없음)"
    news_lines = "\n".join(f"- {n['title']}" for n in context_news[:4]) or "(없음)"
    kind_hint = (
        "'높은 경쟁력' 인기 검색어(검색량 최다) 글. 경쟁이 치열하므로 검색 의도를 폭넓게 충족하는 "
        "포괄적·최신 정보 글로 차별화하고, 핵심 답을 상단에 배치해 이탈을 막는다."
        if kind == "hot"
        else "'낮은 경쟁력' 상록성 검색어(검색량은 적지만 꾸준함) 글. 그 하나의 문제를 끝까지 해결하는 "
        "정확하고 완결된 how-to 가이드로, 검색자가 다른 글을 더 찾을 필요가 없게 만든다."
    )

    return f"""아래 주제로 {label} 블로그 글을 '검색엔진 최적화(SEO)' 기준에 맞게 작성하세요.

핵심 키워드(포커스 키프레이즈): {keyword}
글 유형: {kind_hint}

관련 맥락(참고용, 사실 확인 필수):
{news_lines}

본문에 그대로 사용할 실제 외부 링크(아래 URL만 사용, 절대 지어내지 말 것):
{link_lines}

[SEO 작성 규칙 — 반드시 준수]
1. title: 50~60자. 포커스 키워드를 '앞쪽'에 자연스럽게 포함. 숫자/연도/혜택 등 클릭 유인 요소.
2. meta: 120~155자. 포커스 키워드 1회 포함 + 행동 유도(예: "방법을 단계별로 정리했습니다").
3. slug: 영어 소문자-하이픈, 3~6단어, 핵심 키워드 영문화. (예: epson-l3150-driver-windows11)
4. 첫 문단(약 2~3문장, 100단어 이내)에 포커스 키워드를 한 번 자연스럽게 넣고 검색 의도에 즉시 답한다.
5. 본문 html_body: <h2>/<h3>로 구조화. H2 중 최소 2개에 키워드 또는 연관어(LSI) 포함.
   - how-to면 번호 단계 <ol><li>로 구체적으로.
   - 문단은 2~4문장으로 짧게, 중요한 구절은 <strong>으로 강조(과도 금지).
   - 외부 링크가 있으면 본문 자연스러운 위치에 <a href="URL" target="_blank" rel="noopener">설명적 앵커텍스트</a>로 1~2개 삽입(없으면 넣지 말 것).
   - 총 분량: 핫이슈 900~1300단어, how-to 1000~1600단어.
   - <h1>은 넣지 말 것(시스템이 title로 자동 생성).
6. faqs: 검색자가 실제로 물을 법한 질문 3개와 간결한 답변(각 답변 2~3문장). PAA(People Also Ask) 노림.
7. image_alt: 대표 이미지에 넣을 alt 텍스트(키워드 포함, 1문장).
8. tags: 연관 키워드 5개(롱테일 포함).

출력은 아래 JSON만(코드블록/설명 없이):
{{
  "title": "...",
  "meta": "...",
  "slug": "...",
  "focus_keyword": "{keyword}",
  "tags": ["...","...","...","...","..."],
  "image_alt": "...",
  "html_body": "<p>...첫문단...</p><h2>...</h2>...",
  "faqs": [{{"q":"...","a":"..."}},{{"q":"...","a":"..."}},{{"q":"...","a":"..."}}]
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
    return {}


def _slugify_headings(html_body):
    """h2/h3에 id를 부여하고 (id, 텍스트, 레벨) 목록을 반환해 목차 생성."""
    items = []
    counter = [0]

    def repl(m):
        level = m.group(1)
        attrs = m.group(2) or ""
        inner = m.group(3)
        text = re.sub(r"<[^>]+>", "", inner).strip()
        counter[0] += 1
        hid = f"sec-{counter[0]}"
        items.append((hid, text, level))
        return f'<h{level}{attrs} id="{hid}">{inner}</h{level}>'

    new_html = re.sub(r"<h([23])([^>]*)>(.*?)</h\1>", repl, html_body, flags=re.DOTALL)
    return new_html, items


def _build_toc(items, lang):
    if len(items) < 3:
        return ""
    label = "목차" if lang == "ko" else "Table of Contents"
    lis = "".join(
        f'<li style="margin-left:{0 if lvl=="2" else 16}px"><a href="#{hid}">{html_mod.escape(txt)}</a></li>'
        for hid, txt, lvl in items
    )
    return (f'<nav class="toc" aria-label="{label}">'
            f'<strong>{label}</strong><ul>{lis}</ul></nav>')


def _build_faq_html(faqs, lang):
    if not faqs:
        return ""
    label = "자주 묻는 질문" if lang == "ko" else "Frequently Asked Questions"
    blocks = "".join(
        f'<h3>{html_mod.escape(f.get("q",""))}</h3><p>{html_mod.escape(f.get("a",""))}</p>'
        for f in faqs
    )
    return f"<h2>{label}</h2>{blocks}"


def _build_jsonld(title, meta, faqs, image_alt, slug, lang):
    """구글이 읽는 구조화 데이터: BlogPosting + (있으면) FAQPage."""
    blog = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": title,
        "description": meta,
        "inLanguage": lang,
        "mainEntityOfPage": {"@type": "WebPage"},
    }
    scripts = [json.dumps(blog, ensure_ascii=False)]
    if faqs:
        faq = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": f.get("q", ""),
                    "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")},
                }
                for f in faqs
            ],
        }
        scripts.append(json.dumps(faq, ensure_ascii=False))
    return "".join(f'<script type="application/ld+json">{s}</script>' for s in scripts)


def _assemble_html(data, lang):
    body = data.get("html_body", "")
    body, headings = _slugify_headings(body)
    toc = _build_toc(headings, lang)
    faq_html = _build_faq_html(data.get("faqs", []), lang)
    jsonld = _build_jsonld(
        data.get("title", ""), data.get("meta", ""), data.get("faqs", []),
        data.get("image_alt", ""), data.get("slug", ""), lang)
    # 최종: 목차 + 본문 + FAQ + 구조화데이터
    return f"{toc}{body}{faq_html}{jsonld}"


def generate_article(keyword, kind, llm_cfg, languages=("ko",), context_news=None):
    """키워드 하나에 대해 언어별 SEO 글을 생성해 리스트로 반환."""
    context_news = context_news or []
    links = find_reference_links(keyword, max_results=2)

    articles = []
    for lang in languages:
        prompt = _article_prompt(keyword, lang, kind, links, context_news)
        raw = chat(prompt, llm_cfg, system=SYSTEM, max_tokens=4500, temperature=0.7)
        data = _extract_json(raw)
        if not data:
            # 파싱 실패 시 최소 형태로라도 반환
            data = {"title": keyword, "meta": "", "slug": slugify(keyword),
                    "tags": [], "html_body": raw, "faqs": [], "image_alt": ""}

        slug = (data.get("slug") or "").strip() or slugify(data.get("title", keyword))
        slug = slugify(slug)  # 안전 정규화

        full_html = _assemble_html(data, lang)
        articles.append({
            "keyword": keyword,
            "kind": kind,                 # "hot" 또는 "niche"
            "lang": lang,
            "title": data.get("title") or keyword,
            "meta": data.get("meta", ""),
            "slug": slug,
            "focus_keyword": data.get("focus_keyword", keyword),
            "tags": data.get("tags", []),
            "image_alt": data.get("image_alt", ""),
            "faqs": data.get("faqs", []),
            "html": full_html,
            "links": links,
        })
    return articles
