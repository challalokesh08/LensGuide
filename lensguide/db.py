import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def db_path():
    override = os.environ.get("DATABASE_PATH", "").strip()
    return override or os.path.join(BASE_DIR, "data", "PS-06.db")


def connect():
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_currency(conn, iso4217):
    row = conn.execute(
        "SELECT * FROM currencies WHERE iso4217 = ?", (iso4217,)
    ).fetchone()
    return dict(row) if row else {"iso4217": iso4217, "symbol": iso4217, "minor_unit_exponent": 2}


def format_money(amount_str, currency_code, minor_unit_exponent=2):
    """Render money with the true minor-unit exponent. amount_str stays a string (R3)."""
    try:
        amt = int(round(float(amount_str) * (10 ** minor_unit_exponent)))
    except (TypeError, ValueError):
        return amount_str
    if minor_unit_exponent == 0:
        return f"{amt:,}"
    whole = amt // (10 ** minor_unit_exponent)
    frac = abs(amt) % (10 ** minor_unit_exponent)
    return f"{whole:,}.{frac:0{minor_unit_exponent}d}"


LABEL_CLASSES = []
POI_INDEX = {}
CATEGORY_LABELS = {}


def load_label_index():
    global LABEL_CLASSES, POI_INDEX, CATEGORY_LABELS
    conn = connect()
    LABEL_CLASSES = [
        r["label_class"]
        for r in conn.execute(
            "SELECT DISTINCT label_class FROM landmark_image_set ORDER BY label_class"
        )
    ]
    for r in conn.execute(
        "SELECT label_class, poi_id FROM landmark_image_set WHERE poi_id IS NOT NULL GROUP BY label_class"
    ):
        POI_INDEX[r["label_class"]] = r["poi_id"]
    for r in conn.execute("SELECT category_id, label FROM categories"):
        CATEGORY_LABELS[r["category_id"]] = r["label"]
    conn.close()


load_label_index()