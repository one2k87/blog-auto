"""
build_config.py - 환경변수(또는 GitHub Actions 시크릿)에서 config.json 을 생성.
로컬 실행 시에는 config.json 을 직접 만들어도 됩니다(이 파일은 클라우드 자동화용).

트랙 구성:
  LANGS 에 포함된 언어별로 트랙을 만든다.
    ko → geo=KR, metrics=KO_METRICS_PROVIDER(기본 naver, 네이버 키 사용)
    en → geo=US, metrics=EN_METRICS_PROVIDER(기본 trends, 필요시 google_ads)
"""
import os, json


def b(v, default=False):
    if v is None:
        return default
    return str(v).lower() in ("1", "true", "yes", "on")


def naver_block():
    return {
        "api_key": os.getenv("NAVER_API_KEY", ""),
        "secret_key": os.getenv("NAVER_SECRET_KEY", ""),
        "customer_id": os.getenv("NAVER_CUSTOMER_ID", ""),
    }


def gads_block(lang_id, geo_id):
    return {
        "developer_token": os.getenv("GADS_DEVELOPER_TOKEN", ""),
        "client_id": os.getenv("GADS_CLIENT_ID", ""),
        "client_secret": os.getenv("GADS_CLIENT_SECRET", ""),
        "refresh_token": os.getenv("GADS_REFRESH_TOKEN", ""),
        "login_customer_id": os.getenv("GADS_LOGIN_CUSTOMER_ID", ""),
        "language_id": lang_id,
        "geo_target_id": geo_id,
    }


langs = [s.strip() for s in os.getenv("LANGS", "ko,en").split(",") if s.strip()]
tracks = []

if "ko" in langs:
    tracks.append({
        "lang": "ko",
        "trends_geo": "KR",
        "metrics": {
            "provider": os.getenv("KO_METRICS_PROVIDER", "naver"),
            "low_volume_floor": int(os.getenv("KO_LOW_FLOOR", "100")),
            "low_volume_ceil": int(os.getenv("KO_LOW_CEIL", "8000")),
            "use_trends_steadiness": b(os.getenv("USE_TRENDS_STEADINESS"), True),
            "naver": naver_block(),
            "google_ads": gads_block("1012", "2410"),   # 한국어/대한민국
        },
    })

if "en" in langs:
    tracks.append({
        "lang": "en",
        "trends_geo": "US",
        "metrics": {
            "provider": os.getenv("EN_METRICS_PROVIDER", "trends"),
            "low_volume_floor": int(os.getenv("EN_LOW_FLOOR", "100")),
            "low_volume_ceil": int(os.getenv("EN_LOW_CEIL", "10000")),
            "use_trends_steadiness": b(os.getenv("USE_TRENDS_STEADINESS"), True),
            "naver": naver_block(),
            "google_ads": gads_block("1000", "2840"),   # 영어/미국
        },
    })

cfg = {
    "count_each": int(os.getenv("COUNT_EACH", "5")),
    "llm": {
        "provider": os.getenv("LLM_PROVIDER", "gemini"),
        "api_key": os.getenv("LLM_API_KEY", ""),
        "model": os.getenv("LLM_MODEL", "gemini-2.5-flash"),
    },
    "tracks": tracks,
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
print("config.json 생성 완료: 트랙=%s, wp=%s"
      % ([f"{t['lang']}/{t['trends_geo']}/{t['metrics']['provider']}" for t in tracks],
         cfg["wordpress"]["enabled"]))
