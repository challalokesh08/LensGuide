# Team Reboot Rebels — KogniVera Hackathon 2026

**Problem Statement:** LensGuide — Visual Search & AR Travel Companion (PS-06)  
**College:** Cambridge Institute of Technology

---

## What We Built (MVP Checklist)

- ✅ **Snap → Identify**: Camera/upload → landmark/dish/sign recognition with location-aware matching
- ✅ **Visual Search**: Local vision model (Qwen3.5 4B via LM Studio) identifies places from photos
- ✅ **Location-Aware Results**: Device GPS + catalogue → nearest POI (≤2km) or visual fallback (>2km)
- ✅ **Nearby Landmarks**: Haversine distance from actual device location (not catalogue centroid)
- ✅ **Translate (3 languages)**: English (en-IN), Kannada (kn-IN), Telugu (te-IN) with script validation
- ✅ **Grounded Info Cards**: POI facts from `poi_facts_kb`, knowledge from `place_kb`
- ✅ **Snap-to-Book**: Hours, cost (currency-exponent-aware), accessibility
- ✅ **Offline Demo Mode**: POI picker works without AI keys
- ✅ **Local-First AI**: LM Studio (Qwen3.5 4B) runs entirely on-device; no paid APIs required

---

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Frontend   │────►│  Backend    │────►│   AI/LLM    │
│  (Web/Expo) │     │  (Flask)    │     │  (Local)    │
└─────────────┘     └──────┬──────┘     └──────┬──────┘
                           │                   │
                    ┌──────┴──────┐    ┌───────┴───────┐
                    ▼             ▼    ▼               ▼
             ┌───────────┐ ┌───────────┐ ┌─────────────────┐
             │ Read-only │ │ File Cache│ │ LM Studio       │
             │  PS-06.db │ │ (.cache/) │ │ Qwen3.5 4B      │
             └───────────┘ └───────────┘ └─────────────────┘
```

**Data Flow — Snap → Identify:**
1. User opens Snap → browser requests GPS
2. Snap photo → POST `/api/identify` with `image`, `lat`, `lng`
3. Backend: vision-LLM → nearest catalogue POI (≤2km = location_match)
4. If >2km → LLM visual ID (`in_catalogue: false`) + nearby from **device GPS**
4. Frontend renders identified place + nearby landmarks (click → Browse)

---

## Data Model

### Canonical Tables Used (D1–D9)

| ID | Table | Purpose |
|----|-------|---------|
| D1 | `categories` | POI categories |
| D2 | `currencies` | ISO-4217 with `minor_unit_exponent` |
| D3 | `languages` | BCP-47 tags (en-IN, kn-IN, te-IN) |
| D4 | `countries` | ISO-3166 |
| D5 | `cities` | Cities + primary_language FK |
| D6 | `menu_sign_images` | OCR reference + translations |
| D7 | `xr_scenes` | AR/WebXR metadata |
| D8 | `activities_poi` | Main POI catalogue |
| D9 | `landmark_image_set` | Landmark images |

### Extensions (PS-06)

| Table | FK | Purpose |
|-------|----|---------|
| `poi_facts_kb` | `activities_poi.poi_id` | Grounded facts (confidence: high/medium/low) |
| `place_kb` | `activities_poi.poi_id` | Knowledge chunks (title + body) |
| `poi_travel_matrix` | `from_poi_id`, `to_poi_id` | Precomputed walk/auto/taxi travel |
| `poi_media` | `activities_poi.poi_id` | Media assets |

**Schema**: `data-model/schema.sql` | **Seeds**: `data-model/seed/*.csv` | **Mapping**: `data-model/DATA_MODEL.md`

---

## AI Features

| Feature | Model | Mechanism | Grounding |
|---------|-------|-----------|-----------|
| **Identify (vision)** | Qwen3.5 4B (LM Studio) | JSON-only prompt + `enable_thinking=false` | Returns only structured JSON; no free text |
| **Translate** | Qwen3.5 4B / Gemini | English pivot for kn-IN/te-IN | Script validation (Kannada/Telugu Unicode blocks) |
| **Cache** | In-memory + JSON file | SHA-256 of messages | Shared across HTTPS/HTTP servers |

**Prompts**: `ai/prompts/identify.md`, `ai/prompts/translate.md`  
**Pipeline**: `ai/pipeline/llm.py` (provider chain, caching, script validation)

---

## Run Locally

```bash
# 1. Python env
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt

# 2. Local AI (LM Studio) — one-time setup
#   Install LM Studio ≥0.4.25
#   Download qwen/qwen3.5-4b
#   lms load qwen/qwen3.5-4b --context-length=8192 --identifier qwen/qwen3.5-4b:fast -y
#   lms server start --port 1234

# 3. Env
cp .env.example .env
# Edit .env for your setup (see .env.example)

# 4. Start everything
./scripts/start_local_ai.sh   # loads model + starts LM Studio server
./serve.sh                    # starts HTTPS :8000 + HTTP :8004

# 5. Open
# Web:  https://localhost:8000  (or https://<LAN-IP>:8000)
# App:  http://localhost:8004   (Expo/React Native)
```

**`.env.example`** contains all required vars with dummy values.

---

## Demo Path (Terminal MVP Outcome)

1. **Open** https://localhost:8000 (or LAN IP) in Chrome/Android
2. **Tap "Snap" tab** → "Start camera" (or Upload photo)
3. **Allow location** when prompted (for nearby landmarks)
4. **Point at landmark/sign/menu** → tap **Snap** → **Identify**
5. **See**: Identified place card + **Nearby Landmarks** (real GPS distance)
6. **Tap nearby** → opens in **Browse** with full info card (facts, knowledge, book)
7. **Switch to "Translate" tab** → upload same image → select **Kannada / Telugu / English**
8. **Verify**: Proper native script output (ಕನ್ನಡ / తెలుగు)

---

## Tests / Proof

```bash
# Backend tests (provider fallback, cache, rate-limit contracts)
cd /path/to/repo
source .venv/bin/activate
python -m pytest tests/test_llm_fallback.py -v

# Expected: 11 tests covering:
# - primary rate-limit → fallback
# - quota exhaustion → 429 with quota_exhausted:true
# - transport error → structured LLMError
# - cache prevents repeated calls
# - only 3 target languages accepted
# - dataset reference fallback on quota fail

# Data model conformance
python3 PS-06_LensGuide/tools/validate_conformance.py data/PS-06.db
# Expected: PASS (canonical D1-D9 + extensions)

# Manual verification
# - Open Snap → Identify with GPS → nearby distances match haversine
# - Translate Kannada→Telugu → output in Telugu script (not Kannada)
```

---

## Repository Structure

```
kv-hack2026-reboot-rebels/
├── README.md                    # This file
├── frontend/
│   └── src/
│       ├── app.js               # Snap, Browse, Translate, Nearby, AR
│       ├── index.html
│       └── style.css
├── backend/
│   └── src/
│       ├── app.py               # Flask routes
│       ├── llm.py               # Provider chain, cache, prompts
│       └── db.py                # Read-only SQLite
│   └── requirements.txt
├── data-model/
│   ├── schema.sql               # Canonical D1-D9 + extensions DDL
│   ├── seed/                    # 13 CSVs (D1-D9 + extensions)
│   └── DATA_MODEL.md            # Mapping + constraints
├── ai/
│   ├── prompts/
│   │   ├── identify.md
│   │   └── translate.md
│   └── pipeline/
│       └── llm.py
├── docs/
│   └── ARCHITECTURE.md
├── tests/
│   └── test_llm_fallback.py
├── scripts/
│   ├── start_local_ai.sh        # Load model + start LM Studio server
│   └── serve.sh                 # Start HTTPS (8000) + HTTP (8004)
├── data/
│   └── PS-06.db                 # Read-only catalogue (gitignored, download)
├── .env.example
└── .gitignore
```

---

## Team

**Reboot Rebels** — Cambridge Institute of Technology  
KogniVera Hackathon 2026 · PS-06
