-- PS-06 — LensGuide — Visual Search & AR Companion
-- Starter queries. Every one runs as-is against data/PS-06.db.
--
-- CAST(x AS REAL) appears below only for sorting and rough exploration.
-- Never use it for a value you will show someone or add to another value.

-- ==========================================================================
-- 1. The recognition classes, with their train/eval split
-- Train on the train rows. Report on the eval rows. Do not mix them.
-- ==========================================================================
SELECT label_class, dataset_split, COUNT(*) AS images,
          SUM(CASE WHEN occlusion_pct > 20 THEN 1 ELSE 0 END) AS hard_images
     FROM landmark_image_set GROUP BY label_class, dataset_split
    ORDER BY label_class LIMIT 20;

-- ==========================================================================
-- 2. Difficulty gradient inside the image set
-- Capture conditions and occlusion are deliberate. A model that only works in daylight is not finished.
-- ==========================================================================
SELECT capture_conditions, COUNT(*) AS images, ROUND(AVG(occlusion_pct),1) AS avg_occlusion
     FROM landmark_image_set GROUP BY capture_conditions ORDER BY images DESC;

-- ==========================================================================
-- 3. Grounded facts to return beside a recognised landmark
-- confidence includes 'low' rows on purpose — the statement rewards honest uncertainty.
-- ==========================================================================
SELECT p.name AS poi, f.fact_type, f.confidence, f.display_priority, f.fact_text
     FROM poi_facts_kb f JOIN activities_poi p ON p.poi_id = f.poi_id
    ORDER BY p.name, f.display_priority LIMIT 15;

-- ==========================================================================
-- 4. Menu and sign images with ground truth and a reference translation
-- You can score in-place translation rather than eyeball it. Safety-critical rows matter most.
-- ==========================================================================
SELECT kind, source_language, target_language, difficulty, is_safety_critical,
          source_text_truth, reference_translation
     FROM menu_sign_images WHERE dataset_split='eval'
    ORDER BY is_safety_critical DESC, difficulty DESC LIMIT 12;

-- ==========================================================================
-- 5. Nearby recommendations for a recognised POI
-- The travel matrix gives you minutes and metres without a Maps call.
-- ==========================================================================
SELECT o.name AS from_poi, d.name AS nearby, m.mode, m.minutes, m.distance_km
     FROM poi_travel_matrix m
     JOIN activities_poi o ON o.poi_id = m.origin_poi_id
     JOIN activities_poi d ON d.poi_id = m.dest_poi_id
    WHERE m.mode='walk' ORDER BY m.minutes LIMIT 15;
