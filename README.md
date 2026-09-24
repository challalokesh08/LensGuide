# LensGuide — Visual Search & AR Travel Companion
# Kognivera Hackathon 2026 · PS-06 · Team Reboot Rebels · data model v1.1.0-rc2

Point your camera at a landmark, dish, or foreign-language sign. Get a grounded
info card, nearby places, a sign translation, and a snap-to-book action.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add OPENAI_API_KEY if you want live recognition
python run.py
# open http://localhost:8000
```

Works in the browser on Android Chrome (camera via `getUserMedia`).

## Offline demo mode

Open the app, toggle **Offline mode** in the toolbar. Recognition is replaced by
a POI picker; the app becomes fully self-contained against `data/PS-06.db` with
zero network calls. This is the bulletproof venue fallback (design risk #1).

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/identify` | Vision-LLM: image → `{kind, label_class, name, confidence}` matched to `activities_poi` |
| GET | `/api/poi/<poi_id>` | Grounded info card: POI + `poi_facts_kb` (high/medium/low) + `place_kb` chunks |
| GET | `/api/poi/<poi_id>/nearby?mode=walk` | Nearby from precomputed `poi_travel_matrix` |
| POST | `/api/translate` | `{text}` or `{image}` → OCR + translate, scored against `menu_sign_images` |
| GET | `/api/poi/<poi_id>/book` | Snap-to-book: hours, cost (currency-exponent-aware), accessibility |
| GET | `/api/pois` | Catalogue for the offline POI picker |

## Grounding rules honoured

- Facts come **only** from `poi_facts_kb` / `place_kb`; the LLM never writes facts (design anti-hallucination).
- Money stays a string + ISO-4217; display via `currencies.minor_unit_exponent` (R3).
- Language is BCP-47 (R6), IDs opaque (R2), DB read-only (R1). `PS-06.db` is never mutated.

## Conformance

```bash
python3 tools/validate_conformance.py data/PS-06.db   # upstream tool, expect PASS
```