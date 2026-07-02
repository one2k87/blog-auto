"""
main.py - 매일 1회 실행되는 메인 파이프라인 (언어별 독립 트랙).

트랙(config.tracks)마다 그 나라 기준으로 키워드를 '따로' 산출한다.
  - 한국어 트랙: geo=KR, 네이버 검색광고로 실측 → 트렌드5 + 에버그린5 = 한국어 글 10개
  - 영어 트랙:   geo=US, Google Trends/Ads로 실측 → 트렌드5 + 에버그린5 = 영어 글 10개
  => 두 언어가 서로 다른 키워드/내용으로 각각 10개, 총 20개.

흐름(트랙별 반복):
1) 그 트랙 geo의 트렌드 급상승(높은 경쟁력) + LLM 상록성(낮은 경쟁력) 후보 수집
2) 그 트랙 metrics로 실측 검색량/꾸준함 측정 → 상위 5+5 선별
3) 그 언어로 SEO 블로그 글 생성
4) (옵션) WordPress 게시 / 복붙 HTML 저장
5) (옵션) 구글시트 로깅
6) dashboard/data/latest.json 저장 → 웹/아이폰 대시보드가 읽음

실행: python main.py   설정: config.json
"""

import os
import json
import html as html_mod
from datetime import datetime

import trends
import metrics
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


def get_tracks(cfg):
    """
    config에서 언어별 트랙 목록을 만든다.
    - "tracks"가 있으면 그대로 사용.
    - 없으면 구버전 호환: languages + 공통 metrics + trends_geo 로 트랙을 구성
      (ko→KR, en→US 기본 매핑).
    """
    if cfg.get("tracks"):
        return cfg["tracks"]
    default_geo = {"ko": "KR", "en": "US"}
    tracks = []
    for lang in cfg.get("languages", ["ko"]):
        tracks.append({
            "lang": lang,
            "trends_geo": cfg.get("trends_geo", default_geo.get(lang, "US")),
            "metrics": cfg.get("metrics", {"provider": "none"}),
        })
    return tracks


def collect_keywords_for_track(track, cfg):
    """
    한 트랙(언어)에 대해 그 나라 기준으로 높은/낮은 경쟁력 키워드를 실측 선별.
    반환: (hot[list], low[list]) 각 n개.
    """
    n = cfg.get("count_each", 5)
    lang = track.get("lang", "ko")
    geo = track.get("trends_geo", "KR")
    mcfg = track.get("metrics", {}) or {}
    measured = mcfg.get("provider", "none") != "none"
    pool = 3 if measured else 1

    label = "한국어" if lang == "ko" else ("영어" if lang == "en" else lang)
    print(f"\n[{label} 트랙] geo={geo}, metrics={mcfg.get('provider','none')} 키워드 수집…")

    # ---- 높은 경쟁력 후보: 해당 geo의 트렌드 급상승 ----
    hot_pool = [h for h in trends.fetch_hot_keywords(geo, n * pool) if h["keyword"]]
    if not hot_pool:
        if lang == "en":
            q = f"List {n*pool} highest-volume trending Google search keywords in the US today. Newlines only, no numbering."
        else:
            q = f"오늘 한국에서 검색량이 가장 많은(높은 경쟁력) 실시간 인기 검색어 {n*pool}개를 줄바꿈으로만 출력."
        raw = chat(q, cfg["llm"], max_tokens=400, temperature=0.8)
        hot_pool = trends.parse_niche_keywords(raw, n * pool)

    # ---- 낮은 경쟁력 후보: 해당 언어/시장 상록성 세부 주제 ----
    low_raw = chat(trends.build_niche_prompt(n * pool, lang=lang), cfg["llm"],
                   max_tokens=900, temperature=0.9)
    low_pool = trends.parse_niche_keywords(low_raw, n * pool)

    if not measured:
        return hot_pool[:n], low_pool[:n]

    print(f"  · 검색량 측정 중(높은 경쟁력)…")
    metrics.enrich(hot_pool, mcfg, geo=geo, want_steadiness=False)
    print(f"  · 검색량+꾸준함 측정 중(낮은 경쟁력)…")
    metrics.enrich(low_pool, mcfg, geo=geo, want_steadiness=True)

    def vol(x):
        return x.get("volume") if x.get("volume") is not None else (x.get("interest") or 0)

    hot = sorted(hot_pool, key=vol, reverse=True)[:n]

    floor = mcfg.get("low_volume_floor", 100)
    ceil = mcfg.get("low_volume_ceil", 8000)

    def in_band(x):
        v = x.get("volume")
        return True if v is None else (floor <= v <= ceil)

    cand = [x for x in low_pool if in_band(x)]
    cand.sort(key=lambda x: ((x.get("steadiness") or 0), vol(x)), reverse=True)
    low = (cand or low_pool)[:n]

    print(f"  · [{label}] 높은 경쟁력:", [(k['keyword'], k.get('volume')) for k in hot])
    print(f"  · [{label}] 낮은 경쟁력:", [(k['keyword'], k.get('volume'), k.get('steadiness')) for k in low])
    return hot, low


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
    wp_cfg = cfg.get("wordpress", {})
    auto_publish = wp_cfg.get("enabled", False)

    print(f"=== {datetime.now():%Y-%m-%d %H:%M} 자동 블로그 생성 시작 ===")
    tracks = get_tracks(cfg)

    all_articles = []
    for track in tracks:
        lang = track.get("lang", "ko")
        hot, low = collect_keywords_for_track(track, cfg)

        for kind, kws in (("hot", hot), ("niche", low)):
            for kw in kws:
                if not kw["keyword"]:
                    continue
                print(f"-> [{lang}] 생성 중 [{kind}] {kw['keyword']}")
                # 이 트랙의 언어로만 글 1개 생성
                arts = generate_article(
                    kw["keyword"], kind, cfg["llm"],
                    languages=(lang,), context_news=kw.get("news", []))
                for a in arts:
                    a["volume"] = kw.get("volume")
                    a["competition"] = kw.get("competition", "")
                    a["steadiness"] = kw.get("steadiness")
                    a["interest"] = kw.get("interest")
                    a["metric_source"] = kw.get("metric_source", "")
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
