"""
main.py - 매일 1회 실행되는 메인 파이프라인.

흐름:
1) Google Trends RSS로 핫이슈 키워드 N개 수집
2) LLM으로 세분화(롱테일) 키워드 N개 생성
3) 각 키워드마다 한국어/영어 블로그 글 생성 (참고 링크 포함)
4) (옵션) WordPress 자동 게시 -> 안 하면 복붙용 HTML 저장
5) (옵션) Google Sheets 로깅
6) 오늘 결과를 dashboard/data/날짜.json + latest.json 으로 저장 -> 웹 대시보드가 읽음

실행: python main.py
설정: config.json (config.example.json 참고해서 만들기)
"""

import os
import json
import html as html_mod
from datetime import datetime

import trends
from llm import chat
from generator import generate_article
from publisher import publish_to_wordpress
from sheets import log_rows

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE, "output")           # 복붙용 HTML
DASH_DATA = os.path.join(BASE, "dashboard", "data")  # 대시보드용 JSON


def load_config():
    path = os.path.join(BASE, "config.json")
    if not os.path.exists(path):
        raise SystemExit("config.json 이 없습니다. config.example.json 을 복사해 만드세요.")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def collect_keywords(cfg):
    n = cfg.get("count_each", 5)
    geo = cfg.get("trends_geo", "KR")

    # 1) 핫이슈
    hot = trends.fetch_hot_keywords(geo, n)
    # RSS가 비어있으면 LLM으로 보충
    if all(not h["keyword"] for h in hot):
        raw = chat(
            f"오늘 한국에서 화제가 될 만한 검색 트렌드 키워드 {n}개를 줄바꿈으로만 출력.",
            cfg["llm"], max_tokens=300, temperature=0.8)
        hot = trends.parse_niche_keywords(raw, n)

    # 2) 세분화(롱테일)
    niche_prompt = trends.build_niche_prompt(n)
    niche_raw = chat(niche_prompt, cfg["llm"], max_tokens=600, temperature=0.9)
    niche = trends.parse_niche_keywords(niche_raw, n)

    return hot, niche


def save_copy_html(article):
    os.makedirs(OUT_DIR, exist_ok=True)
    safe = "".join(c for c in article["keyword"][:40] if c.isalnum() or c in " _-").strip()
    fname = f"{datetime.now():%Y%m%d}_{article['kind']}_{article['lang']}_{safe}.html"
    path = os.path.join(OUT_DIR, fname)
    doc = f"""<!doctype html><html><head><meta charset="utf-8">
<title>{html_mod.escape(article['title'])}</title>
<meta name="description" content="{html_mod.escape(article['meta'])}"></head>
<body>{article['html']}</body></html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)
    return path


def run():
    cfg = load_config()
    languages = tuple(cfg.get("languages", ["ko"]))
    wp_cfg = cfg.get("wordpress", {})
    auto_publish = wp_cfg.get("enabled", False)

    print(f"=== {datetime.now():%Y-%m-%d %H:%M} 자동 블로그 생성 시작 ===")
    hot, niche = collect_keywords(cfg)
    print("핫이슈:", [h["keyword"] for h in hot])
    print("세분화:", [n["keyword"] for n in niche])

    all_articles = []
    plan = [("hot", hot), ("niche", niche)]
    for kind, kws in plan:
        for kw in kws:
            if not kw["keyword"]:
                continue
            print(f"-> 생성 중 [{kind}] {kw['keyword']}")
            arts = generate_article(
                kw["keyword"], kind, cfg["llm"],
                languages=languages, context_news=kw.get("news", []))
            for a in arts:
                # 게시 또는 복붙 저장
                if auto_publish:
                    url = publish_to_wordpress(a, wp_cfg)
                    a["status"] = "게시됨" if url else "게시실패"
                    a["post_url"] = url or ""
                else:
                    a["status"] = "복붙대기"
                    a["post_url"] = ""
                a["copy_file"] = save_copy_html(a)
                all_articles.append(a)

    # 5) 시트 로깅
    log_rows(all_articles, cfg.get("sheets"))

    # 6) 대시보드 데이터 저장
    os.makedirs(DASH_DATA, exist_ok=True)
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "auto_publish": auto_publish,
        "articles": all_articles,
    }
    dated = os.path.join(DASH_DATA, f"{datetime.now():%Y-%m-%d}.json")
    latest = os.path.join(DASH_DATA, "latest.json")
    for p in (dated, latest):
        with open(p, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"=== 완료: 총 {len(all_articles)}개 글 생성 ===")
    print(f"대시보드 데이터: {latest}")


if __name__ == "__main__":
    run()
