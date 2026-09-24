# Architecture — LensGuide

## Component Diagram

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   Frontend      │       │   Backend       │       │   AI/LLM        │
│  (Web / Expo)   │◄─────►│  (Flask)        │◄─────►│  (LM Studio /   │
│                 │       │                 │       │   Gemini /      │
│  - Snap/Upload  │       │  - /api/identify│       │   Mock)         │
│  - Identify     │       │  - /api/translate    │       │                 │
│  - Translate    │       │  - /api/nearby   │       │  - Qwen3.5 4B   │
│  - Nearby       │       │  - /api/poi/*    │       │  - Prompts      │
│  - Browse/Book  │       │  - /api/health   │       │  - Cache        │
└─────────────────┘       └────────┬────────┘       └─────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
           ┌─────────────────┐           ┌─────────────────┐
           │  Read-only DB   │           │  File Cache     │
           │  (PS-06.db)     │           │  (.cache/)      │
           │  - POI catalogue│           │  - LLM responses│
           │  - Facts/KB     │           │  - Translations │
           │  - Travel matrix│           │                 │
           └─────────────────┘           └─────────────────┘
```

## Data Flow

### 1. Snap → Identify
```
User opens Snap tab
    │
    ▼
Browser requests GPS (getCurrentPosition)
    │
    ▼
User snaps/upload image → taps "Identify"
    │
    ▼
POST /api/identify {image, lat, lng}
    │
    ▼
Backend: identify_poi(image) → LLM (vision)
    │
    ├─► If lat/lng provided & nearest POI ≤2km → location_match (catalogue)
    ├─► If lat/lng provided & nearest POI >2km → visual_identification (LLM name)
    └─► If no lat/lng → OCR/sign recognition
    │
    ▼
Return {identified_place, matched, nearby[], ocr_text}
    │
    ▼
Frontend renders: identified place + nearby landmarks (click → browse)
```

### 2. Translate
```
POST /api/translate {image, target}
    │
    ▼
Backend: identify_poi → OCR text
    │
    ▼
If target ∈ {kn-IN, te-IN}: pivot via English
    │
    ▼
LLM translate (with script validation)
    │
    ▼
Return {translation, source_language, basis}
```

## AI Pipeline (ai/pipeline/llm.py)

| Feature | Model | Grounding |
|---------|-------|-----------|
| Identify (vision) | Qwen3.5 4B (LM Studio) | Returns JSON only; no hallucination |
| Translate | Qwen3.5 4B / Gemini | English pivot for kn-IN/te-IN; script validation |
| Cache | In-memory + JSON file | Keyed by messages hash |

**Local LM Studio config:**
- Model: `qwen/qwen3.5-4b:fast`
- Context: 8192
- Flags: `OPENAI_DISABLE_THINKING=true`, `OPENAI_RESPONSE_FORMAT=text`

## Frontend (frontend/src/)

- `app.js` — All tabs (Snap, Browse, Translate, Nearby, AR)
- `index.html` — SPA entry
- `style.css` — Theme, components, responsive

## Backend (backend/src/)

| Module | Responsibility |
|--------|----------------|
| `app.py` | Flask routes: identify, translate, nearby, poi, book, health |
| `llm.py` | Provider chain (openai/gemini/mock), caching, prompts, script validation |
| `db.py` | Read-only SQLite access to PS-06.db |

## Data Layer

- **Source**: `data/PS-06.db` (read-only)
- **Canonical tables**: D1–D9 per PS-06 spec
- **Extensions**: `poi_facts_kb`, `place_kb`, `poi_travel_matrix`, `poi_media`
- **Seed**: CSVs in `data-model/seed/`

## Deployment

| Service | Port | Purpose |
|---------|------|---------|
| HTTPS (web) | 8000 | Browser / WebXR |
| HTTP (Expo) | 8004 | React Native app (no TLS) |
| LM Studio | 1234 | Local OpenAI-compatible API |

Start: `./scripts/start_local_ai.sh && ./serve.sh`
