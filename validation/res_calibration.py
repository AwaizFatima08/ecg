#!/usr/bin/env python3
"""Resolution calibration (28 Oct 2026): downscale 60 Phase 0 photo renders to several long-edge widths, run the
digitizer + engine (v13c config) and compare with the adjudicated reference. Picks the width below which the engine
should refuse. Usage: res_calibration.py make | score
"""
import csv, json, random, sys, collections
from pathlib import Path
import cv2
HERE = Path(__file__).resolve().parent
LEVELS = [1600, 1200, 900, 700, 508]
adj = {r["id"]: r["reference_tier"] for r in csv.DictReader(open(HERE / "adjudication.csv"))}
man = {r["id"]: r for r in csv.DictReader(open(HERE / "images" / "manifest.csv"))}
order = {"NO_CRITICAL_PATTERN": 0, "ABNORMAL": 1, "URGENT": 2, "CRITICAL": 3}
def ids():
    ph = sorted(p.stem for p in (HERE / "images").glob("ptbxl*_photo.jpg"))
    random.Random(1).shuffle(ph)
    return sorted(ph[:60])
if sys.argv[1] == "make":
    for L in LEVELS:
        d = HERE / "work" / f"res_{L}"; d.mkdir(parents=True, exist_ok=True)
        for s in ids():
            im = cv2.imread(str(HERE / "images" / f"{s}.jpg"))
            if L < 1600:
                k = L / max(im.shape[:2]); im = cv2.resize(im, (int(im.shape[1] * k), int(im.shape[0] * k)), interpolation=cv2.INTER_AREA)
            cv2.imwrite(str(d / f"{s}.jpg"), im, [cv2.IMWRITE_JPEG_QUALITY, 90])
    print("made", len(ids()), "x", LEVELS)
else:
    print(f"{'long edge':>9} {'px/mm':>6} {'n':>3} {'agree':>6} {'critical->CRIT':>15} {'crit->=URG':>11} {'normal FA':>10} {'AF/flut/SVT/paced on normal':>28}")
    for L in LEVELS:
        f = HERE / "images" / f"readings_res{L}.jsonl"
        if not f.exists(): continue
        rows = [json.loads(l) for l in open(f)]
        n = len(rows); ag = crit = c1 = c2 = nf = nn = ar = 0
        for r in rows:
            rid = r["image"][:10]; e = adj.get(rid, man[rid]["expected"]); t = r["alert"]["tier"]; ag += t == e
            if e == "CRITICAL": crit += 1; c1 += t == "CRITICAL"; c2 += order[t] >= 2
            if e == "NO_CRITICAL_PATTERN": nn += 1; nf += order[t] >= 2; ar += (r["reading"]["rhythm"] or {}).get("code") in ("atrial_fibrillation", "atrial_flutter", "svt", "paced_rhythm", "ventricular_fibrillation")
        print(f"{L:>9} {L/260:>6.1f} {n:>3} {ag/n:>6.0%} {c1:>6}/{crit:<8} {c2:>5}/{crit:<5} {nf:>5}/{nn:<4} {ar:>12}/{nn}")
