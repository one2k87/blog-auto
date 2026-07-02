"""
publisher.py - WordPress REST API로 글을 게시.
인증: 워드프레스 '응용 프로그램 비밀번호(Application Password)' 사용 (사용자 > 프로필에서 발급).
status: "publish"(즉시 게시) 또는 "draft"(임시저장, 검토 후 발행) 선택 가능.
설치: pip install requests
"""

import base64
import requests


def _auth_header(user, app_password):
    token = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def ensure_tags(base_url, headers, tag_names):
    """태그 이름 목록을 태그 ID 목록으로 변환(없으면 생성)."""
    ids = []
    for name in tag_names:
        if not name:
            continue
        try:
            r = requests.get(f"{base_url}/wp-json/wp/v2/tags",
                             params={"search": name}, headers=headers, timeout=20)
            found = next((t for t in r.json() if t.get("name", "").lower() == name.lower()), None)
            if found:
                ids.append(found["id"])
                continue
            c = requests.post(f"{base_url}/wp-json/wp/v2/tags",
                              json={"name": name}, headers=headers, timeout=20)
            if c.status_code in (200, 201):
                ids.append(c.json()["id"])
        except Exception as e:
            print(f"[wp] 태그 처리 실패('{name}'): {e}")
    return ids


def publish_to_wordpress(article, wp_cfg):
    """
    article: generator가 만든 dict
    wp_cfg: {site_url, username, app_password, status, category_id(optional)}
    반환: 게시된 글 URL 또는 None
    """
    base_url = wp_cfg["site_url"].rstrip("/")
    headers = _auth_header(wp_cfg["username"], wp_cfg["app_password"])
    headers["Content-Type"] = "application/json"

    tag_ids = ensure_tags(base_url, headers, article.get("tags", []))

    payload = {
        "title": article["title"],
        "content": article["html"],
        "status": wp_cfg.get("status", "draft"),   # 기본 draft = 안전
        "excerpt": article.get("meta", ""),         # 메타 설명(검색 스니펫)
    }
    if article.get("slug"):
        payload["slug"] = article["slug"]           # SEO 친화 URL
    if tag_ids:
        payload["tags"] = tag_ids
    if wp_cfg.get("category_id"):
        payload["categories"] = [wp_cfg["category_id"]]

    try:
        r = requests.post(f"{base_url}/wp-json/wp/v2/posts",
                          json=payload, headers=headers, timeout=30)
        if r.status_code in (200, 201):
            data = r.json()
            print(f"[wp] 게시 성공({payload['status']}): {data.get('link')}")
            return data.get("link")
        print(f"[wp] 게시 실패 {r.status_code}: {r.text[:300]}")
    except Exception as e:
        print(f"[wp] 게시 예외: {e}")
    return None
