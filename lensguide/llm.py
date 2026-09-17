import base64
import json
import os
import re
from urllib import request, error

from lensguide import db


def provider():
    return os.environ.get("LLM_PROVIDER", "").strip().lower() or "offline"


def _openai_call(messages, json_mode=True):
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    payload = {"model": model, "messages": messages, "temperature": 0}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    req = request.Request(
        f"{base}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    with request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read().decode())
    return body["choices"][0]["message"]["content"]


def _gemini_call(messages):
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    model = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
        f":generateContent?key={key}"
    )
    req = request.Request(
        url,
        data=json.dumps({"contents": [{"parts": messages}]}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read().decode())
    text = body["candidates"][0]["content"]["parts"][0]["text"]
    text = re.sub(r"```(?:json)?", "", text).strip("` \n")
    return text


def _llm(messages):
    p = provider()
    if p == "openai":
        return json.loads(_openai_call(messages))
    if p == "gemini":
        return json.loads(_gemini_call(messages))
    raise RuntimeError(f"No LLM provider configured (got {p!r})")


def image_message(image_b64, mime):
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{mime};base64,{image_b64}"},
    }


def identify_poi(image_b64, mime):
    """Vision-LLM recognition. Returns {kind, label_class, name, confidence, description}.
    kind is one of landmark | food | sign | unknown."""
    class_list = json.dumps(db.LABEL_CLASSES)
    messages = [
        {
            "role": "system",
            "content": (
                "You identify tourist landmarks and POIs from photos for the LensGuide app. "
                "You only produce JSON. If the image shows one of the known classes, set "
                'kind to "landmark"; if it is clearly food, kind="food"; if it contains a '
                'sign, menu, or warning text, kind="sign"; otherwise kind="unknown". '
                f"Known landmark classes:\n{class_list}\n"
                'Return exactly: {"kind": str, "label_class": str, "name": str, '
                '"confidence": "high"|"medium"|"low", "description": str, "text": str or ""}\n'
                "where label_class is one of the listed classes or \"none\", name is the "
                "human-readable POI name or empty, confidence reflects how sure you are, "
                "description is one short sentence, and text is the OCR text if kind==sign.\n"
            ),
        },
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
    messages = [
        {
            "role": "system",
            "content": (
                "You are a translator for a travel app. Translate the given text into the "
                "target language. Keep place names, menu items, and prices exactly as-is. "
                "If the text is a safety warning, keep it prominent and literal. "
                'Return exactly: {"translation": str, "source_language": str, '
                '"confidence": "high"|"medium"|"low"}'
            ),
        },
        {
            "role": "user",
            "content": (
                f"Translate this {source} text to {target}:\\n\\n{text}"
            ),
        },
    ]
    return _llm(messages)


def image_to_b64(file_storage):
    b64 = base64.b64encode(file_storage.read()).decode()
    mime = file_storage.mimetype or "image/jpeg"
    return b64, mime