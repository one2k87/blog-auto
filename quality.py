"""
quality.py - 발행 전 자동 품질 게이트 (애드센스 '대량 저품질' 위험 완화).
- 최소 분량, 소제목 구조, 키워드 과다반복(스터핑), 다른 글과의 유사도(중복) 검사.
- 기준 미달이면 발행 보류(초안 유지) 대상으로 표시한다.
"""

import re


def _text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


def _words(t):
    return re.findall(r"[가-힣A-Za-z0-9]+", t or "")


def _shingles(words, n=3):
    return set(tuple(words[i:i + n]) for i in range(max(0, len(words) - n + 1)))


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def check(article, other_texts, safety):
    """(ok: bool, reason: str) 반환."""
    safety = safety or {}
    html = article.get("html", "")
    t = _text(html)
    words = _words(t)
    reasons = []

    min_chars = int(safety.get("min_chars", 700))
    if len(t) < min_chars:
        reasons.append(f"분량부족({len(t)}자<{min_chars})")

    if html.count("<h2") < int(safety.get("min_h2", 3)):
        reasons.append("소제목부족(H2<3)")

    # 키워드 스터핑
    fk = (article.get("focus_keyword") or "").strip()
    if fk and words:
        cnt = t.count(fk)
        density = cnt / max(1, len(words))
        if cnt >= int(safety.get("stuffing_count", 8)) and density > float(safety.get("max_keyword_density", 0.03)):
            reasons.append(f"키워드과다반복({cnt}회)")

    # 다른 글과 유사도(중복)
    sh = _shingles(words)
    thr = float(safety.get("max_similarity", 0.5))
    for ot in other_texts or []:
        if jaccard(sh, _shingles(_words(_text(ot)))) > thr:
            reasons.append("기존글과유사(중복위험)")
            break

    return (len(reasons) == 0, "; ".join(reasons))
