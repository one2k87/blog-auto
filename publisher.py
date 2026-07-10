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


def upload_media(image_path, wp_cfg, alt=""):
    """이미지를 WordPress 미디어로 업로드하고 공개 URL을 반환(실패 시 None)."""
    import os
    base_url = wp_cfg["site_url"].rstrip("/")
    headers = _auth_header(wp_cfg["username"], wp_cfg["app_password"])
    fname = os.path.basename(image_path)
    headers["Content-Disposition"] = f'attachment; filename="{fname}"'
    headers["Content-Type"] = "image/png"
    try:
        with open(image_path, "rb") as f:
            r = requests.post(f"{base_url}/wp-json/wp/v2/media",
                              headers=headers, data=f.read(), timeout=60)
        if r.status_code in (200, 201):
            data = r.json()
            mid, url = data.get("id"), data.get("source_url")
            if mid and alt:
                requests.post(f"{base_url}/wp-json/wp/v2/media/{mid}",
                              headers={**_auth_header(wp_cfg["username"], wp_cfg["app_password"]),
                                       "Content-Type": "application/json"},
                              json={"alt_text": alt}, timeout=20)
            return url
        print(f"[wp] 미디어 업로드 실패 {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"[wp] 미디어 업로드 예외: {e}")
    return None


def ensure_category(base_url, headers, name, slug=None):
    """WP 카테고리 이름 → ID(없으면 생성). slug 지정 시 영문 주소(/category/slug/)로 만든다."""
    if not name:
        return None
    try:
        # 슬러그로 먼저 조회(있으면 그대로 사용)
        if slug:
            r = requests.get(f"{base_url}/wp-json/wp/v2/categories",
                             params={"slug": slug}, headers=headers, timeout=20)
            if isinstance(r.json(), list) and r.json():
                return r.json()[0]["id"]
        # 이름으로 조회
        r = requests.get(f"{base_url}/wp-json/wp/v2/categories",
                         params={"search": name}, headers=headers, timeout=20)
        found = next((c for c in r.json() if c.get("name", "").strip() == name.strip()), None)
        if found:
            return found["id"]
        # 생성 (slug 포함)
        payload = {"name": name}
        if slug:
            payload["slug"] = slug
        c = requests.post(f"{base_url}/wp-json/wp/v2/categories",
                          json=payload, headers=headers, timeout=20)
        if c.status_code in (200, 201):
            return c.json()["id"]
    except Exception as e:
        print(f"[wp] 카테고리 처리 실패('{name}'): {e}")
    return None


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
    # 글의 카테고리를 WP 카테고리(영문 슬러그 주소)로 매핑해 나눠 게시
    wp_cat_name = article.get("wp_category") or article.get("category")
    wp_cat_slug = article.get("wp_category_slug")
    cat_id = ensure_category(base_url, headers, wp_cat_name, wp_cat_slug) if wp_cat_name else None
    if cat_id:
        payload["categories"] = [cat_id]
    elif wp_cfg.get("category_id"):
        payload["categories"] = [wp_cfg["category_id"]]

    # Rank Math: 포커스 키프레이즈·메타설명 자동 기입(워드프레스에 mu-plugin 등록 필요)
    rm = {}
    if article.get("focus_keyword"):
        rm["rank_math_focus_keyword"] = article["focus_keyword"]
    if article.get("meta"):
        rm["rank_math_description"] = article["meta"]
    if rm:
        payload["meta"] = rm

    try:
        r = requests.post(f"{base_url}/wp-json/wp/v2/posts",
                          json=payload, headers=headers, timeout=30)
        if r.status_code in (200, 201):
            data = r.json()
            article["post_id"] = data.get("id")     # 나중에 '최신글 링크' 배너용
            print(f"[wp] 게시 성공({payload['status']}): {data.get('link')}")
            return data.get("link")
        print(f"[wp] 게시 실패 {r.status_code}: {r.text[:300]}")
    except Exception as e:
        print(f"[wp] 게시 예외: {e}")
    return None


_BANNER_MARK = "data-updatelink"


def add_update_banner(wp_cfg, post_id, new_url, new_title):
    """예전 글(post_id) 상단에 '최신 업데이트 글' 배너를 추가(중복 시 건너뜀).
    반환: True(추가/이미 있음) / False(실패)."""
    if not post_id or not new_url:
        return False
    base_url = wp_cfg["site_url"].rstrip("/")
    headers = _auth_header(wp_cfg["username"], wp_cfg["app_password"])
    headers["Content-Type"] = "application/json"
    try:
        g = requests.get(f"{base_url}/wp-json/wp/v2/posts/{post_id}?context=edit",
                         headers=headers, timeout=30)
        if g.status_code != 200:
            print(f"[wp] 기존글 조회 실패 {g.status_code}")
            return False
        cur = g.json().get("content", {}).get("raw", "") or ""
        if _BANNER_MARK in cur:
            return True   # 이미 배너 있음
        title = (new_title or "최신 글").replace("<", "").replace(">", "")
        banner = (f'<div {_BANNER_MARK}="1" style="margin:0 0 16px;padding:12px 14px;'
                  f'border:1px solid #7c5cff;border-radius:10px;background:#f6f4ff;font-size:14px">'
                  f'🔄 <b>더 최신 정보</b>가 있습니다 → '
                  f'<a href="{new_url}"><b>{title}</b></a></div>')
        p = requests.post(f"{base_url}/wp-json/wp/v2/posts/{post_id}",
                          json={"content": banner + cur}, headers=headers, timeout=30)
        if p.status_code in (200, 201):
            print(f"[wp] 예전글 #{post_id}에 최신글 링크 배너 추가")
            return True
        print(f"[wp] 배너 추가 실패 {p.status_code}: {p.text[:200]}")
    except Exception as e:
        print(f"[wp] 배너 예외: {e}")
    return False
