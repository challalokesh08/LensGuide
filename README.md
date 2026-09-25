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
- ✅ **Android App (APK)**: native shell + bundled catalogue, on-device OCR & EN↔KN/TE translation (ML Kit) — download via GitHub Release

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
             │ Read-only │ │ In-memory │ │ LM Studio       │
             │  PS-06.db │ │ cache     │ │ Qwen3.5 4B      │
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
| **Cache** | In-memory (per server) | SHA-256 of message hashes | Separate in each server process (8000/8004); cleared on restart |

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
# App:  http://localhost:8004   (Expo / Android app)
```

**`.env.example`** contains all required vars with dummy values.

---

## 📱 Android App — download & run on your PC

LensGuide also ships as a standalone Android app (`myapplication3`) — a native
shell (`com.example.myapplication`, **Android 7.0+**) that bundles the full
catalogue (**PS-06.db** on-device) plus **offline OCR** and **offline
English ↔ Kannada/Telugu translation** via Google ML Kit. AI Snap→Identify and
booking call your PC's backend over the local network — still zero paid APIs.

### Step 1 — Download the APK

| Asset | Where |
|---|---|
| **LensGuide-myapplication3.apk** (~108 MB) | [GitHub Release — android-v1.0](https://github.com/challalokesh08/LensGuide/releases/download/android-v1.0/LensGuide-myapplication3.apk) |
| App source | `MyApplication3/` in the project workspace (build with Android Studio) |

> The APK is **>100 MB**, above GitHub's per-file code limit, so it ships as a
> **Release asset** (2 GB cap) instead of a tracked file — it stays out of git.
> The `dist/LensGuide-myapplication3.apk` copy in this workspace is identical.

### Step 2 — Run it (PC emulator or a real phone)

**Option A — on a Windows / macOS / Linux PC (emulator)**

1. Install **Android Studio** (or **BlueStacks** on Windows) and create an AVD
   running **Android 7.0 (API 24)** or newer. (BlueStacks: open the `.apk`
   file directly instead of steps 2–3.)
2. Drag-and-drop the APK onto the running emulator window — or
   `adb install LensGuide-myapplication3.apk`.
3. Open **LensGuide**; allow **Camera** and **Location** when prompted.

**Option B — on a real Android phone**

1. Copy the APK to the phone and tap it to install (enable
   **Install unknown apps** for your file manager).
2. On first launch, allow **Camera** and **Location**.

### Step 3 — Point the app at your PC's backend

The app can run fully offline (browse, POI cards, nearby, OCR, translation),
but **Snap→Identify** and **Snap-to-Book** talk to your Flask backend, so:

1. Start the backend on your PC and keep it running:
   `./serve.sh` (listens on `0.0.0.0:8004`).
2. Find your PC's LAN IP address:
   - Windows: `ipconfig`  ·  macOS: `ipconfig getifaddr en0`  ·  Linux: `hostname -I`
3. In the app, tap the **⚙ Server IP** button in the top bar (or tap the
   provider badge), enter `http://<YOUR-PC-IP>:8004`, and tap **Save**.
   - **Emulator preset**: `http://10.0.2.2:8004` (the emulator's built-in alias
     for your PC's `localhost`) — fastest for testing on a PC.
   - **Physical phone**: use your PC's real LAN IP (same Wi-Fi network);
     the built-in default `http://192.168.1.100:8004` is just a placeholder.

### What works where

| Capability | On-device (offline) | Needs your PC's backend |
|---|---|---|
| Browse catalogue + POI info cards | ✅ bundled `PS-06.db` | — |
| Nearby landmarks (real GPS distance) | ✅ haversine on-device | — |
| Sign/menu OCR + EN→KN/TE translation | ✅ ML Kit (offline) | — |
| Snap → AI identify (landmark/dish/sign) | — | ✅ `/api/identify` |
| Booking — hours, cost, accessibility | — | ✅ `/api/poi/<id>/book` |

### Rebuilding the APK (optional)

Open `MyApplication3/` in **Android Studio** → **Build → Build APK(s)** → output
at `MyApplication3/app/build/outputs/apk/debug/app-debug.apk`.

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
# Backend contract tests (provider fallback, cache, rate-limit contracts)
cd /path/to/repo
source .venv/bin/activate
python -m pytest tests/test_llm_fallback.py -v

# Suite: 11 contract tests — provider fallback chain, 429/rate-limit handling,
# structured LLMError mapping, response cache, 3-language gate, dataset fallback.
# Expected: 11 passed (0.2s, no network) covering:
# - primary rate-limit → configured fallback provider
# - 429 preserved when no fallback succeeds
# - translation cache prevents repeated provider calls
# - invalid credentials → actionable structured error (401)
# - transport error → structured LLMError (503, provider_unreachable)
# - /api/identify → 429 contract (quota_exhausted + Retry-After)
# - only 3 target languages accepted (400)
# - image translation uses OCR source language, not label class
# - quota failure → dataset reference fallback

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
│   └── start_local_ai.sh        # Load model + start LM Studio server
├── serve.sh                     # Start HTTPS (8000) + HTTP (8004) servers
├── data/
│   └── PS-06.db                 # Read-only catalogue (tracked with repo)
├── MyApplication3/              # Android app source (builds the APK)
│   └── app/
│       ├── src/main/assets/     # Bundled web UI + PS-06.db
│       └── build/outputs/apk/debug/app-debug.apk
├── dist/
│   └── LensGuide-myapplication3.apk   # Copy of the release asset (gitignored)
├── .env.example
└── .gitignore
```

---

## Team

**Reboot Rebels** — Cambridge Institute of Technology  
KogniVera Hackathon 2026 · PS-06
