# LensGuide — Visual Search & AR Travel Companion
# Kognivera Hackathon 2026 · PS-06 · Team Reboot Rebels · data model v1.1.0-rc2

Point your camera at a landmark, dish, or foreign-language sign. Get a grounded
info card, nearby places, a sign translation, and a snap-to-book action.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add a Gemini or OpenAI key for live recognition
python run.py
# open http://localhost:8000
```

Works in the browser on Android Chrome (camera via `getUserMedia`).

## Offline demo mode

Open the app, toggle **Offline mode** in the toolbar. Recognition is replaced by
a POI picker; the catalogue is served by the local Flask process from
`data/PS-06.db` with no external AI or internet calls. The local backend must
still be running. This is the bulletproof venue fallback (design risk #1).

## AI provider fallback

The live Identify and Translate routes use the provider selected by
`LLM_PROVIDER`. To survive a quota or transient outage, configure a second
OpenAI-compatible provider in `.env`:

```env
LLM_PROVIDER=gemini
LLM_FALLBACK_PROVIDER=openai
GEMINI_API_KEY=...
# Optional second Gemini model using the same key:
GEMINI_FALLBACK_MODEL=gemini-3.5-flash
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

The backend tries the fallback when the primary provider returns a rate limit,
provider error, or invalid response. If no fallback succeeds, the API returns
HTTP `429` with `quota_exhausted: true` and the provider's retry hint. Set
`LLM_429_RETRIES=0` (the default) to avoid wasting time retrying an exhausted
quota; `LLM_TIMEOUT_SECONDS` controls the provider request timeout.

The web Translate tab exposes exactly three target languages: English (`en-IN`), Kannada (`kn-IN`), and Telugu (`te-IN`). The API rejects other target tags so the UI and model stay aligned.

A health check reports configured providers without spending quota:

```bash
curl http://localhost:8000/api/health
```

## Zero-cost local AI (LM Studio)

For a fully local demo with no API costs, run an OpenAI-compatible server via
LM Studio. The recommended model is **Qwen3.5 4B** (vision-capable, ~3.2 GB):

1. Install LM Studio ≥0.4.25
2. Download `qwen/qwen3.5-4b` (or `qwen/qwen2.5-vl-3b`)
3. Load with 8192 context: `lms load qwen/qwen3.5-4b --context-length=8192 --identifier qwen/qwen3.5-4b:fast -y`
4. Start server: `lms server start --port 1234`
5. Configure `.env`:

```env
LLM_PROVIDER=openai
LLM_FALLBACK_PROVIDER=
OPENAI_BASE_URL=http://127.0.0.1:1234/v1
OPENAI_API_KEY=lm-studio
OPENAI_MODEL=qwen/qwen3.5-4b:fast
OPENAI_RESPONSE_FORMAT=text
OPENAI_DISABLE_THINKING=true
OPENAI_MAX_TOKENS=512
```

**Critical flags:**
- `OPENAI_DISABLE_THINKING=true` — disables Qwen3.5's long reasoning pass, reducing local translation time from minutes to seconds
- `OPENAI_RESPONSE_FORMAT=text` — LM Studio requires `text` (not `json_object`) for chat completions
- `OPENAI_MAX_TOKENS=512` — keeps responses fast; identify uses 1024 internally

After reboot, restart everything:

```bash
./scripts/start_local_ai.sh   # loads model + starts LM Studio server
./serve.sh                    # starts HTTPS (8000) + HTTP (8004) Flask servers
```

## Snap → Identify: Location-aware landmark detection

Open the **Snap** tab, tap **Start camera** (or upload), then **Identify**:

| Scenario | What happens |
|----------|--------------|
| **At a known POI (≤2 km from catalogue)** | Exact catalogue match → grounded info card + nearby from that POI |
| **Near a landmark but >2 km from catalogue** | Local vision model identifies it visually → shows name + `in_catalogue: false` + nearby computed from **your actual GPS** |
| **Anywhere else (signs, menus, unknown)** | OCR + visual identification → shows what the model sees + nearby from **your GPS** |
| **No GPS permission** | Falls back to OCR/sign recognition only |

**Priority order:** device location → visual model → OCR → candidates/refusal.

**API response includes:**
- `identified_place` — {name, poi_category, distance_km, in_catalogue, confidence}
- `matched` — catalogue POI if matched, else `null`
- `nearby` — top 10 landmarks from your device location (or identified place)
- `location` — your device coordinates (if provided)

## Translation (exactly 3 languages)

| Target | Method | Script |
|--------|--------|--------|
| `en-IN` | Direct | Latin |
| `kn-IN` | English pivot | Kannada (ಕನ್ನಡ) |
| `te-IN` | English pivot | Telugu (తెలుగు) |

English pivot ensures script accuracy. Pivot responses marked `"translation_basis": "english_pivot"`.

Exact dataset matches return `"translation_basis": "dataset_reference"`.

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/identify` | Vision-LLM: image (+ optional `lat`/`lng`) → `{identified_place, matched, nearby, ocr_text, ...}` |
| GET | `/api/poi/<poi_id>` | Grounded info card: POI + facts + knowledge chunks |
| GET | `/api/poi/<poi_id>/nearby?mode=walk` | Nearby from precomputed travel matrix |
| POST | `/api/translate` | `{text}` or `{image}` → OCR + translate (3 languages) |
| GET | `/api/poi/<poi_id>/book` | Snap-to-book: hours, cost, accessibility |
| GET | `/api/pois` | Catalogue for offline picker |
| GET | `/api/nearby?lat=...&lng=...` | Nearby POIs from any coordinates |
| GET | `/api/health` | Provider status, cache stats, local AI flag |

## Grounding rules honoured

- Facts come **only** from `poi_facts_kb` / `place_kb`; the LLM never writes facts (design anti-hallucination).
- Money stays a string + ISO-4217; display via `currencies.minor_unit_exponent` (R3).
- Language is BCP-47 (R6), IDs opaque (R2), DB read-only (R1). `PS-06.db` is never mutated.
- Response caching (`.cache/llm_cache.json`) reduces repeated local inference.

## Conformance

```bash
python3 tools/validate_conformance.py data/PS-06.db   # upstream tool, expect PASS
```

## Key files

```
lensguide/
  app.py           # Flask routes: identify, translate, nearby, book, health
  llm.py           # Provider chain, caching, local OpenAI (LM Studio), script validation
  db.py            # Read-only SQLite access to PS-06.db
  static/
    app.js         # Snap, Identify, Translate, Nearby, Browse UI
    index.html     # Web entry
    style.css      # Theme & components
expo-app/          # React Native (Android) – same API, offline mode
scripts/
  start_local_ai.sh   # Load Qwen3.5 4B + start LM Studio server
  serve.sh            # Start HTTPS (8000) + HTTP (8004) servers
tests/
  test_llm_fallback.py  # 11 backend/provider/cache/fallback tests
data/
  PS-06.db            # Read-only catalogue + translations + facts + KB
```