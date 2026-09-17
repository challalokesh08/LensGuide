import os

from flask import Flask, jsonify, request, send_from_directory

from lensguide import db, llm

app = Flask(__name__, static_folder="static", static_url_path="/")


@app.errorhandler(Exception)
def handle_error(e):
    app.logger.exception("Unhandled error")
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
    return jsonify({"ok": True, "provider": llm.provider(), "pois": len(list_pois())})


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
    b64, mime = llm.image_to_b64(file)
    try:
        result = llm.identify_poi(b64, mime)
    except RuntimeError as e:
        return jsonify({"error": str(e), "insecure": True}), 503

    kind = result.get("kind")
    label_class = (result.get("label_class") or "").strip()
    name = (result.get("name") or "").strip()
    confidence = (result.get("confidence") or "low").lower()
    if confidence not in ("high", "medium", "low"):
        confidence = "low"

    poi_id = match_poi(label_class, name)
    matched = None
    if poi_id:
        info = poi_info(poi_id)
        if info:
            matched = {"poi_id": poi_id, "name": info["poi"]["name"]}

    return jsonify(
        {
            "kind": kind,
            "label_class": label_class if kind != "sign" else None,
            "name": name,
            "confidence": confidence,
            "description": result.get("description", ""),
            "ocr_text": result.get("text", "") if kind == "sign" else "",
            "matched": matched,
        }
    )


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
    text = (data.get("text") or "").strip()
    source = data.get("source", "auto")
    target = data.get("target", "en-IN")

    upload = request.files.get("image")
    b64, mime = None, None
    if upload:
        b64, mime = llm.image_to_b64(upload)

    if not text and b64:
        try:
            ocr = llm.identify_poi(b64, mime)
        except RuntimeError as e:
            return jsonify({"error": str(e)}), 503
        text = (ocr.get("text") or "").strip()
        if ocr.get("kind") == "sign":
            source = ocr.get("label_class") or source

    if not text:
        return jsonify({"error": "No text to translate"}), 400

    try:
        result = llm.translate_text(text, source=source, target=target)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503

    translation = (result.get("translation") or "").strip()
    reference = find_reference_translation(text)
    return jsonify(
        {
            "ocr_text": text,
            "translation": translation,
            "source_language": result.get("source_language") or source,
            "target_language": target,
            "confidence": (result.get("confidence") or "low").lower(),
            "reference": reference,
            "matches_reference": bool(
                reference and translation.strip().lower() == reference["reference_translation"].strip().lower()
            ),
        }
    )


def find_reference_translation(text):
    """Score translation against menu_sign_images ground truth (train+eval)."""
    conn = db.connect()
    row = conn.execute(
        "SELECT image_id, kind, reference_translation, difficulty, is_safety_critical, dataset_split "
        "FROM menu_sign_images WHERE trim(source_text_truth) = trim(?) OR "
        "instr(trim(source_text_truth), trim(?)) > 0 LIMIT 1",
        (text, text),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


@app.route("/api/classes")
def classes():
    return jsonify(db.LABEL_CLASSES)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)