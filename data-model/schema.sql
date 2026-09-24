-- KV Hackathon 2026 · travel data model v1.1.0-rc2
-- Only the 13 tables this problem statement needs.

CREATE EXTENSION IF NOT EXISTS vector;   -- optional, for embedding search

-- categories  (Reference & geography)
CREATE TABLE categories (
  category_id                  TEXT PRIMARY KEY,
  code                         TEXT NOT NULL UNIQUE,
  label                        TEXT NOT NULL,
  parent_category_id           TEXT,
  applies_to                   TEXT NOT NULL,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- currencies  (Reference & geography)
CREATE TABLE currencies (
  currency_id                  TEXT PRIMARY KEY,
  iso4217                      CHAR(3) NOT NULL UNIQUE,
  name                         TEXT NOT NULL,
  symbol                       TEXT NOT NULL,
  minor_unit_exponent          SMALLINT NOT NULL,
  display_locale               TEXT NOT NULL,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- languages  (Reference & geography)
CREATE TABLE languages (
  language_id                  TEXT PRIMARY KEY,
  bcp47                        TEXT NOT NULL UNIQUE,
  english_name                 TEXT NOT NULL,
  native_name                  TEXT NOT NULL,
  script                       TEXT NOT NULL,
  rtl                          BOOLEAN NOT NULL,
  tts_supported                BOOLEAN NOT NULL,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- countries  (Reference & geography)
CREATE TABLE countries (
  country_id                   TEXT PRIMARY KEY,
  iso2                         CHAR(2) NOT NULL UNIQUE,
  iso3                         CHAR(3) NOT NULL UNIQUE,
  name                         TEXT NOT NULL,
  default_currency             CHAR(3) NOT NULL,
  calling_code                 TEXT NOT NULL,
  region                       TEXT NOT NULL,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- cities  (Reference & geography)
CREATE TABLE cities (
  city_id                      TEXT PRIMARY KEY,
  name                         TEXT NOT NULL,
  state                        TEXT,
  country_id                   TEXT NOT NULL,
  country_code                 CHAR(2) NOT NULL,
  lat                          NUMERIC(9,6) NOT NULL,
  lng                          NUMERIC(9,6) NOT NULL,
  timezone                     TEXT NOT NULL,
  region                       TEXT NOT NULL,
  population                   INTEGER,
  season_profile               TEXT NOT NULL CHECK (season_profile IN ('winter', 'summer', 'monsoon', 'post_monsoon', 'spring', 'autumn')),
  peak_months                  TEXT NOT NULL,
  primary_language             TEXT NOT NULL,
  description                  TEXT,
  status                       TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'archived', 'draft')),
  updated_at                   TIMESTAMPTZ NOT NULL
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
  dataset_split                TEXT NOT NULL CHECK (dataset_split IN ('train', 'eval')),
  is_safety_critical           BOOLEAN NOT NULL,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- xr_scenes  (XR & immersive)
CREATE TABLE xr_scenes (
  scene_id                     TEXT PRIMARY KEY,
  entity_type                  TEXT NOT NULL CHECK (entity_type IN ('hotel', 'room_type', 'rate_plan', 'flight', 'flight_fare', 'poi', 'package', 'package_component', 'guide', 'transfer', 'event', 'xr_scene')),
  entity_id                    TEXT NOT NULL,
  city_id                      TEXT NOT NULL,
  name                         TEXT NOT NULL,
  scene_type                   TEXT NOT NULL CHECK (scene_type IN ('panorama_360', 'model_3d', 'photogrammetry', 'video_360')),
  default_yaw_deg              SMALLINT NOT NULL,
  default_pitch_deg            SMALLINT NOT NULL,
  real_scale_metres            NUMERIC(6,2),
  total_bytes                  INTEGER NOT NULL,
  supports_webxr               BOOLEAN NOT NULL,
  supports_ar_placement        BOOLEAN NOT NULL,
  fallback_media_id            TEXT,
  licence                      TEXT NOT NULL,
  status                       TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'archived', 'draft')),
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- activities_poi  (Supply & catalogue)
CREATE TABLE activities_poi (
  poi_id                       TEXT PRIMARY KEY,
  city_id                      TEXT NOT NULL,
  name                         TEXT NOT NULL,
  category_id                  TEXT NOT NULL,
  poi_category                 TEXT NOT NULL CHECK (poi_category IN ('heritage', 'nature', 'museum', 'religious', 'adventure', 'food', 'shopping', 'nightlife', 'beach', 'wildlife', 'wellness', 'viewpoint')),
  lat                          NUMERIC(9,6) NOT NULL,
  lng                          NUMERIC(9,6) NOT NULL,
  typical_duration_minutes     INTEGER NOT NULL,
  entry_cost                   NUMERIC(12,2) NOT NULL,
  currency                     CHAR(3) NOT NULL,
  carbon_kg                    NUMERIC(8,3) NOT NULL,
  popularity_score             SMALLINT NOT NULL,
  value_score                  SMALLINT NOT NULL,
  opens_at                     TEXT,
  closes_at                    TEXT,
  closed_days                  TEXT,
  best_season                  TEXT CHECK (best_season IN ('winter', 'summer', 'monsoon', 'post_monsoon', 'spring', 'autumn')),
  accessibility                TEXT NOT NULL,
  tags                         TEXT NOT NULL,
  description                  TEXT NOT NULL,
  has_xr_scene                 BOOLEAN NOT NULL,
  status                       TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'archived', 'draft')),
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- landmark_image_set  (Content, knowledge & safety)
CREATE TABLE landmark_image_set (
  image_id                     TEXT PRIMARY KEY,
  poi_id                       TEXT,
  label_class                  TEXT NOT NULL,
  file_path                    TEXT NOT NULL,
  dataset_split                TEXT NOT NULL CHECK (dataset_split IN ('train', 'eval')),
  width_px                     INTEGER NOT NULL,
  height_px                    INTEGER NOT NULL,
  capture_conditions           TEXT NOT NULL,
  occlusion_pct                SMALLINT NOT NULL,
  licence                      TEXT NOT NULL,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- place_kb  (Content, knowledge & safety)
CREATE TABLE place_kb (
  chunk_id                     TEXT PRIMARY KEY,
  city_id                      TEXT,
  poi_id                       TEXT,
  section                      TEXT NOT NULL CHECK (section IN ('history', 'culture', 'etiquette', 'food', 'transport', 'safety', 'seasonal', 'practical')),
  title                        TEXT NOT NULL,
  body                         TEXT NOT NULL,
  language                     TEXT NOT NULL,
  token_estimate               INTEGER NOT NULL,
  source_label                 TEXT NOT NULL,
  embedding_ref                TEXT,
  seasonal_relevance           TEXT CHECK (seasonal_relevance IN ('winter', 'summer', 'monsoon', 'post_monsoon', 'spring', 'autumn')),
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- poi_facts_kb  (Content, knowledge & safety)
CREATE TABLE poi_facts_kb (
  fact_id                      TEXT PRIMARY KEY,
  poi_id                       TEXT NOT NULL,
  fact_type                    TEXT NOT NULL,
  fact_text                    TEXT NOT NULL,
  language                     TEXT NOT NULL,
  confidence                   TEXT NOT NULL CHECK (confidence IN ('high', 'medium', 'low')),
  display_priority             SMALLINT NOT NULL,
  embedding_ref                TEXT,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- poi_media  (Supply & catalogue)
CREATE TABLE poi_media (
  media_id                     TEXT PRIMARY KEY,
  poi_id                       TEXT NOT NULL,
  file_path                    TEXT NOT NULL,
  media_role                   TEXT NOT NULL CHECK (media_role IN ('hero', 'room', 'lobby', 'exterior', 'dining', 'pool', 'bathroom', 'view', 'landmark', 'menu', 'sign', 'receipt')),
  alt_text                     TEXT NOT NULL,
  label_class                  TEXT NOT NULL,
  dataset_split                TEXT NOT NULL CHECK (dataset_split IN ('train', 'eval')),
  width_px                     INTEGER NOT NULL,
  height_px                    INTEGER NOT NULL,
  capture_conditions           TEXT,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- poi_travel_matrix  (Supply & catalogue)
CREATE TABLE poi_travel_matrix (
  matrix_id                    TEXT PRIMARY KEY,
  origin_poi_id                TEXT NOT NULL,
  dest_poi_id                  TEXT NOT NULL,
  mode                         TEXT NOT NULL CHECK (mode IN ('walk', 'cycle', 'auto_rickshaw', 'cab', 'bus', 'metro', 'train', 'ferry', 'flight')),
  minutes                      INTEGER NOT NULL,
  distance_km                  NUMERIC(7,3) NOT NULL,
  carbon_kg                    NUMERIC(8,3) NOT NULL,
  cost                         NUMERIC(12,2) NOT NULL,
  currency                     CHAR(3) NOT NULL,
  bearing_deg                  SMALLINT NOT NULL,
  updated_at                   TIMESTAMPTZ NOT NULL,
  UNIQUE (origin_poi_id, dest_poi_id, mode)
);

-- foreign keys
ALTER TABLE categories ADD CONSTRAINT fk_categories_parent_category_id FOREIGN KEY (parent_category_id) REFERENCES categories(category_id);
ALTER TABLE countries ADD CONSTRAINT fk_countries_default_currency FOREIGN KEY (default_currency) REFERENCES currencies(iso4217);
ALTER TABLE cities ADD CONSTRAINT fk_cities_country_id FOREIGN KEY (country_id) REFERENCES countries(country_id);
ALTER TABLE cities ADD CONSTRAINT fk_cities_primary_language FOREIGN KEY (primary_language) REFERENCES languages(bcp47);
ALTER TABLE menu_sign_images ADD CONSTRAINT fk_menu_sign_images_city_id FOREIGN KEY (city_id) REFERENCES cities(city_id);
ALTER TABLE menu_sign_images ADD CONSTRAINT fk_menu_sign_images_source_language FOREIGN KEY (source_language) REFERENCES languages(bcp47);
ALTER TABLE menu_sign_images ADD CONSTRAINT fk_menu_sign_images_target_language FOREIGN KEY (target_language) REFERENCES languages(bcp47);
ALTER TABLE xr_scenes ADD CONSTRAINT fk_xr_scenes_city_id FOREIGN KEY (city_id) REFERENCES cities(city_id);
ALTER TABLE activities_poi ADD CONSTRAINT fk_activities_poi_city_id FOREIGN KEY (city_id) REFERENCES cities(city_id);
ALTER TABLE activities_poi ADD CONSTRAINT fk_activities_poi_category_id FOREIGN KEY (category_id) REFERENCES categories(category_id);
ALTER TABLE activities_poi ADD CONSTRAINT fk_activities_poi_currency FOREIGN KEY (currency) REFERENCES currencies(iso4217);
ALTER TABLE landmark_image_set ADD CONSTRAINT fk_landmark_image_set_poi_id FOREIGN KEY (poi_id) REFERENCES activities_poi(poi_id);
ALTER TABLE place_kb ADD CONSTRAINT fk_place_kb_city_id FOREIGN KEY (city_id) REFERENCES cities(city_id);
ALTER TABLE place_kb ADD CONSTRAINT fk_place_kb_poi_id FOREIGN KEY (poi_id) REFERENCES activities_poi(poi_id);
ALTER TABLE place_kb ADD CONSTRAINT fk_place_kb_language FOREIGN KEY (language) REFERENCES languages(bcp47);
ALTER TABLE poi_facts_kb ADD CONSTRAINT fk_poi_facts_kb_poi_id FOREIGN KEY (poi_id) REFERENCES activities_poi(poi_id);
ALTER TABLE poi_facts_kb ADD CONSTRAINT fk_poi_facts_kb_language FOREIGN KEY (language) REFERENCES languages(bcp47);
ALTER TABLE poi_media ADD CONSTRAINT fk_poi_media_poi_id FOREIGN KEY (poi_id) REFERENCES activities_poi(poi_id);
ALTER TABLE poi_travel_matrix ADD CONSTRAINT fk_poi_travel_matrix_origin_poi_id FOREIGN KEY (origin_poi_id) REFERENCES activities_poi(poi_id);
ALTER TABLE poi_travel_matrix ADD CONSTRAINT fk_poi_travel_matrix_dest_poi_id FOREIGN KEY (dest_poi_id) REFERENCES activities_poi(poi_id);
ALTER TABLE poi_travel_matrix ADD CONSTRAINT fk_poi_travel_matrix_currency FOREIGN KEY (currency) REFERENCES currencies(iso4217);

-- indexes
CREATE INDEX idx_categories_parent_category_id ON categories(parent_category_id);
CREATE INDEX idx_countries_default_currency ON countries(default_currency);
CREATE INDEX idx_cities_country_id ON cities(country_id);
CREATE INDEX idx_cities_primary_language ON cities(primary_language);
CREATE INDEX idx_menu_sign_images_city_id ON menu_sign_images(city_id);
CREATE INDEX idx_menu_sign_images_source_language ON menu_sign_images(source_language);
CREATE INDEX idx_menu_sign_images_target_language ON menu_sign_images(target_language);
CREATE INDEX idx_xr_scenes_city_id ON xr_scenes(city_id);
CREATE INDEX idx_activities_poi_city_id ON activities_poi(city_id);
CREATE INDEX idx_activities_poi_category_id ON activities_poi(category_id);
CREATE INDEX idx_activities_poi_currency ON activities_poi(currency);
CREATE INDEX idx_landmark_image_set_poi_id ON landmark_image_set(poi_id);
CREATE INDEX idx_place_kb_city_id ON place_kb(city_id);
CREATE INDEX idx_place_kb_poi_id ON place_kb(poi_id);
CREATE INDEX idx_place_kb_language ON place_kb(language);
CREATE INDEX idx_poi_facts_kb_poi_id ON poi_facts_kb(poi_id);
CREATE INDEX idx_poi_facts_kb_language ON poi_facts_kb(language);
CREATE INDEX idx_poi_media_poi_id ON poi_media(poi_id);
CREATE INDEX idx_poi_travel_matrix_origin_poi_id ON poi_travel_matrix(origin_poi_id);
CREATE INDEX idx_poi_travel_matrix_dest_poi_id ON poi_travel_matrix(dest_poi_id);
CREATE INDEX idx_poi_travel_matrix_currency ON poi_travel_matrix(currency);