import base64
import json
import os
import re
import sqlite3
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


def _retry_after(e):
    """Seconds to wait before retrying a 429, taken from the provider's response."""
    try:
        body = e.read().decode()
    except Exception:
        body = ""
    m = re.search(r"retry in\s+([\d.]+)\s*s", body, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1)) + 1.0
        except ValueError:
            pass
    m = re.search(r"retry[- ]after\s*[:=]?\s*(\d+)", body, re.IGNORECASE)
    if m:
        return float(m.group(1))
    if e.headers and e.headers.get("Retry-After"):
        try:
            return float(e.headers.get("Retry-After"))
        except ValueError:
            pass
    return None


def _raw_http(url, payload, headers, max_retries=1):
    # One short retry on 429: recovers from a transient quota blip without
    # hanging the request for minutes; if the bucket is exhausted it's
    # exhausted, so fail fast and let the user retry.
    retries = 0
    while True:
        req = request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", **headers},
        )
        try:
            with request.urlopen(req, timeout=90) as resp:
                return json.loads(resp.read().decode())
        except error.HTTPError as e:
            if e.code == 429 and retries < max_retries:
                delay = min(_retry_after(e) or 8.0, 8.0)
                retries += 1
                time.sleep(delay)
                continue
            if e.code == 429:
                raise RuntimeError(
                    "The translation service is rate-limited. Wait a few seconds, then press Translate again."
                )
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


def _is_noise(image_b64):
    """True when the image has no spatial coherence (random noise / solid fill),
    so the LLM cannot recognise a real subject."""
    try:
        from PIL import Image
        import io, statistics
        data = base64.b64decode(image_b64)
        im = Image.open(io.BytesIO(data)).convert("RGB").resize((64, 64))
        px = list(im.getdata())
        changed = 0
        total = 0
        for i in range(64):
            for j in range(64):
                here = px[i * 64 + j]
                if j + 1 < 64:
                    right = px[i * 64 + j + 1]
                    if any(abs(a - b) > 35 for a, b in zip(here, right)):
                        changed += 1
                    total += 1
                if i + 1 < 64:
                    down = px[(i + 1) * 64 + j]
                    if any(abs(a - b) > 35 for a, b in zip(here, down)):
                        changed += 1
                    total += 1
        return (changed / max(total, 1)) > 0.30
    except Exception:
        return True


def _mock_poi_name(image_b64):
    """Deterministic POI pick from the DB, indexed by the image hash."""
    conn = db.connect()
    conn.row_factory = sqlite3.Row
    names = [r[0] for r in conn.execute(
        "SELECT name FROM activities_poi WHERE status='active'"
    ).fetchall()]
    conn.close()
    if not names:
        return "Unknown Landmark"
    h = abs(hash(image_b64[:48]))
    return names[h % len(names)]


def _mock_llm(messages):
    """Deterministic, offline-capable stand-in for the LLM.
    Real photo -> recognised (score 0.92, above the 0.85 gate).
    Noise/solid fill -> not_recognised (score 0.05, honest refusal)."""
    # Pick the last user message. Its content may be a plain string or a list.
    user_content = None
    for m in reversed(messages):
        if m.get("role") == "user":
            user_content = m.get("content")
            break
    if user_content is None:
        return json.dumps({"kind": "unknown", "label_class": "none", "name": "",
                           "confidence": "low", "confidence_score": 0.05,
                           "description": "No user message.", "text": ""})
    if isinstance(user_content, list):
        # Identify path: [{"type":"text",...}, {"type":"image_url",...}]
        text_parts = []
        b64 = ""
        for c in user_content:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "text":
                text_parts.append(c.get("text", ""))
            elif c.get("type") == "image_url":
                b64 = c["image_url"]["url"].split(",", 1)[-1]
        user = " ".join(text_parts)
    else:
        user = user_content

    if "What place, dish, or sign is this?" in user:
        if _is_noise(b64):
            return json.dumps({
                "kind": "unknown", "label_class": "none", "name": "",
                "confidence": "low", "confidence_score": 0.05,
                "description": "The image contains no recognisable subject.",
                "text": "",
            })
        return json.dumps({
            "kind": "landmark", "label_class": "heritage",
            "name": _mock_poi_name(b64),
            "confidence": "high", "confidence_score": 0.92,
            "description": "A recognisable tourist landmark.",
            "text": "",
        })

    # translate_text path. Content is "Translate this {src} text to {target}:\n\n{text}".
    text = user.split("Translate this", 1)[-1].split("\n\n", 1)[-1].strip()
    return json.dumps({
        "translation": text, "source_language": "auto",
        "confidence": "high",
    })


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
    elif p == "mock":
        out = _mock_llm(messages)
    else:
        raise RuntimeError(f"No LLM provider configured (got {p!r})")
    _last_llm_call = time.monotonic()
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        # Truncated or malformed response from the provider (common right
        # before a quota cap). Retry once; if it still fails, give the user
        # a clear message instead of an opaque parse error.
        time.sleep(2)
        if p == "openai":
            out = _openai_call(messages)
        elif p == "gemini":
            out = _gemini_call(messages)
        try:
            return json.loads(out)
        except json.JSONDecodeError:
            raise RuntimeError(
                "The AI returned an unreadable response. Please press the button again."
            )


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