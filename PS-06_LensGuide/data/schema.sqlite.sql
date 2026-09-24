-- KV Hackathon 2026 · travel data model v1.1.0-rc2
-- Only the 13 tables this problem statement needs.

-- SQLite has no DECIMAL type, and NUMERIC affinity would turn '8500.00' into the
-- float 8500.0. Money columns are therefore TEXT so the exact value survives.
PRAGMA foreign_keys = ON;

-- categories  (Reference & geography)
CREATE TABLE categories (
  category_id                  TEXT PRIMARY KEY,
  code                         TEXT NOT NULL UNIQUE,
  label                        TEXT NOT NULL,
  parent_category_id           TEXT,
  applies_to                   TEXT NOT NULL,
  updated_at                   TEXT NOT NULL,
  FOREIGN KEY (parent_category_id) REFERENCES categories(category_id)
);

-- currencies  (Reference & geography)
CREATE TABLE currencies (
  currency_id                  TEXT PRIMARY KEY,
  iso4217                      TEXT NOT NULL UNIQUE,
  name                         TEXT NOT NULL,
  symbol                       TEXT NOT NULL,
  minor_unit_exponent          INTEGER NOT NULL,
  display_locale               TEXT NOT NULL,
  updated_at                   TEXT NOT NULL
);

-- languages  (Reference & geography)
CREATE TABLE languages (
  language_id                  TEXT PRIMARY KEY,
  bcp47                        TEXT NOT NULL UNIQUE,
  english_name                 TEXT NOT NULL,
  native_name                  TEXT NOT NULL,
  script                       TEXT NOT NULL,
  rtl                          INTEGER NOT NULL,
  tts_supported                INTEGER NOT NULL,
  updated_at                   TEXT NOT NULL
);

-- countries  (Reference & geography)
CREATE TABLE countries (
  country_id                   TEXT PRIMARY KEY,
  iso2                         TEXT NOT NULL UNIQUE,
  iso3                         TEXT NOT NULL UNIQUE,
  name                         TEXT NOT NULL,
  default_currency             TEXT NOT NULL,
  calling_code                 TEXT NOT NULL,
  region                       TEXT NOT NULL,
  updated_at                   TEXT NOT NULL,
  FOREIGN KEY (default_currency) REFERENCES currencies(iso4217)
);

-- cities  (Reference & geography)
CREATE TABLE cities (
  city_id                      TEXT PRIMARY KEY,
  name                         TEXT NOT NULL,
  state                        TEXT,
  country_id                   TEXT NOT NULL,
  country_code                 TEXT NOT NULL,
  lat                          NUMERIC(9,6) NOT NULL,
  lng                          NUMERIC(9,6) NOT NULL,
  timezone                     TEXT NOT NULL,
  region                       TEXT NOT NULL,
  population                   INTEGER,
  season_profile               TEXT NOT NULL,
  peak_months                  TEXT NOT NULL,
  primary_language             TEXT NOT NULL,
  description                  TEXT,
  status                       TEXT NOT NULL,
  updated_at                   TEXT NOT NULL,
  FOREIGN KEY (country_id) REFERENCES countries(country_id),
  FOREIGN KEY (primary_language) REFERENCES languages(bcp47)
);

-- menu_sign_images  (Content, knowledge & safety)
CREATE TABLE menu_sign_images (
  image_id                     TEXT PRIMARY KEY,
  city_id                      TEXT NOT NULL,
  kind                         TEXT NOT NULL,
  file_path                    TEXT NOT NULL,
  source_text_truth            TEXT NOT NULL,
  source_language              TEXT NOT NULL,
  reference_translation        TEXT NOT NULL,
  target_language              TEXT NOT NULL,
  script                       TEXT NOT NULL,
  difficulty                   TEXT NOT NULL,
  dataset_split                TEXT NOT NULL,
  is_safety_critical           INTEGER NOT NULL,
  updated_at                   TEXT NOT NULL,
  FOREIGN KEY (city_id) REFERENCES cities(city_id),
  FOREIGN KEY (source_language) REFERENCES languages(bcp47),
  FOREIGN KEY (target_language) REFERENCES languages(bcp47)
);

-- xr_scenes  (XR & immersive)
CREATE TABLE xr_scenes (
  scene_id                     TEXT PRIMARY KEY,
  entity_type                  TEXT NOT NULL,
  entity_id                    TEXT NOT NULL,
  city_id                      TEXT NOT NULL,
  name                         TEXT NOT NULL,
  scene_type                   TEXT NOT NULL,
  default_yaw_deg              INTEGER NOT NULL,
  default_pitch_deg            INTEGER NOT NULL,
  real_scale_metres            NUMERIC(6,2),
  total_bytes                  INTEGER NOT NULL,
  supports_webxr               INTEGER NOT NULL,
  supports_ar_placement        INTEGER NOT NULL,
  fallback_media_id            TEXT,
  licence                      TEXT NOT NULL,
  status                       TEXT NOT NULL,
  updated_at                   TEXT NOT NULL,
  FOREIGN KEY (city_id) REFERENCES cities(city_id)
);

-- activities_poi  (Supply & catalogue)
CREATE TABLE activities_poi (
  poi_id                       TEXT PRIMARY KEY,
  city_id                      TEXT NOT NULL,
  name                         TEXT NOT NULL,
  category_id                  TEXT NOT NULL,
  poi_category                 TEXT NOT NULL,
  lat                          NUMERIC(9,6) NOT NULL,
  lng                          NUMERIC(9,6) NOT NULL,
  typical_duration_minutes     INTEGER NOT NULL,
  entry_cost                   TEXT NOT NULL,
  currency                     TEXT NOT NULL,
  carbon_kg                    NUMERIC(8,3) NOT NULL,
  popularity_score             INTEGER NOT NULL,
  value_score                  INTEGER NOT NULL,
  opens_at                     TEXT,
  closes_at                    TEXT,
  closed_days                  TEXT,
  best_season                  TEXT,
  accessibility                TEXT NOT NULL,
  tags                         TEXT NOT NULL,
  description                  TEXT NOT NULL,
  has_xr_scene                 INTEGER NOT NULL,
  status                       TEXT NOT NULL,
  updated_at                   TEXT NOT NULL,
  FOREIGN KEY (city_id) REFERENCES cities(city_id),
  FOREIGN KEY (category_id) REFERENCES categories(category_id),
  FOREIGN KEY (currency) REFERENCES currencies(iso4217)
);

-- landmark_image_set  (Content, knowledge & safety)
CREATE TABLE landmark_image_set (
  image_id                     TEXT PRIMARY KEY,
  poi_id                       TEXT,
  label_class                  TEXT NOT NULL,
  file_path                    TEXT NOT NULL,
  dataset_split                TEXT NOT NULL,
  width_px                     INTEGER NOT NULL,
  height_px                    INTEGER NOT NULL,
  capture_conditions           TEXT NOT NULL,
  occlusion_pct                INTEGER NOT NULL,
  licence                      TEXT NOT NULL,
  updated_at                   TEXT NOT NULL,
  FOREIGN KEY (poi_id) REFERENCES activities_poi(poi_id)
);

-- place_kb  (Content, knowledge & safety)
CREATE TABLE place_kb (
  chunk_id                     TEXT PRIMARY KEY,
  city_id                      TEXT,
  poi_id                       TEXT,
  section                      TEXT NOT NULL,
  title                        TEXT NOT NULL,
  body                         TEXT NOT NULL,
  language                     TEXT NOT NULL,
  token_estimate               INTEGER NOT NULL,
  source_label                 TEXT NOT NULL,
  embedding_ref                TEXT,
  seasonal_relevance           TEXT,
  updated_at                   TEXT NOT NULL,
  FOREIGN KEY (city_id) REFERENCES cities(city_id),
  FOREIGN KEY (poi_id) REFERENCES activities_poi(poi_id),
  FOREIGN KEY (language) REFERENCES languages(bcp47)
);

-- poi_facts_kb  (Content, knowledge & safety)
CREATE TABLE poi_facts_kb (
  fact_id                      TEXT PRIMARY KEY,
  poi_id                       TEXT NOT NULL,
  fact_type                    TEXT NOT NULL,
  fact_text                    TEXT NOT NULL,
  language                     TEXT NOT NULL,
  confidence                   TEXT NOT NULL,
  display_priority             INTEGER NOT NULL,
  embedding_ref                TEXT,
  updated_at                   TEXT NOT NULL,
  FOREIGN KEY (poi_id) REFERENCES activities_poi(poi_id),
  FOREIGN KEY (language) REFERENCES languages(bcp47)
);

-- poi_media  (Supply & catalogue)
CREATE TABLE poi_media (
  media_id                     TEXT PRIMARY KEY,
  poi_id                       TEXT NOT NULL,
  file_path                    TEXT NOT NULL,
  media_role                   TEXT NOT NULL,
  alt_text                     TEXT NOT NULL,
  label_class                  TEXT NOT NULL,
  dataset_split                TEXT NOT NULL,
  width_px                     INTEGER NOT NULL,
  height_px                    INTEGER NOT NULL,
  capture_conditions           TEXT,
  updated_at                   TEXT NOT NULL,
  FOREIGN KEY (poi_id) REFERENCES activities_poi(poi_id)
);

-- poi_travel_matrix  (Supply & catalogue)
CREATE TABLE poi_travel_matrix (
  matrix_id                    TEXT PRIMARY KEY,
  origin_poi_id                TEXT NOT NULL,
  dest_poi_id                  TEXT NOT NULL,
  mode                         TEXT NOT NULL,
  minutes                      INTEGER NOT NULL,
  distance_km                  NUMERIC(7,3) NOT NULL,
  carbon_kg                    NUMERIC(8,3) NOT NULL,
  cost                         TEXT NOT NULL,
  currency                     TEXT NOT NULL,
  bearing_deg                  INTEGER NOT NULL,
  updated_at                   TEXT NOT NULL,
  FOREIGN KEY (origin_poi_id) REFERENCES activities_poi(poi_id),
  FOREIGN KEY (dest_poi_id) REFERENCES activities_poi(poi_id),
  FOREIGN KEY (currency) REFERENCES currencies(iso4217),
  UNIQUE (origin_poi_id, dest_poi_id, mode)
);
