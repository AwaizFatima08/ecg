#!/usr/bin/env python3
"""Time-axis check of digitized Phase 0 traces against the clean PTB-XL signal: best lag of lead II (rhythm strip)
and of the 3x4 leads (rows), in samples at 100 Hz. Usage: lag_check.py <digitized dir>"""
import sys, pathlib, collections
import numpy as np, pandas as pd, wfdb
from engine_e2e import load_digitized
from ecg_measure import COLUMN
DB = "data/ptbxl"; LEADS = ["I","II","III","AVR","AVL","AVF","V1","V2","V3","V4","V5","V6"]
df = pd.read_csv(f"{DB}/ptbxl_database.csv", index_col="ecg_id")
def best_lag(a, x, lo, hi, rng=30):
    cands = [(np.corrcoef(a[lo:hi], x[lo + l:hi + l])[0, 1], l) for l in range(-rng, rng + 1) if lo + l >= 0 and hi + l <= 1000]
    return max(cands, key=lambda t: t[0])
strip, rows, r_strip, r_rows = collections.Counter(), collections.Counter(), [], []
for f in sorted(pathlib.Path(sys.argv[1]).glob("*_timeseries_canonical.csv")):
    eid = int(f.name[5:10]); x = load_digitized(f)
    if x is None: continue
    rec = wfdb.rdrecord(f"{DB}/{df.loc[eid].filename_lr}"); n = [s.upper() for s in rec.sig_name]
    c = np.nan_to_num(rec.p_signal)[:, [n.index(l) for l in LEADS]].T[:, :1000]; x = np.nan_to_num(x)
    r, l = best_lag(c[1], x[1], 40, 960, 60); strip[min(abs(l) // 5 * 5, 30)] += 1; r_strip.append(np.corrcoef(c[1], x[1])[0, 1])
    for j in range(12):
        if j == 1: continue
        w0, w1 = COLUMN[j] * 250, (COLUMN[j] + 1) * 250
        r, l = best_lag(c[j], x[j], w0 + 30, w1 - 30); rows[min(abs(l) // 5 * 5, 30)] += 1; r_rows.append(np.corrcoef(c[j, w0:w1], x[j, w0:w1])[0, 1])
def fmt(cn): tot = sum(cn.values()); return "  ".join(f"|lag|{'>=' if k == 30 else ''}{k}{'-' + str(k + 4) if k < 30 else ''}: {100 * v / tot:.0f}%" for k, v in sorted(cn.items()))
print(f"{sys.argv[1]}  n={sum(strip.values())}")
print("rhythm strip  ", fmt(strip), f" | median r (no alignment) {np.nanmedian(r_strip):.3f}")
print("3x4 leads     ", fmt(rows), f" | median r (no alignment) {np.nanmedian(r_rows):.3f}")
