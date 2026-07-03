"""
llm.py - 여러 LLM 제공자를 하나의 인터페이스로 호출.
config.json 의 "llm" 설정에 따라 OpenAI / Anthropic / Gemini 중 선택.
설치: pip install openai  또는  anthropic  또는  google-generativeai
"""


import time

# 분당 호출 제한(429/quota) 등 '일시적' 오류일 때 재시도
_RETRYABLE = ("rate", "429", "quota", "exhaust", "resource", "unavailable",
              "overloaded", "timeout", "deadline", "503", "500")


def chat(prompt, cfg, system=None, max_tokens=4000, temperature=0.7, retries=3):
    provider = cfg.get("provider", "openai").lower()

    def call():
        if provider == "openai":
            return _openai(prompt, cfg, system, max_tokens, temperature)
        if provider == "anthropic":
            return _anthropic(prompt, cfg, system, max_tokens, temperature)
        if provider in ("gemini", "google"):
            return _gemini(prompt, cfg, system, max_tokens, temperature)
        raise ValueError(f"알 수 없는 LLM provider: {provider}")

    last = None
    for attempt in range(retries):
        try:
            return call()
        except Exception as e:
            last = e
            if attempt < retries - 1 and any(k in str(e).lower() for k in _RETRYABLE):
                wait = 2 * (attempt + 1)      # 2s, 4s 백오프 (분당 제한 회피)
                print(f"[llm] 일시적 오류, {wait}s 후 재시도({attempt+1}): {str(e)[:80]}")
                time.sleep(wait)
                continue
            raise
    raise last


def _openai(prompt, cfg, system, max_tokens, temperature):
    from openai import OpenAI
    client = OpenAI(api_key=cfg["api_key"])
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = client.chat.completions.create(
        model=cfg.get("model", "gpt-4o-mini"),
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return resp.choices[0].message.content


def _anthropic(prompt, cfg, system, max_tokens, temperature):
    import anthropic
    client = anthropic.Anthropic(api_key=cfg["api_key"])
    resp = client.messages.create(
        model=cfg.get("model", "claude-3-5-sonnet-20241022"),
        max_tokens=max_tokens,
        temperature=temperature,
        system=system or "",
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def _gemini(prompt, cfg, system, max_tokens, temperature):
    import google.generativeai as genai
    genai.configure(api_key=cfg["api_key"])
    model = genai.GenerativeModel(
        cfg.get("model", "gemini-1.5-flash"),
        system_instruction=system or None,
    )
    resp = model.generate_content(
        prompt,
        generation_config={"max_output_tokens": max_tokens, "temperature": temperature},
    )
    return resp.text
