#!/usr/bin/env python3
"""Heart-rate accuracy of ecg_measure.r_peaks against a reference detector (wfdb XQRS on the clean PTB-XL lead II),
on clean signals (3x4 windows) and on student-digitized prints. Usage: rate_check.py [--digitized DIR ...]"""
import argparse, ast, sys
from pathlib import Path
import numpy as np, pandas as pd, wfdb
from wfdb.processing import XQRS
from scipy.signal import resample_poly
import ecg_measure
from engine_e2e import load_digitized
from ecg_measure import COLUMN, FS
DB = "data/ptbxl"
LEADS = ["I","II","III","AVR","AVL","AVF","V1","V2","V3","V4","V5","V6"]
ap = argparse.ArgumentParser(); ap.add_argument("--digitized", type=Path, nargs="*", default=[]); ap.add_argument("--n", type=int, default=300)
a = ap.parse_args()
df = pd.read_csv(f"{DB}/ptbxl_database.csv", index_col="ecg_id"); df["codes"] = df.scp_codes.apply(ast.literal_eval)
has = lambda c, k, t=50: c.get(k, -1) >= t
groups = {
 "NORM": df[df.codes.apply(lambda c: has(c,"NORM",100) and len(c) <= 2)].sample(a.n, random_state=1),
 "3AVB": df[df.codes.apply(lambda c: has(c,"3AVB"))], "2AVB": df[df.codes.apply(lambda c: has(c,"2AVB"))],
 "SBRAD": df[df.codes.apply(lambda c: "SBRAD" in c)].sample(a.n, random_state=1),
 "STACH": df[df.codes.apply(lambda c: "STACH" in c)].sample(a.n, random_state=1),
 "AFIB": df[df.codes.apply(lambda c: "AFIB" in c)].sample(a.n, random_state=1),
 "BBB": df[df.codes.apply(lambda c: has(c,"CLBBB") or has(c,"CRBBB"))].sample(a.n, random_state=1),
 "PVC": df[df.codes.apply(lambda c: "PVC" in c)].sample(a.n, random_state=1),
}
mask = np.zeros((12, 1000), bool)
for j in range(12): mask[j, COLUMN[j]*250:(COLUMN[j]+1)*250] = True
mask[1] = True
def clean(ecg_id):
    r = df.loc[ecg_id]; rec = wfdb.rdrecord(f"{DB}/{r.filename_lr}"); n = [s.upper() for s in rec.sig_name]
    return np.nan_to_num(rec.p_signal)[:, [n.index(l) for l in LEADS]].T[:, :1000]
def ref_rate(ecg_id):
    """Reference rate: XQRS on the 500 Hz lead II (at 100 Hz XQRS double-counts T waves)."""
    r = df.loc[ecg_id]; rec = wfdb.rdrecord(f"{DB}/{r.filename_lr}", channel_names=["II"])
    sig = resample_poly(np.nan_to_num(rec.p_signal[:, 0]), 5, 1)  # 100 -> 500 Hz (only records100 are local)
    x = XQRS(sig=sig, fs=500); x.detect(verbose=False); q = np.array(x.qrs_inds)
    if len(q) < 3: return None
    rr = np.diff(q) / 500; rr = rr[(rr > 0.25) & (rr < 2.5)]
    return 60 / np.median(rr) if len(rr) >= 2 else None
def rate(x): return ecg_measure.measure(x).get("rate_bpm")
def report(name, pairs):
    v = [(r, m) for r, m in pairs if r is not None and m is not None]
    if not v: print(f"{name:28s} n/a"); return
    ours_missing = sum(1 for r, m in pairs if r is not None and m is None)
    err = np.array([abs(m - r) / r for r, m in v])
    print(f"{name:28s} n={len(v):4d}  within 10%: {100*np.mean(err<=0.10):5.1f}%  within 20%: {100*np.mean(err<=0.20):5.1f}%  median |err| {100*np.median(err):4.1f}%  (ref missing {sum(1 for r, m in pairs if r is None)}, ours missing {ours_missing})")
for g, d in groups.items():
    pairs = []
    for ecg_id in d.index:
        x = clean(ecg_id); pairs.append((ref_rate(ecg_id), rate(np.where(mask, x, 0.0))))
    report(f"clean {g}", pairs)
for dd in a.digitized:
    pairs, groups_d = [], {}
    for f in sorted(dd.glob("*_timeseries_canonical.csv")):
        ecg_id = int(f.name[5:10])


        x = load_digitized(f)
        if x is None: pairs.append((1, None)); continue
        pairs.append((ref_rate(ecg_id), rate(x)))
    report(f"digitized {dd.name}", pairs)
