"""
images.py - 글에 들어갈 이미지를 '자동 생성'.

제공자(config.images.provider):
  - "openai" : OpenAI 이미지(gpt-image-1). OPENAI 키 필요.
  - "gemini" : Google Imagen. Gemini 키(이미지 모델 권한) 필요.
  - "none"   : 생성 안 함 → generator가 자리 표시(placeholder)로 대체.

생성된 PNG는 out_dir에 저장하고, 상황에 맞게:
  - WordPress 게시 시: 미디어로 업로드해 URL 사용(publisher.upload_media)
  - 그 외: base64 data URI로 본문에 인라인 삽입(복붙/미리보기에서 바로 보임)
실패해도 파이프라인이 멈추지 않도록 항상 안전하게 None을 반환한다.
"""

import os
import time
import base64


def build_prompt(desc, category, style):
    style = style or "clean modern flat vector illustration, soft professional colors, minimal text, no watermark"
    return f"{style}. Topic: {category} 블로그용 이미지 - {desc}"


def generate_image(desc, cfg_images, out_dir, idx=0, category=""):
    """desc(한국어 설명)로 이미지 1장 생성 → 저장 경로 반환(실패 시 None)."""
    provider = (cfg_images or {}).get("provider", "none")
    if provider in ("none", None, ""):
        return None
    size = cfg_images.get("size", "1024x1024")
    prompt = build_prompt(desc, category, cfg_images.get("style"))

    data = None
    if provider == "openai":
        data = _openai(prompt, cfg_images, size)
    elif provider in ("gemini", "imagen", "google"):
        data = _gemini(prompt, cfg_images)
    if not data:
        return None

    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"img_{int(time.time()*1000)}_{idx}.png")
    with open(path, "wb") as f:
        f.write(data)
    return path


def to_data_uri(path):
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def figure_html(src, alt):
    a = (alt or "").replace('"', "'")
    return (f'<figure style="margin:22px 0;text-align:center">'
            f'<img src="{src}" alt="{a}" loading="lazy" '
            f'style="max-width:100%;height:auto;border-radius:10px">'
            f'<figcaption style="font-size:13px;color:#98a2b3;margin-top:6px">{a}</figcaption>'
            f'</figure>')


def _openai(prompt, cfg, size):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=cfg.get("api_key") or os.getenv("OPENAI_API_KEY"))
        r = client.images.generate(model=cfg.get("model", "gpt-image-1"),
                                    prompt=prompt, size=size, n=1)
        return base64.b64decode(r.data[0].b64_json)
    except Exception as e:
        print(f"[images] openai 생성 실패: {e}")
        return None


def _gemini(prompt, cfg):
    try:
        import google.generativeai as genai
        genai.configure(api_key=cfg.get("api_key"))
        model = genai.ImageGenerationModel(cfg.get("model", "imagen-3.0-generate-001"))
        res = model.generate_images(prompt=prompt, number_of_images=1)
        img = res.images[0]
        # 라이브러리 버전에 따라 바이트 접근 경로가 다를 수 있어 방어적으로 처리
        for attr in ("_image_bytes", "image_bytes"):
            b = getattr(img, attr, None)
            if b:
                return b
        if hasattr(img, "_pil_image"):
            import io
            buf = io.BytesIO()
            img._pil_image.save(buf, format="PNG")
            return buf.getvalue()
    except Exception as e:
        print(f"[images] gemini(imagen) 생성 실패: {e}")
    return None
