#!/usr/bin/env python3
"""Scores a digitizer output folder against the true PTB-XL signals (same metric as validation/digitizer_eval.py):
per lead, printed window only, baseline removed, best lag within +/-0.2 s -> Pearson r and SNR (dB).

  python score_digitizer.py <manifest.csv> <digitized_dir> <label>   -> appends a line to out/digitizer_scores.tsv
"""
import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import wfdb

HERE = Path(__file__).resolve().parent
LEADS = ["I", "II", "III", "AVR", "AVL", "AVF", "V1", "V2", "V3", "V4", "V5", "V6"]
COLUMN = [0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3]


def best(gt, pred, max_lag=20):
    out = (-1.0, -99.0)
    for lag in range(-max_lag, max_lag + 1):
        p = np.roll(pred, lag)
        ok = ~np.isnan(p) & ~np.isnan(gt)
        if ok.sum() < 100:
            continue
        g, q = gt[ok] - np.median(gt[ok]), p[ok] - np.median(p[ok])
        if g.std() < 1e-6 or q.std() < 1e-6:
            continue
        r = float(np.corrcoef(g, q)[0, 1])
        noise = np.sum((g - q) ** 2)
        if r > out[0]:
            out = (r, float(10 * np.log10(np.sum(g ** 2) / noise)) if noise > 0 else 60.0)
    return out


def main():
    man, ddir, label = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    db = pd.read_csv(HERE / "data/ptbxl/ptbxl_database.csv", index_col="ecg_id")
    res = {"scan": [], "photo": []}
    fails = {"scan": 0, "photo": 0}
    for row in csv.DictReader(open(man)):
        rec = wfdb.rdrecord(str(HERE / "data/ptbxl" / db.loc[int(row["ecg_id"])].filename_lr))
        n = [s.upper() for s in rec.sig_name]
        gt = np.nan_to_num(rec.p_signal)[:, [n.index(l) for l in LEADS]]
        for v in ("scan", "photo"):
            f = ddir / f"{row['id']}_{v}_timeseries_canonical.csv"
            if not f.exists():
                fails[v] += 1
                continue
            pred = np.genfromtxt(f, delimiter=",", skip_header=1) / 1000.0
            t_src = np.linspace(0, 10, pred.shape[0], endpoint=False)
            for j in range(12):
                col = pred[:, j]
                ok = ~np.isnan(col)
                x = np.full(1000, np.nan)
                if ok.sum() > 10:
                    x = np.interp(np.arange(1000) / 100, t_src[ok], col[ok], left=np.nan, right=np.nan)
                w0, w1 = (0, 1000) if j == 1 else (COLUMN[j] * 250, (COLUMN[j] + 1) * 250)
                g = gt[:1000, j].copy()
                g[:w0] = np.nan
                g[w1:] = np.nan
                res[v].append(best(g, x))
    line = [label]
    for v in ("scan", "photo"):
        r = np.array([a for a, _ in res[v]])
        s = np.array([b for _, b in res[v]])
        line += [f"{v}: median r {np.median(r):.3f}, r>=0.9 {100 * np.mean(r >= 0.9):.0f}%, "
                 f"median SNR {np.median(s):.1f} dB, failed {fails[v]}"]
    print(" | ".join(line), flush=True)
    with open(HERE / "out" / "digitizer_scores.tsv", "a") as fh:
        fh.write("\t".join(line) + "\n")


if __name__ == "__main__":
    main()
