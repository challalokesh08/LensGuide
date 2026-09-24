#!/usr/bin/env python
"""Score the live /api/translate endpoint against menu_sign_images ground truth.

Usage:
    .venv/bin/python scripts/eval_translate.py [--split eval] [--limit 50]
                          [--start 0] [--base https://localhost:8000] [--out out.jsonl]

Sends each dataset row's source_text_truth to the running LensGuide server and
compares the returned translation with reference_translation. Reports exact
match rate, mean token-F1, and breakdowns by difficulty, kind and
safety-criticality. Paces requests to respect the server's own LLM spacing and
retries rate-limit (503) responses a couple of times.
"""
import argparse
import json
import re
import sqlite3
import ssl
import sys
import time
import urllib.request

sys.path.insert(0, ".")
from lensguide import db  # noqa: E402


def token_f1(pred: str, ref: str) -> float:
    pt = re.findall(r"\w+", pred.lower())
    rt = re.findall(r"\w+", ref.lower())
    if not pt or not rt:
        return 1.0 if not pt and not rt else 0.0
    from collections import Counter
    common = sum((Counter(pt) & Counter(rt)).values())
    if common == 0:
        return 0.0
    prec, rec = common / len(pt), common / len(rt)
    return 2 * prec * rec / (prec + rec)


def post_translate(base: str, text: str, ctx: ssl.SSLContext, retries: int = 3, backoff: float = 20.0):
    body = json.dumps({"text": text}).encode()
    for attempt in range(retries + 1):
        req = urllib.request.Request(
            f"{base}/api/translate", data=body,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120, context=ctx) as r:
                return json.loads(r.read().decode()), None
        except urllib.error.HTTPError as e:
            try:
                payload = json.loads(e.read().decode())
            except Exception:
                payload = {}
            msg = payload.get("error", f"HTTP {e.code}")
            if ("rate-limited" in msg.lower() or "LLM provider error" in msg) and attempt < retries:
                time.sleep(backoff)
                continue
            return None, msg
        except Exception as e:
            return None, str(e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="eval", choices=["eval", "train", "all"])
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0, help="0 = all rows in split")
    ap.add_argument("--base", default="https://localhost:8000")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    ctx = ssl._create_unverified_context() if args.base.startswith("https") else None
    conn = db.connect()
    conn.row_factory = sqlite3.Row
    q = ("SELECT image_id, kind, source_text_truth, reference_translation, "
         "difficulty, is_safety_critical, source_language, dataset_split "
         "FROM menu_sign_images WHERE reference_translation != ''")
    if args.split != "all":
        q += " AND dataset_split = ?"
        rows = conn.execute(q + " ORDER BY image_id", (args.split,)).fetchall()
    else:
        rows = conn.execute(q + " ORDER BY image_id").fetchall()
    conn.close()
    rows = rows[args.start: args.start + args.limit] if args.limit else rows[args.start:]
    if not rows:
        print("no rows selected"); return

    out_f = open(args.out, "w") if args.out else None
    n = exact = 0
    f1_sum = 0.0
    buckets = {}
    fails = []

    for i, r in enumerate(rows, 1):
        truth = r["source_text_truth"].strip()
        ref = r["reference_translation"].strip()
        res, err = post_translate(args.base, truth, ctx)
        if err or not res:
            fails.append((r["image_id"], err))
            print(f"[{i}/{len(rows)}] {r['image_id']} FAILED: {err}")
            continue
        pred = (res.get("translation") or "").strip()
        em = pred.lower() == ref.lower()
        f1 = token_f1(pred, ref)
        n += 1
        exact += em
        f1_sum += f1
        for key in (f"difficulty={r['difficulty']}", f"kind={r['kind']}",
                    f"safety={bool(r['is_safety_critical'])}", "overall"):
            b = buckets.setdefault(key, [0, 0, 0.0])
            b[0] += 1; b[1] += em; b[2] += f1
        rec = {"image_id": r["image_id"], "kind": r["kind"], "difficulty": r["difficulty"],
               "safety": bool(r["is_safety_critical"]), "lang": r["source_language"],
               "truth": truth, "ref": ref, "pred": pred, "exact": em, "f1": round(f1, 3)}
        if out_f:
            out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        flag = "OK " if em else ("~  " if f1 >= 0.6 else "MISS")
        print(f"[{i}/{len(rows)}] {flag} f1={f1:.2f} | {ref[:38]!r} -> {pred[:38]!r}")
        time.sleep(1)  # server paces LLM calls itself; keep client gentle too

    if out_f:
        out_f.close()
    print(f"\n=== {args.split} split, {n} scored, {len(fails)} failed requests ===")
    print(f"exact match: {exact}/{n} = {exact / max(n, 1):.0%}")
    print(f"mean token-F1: {f1_sum / max(n, 1):.3f}")
    for key in sorted(buckets):
        c, e, f = buckets[key]
        print(f"  {key:24} n={c:3}  exact={e / c:5.0%}  f1={f / c:.3f}")


if __name__ == "__main__":
    main()
