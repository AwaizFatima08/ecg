#!/usr/bin/env python3
"""Grid self-check diagnostics (28 Oct 2026): does the digitizer actually find the paper grid? Per image: the two
autocorrelation estimates (columns / rows) of px-per-mm, their peak strengths, and whether the prior was used.
  grid_diag.py <jpg dir> <out csv> [limit]"""
import csv, sys
from pathlib import Path
import cv2, numpy as np
import lite_digitizer as L
d, out = Path(sys.argv[1]), Path(sys.argv[2]); lim = int(sys.argv[3]) if len(sys.argv) > 3 else 0
seg = L.Segmenter(None, Path("models/onnx/student_16_32_64_128_160_160.pt"))
fs = sorted(d.glob("*.jpg"))[:lim or None]
rows = []
for f in fs:
    sig, grid = L.segment(cv2.imread(str(f)), seg, 1600, 0)
    ang = L.best_rotation(grid); sig, grid = L.rotate(sig, ang), L.rotate(grid, ang)
    cols = np.where(sig.sum(0) > sig.sum(0).max() * 0.05)[0]
    prior = (cols[-1] - cols[0]) / 258.0
    lo, hi = int(5 * prior * 0.75), int(np.ceil(5 * prior * 1.25)); r = {"file": f.stem, "prior": round(prior, 2), "ppm_x": "", "ac_x": "", "ppm_y": "", "ac_y": ""}
    for key, prof in (("x", grid.sum(0)), ("y", grid.sum(1))):
        prof = prof - prof.mean(); ac = np.correlate(prof, prof, mode="full")[len(prof) - 1:]; ac /= ac[0] + 1e-9
        if hi + 1 >= len(ac) or lo < 2: continue
        lag = lo + int(np.argmax(ac[lo:hi + 1])); r[f"ac_{key}"] = round(float(ac[lag]), 3)
        if ac[lag] < 0.05 or lag in (lo, hi): continue
        r[f"ppm_{key}"] = round(lag / 5, 2)
    rows.append(r)
with open(out, "w", newline="") as fh:
    w = csv.DictWriter(fh, rows[0].keys()); w.writeheader(); w.writerows(rows)
print("done", len(rows))
