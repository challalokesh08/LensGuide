# PS-06 — your data model

**LensGuide — Visual Search & AR Companion**  
Kognivera Hackathon 2026 · Travel & Tourism · data model v1.1.0-rc2

> **The problem statement itself, the 24-hour MVP scope and the XR device requirement live in the hackathon application**, on your statement's page. This document is the data you have been given to build it with: every table, every field, and what each one is for.

---

You have **12,289 rows across 13 tables**. 12 of them are the tables this statement is built on; the remaining 1 is a reference table the others point at, included so the database works on its own.

All of it is in the `data/` folder beside this document: as `PS-06.db` (SQLite, indexed, ready to query), as CSV, and as DDL for Postgres and SQLite.

## What the data gives you

60 labelled landmark classes × 10 images with a train/eval split and a deliberate difficulty gradient, 200 menu/sign images with ground-truth text *and* a reference translation, and 900 grounded POI facts with honest confidence bands.

## Watch out for this one

Train on `dataset_split='train'` and report on `'eval'`. Mixing them produces a number that means nothing and a judge will ask.

## The tables this statement is built on

| Table | Rows | What you use it for |
|---|---|---|
| `activities_poi` | 900 | Points of interest with real depth — cost, duration, carbon, hours and tags — because APS-09 optimises over exactly these fields. |
| `cities` | 60 | The geographic anchor of the whole model. 60 cities; every hotel, POI, package, advisory and weather row hangs off one. |
| `countries` | 30 | ISO country reference. Every city, currency default and calling code resolves here. |
| `currencies` | 25 | carries the true minor-unit exponent so JPY/KWD display correctly even though storage is always DECIMAL(12,2). |
| `languages` | 26 | Rule R6: BCP-47 is the only legal way to say 'language' anywhere in the model. |
| `landmark_image_set` | 600 | 60 labelled classes x 10 images, split train / eval. Without inputs, PS-06's core AI feature is unbuildable. |
| `menu_sign_images` | 200 | Ground-truth source text plus a reference translation, so in-place translation can be scored rather than eyeballed. |
| `place_kb` | 1,200 | chunked, embeddable prose. If retrieval returns filler the grounding claim collapses, so this text is written to be worth retrieving. |
| `poi_facts_kb` | 900 | Short grounded facts — what PS-06 returns beside a recognised landmark and what APS-03 puts on an info card. |
| `poi_media` | 1,800 | Labelled imagery per POI — the recognition training and evaluation surface for PS-06. |
| `poi_travel_matrix` | 6,418 | precomputed edge costs between POIs. This is what removes the Google Maps dependency for APS-09 and makes results comparable across teams. |
| `xr_scenes` | 60 | One immersive scene per previewable space. PS-05 embeds it on the booking page; APS-07 loads it in WebXR. Both point at the same canonical supply row. |

## Reference tables, included so the database is valid

You will mostly join through these rather than think about them.

| Table | Rows | What it is |
|---|---|---|
| `categories` | 70 | One two-level taxonomy shared by POI type, package theme and expense category — so the three never drift apart. |

## How they fit together

Open `02_DATA_MODEL_DIAGRAM.html` in a browser for the clickable version — it shows these tables and nothing else. Download it first; it will not render inside SharePoint.

Some tables point at "any bookable thing" using an `(entity_type, entity_id)` pair rather than a typed foreign key. That is deliberate: it is what lets one feature refer to a hotel, a flight, a point of interest or a package without a separate join table for each. The legal values of `entity_type` are in `data/enums.json`.

---

## Every field, table by table

Columns marked **PK** are the primary key. **FK** shows what a column points at. Enum columns list their legal values — anything else is rejected by the conformance check.

### `categories`

*Reference & geography · 70 rows · IDs start `cat_` · reference table*

One two-level taxonomy shared by POI type, package theme and expense category — so the three never drift apart.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `category_id` | text | **PK** | cat_ prefixed. |
| `code` | text | UNIQUE · NOT NULL | snake_case. |
| `label` | text | NOT NULL |  |
| `parent_category_id` | text | FK → `categories.category_id` | Null for top-level; self-referencing. |
| `applies_to` | text | NOT NULL | poi | package | expense | mixed. |
| `updated_at` | timestamptz | NOT NULL |  |

### `currencies`

*Reference & geography · 25 rows · IDs start `cur_`*

carries the true minor-unit exponent so JPY/KWD display correctly even though storage is always DECIMAL(12,2).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `currency_id` | text | **PK** | cur_ prefixed. |
| `iso4217` | char(3) | UNIQUE · NOT NULL | e.g. INR. |
| `name` | text | NOT NULL |  |
| `symbol` | text | NOT NULL |  |
| `minor_unit_exponent` | smallint | NOT NULL | 0 for JPY/KRW, 2 default, 3 for KWD/BHD. |
| `display_locale` | text | NOT NULL | BCP-47 locale used for formatting. |
| `updated_at` | timestamptz | NOT NULL |  |

### `languages`

*Reference & geography · 26 rows · IDs start `lng_`*

Rule R6: BCP-47 is the only legal way to say 'language' anywhere in the model.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `language_id` | text | **PK** | lng_ prefixed. |
| `bcp47` | text | UNIQUE · NOT NULL | e.g. ta, hi, en-IN — never 'Tamil'. |
| `english_name` | text | NOT NULL |  |
| `native_name` | text | NOT NULL |  |
| `script` | text | NOT NULL | ISO-15924, e.g. Taml, Deva, Latn. |
| `rtl` | bool | NOT NULL | Right-to-left rendering flag. |
| `tts_supported` | bool | NOT NULL | Relevant to PS-13 voice output. |
| `updated_at` | timestamptz | NOT NULL |  |

### `countries`

*Reference & geography · 30 rows · IDs start `cnt_`*

ISO country reference. Every city, currency default and calling code resolves here.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `country_id` | text | **PK** | Canonical ID, cnt_ prefixed. |
| `iso2` | char(2) | UNIQUE · NOT NULL | ISO-3166-1 alpha-2, e.g. IN. |
| `iso3` | char(3) | UNIQUE · NOT NULL | ISO-3166-1 alpha-3, e.g. IND. |
| `name` | text | NOT NULL | English short name. |
| `default_currency` | char(3) | FK → `currencies.iso4217` · NOT NULL | ISO-4217 code. |
| `calling_code` | text | NOT NULL | E.164 country calling code, e.g. +91. |
| `region` | text | NOT NULL | UN sub-region grouping. |
| `updated_at` | timestamptz | NOT NULL | Rule R4: UTC, ISO-8601 with offset. |

### `cities`

*Reference & geography · 60 rows · IDs start `cty_`*

The geographic anchor of the whole model. 60 cities; every hotel, POI, package, advisory and weather row hangs off one.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `city_id` | text | **PK** | cty_ prefixed. |
| `name` | text | NOT NULL | City name. |
| `state` | text |  | State / province, nullable for city-states. |
| `country_id` | text | FK → `countries.country_id` · NOT NULL |  |
| `country_code` | char(2) | NOT NULL | Denormalised ISO2 for convenient joins. |
| `lat` | decimal(9,6) | NOT NULL | Rule R7: WGS-84, 6dp. |
| `lng` | decimal(9,6) | NOT NULL | Rule R7: WGS-84, 6dp. |
| `timezone` | text | NOT NULL | IANA zone, e.g. Asia/Kolkata. |
| `region` | text | NOT NULL | Domestic region grouping, e.g. South India. |
| `population` | int |  | Approximate, for demand weighting. |
| `season_profile` | text | NOT NULL · one of `winter`, `summer`, `monsoon`, `post_monsoon`, `spring`, `autumn` | Dominant season at the peak travel window. |
| `peak_months` | text | NOT NULL | Comma-separated month numbers, e.g. 10,11,12. |
| `primary_language` | text | FK → `languages.bcp47` · NOT NULL | Rule R6: BCP-47 tag. |
| `description` | text |  | One-paragraph orientation blurb, used by PS-13. |
| `status` | text | NOT NULL · one of `active`, `inactive`, `archived`, `draft` |  |
| `updated_at` | timestamptz | NOT NULL |  |

### `menu_sign_images`

*Content, knowledge & safety · 200 rows · IDs start `sgn_`*

Ground-truth source text plus a reference translation, so in-place translation can be scored rather than eyeballed.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `image_id` | text | **PK** | sgn_ prefixed. |
| `city_id` | text | FK → `cities.city_id` · NOT NULL |  |
| `kind` | text | NOT NULL | menu | street_sign | transit_board | warning | notice. |
| `file_path` | text | NOT NULL |  |
| `source_text_truth` | text | NOT NULL | Ground-truth OCR text. |
| `source_language` | text | FK → `languages.bcp47` · NOT NULL |  |
| `reference_translation` | text | NOT NULL | Reference target text. |
| `target_language` | text | FK → `languages.bcp47` · NOT NULL |  |
| `script` | text | NOT NULL | ISO-15924. |
| `difficulty` | text | NOT NULL | easy | medium | hard. |
| `dataset_split` | text | NOT NULL · one of `train`, `eval` |  |
| `is_safety_critical` | bool | NOT NULL | APS-03 — a confidently mistranslated warning is worse than an unsure one. |
| `updated_at` | timestamptz | NOT NULL |  |

### `xr_scenes`

*XR & immersive · 60 rows · IDs start `xrs_`*

One immersive scene per previewable space. PS-05 embeds it on the booking page; APS-07 loads it in WebXR. Both point at the same canonical supply row.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `scene_id` | text | **PK** | xrs_ prefixed. |
| `entity_type` | text | NOT NULL · one of `hotel`, `room_type`, `rate_plan`, `flight`, `flight_fare`, `poi`, `package`, `package_component`, `guide`, `transfer`, `event`, `xr_scene` | hotel | room_type | poi. |
| `entity_id` | text | NOT NULL | Canonical ID of the space being previewed. |
| `city_id` | text | FK → `cities.city_id` · NOT NULL |  |
| `name` | text | NOT NULL |  |
| `scene_type` | text | NOT NULL · one of `panorama_360`, `model_3d`, `photogrammetry`, `video_360` |  |
| `default_yaw_deg` | smallint | NOT NULL | Initial camera heading. |
| `default_pitch_deg` | smallint | NOT NULL |  |
| `real_scale_metres` | decimal(6,2) |  | Longest dimension — PS-05's AR mode needs true scale. |
| `total_bytes` | int | NOT NULL | Asset budget check for the judging bar. |
| `supports_webxr` | bool | NOT NULL |  |
| `supports_ar_placement` | bool | NOT NULL |  |
| `fallback_media_id` | text |  | hotel_media or poi_media row used when XR is unsupported. |
| `licence` | text | NOT NULL | Synthetic or openly-licensed only. |
| `status` | text | NOT NULL · one of `active`, `inactive`, `archived`, `draft` |  |
| `updated_at` | timestamptz | NOT NULL |  |

### `activities_poi`

*Supply & catalogue · 900 rows · IDs start `poi_`*

Points of interest with real depth — cost, duration, carbon, hours and tags — because APS-09 optimises over exactly these fields.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `poi_id` | text | **PK** | poi_ prefixed. |
| `city_id` | text | FK → `cities.city_id` · NOT NULL |  |
| `name` | text | NOT NULL |  |
| `category_id` | text | FK → `categories.category_id` · NOT NULL |  |
| `poi_category` | text | NOT NULL · one of `heritage`, `nature`, `museum`, `religious`, `adventure`, `food`, `shopping`, `nightlife`, `beach`, `wildlife`, `wellness`, `viewpoint` | Denormalised top-level category. |
| `lat` | decimal(9,6) | NOT NULL |  |
| `lng` | decimal(9,6) | NOT NULL |  |
| `typical_duration_minutes` | int | NOT NULL | APS-09 constraint input. |
| `entry_cost` | decimal(12,2) | NOT NULL | 0.00 where free. |
| `currency` | char(3) | FK → `currencies.iso4217` · NOT NULL |  |
| `carbon_kg` | decimal(8,3) | NOT NULL | On-site footprint estimate. |
| `popularity_score` | smallint | NOT NULL | 0–100, drives APS-04 baseline ranking. |
| `value_score` | smallint | NOT NULL | 0–100, editorial worth-the-stop rating. In APS-09 this is the value signal the eval_optimizer_cases reference plans were built on (highest value_score per unit of entry_cost). It is not one of the three capped objectives — cost, time and carbon are — so a higher-value plan is a legitimate way to beat the reference. |
| `opens_at` | text |  | Local HH:MM; null where always open. |
| `closes_at` | text |  |  |
| `closed_days` | text |  | Comma-separated 0–6, 0 = Monday. |
| `best_season` | text | one of `winter`, `summer`, `monsoon`, `post_monsoon`, `spring`, `autumn` |  |
| `accessibility` | text | NOT NULL | step_free | partial | none. |
| `tags` | text | NOT NULL | Comma-separated free tags for hybrid retrieval. |
| `description` | text | NOT NULL | Plausible prose. |
| `has_xr_scene` | bool | NOT NULL | PS-05 / APS-07. |
| `status` | text | NOT NULL · one of `active`, `inactive`, `archived`, `draft` |  |
| `updated_at` | timestamptz | NOT NULL |  |

### `landmark_image_set`

*Content, knowledge & safety · 600 rows · IDs start `lmk_`*

60 labelled classes x 10 images, split train / eval. Without inputs, PS-06's core AI feature is unbuildable.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `image_id` | text | **PK** | lmk_ prefixed. |
| `poi_id` | text | FK → `activities_poi.poi_id` | Null for generic classes. |
| `label_class` | text | NOT NULL | The 60-way recognition label. |
| `file_path` | text | NOT NULL |  |
| `dataset_split` | text | NOT NULL · one of `train`, `eval` |  |
| `width_px` | int | NOT NULL |  |
| `height_px` | int | NOT NULL |  |
| `capture_conditions` | text | NOT NULL | daylight | dusk | night | rain | crowded. |
| `occlusion_pct` | smallint | NOT NULL | Deliberate difficulty gradient. |
| `licence` | text | NOT NULL | Synthetic or openly-licensed only — no real people. |
| `updated_at` | timestamptz | NOT NULL |  |

### `place_kb`

*Content, knowledge & safety · 1,200 rows · IDs start `kbc_`*

chunked, embeddable prose. If retrieval returns filler the grounding claim collapses, so this text is written to be worth retrieving.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `chunk_id` | text | **PK** | kbc_ prefixed. |
| `city_id` | text | FK → `cities.city_id` | One of city_id / poi_id is always set. |
| `poi_id` | text | FK → `activities_poi.poi_id` |  |
| `section` | text | NOT NULL · one of `history`, `culture`, `etiquette`, `food`, `transport`, `safety`, `seasonal`, `practical` |  |
| `title` | text | NOT NULL |  |
| `body` | text | NOT NULL | 120–260 words of plausible prose. |
| `language` | text | FK → `languages.bcp47` · NOT NULL |  |
| `token_estimate` | int | NOT NULL |  |
| `source_label` | text | NOT NULL | Synthetic provenance label, shown in citations. |
| `embedding_ref` | text |  | Row key into the precomputed embeddings parquet. |
| `seasonal_relevance` | text | one of `winter`, `summer`, `monsoon`, `post_monsoon`, `spring`, `autumn` | Null where the chunk is season-agnostic. |
| `updated_at` | timestamptz | NOT NULL |  |

### `poi_facts_kb`

*Content, knowledge & safety · 900 rows · IDs start `fct_`*

Short grounded facts — what PS-06 returns beside a recognised landmark and what APS-03 puts on an info card.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `fact_id` | text | **PK** | fct_ prefixed. |
| `poi_id` | text | FK → `activities_poi.poi_id` · NOT NULL |  |
| `fact_type` | text | NOT NULL | history | architecture | practical | trivia | etiquette. |
| `fact_text` | text | NOT NULL | One or two sentences, verifiable in tone. |
| `language` | text | FK → `languages.bcp47` · NOT NULL |  |
| `confidence` | text | NOT NULL · one of `high`, `medium`, `low` | Lets PS-06/APS-03 demo honest low-confidence handling. |
| `display_priority` | smallint | NOT NULL |  |
| `embedding_ref` | text |  |  |
| `updated_at` | timestamptz | NOT NULL |  |

### `poi_media`

*Supply & catalogue · 1,800 rows · IDs start `pmd_`*

Labelled imagery per POI — the recognition training and evaluation surface for PS-06.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `media_id` | text | **PK** | pmd_ prefixed. |
| `poi_id` | text | FK → `activities_poi.poi_id` · NOT NULL |  |
| `file_path` | text | NOT NULL |  |
| `media_role` | text | NOT NULL · one of `hero`, `room`, `lobby`, `exterior`, `dining`, `pool`, `bathroom`, `view`, `landmark`, `menu`, `sign`, `receipt` |  |
| `alt_text` | text | NOT NULL |  |
| `label_class` | text | NOT NULL | Recognition class label. |
| `dataset_split` | text | NOT NULL · one of `train`, `eval` | F9 / train vs eval split. |
| `width_px` | int | NOT NULL |  |
| `height_px` | int | NOT NULL |  |
| `capture_conditions` | text |  | daylight | dusk | indoor | crowded — APS-03 stress cases. |
| `updated_at` | timestamptz | NOT NULL |  |

### `poi_travel_matrix`

*Supply & catalogue · 6,418 rows · IDs start `ptm_`*

precomputed edge costs between POIs. This is what removes the Google Maps dependency for APS-09 and makes results comparable across teams.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `matrix_id` | text | **PK** | ptm_ prefixed. |
| `origin_poi_id` | text | FK → `activities_poi.poi_id` · NOT NULL |  |
| `dest_poi_id` | text | FK → `activities_poi.poi_id` · NOT NULL |  |
| `mode` | text | NOT NULL · one of `walk`, `cycle`, `auto_rickshaw`, `cab`, `bus`, `metro`, `train`, `ferry`, `flight` |  |
| `minutes` | int | NOT NULL |  |
| `distance_km` | decimal(7,3) | NOT NULL |  |
| `carbon_kg` | decimal(8,3) | NOT NULL |  |
| `cost` | decimal(12,2) | NOT NULL | 0.00 for walk. |
| `currency` | char(3) | FK → `currencies.iso4217` · NOT NULL |  |
| `bearing_deg` | smallint | NOT NULL | APS-03 wayfinding — bearing origin → destination. |
| `updated_at` | timestamptz | NOT NULL |  |

*Unique together:* `(origin_poi_id, dest_poi_id, mode)`

---

## The rules that apply to these fields

| # | Rule |
|---|---|
| R1 | **Additive only.** Add columns, tables and stores freely. Never rename, drop or repurpose a field that came with the data. |
| R2 | **IDs are opaque prefixed strings** — `htl_a91f3c`. Never integers, never parsed for meaning. |
| R3 | **Money is a pair**: a 2-place decimal plus an ISO-4217 currency code. Never a float. |
| R4 | **Time is ISO-8601 with an offset.** `_at` fields carry an offset; `_date` fields have no zone. |
| R5 | **Enums are lowercase snake_case** and the legal values are in `data/enums.json`. |
| R6 | **Language is a BCP-47 tag** — `ta`, not "Tamil". |
| R7 | **Geography is WGS-84** to 6 decimal places, `lat` and `lng` together or not at all. |
| R8 | **Nothing is hard-deleted.** Rows carry `status` and `updated_at`. |

Add whatever you like beside these fields — new columns, new tables, your own vector store, your own services. That is the point of R1. What you must not do is rename or re-key the fields that came with the data, because that is what would stop sixteen independent builds being put together afterwards.

`data/WORKING_WITH_THE_DATA.md` has the loading instructions, including how to read money without corrupting it. `tools/validate_conformance.py` tells you in thirty seconds whether you are still conformant.
