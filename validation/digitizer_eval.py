#!/usr/bin/env python3
"""Feasibility test for the on-device engine, step 1: photo -> signal.

Compares the signals a digitizer recovered from our rendered images with the
original PTB-XL signals the images were drawn from (exact ground truth).

Input: a folder of <id>_<variant>_timeseries_canonical.csv files (12 columns,
values in microvolts, spanning 10 s), as written by Open-ECG-Digitizer.

Per lead it reports Pearson r and SNR (dB, the PhysioNet 2024 metric), after
removing the baseline and allowing up to +/-0.2 s of time shift. In a 3x4
layout each lead is only printed for 2.5 s, so only the printed window counts.

  .venv/bin/python digitizer_eval.py engines/out --run <name>
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import wfdb

HERE = Path(__file__).resolve().parent
LEADS = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]
# Column (0..3) of each lead in the rendered 3x4 layout; lead II also has the 10 s rhythm strip.
COLUMN = {"I": 0, "II": 0, "III": 0, "aVR": 1, "aVL": 1, "aVF": 1, "V1": 2, "V2": 2, "V3": 2, "V4": 3, "V5": 3, "V6": 3}
FS = 100  # PTB-XL low-rate files used for rendering


def truth(manifest_row: dict) -> np.ndarray:
    import pandas as pd  # noqa: F401  (wfdb needs it)
    db = HERE / "data" / "ptbxl"
    rel = DB_FILES[int(manifest_row["ecg_id"])]
    rec = wfdb.rdrecord(str(db / rel))
    names = [s.upper() for s in rec.sig_name]
    return np.nan_to_num(rec.p_signal)[:, [names.index(l.upper()) for l in LEADS]]  # (1000, 12) mV


def best_match(gt: np.ndarray, pred: np.ndarray, max_lag: int) -> tuple[float, float]:
    """Pearson r and SNR(dB) at the best lag; both series 1-D, same length, pred may have NaN."""
    best = (-1.0, -99.0)
    for lag in range(-max_lag, max_lag + 1):
        p = np.roll(pred, lag)
        ok = ~np.isnan(p) & ~np.isnan(gt)
        if ok.sum() < FS:  # need at least 1 s of overlap
            continue
        g, q = gt[ok] - np.median(gt[ok]), p[ok] - np.median(p[ok])
        if g.std() < 1e-6 or q.std() < 1e-6:
            continue
        r = float(np.corrcoef(g, q)[0, 1])
        noise = np.sum((g - q) ** 2)
        snr = float(10 * np.log10(np.sum(g ** 2) / noise)) if noise > 0 else 60.0
        if r > best[0]:
            best = (r, snr)
    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir", type=Path)
    ap.add_argument("--run", default="digitizer")
    a = ap.parse_args()

    import pandas as pd
    db = pd.read_csv(HERE / "data" / "ptbxl" / "ptbxl_database.csv", index_col="ecg_id")
    global DB_FILES
    DB_FILES = db.filename_lr.to_dict()
    man = {r["id"]: r for r in csv.DictReader(open(HERE / "images" / "manifest.csv"))}

    per_variant = defaultdict(lambda: defaultdict(list))  # variant -> lead -> [(r, snr)]
    failed = defaultdict(int)
    total = defaultdict(int)
    rows = []
    for rid, m in man.items():
        gt = truth(m)
        for variant in ("scan", "photo"):
            total[variant] += 1
            f = a.outdir / f"{rid}_{variant}_timeseries_canonical.csv"
            if not f.exists():
                failed[variant] += 1
                rows.append({"id": rid, "variant": variant, "status": "no output"})
                continue
            pred = np.genfromtxt(f, delimiter=",", skip_header=1)  # (n, 12) microvolts
            if pred.ndim != 2 or pred.shape[1] < 12:
                failed[variant] += 1
                rows.append({"id": rid, "variant": variant, "status": "bad output"})
                continue
            pred = pred / 1000.0  # -> mV
            # resample to 100 Hz over 10 s
            t_src = np.linspace(0, 10, pred.shape[0], endpoint=False)
            t_dst = np.arange(1000) / FS
            res = np.full((1000, 12), np.nan)
            for j in range(12):
                col = pred[:, j]
                ok = ~np.isnan(col)
                if ok.sum() > 10:
                    res[:, j] = np.interp(t_dst, t_src[ok], col[ok], left=np.nan, right=np.nan)
            rec_scores = {}
            for j, lead in enumerate(LEADS):
                c = COLUMN[lead]
                w0, w1 = (0, 1000) if lead == "II" else (int(c * 250), int((c + 1) * 250))
                g = gt[:, j].copy()
                g[:w0] = np.nan
                g[w1:] = np.nan
                r, snr = best_match(g, res[:, j], max_lag=20)
                per_variant[variant][lead].append((r, snr))
                rec_scores[lead] = (r, snr)
            rows.append({"id": rid, "variant": variant, "status": "ok", "expected": m["expected"],
                         "median_r": round(float(np.median([v[0] for v in rec_scores.values()])), 3),
                         "median_snr": round(float(np.median([v[1] for v in rec_scores.values()])), 2),
                         "leadII_r": round(rec_scores["II"][0], 3)})

    out = [f"# Digitizer feasibility — {a.run}", "",
           "Ground truth: the PTB-XL signals each test image was drawn from. Metrics per lead, printed window only,",
           "baseline removed, best lag within ±0.2 s. r = Pearson correlation (1 = perfect shape).",
           "SNR in dB as in PhysioNet 2024 (higher is better; ~0 dB = no better than a flat line).", ""]
    for variant in ("scan", "photo"):
        ok = total[variant] - failed[variant]
        out.append(f"## {variant}: {ok}/{total[variant]} images digitized")
        out.append("")
        out.append("| lead | median r | r ≥ 0.9 | median SNR dB |")
        out.append("|---|---|---|---|")
        allr = []
        for lead in LEADS:
            v = per_variant[variant][lead]
            if not v:
                continue
            rs = np.array([x[0] for x in v]); sn = np.array([x[1] for x in v])
            allr += list(rs)
            out.append(f"| {lead} | {np.median(rs):.2f} | {100 * np.mean(rs >= 0.9):.0f}% | {np.median(sn):.1f} |")
        if allr:
            out.append(f"| **all** | **{np.median(allr):.2f}** | **{100 * np.mean(np.array(allr) >= 0.9):.0f}%** | |")
        out.append("")
    (HERE / "results").mkdir(exist_ok=True)
    rep = HERE / "results" / f"digitizer_{a.run}.md"
    rep.write_text("\n".join(out) + "\n")
    with open(HERE / "results" / f"digitizer_{a.run}.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "variant", "status", "expected", "median_r", "median_snr", "leadII_r"])
        w.writeheader(); w.writerows(rows)
    print("\n".join(out))
    print(f"report: {rep}")
    return 0


DB_FILES: dict = {}

if __name__ == "__main__":
    sys.exit(main())
