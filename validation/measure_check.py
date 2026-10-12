#!/usr/bin/env python3
"""Checks ecg_measure.py against PTB-XL labels (clean signals, cut to the 3x4 print windows,
or digitized signals with --digitized npz from the homidev job)."""
import ast, sys
import numpy as np, pandas as pd, wfdb
from ecg_measure import measure, COLUMN
DB = "data/ptbxl"
LEADS = ["I","II","III","AVR","AVL","AVF","V1","V2","V3","V4","V5","V6"]
df = pd.read_csv(f"{DB}/ptbxl_database.csv", index_col="ecg_id"); df["codes"] = df.scp_codes.apply(ast.literal_eval)
has = lambda c, k, t=50: c.get(k, -1) >= t
groups = {
 "NORM": df[df.codes.apply(lambda c: has(c,"NORM",100) and len(c) <= 2)].sample(400, random_state=1),
 "BBB": df[df.codes.apply(lambda c: has(c,"CLBBB") or has(c,"CRBBB"))].sample(150, random_state=1),
 "1AVB": df[df.codes.apply(lambda c: has(c,"1AVB"))].sample(150, random_state=1),
 "LNGQT": df[df.codes.apply(lambda c: has(c,"LNGQT"))],
 "LAFB": df[df.codes.apply(lambda c: has(c,"LAFB"))].sample(150, random_state=1),
 "3AVB": df[df.codes.apply(lambda c: has(c,"3AVB"))],
 "2AVB": df[df.codes.apply(lambda c: has(c,"2AVB"))],
 "AFIB": df[df.codes.apply(lambda c: "AFIB" in c)].sample(150, random_state=1),
}
mask = np.zeros((12, 1000), bool)
for j in range(12): mask[j, COLUMN[j]*250:(COLUMN[j]+1)*250] = True
mask[1] = True
def get(r):
    rec = wfdb.rdrecord(f"{DB}/{r.filename_lr}"); n = [s.upper() for s in rec.sig_name]
    x = np.nan_to_num(rec.p_signal)[:, [n.index(l) for l in LEADS]].T[:, :1000]
    return np.where(mask, x, 0.0)
M = {g: [measure(get(r)) for _, r in d.iterrows()] for g, d in groups.items()}
def frac(g, f): v = [f(m) for m in M[g]]; v = [t for t in v if t is not None]; return f"{100*np.mean(v):.0f}% (n={len(v)}/{len(M[g])})" if v else "n/a"
q = lambda k, op: (lambda m: None if m.get(k) is None else op(m[k]))
print("QRS>=120:  BBB", frac("BBB", q("qrs_ms", lambda v: v>=120)), "| NORM", frac("NORM", q("qrs_ms", lambda v: v>=120)))
print("PR>200:    1AVB", frac("1AVB", q("pr_ms", lambda v: v>200)), "| NORM", frac("NORM", q("pr_ms", lambda v: v>200)))
print("QTc>=470:  LNGQT", frac("LNGQT", q("qtc_ms", lambda v: v>=470)), "| NORM", frac("NORM", q("qtc_ms", lambda v: v>=470)))
print("QTc>=500:  LNGQT", frac("LNGQT", q("qtc_ms", lambda v: v>=500)), "| NORM", frac("NORM", q("qtc_ms", lambda v: v>=500)))
print("axis left: LAFB", frac("LAFB", q("axis_label", lambda v: v=="left")), "| NORM not-normal", frac("NORM", q("axis_label", lambda v: v!="normal")))
for g in ["3AVB","2AVB","NORM","AFIB","1AVB","BBB","LAFB"]:
    print(f"AV block suspected {g:5s}", frac(g, lambda m: bool(m.get("av_block_suspected", False))))
print("median NORM: QRS", np.nanmedian([m.get("qrs_ms", np.nan) for m in M["NORM"]]), "PR", np.nanmedian([m.get("pr_ms", np.nan) for m in M["NORM"]]),
      "QTc", np.nanmedian([m.get("qtc_ms", np.nan) for m in M["NORM"]]))
