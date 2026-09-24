import base64
import json
import os
import re
import time
from urllib import request, error

from lensguide import db

# Leave at least this long between LLM calls to stay under free-tier per-minute
# rate limits during demos. Free tier for flash models is ~10-15 req/min,
# so 4.5s spacing (<=13 req/min) keeps us safely under.
_MIN_INTERVAL = 4.5
_last_llm_call = 0.0


def provider():
    return os.environ.get("LLM_PROVIDER", "").strip().lower() or "offline"


def _raw_http(url, payload, headers):
    req = request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **headers},
    )
    try:
        with request.urlopen(req, timeout=90) as resp:
            return json.loads(resp.read().decode())
    except error.HTTPError as e:
        if e.code == 429:
            raise RuntimeError("LLM provider is rate-limited (429). Wait ~1 minute, then retry.")
        raise RuntimeError(f"LLM provider error ({e.code}): {e.reason}")


def _openai_call(messages):
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    payload = {
        "model": model,
        "messages": [
            {"role": m["role"], "content": m["content"]} for m in messages
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    return _raw_http(
        f"{base}/chat/completions",
        payload,
        {"Authorization": f"Bearer {key}"},
    )["choices"][0]["message"]["content"]


def _gemini_call(messages):
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    model = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    parts = []
    for m in messages:
        if isinstance(m["content"], str):
            parts.append({"text": m["content"]})
        else:
            for item in m["content"]:
                if item.get("type") == "text":
                    parts.append({"text": item["text"]})
                elif item.get("type") == "image_url":
                    url = item["image_url"]["url"]  # data:<mime>;base64,<b64>
                    meta, b64 = url.split(",", 1)
                    mime = meta.split(";")[0].split(":")[1]
                    parts.append({"inline_data": {"mime_type": mime, "data": b64}})

    body = _raw_http(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
        f":generateContent?key={key}",
        {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": 0,
                "thinkingConfig": {"thinkingBudget": 0},
            },
        },
        {},
    )
    text = body["candidates"][0]["content"]["parts"][0]["text"]
    text = re.sub(r"```(?:json)?", "", text).strip("` \n")
    return text


def _llm(messages):
    global _last_llm_call
    wait = _MIN_INTERVAL - (time.monotonic() - _last_llm_call)
    if wait > 0:
        time.sleep(wait)
    p = provider()
    if p == "openai":
        out = _openai_call(messages)
    elif p == "gemini":
        out = _gemini_call(messages)
    else:
        raise RuntimeError(f"No LLM provider configured (got {p!r})")
    _last_llm_call = time.monotonic()
    return json.loads(out)


def image_message(image_b64, mime):
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{mime};base64,{image_b64}"},
    }


def identify_poi(image_b64, mime):
    """Vision-LLM recognition. Returns {kind, label_class, name, confidence,
    confidence_score, description, text}.
    kind is one of landmark | food | sign | unknown."""
    class_list = json.dumps(db.LABEL_CLASSES)
    system = (
        "You identify tourist landmarks and POIs from photos for the LensGuide app. "
        "You only produce JSON. If the image shows one of the known classes, set "
        'kind to "landmark"; if it is clearly food, kind="food"; if it contains a '
        'sign, menu, or warning text, kind="sign"; otherwise kind="unknown". '
        f"Known landmark classes:\n{class_list}\n"
        'Return exactly: {"kind": str, "label_class": str, "name": str, '
        '"confidence": "high"|"medium"|"low", "confidence_score": 0.0, '
        '"description": str, "text": str or ""}\n'
        "where label_class is one of the listed classes or \"none\", name is the "
        "human-readable POI name or empty string when unsure, confidence reflects "
        "how sure you are, confidence_score is a single number from 0.0 to 1.0 "
        "reflecting how confident you are in the identification (be honest: a "
        "blurry, ambiguous, or partial view must get a LOW score), description is "
        "one short sentence, and text is the OCR text if kind==sign.\n"
    )
    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What place, dish, or sign is this?"},
                image_message(image_b64, mime),
            ],
        },
    ]
    result = _llm(messages)
    if not isinstance(result, dict):
        raise RuntimeError("LLM returned non-JSON")
    return result


def translate_text(text, source="auto", target="en-IN"):
    """Translate OCR'd text. source is a BCP-47 tag or 'auto'."""
    system = (
        "You are a translator for a travel app. Translate the given text into the "
        "target language. Keep place names, menu items, and prices exactly as-is. "
        "If the text is a safety warning, keep it prominent and literal. "
        'Return exactly: {"translation": str, "source_language": str, '
        '"confidence": "high"|"medium"|"low"}'
    )
    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": f"Translate this {source} text to {target}:\n\n{text}",
        },
    ]
    return _llm(messages)


def image_to_b64(file_storage):
    b64 = base64.b64encode(file_storage.read()).decode()
    mime = file_storage.mimetype or "image/jpeg"
    return b64, mime