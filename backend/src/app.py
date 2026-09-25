import math
import os

from flask import Flask, jsonify, request, send_from_directory

from backend.src import db, llm

app = Flask(__name__, static_folder="static", static_url_path="/")
ALLOWED_TARGET_LANGUAGES = {"en-IN", "kn-IN", "te-IN"}


def _llm_error_response(error):
    """Return a consistent, actionable provider error to web and mobile."""
    payload = {
        "error": str(error),
        "code": getattr(error, "code", "llm_unavailable"),
    }
    provider = getattr(error, "provider", None)
    if provider:
        payload["provider"] = provider
    retry_after = getattr(error, "retry_after", None)
    if retry_after is not None:
        payload["retry_after"] = retry_after
    if getattr(error, "status", None) == 429:
        payload["quota_exhausted"] = True
    response = jsonify(payload)
    if retry_after is not None:
        response.headers["Retry-After"] = str(max(1, int(retry_after)))
    return response, getattr(error, "status", 503)


@app.errorhandler(Exception)
def handle_error(e):
    app.logger.exception("Unhandled error")
    if isinstance(e, llm.LLMError):
        return _llm_error_response(e)
    status = getattr(e, "code", 500)
    if isinstance(e, (RuntimeError, ValueError)):
        status = 400
    return jsonify({"error": str(e)}), status


def get_poi_row(poi_id):
    conn = db.connect()
    row = conn.execute(
        "SELECT p.*, l.bcp47 AS primary_language FROM activities_poi p "
        "LEFT JOIN cities c ON c.city_id = p.city_id "
        "LEFT JOIN languages l ON l.bcp47 = c.primary_language "
        "WHERE p.poi_id = ?",
        (poi_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def poi_info(poi_id):
    conn = db.connect()
    poi = conn.execute(
        "SELECT p.*, c.name AS city_name, cnt.name AS country_name "
        "FROM activities_poi p "
        "JOIN cities c ON c.city_id = p.city_id "
        "JOIN countries cnt ON cnt.country_id = c.country_id "
        "WHERE p.poi_id = ?",
        (poi_id,),
    ).fetchone()
    if not poi:
        conn.close()
        return None

    cur = db.get_currency(conn, poi["currency"])
    poi = dict(poi)
    poi["category"] = db.CATEGORY_LABELS.get(poi["category_id"], poi["poi_category"])
    poi["entry_cost_display"] = (
        f"{cur['symbol']} {db.format_money(poi['entry_cost'], poi['currency'], cur['minor_unit_exponent'])}"
    )
    poi["tags"] = [t.strip() for t in (poi["tags"] or "").split(",") if t.strip()]

    facts = [
        dict(r)
        for r in conn.execute(
            "SELECT fact_type, confidence, fact_text, language, display_priority "
            "FROM poi_facts_kb WHERE poi_id = ? "
            "ORDER BY CASE WHEN language='en-IN' THEN 0 ELSE 1 END, display_priority LIMIT 8",
            (poi_id,),
        )
    ]

    knowledge = [
        dict(r)
        for r in conn.execute(
            "SELECT section, title, body, language, source_label "
            "FROM place_kb WHERE poi_id = ? "
            "ORDER BY CASE WHEN language='en-IN' THEN 0 ELSE 1 END, length(body) LIMIT 5",
            (poi_id,),
        )
    ]
    conn.close()
    return {"poi": poi, "facts": facts, "knowledge": knowledge}


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/health")
def health():
    return jsonify(
        {
            "ok": True,
            "provider": llm.provider(),
            "fallback_provider": llm.fallback_provider(),
            "configured_providers": llm.configured_providers(),
            "ai_configured": llm.ai_configured(),
            "local_ai": llm.is_local_openai(),
            "cache": llm.cache_stats(),
            "pois": len(list_pois()),
        }
    )


def list_pois():
    conn = db.connect()
    rows = [
        dict(r)
        for r in conn.execute(
            "SELECT p.poi_id, p.name, p.poi_category, c.name AS city "
            "FROM activities_poi p JOIN cities c ON c.city_id = p.city_id "
            "ORDER BY c.name, p.name"
        )
    ]
    conn.close()
    return rows


@app.route("/api/pois")
def pois():
    return jsonify(list_pois())


@app.route("/api/map")
def map_pois():
    """All active POIs with GPS coordinates — powers the finger-click map view."""
    conn = db.connect()
    rows = [
        dict(r)
        for r in conn.execute(
            "SELECT poi_id, name, poi_category, city_id, lat, lng, popularity_score "
            "FROM activities_poi "
            "WHERE lat IS NOT NULL AND lng IS NOT NULL AND status='active' "
            "ORDER BY popularity_score DESC"
        )
    ]
    conn.close()
    return jsonify({"pois": rows, "count": len(rows)})


@app.route("/api/poi/<poi_id>")
def poi(poi_id):
    info = poi_info(poi_id)
    if not info:
        return jsonify({"error": "Unknown POI"}), 404
    return jsonify(info)


@app.route("/api/poi/<poi_id>/nearby")
def nearby(poi_id):
    mode = request.args.get("mode", "best")
    limit = min(int(request.args.get("limit", 6)), 20)
    if mode not in ("walk", "cab", "best"):
        mode = "best"
    conn = db.connect()
    if not conn.execute("SELECT 1 FROM activities_poi WHERE poi_id=?", (poi_id,)).fetchone():
        conn.close()
        return jsonify({"error": "Unknown POI"}), 404
    rows = [
        dict(r)
        for r in conn.execute(
            "SELECT d.poi_id, d.name, d.poi_category, d.popularity_score, "
            "m.mode, m.minutes, m.distance_km, m.carbon_kg, m.cost, m.currency, m.bearing_deg "
            "FROM poi_travel_matrix m "
            "JOIN activities_poi d ON d.poi_id = m.dest_poi_id "
            "WHERE m.origin_poi_id = ? AND (? = 'best' OR m.mode = ?) "
            "ORDER BY m.minutes LIMIT 300",
            (poi_id, mode, mode),
        )
    ]
    if mode == "best":
        by_dest = {}
        for r in rows:
            prev = by_dest.get(r["poi_id"])
            if prev is None or r["minutes"] < prev["minutes"]:
                by_dest[r["poi_id"]] = r
        rows = sorted(by_dest.values(), key=lambda r: r["minutes"])[:limit]
    else:
        rows = rows[:limit]
    cur_map = {}
    for r in rows:
        cur = cur_map.get(r["currency"])
        if cur is None:
            cur = db.get_currency(conn, r["currency"])
            cur_map[r["currency"]] = cur
        r["cost_display"] = (
            f"{cur['symbol']} {db.format_money(r['cost'], r['currency'], cur['minor_unit_exponent'])}"
        )
    conn.close()
    return jsonify({"mode": mode, "nearby": rows})


@app.route("/api/nearby")
def nearby_location():
    """Return POIs sorted by Haversine distance from (lat, lng)."""
    try:
        lat = float(request.args.get("lat"))
        lng = float(request.args.get("lng"))
    except (TypeError, ValueError):
        return jsonify({"error": "lat and lng required"}), 400
    limit = min(max(int(request.args.get("limit", 10)), 1), 25)
    conn = db.connect()
    rows = []
    for r in conn.execute(
        "SELECT poi_id, name, poi_category, city_id, lat, lng, poi_category, popularity_score FROM activities_poi WHERE lat IS NOT NULL AND lng IS NOT NULL AND status='active'"
    ).fetchall():
        d = _haversine(lat, lng, float(r["lat"]), float(r["lng"]))
        rows.append({**dict(r), "distance_km": round(d, 2)})
    conn.close()
    rows.sort(key=lambda x: x["distance_km"])
    rows = rows[:limit]
    return jsonify({"lat": lat, "lng": lng, "nearby": rows})


def _haversine(lat1, lng1, lat2, lng2):
    R = 6371.0
    p = math.pi / 180
    dlat = (lat2 - lat1) * p
    dlng = (lng2 - lng1) * p
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin(dlng / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


@app.route("/api/poi/<poi_id>/book")
def book(poi_id):
    conn = db.connect()
    row = conn.execute(
        "SELECT p.poi_id, p.name, p.poi_category, p.entry_cost, p.currency, "
        "p.opens_at, p.closes_at, p.closed_days, p.accessibility, p.best_season, "
        "p.typical_duration_minutes, p.carbon_kg, p.has_xr_scene, p.description, "
        "c.name AS city_name "
        "FROM activities_poi p JOIN cities c ON c.city_id = p.city_id "
        "WHERE p.poi_id = ?",
        (poi_id,),
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Unknown POI"}), 404
    data = dict(row)
    cur = db.get_currency(conn, data["currency"])
    data["currency_display"] = cur
    data["entry_cost_display"] = (
        f"{cur['symbol']} {db.format_money(data['entry_cost'], data['currency'], cur['minor_unit_exponent'])}"
    )
    data["closed_days"] = [d for d in (data["closed_days"] or "").split(",") if d]
    conn.close()
    return jsonify(data)


@app.route("/api/identify", methods=["POST"])
def identify():
    file = request.files.get("image")
    if not file:
        return jsonify({"error": "No image uploaded (field name 'image')"}), 400
    
    # Optional location from device
    lat = request.form.get("lat")
    lng = request.form.get("lng")
    has_location = False
    if lat is not None and lng is not None:
        try:
            lat = float(lat)
            lng = float(lng)
            has_location = True
        except (TypeError, ValueError):
            pass
    
    b64, mime = llm.image_to_b64(file)
    try:
        result = llm.identify_poi(b64, mime)
    except llm.LLMError as e:
        return _llm_error_response(e)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503

    kind = result.get("kind")
    label_class = (result.get("label_class") or "").strip()
    name = (result.get("name") or "").strip()
    confidence = (result.get("confidence") or "low").lower()
    if confidence not in ("high", "medium", "low"):
        confidence = "low"
    score = _parse_score(result, confidence)

    # ---- Confidence Gate ----
    THRESH = 0.85
    ocr_text = (result.get("text") or "").strip()
    matched = None
    candidates = []
    status = "not_recognised"
    reason = "no_candidate"
    identified_place = None
    nearby_pois = []

    # PRIMARY: If location provided, find nearest known POI as the identified place
    min_dist = None
    nearest_row = None
    if has_location:
        conn = db.connect()
        min_dist = float('inf')
        for r in conn.execute(
            "SELECT poi_id, name, poi_category, city_id, lat, lng, popularity_score, description "
            "FROM activities_poi WHERE lat IS NOT NULL AND lng IS NOT NULL AND status='active'"
        ).fetchall():
            d = _haversine(lat, lng, float(r["lat"]), float(r["lng"]))
            if d < min_dist:
                min_dist = d
                nearest_row = {**dict(r), "distance_km": round(d, 2)}
        conn.close()
        
        if nearest_row:
            identified_place = nearest_row
            # Use this as the matched POI
            matched = {"poi_id": nearest_row["poi_id"], "name": nearest_row["name"]}
            status = "recognised"
            reason = "location_match"
            name = nearest_row["name"]
            confidence = "high"
            score = 1.0
            
            # Fetch nearby POIs from the IDENTIFIED place location (not device location)
            place_lat, place_lng = nearest_row["lat"], nearest_row["lng"]
            conn = db.connect()
            nearby_rows = []
            for r in conn.execute(
                "SELECT poi_id, name, poi_category, city_id, lat, lng, popularity_score FROM activities_poi WHERE lat IS NOT NULL AND lng IS NOT NULL AND status='active'"
            ).fetchall():
                d = _haversine(place_lat, place_lng, float(r["lat"]), float(r["lng"]))
                if d > 0.05:  # exclude the place itself (within 50m)
                    nearby_rows.append({**dict(r), "distance_km": round(d, 2)})
            conn.close()
            nearby_rows.sort(key=lambda x: x["distance_km"])
            nearby_pois = nearby_rows[:10]
    
    # SECONDARY: Visual recognition (for signs, or when no location match)
    if not identified_place and kind == "sign" and ocr_text:
        status, reason = "recognised", "above_threshold"
        name = ocr_text
        confidence, score = "high", max(score, 1.0)
        identified_place = None  # signs don't have a fixed location
    elif not identified_place and score >= THRESH:
        status, reason = "recognised", "above_threshold"
        poi_id = match_poi(label_class, name)
        if poi_id:
            info = poi_info(poi_id)
            if info:
                matched = {"poi_id": poi_id, "name": info["poi"]["name"]}
        confidence = "high" if score >= THRESH else confidence
    elif not identified_place:
        candidates = poi_candidates(label_class, name, limit=3)
        if candidates:
            status, reason = "candidates", "below_threshold"
        name = ""
    
    # FALLBACK: If location provided but nearest catalogued POI is far (>2km),
    # also try LLM's visual identification as the place name
    if has_location and min_dist is not None and min_dist > 2.0:
        # LLM already identified something from the image
        if kind in ("landmark", "food", "sign") and name and score >= 0.6:
            # For signs, use OCR text as the name
            visual_name = name if kind != "sign" else (ocr_text[:200] if ocr_text else name)
            # Try to fuzzy-match LLM's name to our database
            poi_id = match_poi(label_class, visual_name)
            if poi_id:
                info = poi_info(poi_id)
                if info:
                    matched = {"poi_id": poi_id, "name": info["poi"]["name"]}
                    identified_place = info["poi"]
                    identified_place["distance_km"] = round(_haversine(lat, lng, identified_place["lat"], identified_place["lng"]), 2)
                    status = "recognised"
                    reason = "visual_match_fuzzy"
                    # Re-fetch nearby from the matched place
                    place_lat, place_lng = identified_place["lat"], identified_place["lng"]
                    conn = db.connect()
                    nearby_rows = []
                    for r in conn.execute(
                        "SELECT poi_id, name, poi_category, city_id, lat, lng, popularity_score FROM activities_poi WHERE lat IS NOT NULL AND lng IS NOT NULL AND status='active'"
                    ).fetchall():
                        d = _haversine(place_lat, place_lng, float(r["lat"]), float(r["lng"]))
                        if d > 0.05:
                            nearby_rows.append({**dict(r), "distance_km": round(d, 2)})
                    conn.close()
                    nearby_rows.sort(key=lambda x: x["distance_km"])
                    nearby_pois = nearby_rows[:10]
            else:
                # No database match - return LLM's identification as "identified_place" 
                # with flag that it's not in our catalogue
                identified_place = {
                    "name": visual_name,
                    "poi_category": label_class or kind,
                    "description": result.get("description", ""),
                    "poi_id": None,
                    "in_catalogue": False,
                    "confidence": confidence,
                    "confidence_score": score,
                    "distance_km": round(min_dist, 2)
                }
                matched = None  # Clear matched - this is visual ID, not database match
                status = "recognised"
                reason = "visual_identification"
                
                # Fetch nearby POIs from DEVICE location (not database POI)
                conn = db.connect()
                nearby_rows = []
                for r in conn.execute(
                    "SELECT poi_id, name, poi_category, city_id, lat, lng, popularity_score FROM activities_poi WHERE lat IS NOT NULL AND lng IS NOT NULL AND status='active'"
                ).fetchall():
                    d = _haversine(lat, lng, float(r["lat"]), float(r["lng"]))
                    nearby_rows.append({**dict(r), "distance_km": round(d, 2)})
                conn.close()
                nearby_rows.sort(key=lambda x: x["distance_km"])
                nearby_pois = nearby_rows[:10]

    return jsonify(
        {
            "kind": kind,
            "label_class": label_class if kind != "sign" and status == "recognised" else None,
            "name": name,
            "confidence": confidence,
            "confidence_score": round(score, 2),
            "status": status,
            "reason": reason,
            "description": result.get("description", ""),
            "ocr_text": ocr_text,
            "matched": matched,
            "candidates": candidates,
            "identified_place": identified_place,
            "nearby": nearby_pois,
            "location": {"lat": lat, "lng": lng} if has_location else None,
        }
    )


def _parse_score(result, confidence):
    """Numeric 0..1. Prefer the LLM's confidence_score; fall back to the label."""
    raw = result.get("confidence_score")
    if raw is not None:
        try:
            s = float(raw)
            if 0.0 <= s <= 1.0:
                return s
        except (TypeError, ValueError):
            pass
    return {"high": 0.9, "medium": 0.65, "low": 0.35}.get(confidence, 0.35)


def poi_candidates(label_class, name, limit=3, min_score=0.45):
    """Top plausible POIs for a below-threshold input. Each has a score; the
    CLIENT asks the traveller to pick one, then grounds on it."""
    conn = db.connect()
    rows = conn.execute(
        "SELECT poi_id, name FROM activities_poi WHERE status='active'"
    ).fetchall()
    conn.close()
    scored = []
    if label_class and label_class != "none":
        pid = db.POI_INDEX.get(label_class)
        if pid:
            for r in rows:
                if r["poi_id"] == pid:
                    scored.append((pid, r["name"], 0.95))
                    break
    if name:
        name_l = name.lower()
        for r in rows:
            if any(s[0] == r["poi_id"] for s in scored):
                continue
            target = r["name"].lower()
            if target == name_l:
                s = 0.9
            elif name_l in target or target in name_l:
                s = 0.7
            else:
                tokens = set(name_l.split())
                s = len(tokens & set(target.split())) / max(len(tokens), 1)
            if s >= min_score:
                scored.append((r["poi_id"], r["name"], s))
    best = sorted(scored, key=lambda t: -t[2])[:limit]
    return [{"poi_id": p, "name": n, "score": round(s, 2)} for p, n, s in best]


def match_poi(label_class, name):
    """Resolve recognition output to a poi_id. Prefer the 60-class label map, then name match."""
    if label_class and label_class != "none":
        pid = db.POI_INDEX.get(label_class)
        if pid:
            return pid
    if not name:
        return None
    name_l = name.lower()
    conn = db.connect()
    rows = conn.execute(
        "SELECT poi_id, name FROM activities_poi WHERE status='active'"
    ).fetchall()
    conn.close()
    best, best_score = None, 0.0
    for r in rows:
        target = r["name"].lower()
        score = 0.0
        if target == name_l:
            score = 1.0
        elif name_l in target or target in name_l:
            score = 0.7
        else:
            tokens = set(name_l.split())
            overlap = len(tokens & set(target.split()))
            score = overlap / max(len(tokens), 1)
        if score > best_score:
            best, best_score = r["poi_id"], score
    return best if best_score >= 0.4 else None


@app.route("/api/translate", methods=["POST"])
def translate():
    data = request.get_json(silent=True) or {}
    form = request.form
    text = (data.get("text") or form.get("text") or "").strip()
    source = data.get("source") or form.get("source") or "auto"
    target = data.get("target") or form.get("target") or "en-IN"
    if not isinstance(target, str) or target not in ALLOWED_TARGET_LANGUAGES:
        return jsonify({"error": "Unsupported target language"}), 400

    upload = request.files.get("image")
    b64, mime = None, None
    if upload:
        b64, mime = llm.image_to_b64(upload)

    def _norm_lang(tag):
        t = (tag or "auto").strip().lower()
        if t in ("english", "en", "en-in", "en-us", "en-gb"):
            return "en"
        if t in ("kannada", "kn", "kn-in"):
            return "kn"
        if t in ("telugu", "te", "te-in"):
            return "te"
        if t in ("hindi", "hi", "hi-in"):
            return "hi"
        return t or "auto"

    def _detect_script_lang(text):
        """Detect language from script in text."""
        if not text:
            return "auto"
        # Check for Kannada script
        if any(0x0C80 <= ord(c) <= 0x0CFF for c in text):
            return "kn"
        # Check for Telugu script
        if any(0x0C00 <= ord(c) <= 0x0C7F for c in text):
            return "te"
        # Check for Devanagari
        if any(0x0900 <= ord(c) <= 0x097F for c in text):
            return "hi"
        # Check for Latin
        if any(0x0041 <= ord(c) <= 0x005A or 0x0061 <= ord(c) <= 0x007A for c in text):
            return "en"
        return "auto"

    ocr_text = ""
    ocr_source = "auto"
    if not text and b64:
        try:
            ocr = llm.identify_poi(b64, mime)
        except llm.LLMError as e:
            return _llm_error_response(e)
        except RuntimeError as e:
            return jsonify({"error": str(e)}), 503
        ocr_text = (ocr.get("text") or "").strip()
        ocr_source = _norm_lang(ocr.get("source_language"))
        if ocr_source == "auto":
            ocr_source = _detect_script_lang(ocr_text)
        text = ocr_text
        source = ocr_source

    if not text:
        return jsonify({"error": "No text to translate"}), 400

    # Prefer the bundled English reference for exact dataset text.
    reference = find_reference_translation(text, "en-IN")
    if reference and target == "en-IN":
        return jsonify(_dataset_reference_payload(text, source, target))

    translation_input = text
    translation_source = source
    translation_basis = "direct"

    # For kn-IN/te-IN targets, pivot through English (model can't do direct kn↔te)
    if target in ("kn-IN", "te-IN"):
        # Translate to English first
        english_result = llm.translate_text(text, source=source, target="en-IN")
        translation_input = english_result.get("translation", "")
        translation_source = "en"
        translation_basis = "english_pivot"
    # For exact dataset matches, use the known reference translation
    elif reference and target in ("kn-IN", "te-IN"):
        translation_input = reference["reference_translation"]
        translation_source = "en"
        translation_basis = "dataset_reference"

    try:
        result = llm.translate_text(
            translation_input,
            source=translation_source,
            target=target,
        )
    except llm.LLMError as e:
        fallback = _dataset_reference_payload(text, source, target)
        if fallback:
            return jsonify(fallback)
        return _llm_error_response(e)
    except RuntimeError as e:
        fallback = _dataset_reference_payload(text, source, target)
        if fallback:
            return jsonify(fallback)
        return jsonify({"error": str(e)}), 503

    translation = (result.get("translation") or "").strip()
    return jsonify(
        {
            "ocr_text": text,
            "translation": translation,
            "source_language": (
                reference.get("source_language")
                if translation_basis == "dataset_reference"
                else result.get("source_language") or source
            ),
            "target_language": target,
            "confidence": (result.get("confidence") or "low").lower(),
            "reference": reference,
            "matches_reference": bool(
                target == "en-IN"
                and reference
                and translation.strip().lower() == reference["reference_translation"].strip().lower()
            ),
            "translation_basis": translation_basis,
        }
    )


def find_reference_translation(text, target="en-IN"):
    """Return only an exact, target-matching dataset translation.

    Exact matching prevents an arbitrary OCR fragment from being compared with
    an unrelated sign. This is grounded data, not generated translation.
    """
    conn = db.connect()
    row = conn.execute(
        "SELECT image_id, kind, source_language, reference_translation, "
        "difficulty, is_safety_critical, dataset_split "
        "FROM menu_sign_images WHERE trim(source_text_truth) = trim(?) "
        "AND (trim(target_language) = trim(?) OR target_language IS NULL) "
        "ORDER BY CASE WHEN trim(target_language) = trim(?) THEN 0 ELSE 1 END, image_id LIMIT 1",
        (text, target, target),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def _dataset_reference_payload(text, source, target):
    reference = find_reference_translation(text, target)
    if not reference:
        return None
    return {
        "ocr_text": text,
        "translation": reference["reference_translation"],
        "source_language": reference.get("source_language") or source,
        "target_language": target,
        "confidence": "high",
        "reference": reference,
        "matches_reference": True,
        "fallback": "dataset_reference",
    }


@app.route("/api/classes")
def classes():
    return jsonify(db.LABEL_CLASSES)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)