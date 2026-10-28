#!/usr/bin/env python3
"""Territory check on Phase 0 renders: PTB-XL statements -> true territories; engine readings -> territory probabilities.
  python3 territory_check.py images/readings_engine-v17b.jsonl"""
import ast, csv, json, sys
import numpy as np
from train_classifier import LABELS, NAMES, TERRITORY, label_vector
rows = {r["ecg_id"]: r for r in csv.DictReader(open("data/ptbxl/ptbxl_database.csv"))}
_m = json.load(open(__import__("os").environ.get("META", "models/v16/ensemble3_meta_v16.json")))["thresholds"]
THR = np.array([_m["mi_anterior"], _m["mi_inferior"], _m["mi_lateral"]])
T = {}
for l in open(sys.argv[1]):
    r = json.loads(l); rid = r["image"][:10]; eid = str(int(rid[5:]))
    y = label_vector(ast.literal_eval(rows[eid]["scp_codes"]), rows[eid]["infarction_stadium1"] or "")
    truth = np.array([y[NAMES.index(n)] for n in TERRITORY]); pr = r.get("territory", {})
    T[r["image"]] = (truth, np.array([pr.get("anterior", 0), pr.get("inferior", 0), pr.get("lateral", 0)]))
truth = np.stack([v[0] for v in T.values()]); P = np.stack([v[1] for v in T.values()])
mi = truth.sum(1) > 0
print(f"{len(T)} renders, {int(mi.sum())} with an infarct territory in PTB-XL (anterior {int(truth[:,0].sum())}, inferior {int(truth[:,1].sum())}, lateral {int(truth[:,2].sum())})")
top_ok = truth[mi][np.arange(mi.sum()), P[mi].argmax(1)] == 1
print(f"top territory is a true territory: {int(top_ok.sum())}/{int(mi.sum())}")
for k, n in enumerate(("anterior", "inferior", "lateral")):
    hit = (P[mi][:, k] >= THR[k]) == (truth[mi][:, k] == 1)
    print(f"  {n:9} sens {int(((P[mi][:,k]>=THR[k])&(truth[mi][:,k]==1)).sum())}/{int((truth[mi][:,k]==1).sum())}  spec {int(((P[mi][:,k]<THR[k])&(truth[mi][:,k]==0)).sum())}/{int((truth[mi][:,k]==0).sum())}")
print(f"non-infarct renders with any territory >= 0.5: {int(((P[~mi] >= THR).any(1)).sum())}/{int((~mi).sum())}")
