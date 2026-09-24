# Data Model Mapping — LensGuide (PS-06)

## Canonical Tables Used (D1–D9)

| Canonical | Table Name | Description |
|-----------|------------|-------------|
| D1 | `categories` | POI categories (heritage, museum, temple, beach, etc.) |
| D2 | `currencies` | ISO-4217 currencies with minor_unit_exponent |
| D3 | `languages` | BCP-47 language tags (en-IN, kn-IN, te-IN, etc.) |
| D4 | `countries` | ISO-3166 countries |
| D5 | `cities` | Cities with primary_language (FK to languages) |
| D6 | `menu_sign_images` | OCR reference images with source_language + reference_translation |
| D7 | `xr_scenes` | AR/WebXR scene metadata per POI |
| D8 | `activities_poi` | Main POI table (landmarks, food, signs, etc.) |
| D9 | `landmark_image_set` | Image sets for landmark recognition |

## Additional Tables (PS-06 Extensions)

| Table | Purpose | Canonical Ref |
|-------|---------|---------------|
| `poi_facts_kb` | Grounded facts per POI (confidence: high/medium/low) | FK → activities_poi.poi_id |
| `place_kb` | Knowledge chunks per POI (title + body) | FK → activities_poi.poi_id |
| `poi_travel_matrix` | Precomputed travel matrix (walk/auto/taxi) | FK → activities_poi (from_poi_id, to_poi_id) |
| `poi_media` | Media assets per POI (images, audio) | FK → activities_poi.poi_id |

## Key Constraints Enforced in Code

- **Currency display**: `currencies.minor_unit_exponent` used for correct minor-unit formatting (R3)
- **Language tags**: BCP-47 enforced (R6) — only `en-IN`, `kn-IN`, `te-IN` accepted for translation
- **DB read-only**: `PS-06.db` opened with `mode=ro` — never mutated (R1)
- **IDs opaque**: `poi_id` treated as opaque strings (R2)
- **Boundary rules**: Confidence threshold 0.85 for identification; script validation for kn-IN/te-IN

## Schema Source

See `data-model/schema.sql` for full DDL (canonical + extensions).
Seed CSVs in `data-model/seed/` match the canonical + extension tables.
