"""
build_config.py - 환경변수(또는 GitHub Actions 시크릿)에서 config.json 을 생성.
로컬 실행 시에는 그냥 config.json 을 직접 만들어도 됩니다(이 파일은 클라우드 자동화용).
"""
import os, json

def b(v, default=False):
    if v is None: return default
    return str(v).lower() in ("1", "true", "yes", "on")

cfg = {
    "count_each": int(os.getenv("COUNT_EACH", "5")),
    "trends_geo": os.getenv("TRENDS_GEO", "KR"),
    "languages": [s.strip() for s in os.getenv("LANGS", "ko,en").split(",") if s.strip()],
    "llm": {
        "provider": os.getenv("LLM_PROVIDER", "openai"),
        "api_key": os.getenv("LLM_API_KEY", ""),
        "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
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
print("config.json 생성 완료 (provider=%s, langs=%s, wp=%s)"
      % (cfg["llm"]["provider"], cfg["languages"], cfg["wordpress"]["enabled"]))
