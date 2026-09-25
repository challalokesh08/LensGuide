#!/usr/bin/env python3
"""Generate LensGuide pitch deck (8 slides) — KogniVera Hackathon 2026, PS-06."""
import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

# ----------------------------------------------------------------------------
# Theme
# ----------------------------------------------------------------------------
NAVY    = RGBColor(0x16, 0x2B, 0x4A)   # deep navy
NAVY2   = RGBColor(0x1F, 0x3A, 0x63)   # lighter navy
TEAL    = RGBColor(0x00, 0xC3, 0x89)   # accent green
ORANGE  = RGBColor(0xFF, 0x8C, 0x42)   # accent orange
LIGHT   = RGBColor(0xF4, 0xF7, 0xFB)   # light card bg
WHITE   = RGBColor(0xFF, 0xFF, 0xFF)
GREY    = RGBColor(0x5A, 0x6B, 0x80)   # muted text
DARKGREY= RGBColor(0x33, 0x40, 0x52)
GOLD    = RGBColor(0xFF, 0xC8, 0x5C)

EMU_IN = 914400
SLIDE_W, SLIDE_H = Inches(13.333), Inches(7.5)

prs = Presentation()
prs.slide_width = SLIDE_W
prs.slide_height = SLIDE_H
BLANK = prs.slide_layouts[6]


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def add_slide():
    return prs.slides.add_slide(BLANK)


def rect(slide, x, y, w, h, fill=None, line=None, shape=MSO_SHAPE.RECTANGLE,
         line_w=None, shadow=False):
    sp = slide.shapes.add_shape(shape, x, y, w, h)
    if fill is None:
        sp.fill.background()
    else:
        sp.fill.solid()
        sp.fill.fore_color.rgb = fill
    if line is None:
        sp.line.fill.background()
    else:
        sp.line.color.rgb = line
        sp.line.width = line_w or Pt(1)
    sp.shadow.inherit = False
    return sp


def text(slide, x, y, w, h, lines, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         wrap=True):
    """lines: list of (text, size, bold, color, font) or dicts."""
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = wrap
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    for i, spec in enumerate(lines):
        if isinstance(spec, tuple):
            txt, size, bold, color = spec
            font = "Calibri"
        else:
            txt, size, bold, color = spec["t"], spec["s"], spec["b"], spec["c"]
            font = spec.get("f", "Calibri")
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(4)
        r = p.add_run()
        r.text = txt
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
        r.font.name = font
    return box


def header(slide, title, kicker):
    """Standard content-slide header bar."""
    rect(slide, 0, 0, SLIDE_W, Inches(1.25), fill=NAVY)
    rect(slide, 0, Inches(1.25), SLIDE_W, Pt(4), fill=TEAL)
    text(slide, Inches(0.55), Inches(0.16), Inches(9.5), Inches(0.35),
         [(kicker.upper(), 12, True, TEAL)])
    text(slide, Inches(0.55), Inches(0.48), Inches(12.2), Inches(0.7),
         [(title, 28, True, WHITE)])
    text(slide, Inches(11.1), Inches(0.5), Inches(1.9), Inches(0.5),
         [("PS-06", 12, True, GOLD)], align=PP_ALIGN.RIGHT)


def footer(slide, n):
    text(slide, Inches(0.55), Inches(7.05), Inches(9), Inches(0.35),
         [("LensGuide · KogniVera Hackathon 2026 · PS-06", 9, False, GREY)])
    text(slide, Inches(12.3), Inches(7.05), Inches(0.8), Inches(0.35),
         [(str(n), 10, True, GREY)], align=PP_ALIGN.RIGHT)


def chip(slide, x, y, w, h, label, fill, fg=WHITE, size=11):
    sp = rect(slide, x, y, w, h, fill=fill, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    sp.adjustments[0] = 0.5
    tf = sp.text_frame
    tf.word_wrap = False
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = label
    r.font.size = Pt(size)
    r.font.bold = True
    r.font.color.rgb = fg
    return sp


def card(slide, x, y, w, h, fill=LIGHT, line=None, radius=0.12):
    sp = rect(slide, x, y, w, h, fill=fill, line=line,
              shape=MSO_SHAPE.ROUNDED_RECTANGLE, line_w=Pt(1.25))
    try:
        sp.adjustments[0] = radius
    except Exception:
        pass
    return sp


# ============================================================================
# SLIDE 1 — TITLE
# ============================================================================
s = add_slide()
rect(s, 0, 0, SLIDE_W, SLIDE_H, fill=NAVY)
rect(s, 0, Inches(4.9), SLIDE_W, Pt(4), fill=TEAL)
# decorative circles (bottom-right)
for i, (dx, dy, d, a) in enumerate([(11.2, 5.4, 2.6, 0.06), (12.2, 6.2, 1.9, 0.05)]):
    c = rect(s, Inches(dx), Inches(dy), Inches(d), Inches(d),
             fill=NAVY2, shape=MSO_SHAPE.OVAL)
    c.fill.fore_color.rgb = NAVY2
    c.fill.transparency = 0

text(s, Inches(0.9), Inches(0.9), Inches(6), Inches(0.4),
     [("KOGNIVERA HACKATHON 2026  ·  TRAVEL & TOURISM  ·  PS-06", 13, True, TEAL)])
text(s, Inches(0.9), Inches(1.7), Inches(11), Inches(1.6),
     [("LensGuide", 66, True, WHITE)])
text(s, Inches(0.9), Inches(3.0), Inches(11.5), Inches(0.8),
     [("Visual Search & AR Travel Companion", 26, False, GOLD)])
text(s, Inches(0.9), Inches(3.75), Inches(11.5), Inches(0.9),
     [("Snap a landmark, sign, or menu — get an instant, location-aware answer in "
       "your own language.", 15, False, RGBColor(0xC9, 0xD6, 0xE8))])

# feature chips
fx = 0.9
for lbl, wc in [("Snap → Identify", 3.1), ("Translate 3 Languages", 3.8),
                ("Nearby Landmarks", 3.35)]:
    chip(s, Inches(fx), Inches(5.35), Inches(wc), Inches(0.5), lbl, TEAL, size=13)
    fx += wc + 0.25

text(s, Inches(0.9), Inches(6.35), Inches(11.5), Inches(0.6),
     [("Team Reboot Rebels  ·  Cambridge Institute of Technology", 15, True, WHITE)])


# ============================================================================
# SLIDE 2 — PROBLEM & SCOPE
# ============================================================================
s = add_slide()
header(s, "Every traveller hits the same wall", "The Problem")
footer(s, 2)

# Left: pain points
card(s, Inches(0.55), Inches(1.6), Inches(6.0), Inches(5.1))
text(s, Inches(0.85), Inches(1.85), Inches(5.4), Inches(0.4),
     [("A tourist with a camera, but no context", 15, True, NAVY)])
pains = [
    ("Identify landmarks", "That monument is … what, exactly?"),
    ("Read signs & menus", "Cannot read the local script at all."),
    ("Find what's near me", "No idea where best things are from where I stand."),
    ("Language barrier", "English ↔ Kannada ↔ Telugu — nowhere, offline."),
    ("Trustworthy info", "Generic travel sites, not grounded facts."),
]
py = 2.4
for title, sub in pains:
    rect(s, Inches(0.85), Inches(py), Inches(0.16), Inches(0.75), fill=ORANGE)
    text(s, Inches(1.15), Inches(py), Inches(5.2), Inches(0.8),
         [(title, 13, True, DARKGREY), (sub, 11, False, GREY)])
    py += 0.86

# Right: PS-06 scope
card(s, Inches(6.9), Inches(1.6), Inches(5.9), Inches(5.1))
text(s, Inches(7.2), Inches(1.85), Inches(5.3), Inches(0.4),
     [("What the 24-hour data gives us", 15, True, NAVY)])
stats = [
    ("60 classes", "labelled landmarks × 10 images each (train/eval split)"),
    ("200", "menu/sign images with ground-truth text + reference translations"),
    ("900", "grounded POI facts with honest confidence bands"),
    ("3 languages", "BCP-47 only: en-IN · kn-IN · te-IN (Rule R6)"),
    ("₹0.00", "paid-API budget → local-first AI (LM Studio)"),
]
sy = 2.4
for num, sub in stats:
    rect(s, Inches(7.2), Inches(sy), Inches(1.0), Inches(0.75), fill=NAVY,
         shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    t = s.shapes[-1].text_frame
    t.word_wrap = True
    t.margin_left = t.margin_right = Emu(0)
    p = t.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = num
    r.font.size = Pt(14); r.font.bold = True; r.font.color.rgb = TEAL
    text(s, Inches(8.4), Inches(sy), Inches(4.2), Inches(0.85),
         [(sub, 11.5, False, DARKGREY)])
    sy += 0.86


# ============================================================================
# SLIDE 3 — WHAT WE BUILT (MVP)
# ============================================================================
s = add_slide()
header(s, "One camera flow, eight MVP capabilities", "What We Built")
footer(s, 3)

features = [
    ("1", "Snap → Identify", "Camera/upload to landmark, dish, sign or food with location-aware matching"),
    ("2", "Visual Search", "Local vision model recognises real-world landmarks — not just the catalogue"),
    ("3", "Translate · 3 languages", "Signs & menus → English (en-IN), Kannada (kn-IN), Telugu (te-IN)"),
    ("4", "Nearby Landmarks", "Top 10 places ranked by real device GPS (haversine), tap to open"),
    ("5", "Grounded Info Cards", "POI facts (poi_facts_kb) + knowledge chunks (place_kb) — honest confidence"),
    ("6", "Snap-to-Book", "Hours, cost (currency-exponent-aware), accessibility, carbon — one tap"),
    ("7", "Offline Demo Mode", "Full POI picker works with zero AI keys",
     ),
    ("8", "Local-First AI", "Qwen3.5 4B on LM Studio — no paid APIs, fully on-device"),
]
cw, ch, gx, gy = Inches(2.96), Inches(2.32), Inches(0.22), Inches(0.30)
start_x, start_y = Inches(0.55), Inches(1.65)
for idx, (num, title, desc) in enumerate(features):
    col, row = idx % 4, idx // 4  # 4 columns × 2 rows grid
    x = start_x + col * (cw + gx)
    y = start_y + row * (ch + gy)
    card(s, x, y, cw, ch)
    # number badge
    sp = rect(s, x + Inches(0.18), y + Inches(0.16), Inches(0.42), Inches(0.42),
              fill=TEAL, shape=MSO_SHAPE.OVAL)
    tf = sp.text_frame; tf.margin_left = tf.margin_right = Emu(0)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = num
    r.font.size = Pt(16); r.font.bold = True; r.font.color.rgb = WHITE
    text(s, x + Inches(0.72), y + Inches(0.2), cw - Inches(0.9), Inches(0.4),
         [(title, 13.5, True, NAVY)])
    text(s, x + Inches(0.18), y + Inches(0.78), cw - Inches(0.36), Inches(1.4),
         [(desc, 10.5, False, DARKGREY)])

# Roadmap strip — what comes after this MVP
card(s, Inches(0.55), Inches(6.62), Inches(12.25), Inches(0.42), fill=LIGHT)
rect(s, Inches(0.55), Inches(6.62), Inches(0.09), Inches(0.42), fill=ORANGE)
text(s, Inches(0.85), Inches(6.68), Inches(11.75), Inches(0.32),
     [("Beyond this MVP ▸  AR live overlay · 2.5D routes · 3D landmark models (xr_scenes)", 11, True, NAVY)],
     anchor=MSO_ANCHOR.MIDDLE)


# ============================================================================
# SLIDE 4 — ARCHITECTURE
# ============================================================================
s = add_slide()
header(s, "Clean three-tier design, AI at the edge", "Architecture")
footer(s, 4)

def box(s, x, y, w, h, title_lines, fill, title_color=WHITE, sub_size=10.5):
    card(s, x, y, w, h, fill=fill)
    lines = []
    for i, (t, b) in enumerate(title_lines):
        lines.append((t, 13 if i == 0 else sub_size, i == 0, title_color))
    text(s, x + Inches(0.14), y + Inches(0.1), w - Inches(0.28), h - Inches(0.2),
         lines)

# Row 0: three main tiers
fw, fin = Inches(3.6), Inches(0.0)
bx, by, bw, bh = Inches(0.55), Inches(1.6), Inches(3.75), Inches(2.15)
box(s, bx, by, bw, bh,
    [("Frontend", WHITE), ("Web SPA (JS) + React Native app", WHITE),
     ("Snap / Browse / Translate / Nearby / AR", RGBColor(0xBF, 0xE3, 0xD6))],
    NAVY2)
box(s, Inches(4.8), by, Inches(3.75), bh,
    [("Backend · Flask", WHITE), ("/api/identify · /api/translate", WHITE),
     ("/api/poi/* · /api/nearby · /api/health", RGBColor(0xBF, 0xE3, 0xD6))],
    NAVY)
box(s, Inches(9.05), by, Inches(3.75), bh,
    [("AI / LLM Layer", WHITE), ("LM Studio · Qwen3.5 4B (local)", WHITE),
     ("Gemini fallback · mock · file cache", RGBColor(0xBF, 0xE3, 0xD6))],
    NAVY2)

# arrows row 0
for ax in [Inches(4.32), Inches(8.57)]:
    ar = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, ax, Inches(2.5),
                            Inches(0.48), Inches(0.4))
    ar.fill.solid(); ar.fill.fore_color.rgb = TEAL; ar.line.fill.background()
    ar.shadow.inherit = False

# Row 1: data + cache
box(s, Inches(1.8), Inches(4.35), Inches(4.6), Inches(1.55),
    [("Read-only SQLite · PS-06.db", WHITE),
     ("D1–D9 canonical tables + poi_facts_kb, place_kb,", RGBColor(0xBF, 0xE3, 0xD6)),
     ("poi_travel_matrix, poi_media", RGBColor(0xBF, 0xE3, 0xD6))], NAVY2)
box(s, Inches(6.9), Inches(4.35), Inches(4.6), Inches(1.55),
    [("File Cache (.cache/)", WHITE),
     ("LLM responses keyed by hash — shared", RGBColor(0xBF, 0xE3, 0xD6)),
     ("across HTTPS (8000) and HTTP (8004)", RGBColor(0xBF, 0xE3, 0xD6))], NAVY2)

# arrows to row 1
ar = s.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, Inches(3.55), Inches(3.8),
                        Inches(0.4), Inches(0.5))
ar.fill.solid(); ar.fill.fore_color.rgb = TEAL; ar.line.fill.background(); ar.shadow.inherit = False
ar = s.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, Inches(10.6), Inches(3.8),
                        Inches(0.4), Inches(0.5))
ar.fill.solid(); ar.fill.fore_color.rgb = TEAL; ar.line.fill.background(); ar.shadow.inherit = False

text(s, Inches(0.55), Inches(6.15), Inches(12.3), Inches(0.8),
     [("", 8, False, GREY),
      ("GPS → identify: POI within 2 km = catalogue match · beyond 2 km = visual LLM ID + "
       "nearby from real device location", 12, False, NAVY)])

# arrow labels
text(s, Inches(4.05), Inches(2.22), Inches(1.0), Inches(0.4),
     [("REST", 9, True, GREY)], align=PP_ALIGN.CENTER)
text(s, Inches(8.3), Inches(2.22), Inches(1.0), Inches(0.4),
     [("OpenAI API", 8.5, True, GREY)], align=PP_ALIGN.CENTER)


# ============================================================================
# SLIDE 5 — AI PIPELINE
# ============================================================================
s = add_slide()
header(s, "Local-first AI: deterministic, grounded, honest", "AI Pipeline")
footer(s, 5)

# Provider chain row
text(s, Inches(0.55), Inches(1.6), Inches(6), Inches(0.4),
     [("Provider chain — openai (local) → gemini → mock", 14, True, NAVY)])
chain = [("LM Studio", "Qwen3.5 4B\nport 1234", TEAL),
         ("Gemini", "free-tier\nfallback", NAVY),
         ("Mock", "offline\ndemo", GREY)]
cx = Inches(0.55)
for name, sub, color in chain:
    card(s, cx, Inches(2.1), Inches(2.1), Inches(1.15), fill=color)
    text(s, cx + Inches(0.1), Inches(2.22), Inches(1.9), Inches(0.9),
         [(name, 14, True, WHITE), (sub, 9.5, False, WHITE)], align=PP_ALIGN.CENTER)
    if name != "Mock":
        ar = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW,
                                cx + Inches(2.12), Inches(2.5), Inches(0.42), Inches(0.36))
        ar.fill.solid(); ar.fill.fore_color.rgb = ORANGE
        ar.line.fill.background(); ar.shadow.inherit = False
    cx += Inches(2.54)

# Right: tuning box
card(s, Inches(8.15), Inches(2.1), Inches(4.65), Inches(2.0))
text(s, Inches(8.4), Inches(2.25), Inches(4.2), Inches(0.4),
     [("Tuning for a 4B local model", 13, True, NAVY)])
tuning = [
    "enable_thinking=false → fast, token-efficient",
    "Images downscaled to 768 px (context-safe)",
    "512 max tokens · JSON-only prompts",
    "In-memory + file cache keyed by message hash",
]
ty = 2.72
for t in tuning:
    rect(s, Inches(8.4), Inches(ty + 0.05), Inches(0.14), Inches(0.14), fill=TEAL,
         shape=MSO_SHAPE.OVAL)
    text(s, Inches(8.65), Inches(ty), Inches(4.05), Inches(0.6), [(t, 10.5, False, DARKGREY)])
    ty += 0.34

# Bottom: pipeline steps
steps = [("1  Identify (vision)", "JSON {kind, name, confidence_score, text}"),
         ("2  OCR text", "Extracted from sign / menu / lyrics"),
         ("3  Translate", "en-IN direct · kn-IN / te-IN via English pivot"),
         ("4  Validate script", "Kannada ⇢ ಕನ್ನಡ · Telugu ⇢ తెలుగు blocks; retry if wrong")]
sx = Inches(0.55)
sw, sg = Inches(2.99), Inches(0.2)
for i, (t, d) in enumerate(steps):
    x = sx + i * (sw + sg)
    card(s, x, Inches(4.55), sw, Inches(1.95), fill=LIGHT)
    rect(s, x, Inches(4.55), sw, Inches(0.14), fill=TEAL)
    text(s, x + Inches(0.15), Inches(4.8), sw - Inches(0.3), Inches(0.45),
         [(t, 12.5, True, NAVY)])
    text(s, x + Inches(0.15), Inches(5.3), sw - Inches(0.3), Inches(1.1),
         [(d, 10.5, False, DARKGREY)])

text(s, Inches(0.55), Inches(6.7), Inches(12.3), Inches(0.4),
     [("English pivot: local 4B can't translate kn↔te directly — translate to English first, "
       "then to target script. Script validation fails → retry, keeps output native.", 10.5, False, GREY)])


# ============================================================================
# SLIDE 6 — DATA MODEL
# ============================================================================
s = add_slide()
header(s, "Built on the official PS-06 data model", "Data Model")
footer(s, 6)

tables = [("D1", "categories"), ("D2", "currencies"), ("D3", "languages"),
          ("D4", "countries"), ("D5", "cities"), ("D6", "menu_sign_images"),
          ("D7", "xr_scenes"), ("D8", "activities_poi"), ("D9", "landmark_image_set")]
tx, ty = Inches(0.55), Inches(1.6)
tw, th, tg, tgy = Inches(2.1), Inches(1.02), Inches(0.18), Inches(0.14)
for i, (dnum, tname) in enumerate(tables):
    col, row = i % 3, i // 3  # 3 columns × 3 rows grid
    x = tx + col * (tw + tg)
    y = ty + row * (th + tgy)
    card(s, x, y, tw, th, fill=LIGHT)
    rect(s, x, y, Inches(0.55), th, fill=NAVY)
    text(s, x + Inches(0.03), y + Inches(0.3), Inches(0.5), Inches(0.4),
         [(dnum, 12, True, TEAL)], align=PP_ALIGN.CENTER)
    text(s, x + Inches(0.7), y + Inches(0.28), tw - Inches(0.8), Inches(0.5),
         [(tname, 10.5, True, NAVY)])

# extensions — four chips under the table grid
text(s, Inches(0.55), Inches(5.1), Inches(6), Inches(0.35),
     [("PS-06 extensions added on top", 12.5, True, NAVY)])
exts = [("poi_facts_kb", "grounded facts · confidence bands"),
        ("place_kb", "knowledge chunks · title + body"),
        ("poi_travel_matrix", "walk / auto / taxi precomputed"),
        ("poi_media", "images & audio per POI")]
exw, exh, exg = Inches(1.66), Inches(0.95), Inches(0.53)
for i, (t, d) in enumerate(exts):
    x = Inches(0.55) + i * (exw + exg)
    card(s, x, Inches(5.5), exw, exh, fill=LIGHT, line=RGBColor(0xDD, 0xE4, 0xEE))
    rect(s, x, Inches(5.5), exw, Inches(0.07), fill=ORANGE)
    text(s, x + Inches(0.1), Inches(5.64), exw - Inches(0.2), Inches(0.35),
         [(t, 9.5, True, NAVY)])
    text(s, x + Inches(0.1), Inches(5.98), exw - Inches(0.2), Inches(0.42),
         [(d, 8, False, GREY)])

text(s, Inches(0.55), Inches(6.62), Inches(6.7), Inches(0.3),
     [("Schema: data-model/schema.sql  ·  Seeds: data-model/seed/ (13 CSVs)  ·  Mapping: data-model/DATA_MODEL.md",
       8.5, False, GREY)])

# right: rules card
card(s, Inches(7.45), Inches(1.6), Inches(5.35), Inches(5.1), fill=NAVY)
text(s, Inches(7.75), Inches(1.8), Inches(4.9), Inches(0.4),
     [("Boundary rules enforced in code", 14, True, TEAL)])
rules = [
    ("R1", "DB opened read-only (mode=ro) — never mutated"),
    ("R2", "poi_id treated as opaque strings"),
    ("R3", "currency minor_unit_exponent → correct display (¥, ₹, KD)"),
    ("R6", "BCP-47 only — exactly en-IN · kn-IN · te-IN accepted"),
    ("R7", "WGS-84 coordinates + haversine distance"),
]
ry = 2.35
for rnum, body in rules:
    sp = rect(s, Inches(7.75), Inches(ry), Inches(0.5), Inches(0.5), fill=TEAL,
              shape=MSO_SHAPE.OVAL)
    tf = sp.text_frame; tf.margin_left = tf.margin_right = Emu(0)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    rr = p.add_run(); rr.text = rnum
    rr.font.size = Pt(11); rr.font.bold = True; rr.font.color.rgb = NAVY
    text(s, Inches(8.4), Inches(ry), Inches(4.25), Inches(0.75),
         [(body, 11.5, False, WHITE)])
    ry += 0.72

# stat line at bottom of the rules card
rect(s, Inches(7.75), Inches(5.72), Inches(4.75), Inches(0.7), fill=TEAL,
     shape=MSO_SHAPE.ROUNDED_RECTANGLE)
text(s, Inches(7.95), Inches(5.82), Inches(4.4), Inches(0.5),
     [("13 tables · 12,289 rows · PS-06.db (read-only)", 11.5, True, NAVY)],
     anchor=MSO_ANCHOR.MIDDLE)


# ============================================================================
# SLIDE 7 — DEMO PATH
# ============================================================================
s = add_slide()
header(s, "Five taps from photo to answer", "Demo Path")
footer(s, 7)

steps = [
    ("1", "Open & Allow GPS", "Snap tab · camera/upload · location shared"),
    ("2", "Snap → Identify", "Landmark / sign / menu / dish recognised by vision LLM"),
    ("3", "Get the Place", "Nearest catalogue POI (≤2 km) or live visual ID (+ name)"),
    ("4", "Explore Nearby", "Top-10 landmarks by real GPS distance — tap to open"),
    ("5", "Read Info Card", "Grounded facts, knowledge, hours, cost, accessibility"),
    ("6", "Translate", "Same photo → Kannada / Telugu / English native script"),
]
dx, dy = Inches(0.55), Inches(1.62)
dw, dh, dg, dgy = Inches(4.0), Inches(2.18), Inches(0.27), Inches(0.2)
for i, (num, title, desc) in enumerate(steps):
    col, row = i % 3, i // 3  # 3 columns × 2 rows grid
    x = dx + col * (dw + dg)
    y = dy + row * (dh + dgy)
    card(s, x, y, dw, dh)
    rect(s, x, y, dw, Inches(0.12), fill=ORANGE)
    sp = rect(s, x + Inches(0.2), y + Inches(0.26), Inches(0.55), Inches(0.55),
              fill=NAVY, shape=MSO_SHAPE.OVAL)
    tf = sp.text_frame; tf.margin_left = tf.margin_right = Emu(0)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = num
    r.font.size = Pt(18); r.font.bold = True; r.font.color.rgb = TEAL
    text(s, x + Inches(0.9), y + Inches(0.3), dw - Inches(1.05), Inches(0.45),
         [(title, 13.5, True, NAVY)])
    text(s, x + Inches(0.2), y + Inches(1.02), dw - Inches(0.4), Inches(1.1),
         [(desc, 11, False, DARKGREY)])

# Result strip
card(s, Inches(0.55), Inches(6.45), Inches(12.25), Inches(0.55), fill=TEAL)
text(s, Inches(0.85), Inches(6.5), Inches(11.8), Inches(0.45),
     [("Verified end-to-end:  Kannada lyric screenshot → translate to ಕನ್ನಡ / తెలుగు / English with correct "
       "native script, plus identify with Bangalore GPS (10 nearby landmarks).", 12.5, True, NAVY)],
     anchor=MSO_ANCHOR.MIDDLE)


# ============================================================================
# SLIDE 8 — TESTS, PROOF & DELIVERABLES
# ============================================================================
s = add_slide()
header(s, "Proof, tests, and what's in the repo", "Tests & Deliverables")
footer(s, 8)

# Left: test coverage
card(s, Inches(0.55), Inches(1.6), Inches(5.9), Inches(2.55))
text(s, Inches(0.85), Inches(1.75), Inches(5.3), Inches(0.4),
     [("Test suite (11 tests)", 14, True, NAVY)])
tests = [
    "Provider fallback on rate-limit & quota-exhaustion (429 contract)",
    "Cache prevents repeat LLM calls; transport errors → structured LLMError",
    "Only en-IN / kn-IN / te-IN accepted (Rule R6)",
    "Dataset-reference fallback when AI quota is exhausted",
]
thy = 2.3
for t in tests:
    rect(s, Inches(0.85), Inches(thy + 0.05), Inches(0.14), Inches(0.14), fill=TEAL,
         shape=MSO_SHAPE.OVAL)
    text(s, Inches(1.1), Inches(thy), Inches(5.2), Inches(0.55), [(t, 10, False, DARKGREY)])
    thy += 0.45

# Bottom-left: conformance + health
card(s, Inches(0.55), Inches(4.35), Inches(5.9), Inches(2.35), fill=LIGHT)
text(s, Inches(0.85), Inches(4.5), Inches(5.3), Inches(0.4),
     [("Data conformance & runtime health", 13, True, NAVY)])
text(s, Inches(0.85), Inches(4.98), Inches(5.3), Inches(1.5),
     [("✓  conformance tool passes D1–D9 + extensions on PS-06.db", 11, False, DARKGREY),
      ("✓  /api/health → ok:true · local_ai:true · 900 POIs indexed", 11, False, DARKGREY),
      ("✓  train/eval split respected; DB never mutated (R1)", 11, False, DARKGREY),
      ("✓  live: HTTPS :8000 (web) · HTTP :8004 (app) · LM Studio :1234", 11, False, DARKGREY)])

# Right: repo structure
text(s, Inches(6.85), Inches(1.6), Inches(6), Inches(0.4),
     [("Repository (required hackathon layout)", 14, True, NAVY)])
repo = [
    ("frontend/", "web SPA (src/) + React Native app (expo-app/)"),
    ("backend/", "Flask — app.py · llm.py · db.py + requirements.txt"),
    ("data-model/", "schema.sql · 13 seed CSVs · DATA_MODEL.md"),
    ("ai/", "prompts/ (identify.md, translate.md) · pipeline/llm.py"),
    ("docs/", "ARCHITECTURE.md (component diagram, data flows)"),
    ("tests/", "test_llm_fallback.py — 11 tests"),
    ("scripts/ + serve.sh", "start_local_ai.sh · serve.sh (root)"),
    ("README + .env.example", "8-section contract + all env vars documented"),
]
rcz_y = 2.12
for name, desc in repo:
    rect(s, Inches(6.85), Inches(rcz_y), Inches(2.05), Inches(0.4), fill=NAVY)
    t = s.shapes[-1].text_frame
    t.margin_left = t.margin_right = Emu(5000)
    p = t.paragraphs[0]
    r = p.add_run(); r.text = name
    r.font.size = Pt(10.5); r.font.bold = True; r.font.color.rgb = TEAL
    r.font.name = "Consolas"
    text(s, Inches(9.05), Inches(rcz_y + 0.01), Inches(3.7), Inches(0.5),
         [(desc, 9.5, False, DARKGREY)])
    rcz_y += 0.5

# Bottom banner
rect(s, Inches(6.85), Inches(6.25), Inches(5.95), Inches(0.55), fill=ORANGE,
     shape=MSO_SHAPE.ROUNDED_RECTANGLE)
text(s, Inches(7.05), Inches(6.31), Inches(5.6), Inches(0.45),
     [("github.com/challalokesh08/LensGuide  ·  main  ·  8/8 slides verified", 12, True, NAVY)],
     anchor=MSO_ANCHOR.MIDDLE)

out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "LensGuide_Pitch.pptx")
prs.save(out)
print("Saved:", out)