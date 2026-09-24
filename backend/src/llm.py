import base64
import json
import os
import re
import sqlite3
import time
from urllib import request, error

from backend.src import db


class LLMError(Exception):
    """Structured LLM error with provider context."""
    def __init__(self, message, status=503, provider=None, code=None, retry_after=None):
        super().__init__(message)
        self.status = status
        self.provider = provider
        self.code = code
        self.retry_after = retry_after

# Leave at least this long between LLM calls to stay under free-tier per-minute
# rate limits during demos. Free tier for flash models is ~10-15 req/min,
# so 4.5s spacing (<=13 req/min) keeps us safely under.
_MIN_INTERVAL = 4.5
_last_llm_call = 0.0


def provider():
    return os.environ.get("LLM_PROVIDER", "").strip().lower() or "offline"


def fallback_provider():
    return os.environ.get("LLM_FALLBACK_PROVIDER", "").strip().lower() or ""


def configured_providers():
    result = []
    for name in ("openai", "gemini", "mock"):
        if _provider_configured(name):
            result.append(name)
    return result


def _provider_configured(name):
    if name == "openai":
        return bool(os.environ.get("OPENAI_API_KEY", "").strip())
    if name == "gemini":
        return bool(os.environ.get("GEMINI_API_KEY", "").strip())
    if name == "mock":
        return True
    return False


def ai_configured():
    return any(_provider_configured(p) for p in ("openai", "gemini"))


def is_local_openai():
    base = os.environ.get("OPENAI_BASE_URL", "").strip()
    return base.startswith("http://127.0.0.1") or base.startswith("http://localhost")


def _env_flag(name):
    val = os.environ.get(name, "").strip().lower()
    return val in ("1", "true", "yes", "on")


def _env_int(name, default):
    try:
        return int(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default


def cache_stats():
    return {"enabled": False, "entries": 0}


# --- Provider chain & fallback ------------------------------------------------

def provider_chain():
    """Return ordered list of providers to try (primary then fallback)."""
    primary = provider()
    fallback = fallback_provider()
    chain = [primary]
    if fallback and fallback != primary:
        chain.append(fallback)
    return chain


# --- Response caching ---------------------------------------------------------

_CACHE = {}


def _cache_key(messages):
    """Generate a hashable key from messages for caching."""
    import hashlib
    content = json.dumps(messages, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()


def cache_get(messages):
    return _CACHE.get(_cache_key(messages))


def cache_put(messages, result):
    _CACHE[_cache_key(messages)] = result


def cache_stats():
    return {"enabled": True, "entries": len(_CACHE)}


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


def _raw_http(url, payload, headers, max_retries=1, max_503_retries=2, provider_name="unknown"):
    # Short retries: one on 429 (transient quota blip) and up to two on 5xx
    # (Google occasionally returns 503s in bursts). Fail fast on persistent
    # quota exhaustion so the user gets a clear message instead of a hang.
    retries = 0
    retries_503 = 0
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
                raise LLMError(
                    "The translation service is rate-limited. Wait a few seconds, then press Translate again.",
                    status=429,
                    provider=provider_name,
                    code="rate_limited",
                )
            if e.code >= 500 and retries_503 < max_503_retries:
                retries_503 += 1
                time.sleep(2 * retries_503)  # 2s, then 4s
                continue
            raise LLMError(
                f"LLM provider error ({e.code}): {e.reason}",
                status=e.code,
                provider=provider_name,
                code="provider_error",
            )
        except Exception as e:
            raise LLMError(
                f"LLM provider unreachable: {e}",
                status=503,
                provider=provider_name,
                code="provider_unreachable",
            )


def _openai_call(messages):
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    if not key:
        raise LLMError("OPENAI_API_KEY is not set", provider="openai", code="not_configured")
    payload = {
        "model": model,
        "messages": [
            {"role": m["role"], "content": m["content"]} for m in messages
        ],
        "temperature": 0,
    }
    # Local OpenAI-compatible servers (LM Studio, vLLM, etc.) often don't support
    # response_format=json_object. Use text mode and rely on prompt engineering.
    response_format = os.environ.get("OPENAI_RESPONSE_FORMAT", "json_object").strip().lower()
    if response_format not in ("", "none", "text"):
        payload["response_format"] = {"type": response_format}
    max_tokens = _env_int("OPENAI_MAX_TOKENS", 0)
    if max_tokens > 0:
        payload["max_tokens"] = max_tokens
    if _env_flag("OPENAI_DISABLE_THINKING"):
        payload["chat_template_kwargs"] = {"enable_thinking": False}
        payload["enable_thinking"] = False
        payload["reasoning_effort"] = "none"
    try:
        return _raw_http(
            f"{base}/chat/completions",
            payload,
            {"Authorization": f"Bearer {key}"},
            provider_name="openai",
        )["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise LLMError(
            "OpenAI returned an unexpected response.",
            status=503,
            provider="openai",
            code="invalid_response",
        )


def _gemini_call(messages):
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    model = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
    if not key:
        raise LLMError("GEMINI_API_KEY is not set", provider="gemini", code="not_configured")

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
        provider_name="gemini",
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
    """Call the primary provider, then an optional configured fallback.

    A quota/rate-limit failure is returned as a structured 429 only when no
    usable fallback can complete the request. This keeps a Gemini quota
    problem from taking down the whole app when another provider is available.
    """
    global _last_llm_call
    errors = []
    chain = provider_chain()
    for index, name in enumerate(chain):
        if name == "offline":
            continue
        if not _provider_configured(name):
            errors.append(
                LLMError(
                    f"{name} is selected but its API key is not configured.",
                    status=503,
                    provider=name,
                    code="not_configured",
                )
            )
            continue
        # Check cache first
        cached = cache_get(messages)
        if cached is not None:
            if index:
                print(f"LLM fallback cache hit via {name}")
            return cached
        try:
            wait = _MIN_INTERVAL - (time.monotonic() - _last_llm_call)
            if wait > 0:
                time.sleep(wait)
            if name == "openai":
                out = _openai_call(messages)
            elif name == "gemini":
                out = _gemini_call(messages)
            elif name == "mock":
                out = _mock_llm(messages)
            else:
                raise LLMError(
                    f"Unsupported LLM provider {name!r}.",
                    status=503,
                    provider=name,
                    code="not_configured",
                )
            # Strip code blocks if present
            out = out.strip()
            if out.startswith("```"):
                out = out.strip("` \n")
                if out.startswith("json"):
                    out = out[4:].strip()
            result = json.loads(out)
            cache_put(messages, result)
            _last_llm_call = time.monotonic()
            if index:
                print(f"LLM fallback succeeded via {name}")
            return result
        except LLMError as exc:
            exc.provider = name
            errors.append(exc)
            # If it's a rate limit (429), try fallback
            if exc.status == 429 and index < len(chain) - 1:
                continue
            # If it's a provider error (5xx), try fallback
            if exc.status >= 500 and index < len(chain) - 1:
                continue
            # Other errors - don't fallback
            raise
    # All providers exhausted
    if errors:
        # Return the last error if all failed
        raise errors[-1]
    raise LLMError(
        "No LLM provider available.",
        status=503,
        code="no_provider",
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
    system = (
        "You identify tourist landmarks and POIs from photos for the LensGuide app. "
        "You only produce JSON. If the image shows a landmark, set kind to \"landmark\"; "
        "if it is clearly food, kind=\"food\"; if it contains a sign, menu, or warning text, kind=\"sign\"; otherwise kind=\"unknown\". "
        'Return exactly: {"kind": str, "label_class": str, "name": str, '
        '"confidence": "high"|"medium"|"low", "confidence_score": 0.0, '
        '"description": str, "text": str or "", "source_language": str or "auto"}\n'
        "where label_class is one of the listed classes or \"none\", name is the "
        "human-readable POI name or empty string when unsure, confidence reflects "
        "how sure you are, confidence_score is a single number from 0.0 to 1.0 "
        "reflecting how confident you are in the identification (be honest: a "
        "blurry, ambiguous, or partial view must get a LOW score), description is "
        "one short sentence, text is the OCR text if kind==sign, and "
        "source_language is a BCP-47 tag (e.g., \"kn\", \"te\", \"en\", \"hi\") when the script is clear, or \"auto\".\n\n"
        "IMPORTANT for OCR: Extract text EXACTLY as it appears. Read carefully — "
        "this may be a screenshot of search results, a sign, or a menu. "
        "If you see Kannada (ಕನ್ನಡ), Telugu (తెలుగు), Devanagari (हिंदी), or Latin script, "
        "transcribe it faithfully. Do not guess or hallucinate."
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


_TARGET_LANGUAGE_NAMES = {
    "en-IN": "English (India)",
    "kn-IN": "Kannada (ಕನ್ನಡ)",
    "te-IN": "Telugu (తెలుగు)",
}

# Unicode blocks used by the source languages in the bundled dataset plus
# Latin. A target response containing letters from any of these other scripts
# is not considered a valid translation, even if it also contains one target
# character. Digits, punctuation, currency signs, and whitespace are allowed.
_SCRIPT_RANGES = {
    "Latin": ((0x0041, 0x005A), (0x0061, 0x007A), (0x00C0, 0x024F)),
    "Bengali": ((0x0980, 0x09FF),),
    "Devanagari": ((0x0900, 0x097F),),
    "Kannada": ((0x0C80, 0x0CFF),),
    "Malayalam": ((0x0D00, 0x0D7F),),
    "Gurmukhi": ((0x0A00, 0x0A7F),),
    "Tamil": ((0x0B80, 0x0BFF),),
    "Telugu": ((0x0C00, 0x0C7F),),
}


def _has_script(text, script):
    return any(
        any(start <= ord(char) <= end for start, end in _SCRIPT_RANGES.get(script, ()))
        for char in (text or "")
    )


def _target_script_valid(text, target):
    text = text or ""
    if not text.strip():
        return False
    if target == "kn-IN":
        target_script = "Kannada"
    elif target == "te-IN":
        target_script = "Telugu"
    else:
        return True
    if not _has_script(text, target_script):
        return False
    forbidden = set(_SCRIPT_RANGES) - {target_script, "Latin"}
    return not any(_has_script(text, script) for script in forbidden)


def translate_text(text, source="auto", target="en-IN"):
    """Translate OCR'd text. source is a BCP-47 tag or 'auto'."""
    target_name = _TARGET_LANGUAGE_NAMES.get(target, target)
    source_name = _TARGET_LANGUAGE_NAMES.get(source, source)
    system = (
        "You are a translator for a travel app. Translate the given text into the "
        "target language. Keep place names, menu items, and prices exactly as-is. "
        "If the text is a safety warning, keep it prominent and literal. "
        "The translation MUST be in the target language's native script. "
        "The input text may contain OCR errors — translate the MEANING, not the noise. "
        "If the text is garbled/unclear, produce the best English translation of what it likely says. "
        'Return exactly: {"translation": str, "source_language": str, '
        '"confidence": "high"|"medium"|"low"}'
    )
    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": f"Translate this {source_name} text to {target_name}:\n\n{text}",
        },
    ]
    # Try up to 2 times with script validation
    for attempt in range(2):
        result = _llm(messages)
        if not isinstance(result, dict):
            continue
        translation = result.get("translation", "")
        if _target_script_valid(translation, target):
            return result
        # Retry with stricter prompt
        if attempt == 0:
            messages[0]["content"] += (
                f"\n\nIMPORTANT: The translation MUST be in {target_name} script only. "
                f"Do NOT use any other script (especially not Kannada for Telugu or vice versa)."
            )
    return result


def image_to_b64(file_storage):
    from PIL import Image
    from io import BytesIO
    data = file_storage.read()
    im = Image.open(BytesIO(data))
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGB")
    # Resize to max 768px to fit context window
    if max(im.width, im.height) > 768:
        im.thumbnail((768, 768), Image.LANCZOS)
    out = BytesIO()
    im.save(out, format="JPEG", quality=85, optimize=True)
    b64 = base64.b64encode(out.getvalue()).decode()
    return b64, "image/jpeg"