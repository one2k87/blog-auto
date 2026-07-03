"""
build_config.py - 환경변수(GitHub Actions 시크릿)에서 config.json 생성 (카테고리 집중판).
로컬은 config.json 을 직접 편집해도 됩니다.
"""
import os, json


def b(v, default=False):
    if v is None:
        return default
    return str(v).lower() in ("1", "true", "yes", "on")


DEFAULT_CATS = [
    {"name": "금융/재테크", "desc": "신용카드, 대출, 정부지원금, 연금, 세금, 청약, 재테크, 주식/ETF 등 고단가 금융 주제"},
    {"name": "건강/생활", "desc": "다이어트, 영양제, 탈모, 피부, 수면, 홈트, 건강검진 등 고단가 건강·생활 주제"},
    {"name": "경제/IT", "desc": "물가·금리·부동산 경제, AI 도구, 클라우드, 앱/프로그램 사용법 등 경제/IT 주제"},
]
try:
    categories = json.loads(os.getenv("CATEGORIES_JSON", "")) or DEFAULT_CATS
except Exception:
    categories = DEFAULT_CATS

cfg = {
    "blog_url": os.getenv("BLOG_URL", os.getenv("WP_SITE", "")),
    "categories": categories,
    "counts": {
        "long_series": int(os.getenv("LONG_SERIES", "2")),
        "long_single": int(os.getenv("LONG_SINGLE", "2")),
        "season_series": int(os.getenv("SEASON_SERIES", "1")),
        "season_single": int(os.getenv("SEASON_SINGLE", "1")),
        "series_min_parts": int(os.getenv("SERIES_MIN", "2")),
        "series_max_parts": int(os.getenv("SERIES_MAX", "3")),
    },
    "ads": {"insert_slots": b(os.getenv("INSERT_ADS"), True)},
    "images": {
        "provider": os.getenv("IMAGE_PROVIDER", "gemini"),
        "model": os.getenv("IMAGE_MODEL", "imagen-3.0-generate-001"),
        "size": os.getenv("IMAGE_SIZE", "1024x1024"),
        "api_key": os.getenv("IMAGE_API_KEY", ""),
    },
    "llm": {
        "provider": os.getenv("LLM_PROVIDER", "gemini"),
        "api_key": os.getenv("LLM_API_KEY", ""),
        "model": os.getenv("LLM_MODEL", "gemini-2.5-flash"),
    },
    "metrics": {
        "provider": os.getenv("METRICS_PROVIDER", "naver"),
        "low_volume_floor": int(os.getenv("LOW_VOLUME_FLOOR", "100")),
        "low_volume_ceil": int(os.getenv("LOW_VOLUME_CEIL", "8000")),
        "use_trends_steadiness": b(os.getenv("USE_TRENDS_STEADINESS"), True),
        "naver": {
            "api_key": os.getenv("NAVER_API_KEY", ""),
            "secret_key": os.getenv("NAVER_SECRET_KEY", ""),
            "customer_id": os.getenv("NAVER_CUSTOMER_ID", ""),
        },
    },
    "wordpress": {
        "enabled": b(os.getenv("WP_ENABLED"), False),
        "site_url": os.getenv("WP_SITE", ""),
        "username": os.getenv("WP_USER", ""),
        "app_password": os.getenv("WP_APP_PASSWORD", ""),
        "status": os.getenv("WP_STATUS", "draft"),
    },
    "sheets": {"enabled": False},
}

with open("config.json", "w", encoding="utf-8") as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
print("config.json 생성: 카테고리=%s, 하루=%d개, metrics=%s, wp=%s" % (
    cfg["site"]["category"], cfg["counts"]["long"] + cfg["counts"]["season"],
    cfg["metrics"]["provider"], cfg["wordpress"]["enabled"]))
