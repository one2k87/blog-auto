"""
build_config.py - 환경변수(GitHub Actions 시크릿)에서 config.json 생성 (카테고리 집중판).
로컬은 config.json 을 직접 편집해도 됩니다.

주의: GitHub Actions 는 '등록 안 한 시크릿'을 빈 문자열("")로 넘깁니다.
그래서 os.getenv(name, default) 의 default 가 무시되므로, 아래 helper 로 '빈 값이면 기본값' 처리를 합니다.
"""
import os, json


def envs(name, default=""):
    """환경변수 문자열: 없거나 빈 값이면 default."""
    v = os.getenv(name)
    return v if (v is not None and v.strip() != "") else default


def envi(name, default):
    """환경변수 정수: 없거나 빈 값/이상값이면 default(int)."""
    v = os.getenv(name)
    if v is None or str(v).strip() == "":
        return int(default)
    try:
        return int(str(v).strip())
    except ValueError:
        return int(default)


def b(name, default=False):
    v = os.getenv(name)
    if v is None or str(v).strip() == "":
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "on")


DEFAULT_CATS = [
    {"name": "금융/재테크", "wp_category": "금융", "desc": "신용카드, 대출, 정부지원금, 연금, 세금, 청약, 재테크, 주식/ETF 등 고단가 금융 주제"},
    {"name": "건강/생활", "wp_category": "건강", "desc": "다이어트, 영양제, 탈모, 피부, 수면, 홈트, 건강검진 등 고단가 건강·생활 주제"},
    {"name": "경제/IT", "wp_category": "경제IT", "desc": "물가·금리·부동산 경제, AI 도구, 클라우드, 앱/프로그램 사용법 등 경제/IT 주제"},
]
try:
    categories = json.loads(envs("CATEGORIES_JSON", "")) or DEFAULT_CATS
except Exception:
    categories = DEFAULT_CATS

cfg = {
    "blog_url": envs("BLOG_URL", envs("WP_SITE", "")),
    "categories": categories,
    "counts": {
        "long_series": envi("LONG_SERIES", 2),
        "long_single": envi("LONG_SINGLE", 2),
        "season_series": envi("SEASON_SERIES", 1),
        "season_single": envi("SEASON_SINGLE", 1),
        "series_min_parts": envi("SERIES_MIN", 2),
        "series_max_parts": envi("SERIES_MAX", 3),
    },
    "ads": {"insert_slots": b("INSERT_ADS", True)},
    "images": {
        # 폰/수동 실행에서 images=false 를 넘기면 이미지 생성 끔
        "provider": ("none" if str(os.getenv("IMAGE_ENABLED", "")).strip().lower() == "false"
                     else envs("IMAGE_PROVIDER", "gemini")),
        "model": envs("IMAGE_MODEL", "imagen-3.0-generate-001"),
        "size": envs("IMAGE_SIZE", "1024x1024"),
        "api_key": envs("IMAGE_API_KEY", ""),
    },
    "llm": {
        "provider": envs("LLM_PROVIDER", "gemini"),
        "api_key": envs("LLM_API_KEY", ""),
        # 무료 등급: 2.5-flash 는 하루 20회로 축소됨 → flash-lite(하루 ~1,000회)를 기본값으로
        "model": envs("LLM_MODEL", "gemini-2.5-flash-lite"),
    },
    "metrics": {
        "provider": envs("METRICS_PROVIDER", "naver"),
        "low_volume_floor": envi("LOW_VOLUME_FLOOR", 100),
        "low_volume_ceil": envi("LOW_VOLUME_CEIL", 8000),
        "use_trends_steadiness": b("USE_TRENDS_STEADINESS", False),
        "naver": {
            "api_key": envs("NAVER_API_KEY", ""),
            "secret_key": envs("NAVER_SECRET_KEY", ""),
            "customer_id": envs("NAVER_CUSTOMER_ID", ""),
        },
    },
    "wordpress": {
        "enabled": b("WP_ENABLED", False),
        "site_url": envs("WP_SITE", ""),
        "username": envs("WP_USER", ""),
        "app_password": envs("WP_APP_PASSWORD", ""),
        "status": envs("WP_STATUS", "draft"),
    },
    "sheets": {"enabled": False},
    "perf": {
        "workers": envi("WORKERS", 3),      # 슬롯 병렬 생성(이미지·글 대기시간 겹치기)
        "classify": b("CLASSIFY", True),    # false 면 판별 LLM 호출 생략(무료 등급 속도↑)
    },
}

with open("config.json", "w", encoding="utf-8") as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
slots_each = (cfg["counts"]["long_series"] + cfg["counts"]["long_single"]
              + cfg["counts"]["season_series"] + cfg["counts"]["season_single"])
print("config.json 생성: 카테고리 %d개, 각 %d슬롯, images=%s, metrics=%s, wp=%s" % (
    len(cfg["categories"]), slots_each, cfg["images"]["provider"],
    cfg["metrics"]["provider"], cfg["wordpress"]["enabled"]))
