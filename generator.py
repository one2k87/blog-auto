"""
generator.py - 애드센스 '수익형 + 상위노출' 한국어 글 생성.

참고 자료(애드센스 실전 전략) 반영:
1) 클릭률 구조: 이미지 자리 → 그 아래 문단 사이 광고 자리 + 정책 안전한 유도문장.
2) 고단가 키워드 배치: 제목/첫문단/중반/마지막에 핵심 키워드 분산.
3) 체류시간: 3초 후킹 첫문장(질문/공감형), 요약표, 소제목 구조(H1>H2>H3).
4) 카테고리 반복수익: 끝에 '함께 보면 좋은 글' 내부링크(같은 카테고리 이전 글).
+ SEO: 슬러그, 메타(120~155자), 목차, FAQ, JSON-LD(BlogPosting+FAQPage).

광고/이미지 자리는 파이썬에서 안정적으로 삽입한다. LLM은 본문에 [[AD]] / [[IMG:설명]]
마커를 넣고, 없으면 파이썬이 소제목 사이에 자동 배치한다.
"""

import json
import re
import html as html_mod
import random
from llm import chat
from links import find_reference_links

SYSTEM = (
    "당신은 구글 애드센스로 실제 수익을 내는 한국어 블로그 전문 작가입니다. "
    "고단가 키워드를 자연스러운 회화체로 녹이고, 방문자가 끝까지 읽고 광고에 시선이 가도록 "
    "구조를 설계합니다. 광고 클릭을 직접 유도하는 표현은 절대 쓰지 않고, 정책을 준수합니다. "
    "사실이 불확실하면 단정하지 않습니다."
)

# 광고 근처에 놓는 '정책 안전한' 유도문장 (클릭 직접 유도 아님)
CTA_LINES = [
    "더 자세한 내용은 아래에서 이어서 확인해보세요.",
    "관련 정보가 궁금하다면 다음 내용을 참고해보세요.",
    "아래에서 핵심 내용을 계속 확인해보세요.",
    "이어지는 내용도 함께 살펴보세요.",
]


def slugify(text, max_words=8):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text).strip("-")
    return "-".join(text.split("-")[:max_words]) or "post"


def _ad_slot():
    cta = random.choice(CTA_LINES)
    return (
        '<div class="ad-slot" style="margin:26px 0;padding:14px;border:1px dashed #d8dbe0;'
        'border-radius:10px;text-align:center;background:#fafbfc">'
        f'<p style="margin:0 0 8px;color:#666;font-size:14px">{cta}</p>'
        '<!-- 애드센스 광고 코드를 이 자리에 붙여넣으세요 -->'
        '<div style="color:#b6bcc6;font-size:13px">[ 광고 자리 ]</div>'
        '</div>'
    )


def _img_slot(desc):
    d = html_mod.escape(desc or "관련 이미지")
    return (
        '<figure style="margin:22px 0;text-align:center">'
        f'<div style="padding:38px 12px;background:#f2f4f7;border-radius:10px;color:#98a2b3">'
        f'📷 이미지 삽입: {d}</div>'
        f'<figcaption style="font-size:13px;color:#98a2b3;margin-top:6px">{d}</figcaption>'
        f'</figure><!-- alt: {d} -->'
    )


def _article_prompt(keyword, kind, category, links, related, insert_ads):
    link_lines = "\n".join(f"- {l['title']}: {l['url']}" for l in links) or "(없음)"
    rel_lines = "\n".join(f"- {r['title']}" for r in related) or "(없음)"
    kind_hint = (
        "시즌 선점 글: 앞으로 검색이 붙을 시기를 겨냥해 지금 미리 완결성 있게 정리"
        if kind == "season"
        else "저경쟁 롱테일 글: 좁고 명확한 문제를 끝까지 해결해 상위노출을 노림"
    )
    ad_rule = (
        "5. 이미지는 '딱 1개'만 [[IMG:이미지설명]]로 본문 상단부(첫 소제목 부근) 적절한 위치에 넣고, "
        "그 바로 아래에 [[AD]]를 배치(이미지→광고 순서). 추가로 본문 중간 '정보가 끝나는 문단 뒤'에 "
        "[[AD]] 1개를 더 넣어 광고는 총 2개."
        if insert_ads
        else "5. 이미지는 '딱 1개'만 [[IMG:이미지설명]]로 본문 상단부에 넣으세요(광고 마커는 넣지 말 것)."
    )

    return f"""'{category}' 카테고리의 애드센스 수익형 한국어 블로그 글을 작성하세요.

[애드센스 실전 전략 5가지 — 반드시 그대로 반영]
① 클릭률 구조: 훑어읽는 독자를 위해 이미지를 먼저 배치하고, '정보가 끝나는 문단 뒤'에 광고가 오게 설계.
② 고단가 키워드: 금융/보험/건강/기술 계열 고단가 키워드를 제목·첫문단·중반·마지막에 자연스러운 회화체로 분산.
③ 타이밍/시의성: 검색이 붙을 시점을 고려해 지금 완결성 있게 정리(시즌 글은 다가올 시기를 겨냥).
④ 체류시간: 3초 후킹 첫문장(질문/공감형) + 요약표 + 이미지/표로 시선 유지, 서론은 짧게.
⑤ 카테고리 반복수익: 끝에 같은 카테고리의 '함께 보면 좋은 글'로 내부링크(다음 글 유도).

핵심 키워드(고단가): {keyword}
글 성격: {kind_hint}

본문에 그대로 쓸 실제 외부 링크(URL을 지어내지 말 것, 없으면 넣지 않음):
{link_lines}

[작성 규칙 — 자료 전략 그대로]
1. 제목(title): 50~60자. 핵심 키워드를 앞쪽에 넣고, 숫자/조건/혜택으로 클릭 유인. 고단가 키워드가 제목에 분명히 드러나야 함.
2. hook(첫 문장): 3초 안에 이탈을 막는 질문형 또는 공감형 한 문장. (예: "대출 이자 부담, 조금이라도 줄일 방법 없을까요?")
3. 첫 문단에서 검색 의도에 바로 답하고 핵심 키워드를 1회 자연스럽게 포함.
4. 키워드를 제목·첫문단·본문 중반·마지막 문단에 나눠서 자연스러운 회화체로 배치.
{ad_rule}
6. 구조: <h2>/<h3> 계층. H2 최소 3개, 각 H2 아래 2~4문장 문단. 정보가 끝나는 지점에서 문단을 끊어 광고가 들어갈 여지를 만든다.
7. summary_table: 핵심을 한눈에 보는 요약표(2~4행) 데이터를 rows로 제공(체류시간↑).
8. faqs: 실제로 많이 묻는 질문 3개와 간결한 답(각 2~3문장).
9. 총 900~1500자 분량. 광고 클릭을 직접 유도하는 문구 금지.

참고: 같은 카테고리의 다른 글 제목(내부링크로 이어질 수 있음, 참고만):
{rel_lines}

출력은 아래 JSON만(코드블록/설명 없이):
{{
  "title": "...",
  "meta": "120~155자 메타설명, 키워드 포함",
  "slug": "english-hyphen-slug",
  "focus_keyword": "{keyword}",
  "tags": ["...","...","...","...","..."],
  "hook": "첫 문장",
  "summary_table": {{"headers": ["항목","내용"], "rows": [["...","..."],["...","..."]]}},
  "html_body": "<p>첫문단...</p><h2>...</h2><p>[[IMG:대표 이미지 설명]]</p>[[AD]]<p>...</p><h2>...</h2><p>...[[AD]]</p>...",
  "faqs": [{{"q":"...","a":"..."}},{{"q":"...","a":"..."}},{{"q":"...","a":"..."}}]
}}"""


def _extract_json(text):
    text = (text or "").strip()
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


def _convert_markers(html_body, insert_ads, resolver=None):
    """[[IMG:..]] / [[AD]] 마커를 실제 이미지/광고 자리로 치환. 부족하면 자동 보충."""
    counter = [0]

    def img_repl(m):
        counter[0] += 1
        if counter[0] > 1:                # 글당 이미지 1개만: 초과 마커 제거
            return ""
        desc = m.group(1)
        if resolver:                      # 이미지 자동 생성 시도
            html = resolver(desc, counter[0])
            if html:
                return html
        return _img_slot(desc)            # 실패/미설정 시 자리 표시

    html_body = re.sub(r"\[\[IMG:([^\]]*)\]\]", img_repl, html_body)
    if insert_ads:
        if "[[AD]]" in html_body:
            html_body = html_body.replace("[[AD]]", _ad_slot())
        else:
            # 마커가 없으면 소제목(H2) 사이 2곳에 자동 삽입
            parts = re.split(r"(?=<h2)", html_body)
            if len(parts) >= 3:
                insert_at = [1, min(3, len(parts) - 1)]
                for off, idx in enumerate(insert_at):
                    parts.insert(idx + off, _ad_slot())
                html_body = "".join(parts)
            else:
                html_body += _ad_slot()
    else:
        html_body = html_body.replace("[[AD]]", "")
    return html_body


def _summary_table_html(tbl):
    if not tbl or not tbl.get("rows"):
        return ""
    headers = tbl.get("headers") or []
    th = "".join(f"<th style='text-align:left;padding:8px;border-bottom:2px solid #e5e7eb'>{html_mod.escape(str(h))}</th>" for h in headers)
    trs = ""
    for row in tbl["rows"]:
        tds = "".join(f"<td style='padding:8px;border-bottom:1px solid #eef0f3'>{html_mod.escape(str(c))}</td>" for c in row)
        trs += f"<tr>{tds}</tr>"
    head = f"<thead><tr>{th}</tr></thead>" if th else ""
    return (f'<table class="summary" style="border-collapse:collapse;width:100%;margin:16px 0">'
            f'{head}<tbody>{trs}</tbody></table>')


def _slugify_headings(html_body):
    items, counter = [], [0]

    def repl(m):
        level, attrs, inner = m.group(1), m.group(2) or "", m.group(3)
        text = re.sub(r"<[^>]+>", "", inner).strip()
        counter[0] += 1
        hid = f"sec-{counter[0]}"
        items.append((hid, text, level))
        return f'<h{level}{attrs} id="{hid}">{inner}</h{level}>'

    return re.sub(r"<h([23])([^>]*)>(.*?)</h\1>", repl, html_body, flags=re.DOTALL), items


def _build_toc(items):
    if len(items) < 3:
        return ""
    lis = "".join(
        f'<li style="margin-left:{0 if lvl=="2" else 16}px"><a href="#{hid}">{html_mod.escape(txt)}</a></li>'
        for hid, txt, lvl in items)
    return f'<nav class="toc" aria-label="목차"><strong>목차</strong><ul>{lis}</ul></nav>'


def _build_faq_html(faqs):
    if not faqs:
        return ""
    blocks = "".join(
        f'<h3>{html_mod.escape(f.get("q",""))}</h3><p>{html_mod.escape(f.get("a",""))}</p>'
        for f in faqs)
    return f"<h2>자주 묻는 질문</h2>{blocks}"


def _build_internal_links(related, blog_url):
    """같은 카테고리 이전 글로 '함께 보면 좋은 글' 내부링크."""
    if not related:
        return ""
    items = []
    for r in related[:3]:
        url = r.get("url") or (f"{blog_url.rstrip('/')}/{r['slug']}" if blog_url and r.get("slug") else "#")
        items.append(f'<li><a href="{url}">{html_mod.escape(r["title"])}</a></li>')
    return ('<h2>함께 보면 좋은 글</h2>'
            f'<ul class="related">{"".join(items)}</ul>')


def _build_jsonld(title, meta, faqs, lang="ko"):
    blog = {"@context": "https://schema.org", "@type": "BlogPosting",
            "headline": title, "description": meta, "inLanguage": lang,
            "mainEntityOfPage": {"@type": "WebPage"}}
    scripts = [json.dumps(blog, ensure_ascii=False)]
    if faqs:
        faq = {"@context": "https://schema.org", "@type": "FAQPage",
               "mainEntity": [{"@type": "Question", "name": f.get("q", ""),
                               "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")}}
                              for f in faqs]}
        scripts.append(json.dumps(faq, ensure_ascii=False))
    return "".join(f'<script type="application/ld+json">{s}</script>' for s in scripts)


def _assemble(data, related, blog_url, insert_ads, resolver=None, series_nav=""):
    body = _convert_markers(data.get("html_body", ""), insert_ads, resolver)
    body, headings = _slugify_headings(body)
    toc = _build_toc(headings)
    summary = _summary_table_html(data.get("summary_table"))
    hook = data.get("hook", "")
    hook_html = f'<p class="hook" style="font-size:17px;font-weight:600">{html_mod.escape(hook)}</p>' if hook else ""
    faq_html = _build_faq_html(data.get("faqs", []))
    internal = _build_internal_links(related, blog_url)
    jsonld = _build_jsonld(data.get("title", ""), data.get("meta", ""), data.get("faqs", []))
    # 순서: 후킹 → (시리즈 내비) → 목차 → 요약표 → 본문(이미지/광고) → FAQ → (시리즈 내비) → 내부링크 → 구조화데이터
    return f"{hook_html}{series_nav}{toc}{summary}{body}{faq_html}{series_nav}{internal}{jsonld}"


def _gen_one(keyword, kind, llm_cfg, category, links, related, blog_url,
             insert_ads, image_resolver, series_nav=""):
    prompt = _article_prompt(keyword, kind, category, links, related, insert_ads)
    raw = chat(prompt, llm_cfg, system=SYSTEM, max_tokens=4500, temperature=0.7)
    data = _extract_json(raw)
    if not data:
        data = {"title": keyword, "meta": "", "slug": slugify(keyword),
                "tags": [], "hook": "", "summary_table": {}, "html_body": raw, "faqs": []}
    slug = slugify((data.get("slug") or "").strip() or slugify(data.get("title", keyword)))
    full_html = _assemble(data, related, blog_url, insert_ads, image_resolver, series_nav)
    return {
        "keyword": keyword, "kind": kind, "lang": "ko", "category": category,
        "title": data.get("title") or keyword,
        "meta": data.get("meta", ""), "slug": slug,
        "focus_keyword": data.get("focus_keyword", keyword),
        "tags": data.get("tags", []), "faqs": data.get("faqs", []),
        "html": full_html, "links": links,
    }


def generate_article(keyword, kind, llm_cfg, category="", related=None,
                     blog_url="", insert_ads=True, context_news=None, image_resolver=None):
    """키워드 1개 → 수익형 한국어 글 dict 반환(리스트로 감싸 반환)."""
    related = related or []
    links = find_reference_links(keyword, max_results=2)
    art = _gen_one(keyword, kind, llm_cfg, category, links, related, blog_url,
                   insert_ads, image_resolver)
    return [art]


def _series_nav(parts_meta, cur_idx, blog_url):
    """시리즈 편 간 내비게이션(마지막 편 → 처음 편 루프 포함)."""
    n = len(parts_meta)
    links = []
    for i, p in enumerate(parts_meta):
        url = p.get("url") or (f"{blog_url.rstrip('/')}/{p['slug']}" if blog_url and p.get("slug") else "#")
        label = f"{i+1}편"
        if i == cur_idx:
            links.append(f'<strong style="color:#7c5cff">{label}(현재)</strong>')
        else:
            links.append(f'<a href="{url}">{label}</a>')
    return ('<nav class="series-nav" style="margin:16px 0;padding:10px 14px;background:#f6f4ff;'
            'border-radius:10px;font-size:14px">📚 시리즈: ' + " · ".join(links) + '</nav>')


def generate_series(topic, kind, n_parts, llm_cfg, category="", related=None,
                    blog_url="", insert_ads=True, image_resolver=None):
    """
    하나의 주제를 2~3편 시리즈로 기획해 각 편을 완성 글로 생성.
    편 간 내부링크 + 마지막→처음 루프. 반환: 편 리스트(모두 같은 series_id).
    시리즈는 상위(main)에서 1건으로 카운트한다.
    """
    related = related or []
    # 1) 시리즈 편 구성(part별 소주제) 기획
    plan_prompt = f"""'{category}' 카테고리에서 아래 주제를 {n_parts}편 시리즈로 나누세요.
주제: {topic}
각 편은 겹치지 않게 단계적으로 이어지며, 각 편만으로도 완결성이 있어야 합니다.
(예: 준비편 → 실행편 → 최적화편)
출력은 각 편의 '구체적 제목 키워드'를 줄바꿈으로 {n_parts}개만. 번호/설명 없이."""
    raw = chat(plan_prompt, llm_cfg, max_tokens=300, temperature=0.7)
    part_kws = [re.sub(r"^[\-\*\d\.\)\s]+", "", ln).strip()
                for ln in (raw or "").splitlines() if ln.strip()][:n_parts]
    while len(part_kws) < n_parts:
        part_kws.append(f"{topic} {len(part_kws)+1}편")

    import uuid as _uuid
    series_id = "s" + _uuid.uuid4().hex[:8]
    # 2) 편별 슬러그 먼저 확정(상호 링크용)
    parts_meta = [{"slug": slugify(kw) + f"-{i+1}", "url": ""} for i, kw in enumerate(part_kws)]

    links = find_reference_links(topic, max_results=2)
    arts = []
    for i, kw in enumerate(part_kws):
        nav = _series_nav(parts_meta, i, blog_url)
        rel = related[:2]
        art = _gen_one(kw, kind, llm_cfg, category, links, rel, blog_url,
                       insert_ads, image_resolver, series_nav=nav)
        art["slug"] = parts_meta[i]["slug"]     # 확정 슬러그 유지(링크 일치)
        art["series_id"] = series_id
        art["series_part"] = i + 1
        art["series_total"] = n_parts
        art["title"] = f"[{i+1}편] " + art["title"]
        arts.append(art)
    return arts
