#!/usr/bin/env python3
"""Re-derive per-label decision thresholds on the validation fold (9).

Policy (safety first, but no flood of benign over-calls):
- Labels that feed URGENT/CRITICAL rules: threshold for >= 90 % sensitivity.
- Everything else: Youden's J (best sensitivity + specificity).
- Labels in DROP are never reported (too weak to be useful).
"""
import ast
import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from train_classifier import DB, EcgNet, label_vector, load, paper_view

HERE = Path(__file__).resolve().parent
HIGH_SENS = {"st_elevation_injury", "acute_or_recent_mi", "st_depression_ischaemia", "atrial_fibrillation",
             "atrial_flutter", "svt", "second_or_third_degree_av_block", "long_qt", "wpw_preexcitation"}
DROP = {"nonspecific_ivcd"}

ck = torch.load(HERE / "models" / "ecgnet.pt", map_location="cpu")
model = EcgNet(len(ck["labels"]), ck["width"]); model.load_state_dict(ck["state_dict"]); model.eval()
labels = ck["labels"]
df = pd.read_csv(DB / "ptbxl_database.csv", index_col="ecg_id")
df["codes"] = df.scp_codes.apply(ast.literal_eval)
held = {int(r["ecg_id"]) for r in csv.DictReader(open(HERE / "images" / "manifest.csv"))}
va = df[(df.strat_fold == 9) & ~df.index.isin(held)]
X = load(va)
Y = np.stack([label_vector(c, s if isinstance(s, str) else "") for c, s in zip(va.codes, va.infarction_stadium1)])
with torch.no_grad():
    P = np.concatenate([torch.sigmoid(model(torch.from_numpy(paper_view(X[i:i + 256], None)))).numpy() for i in range(0, len(X), 256)])

meta = json.load(open(HERE / "models" / "ecgnet_meta.json"))
thr = {}
for k, n in enumerate(labels):
    y, p = Y[:, k], P[:, k]
    if n in DROP:
        thr[n] = 2.0  # never fires
    elif y.sum() < 5:
        thr[n] = meta["thresholds"].get(n, 0.5)
    elif n in HIGH_SENS:
        s = np.sort(p[y == 1]); thr[n] = float(s[int(0.1 * len(s))])
    else:
        cands = np.unique(p)
        best = max(cands, key=lambda t: ((p >= t) & (y == 1)).sum() / y.sum() + ((p < t) & (y == 0)).sum() / (y == 0).sum())
        thr[n] = float(best)
    print(f"{n:34s} {thr[n]:.3f}")
meta["thresholds"] = thr
meta["policy"] = "high-sensitivity (>=90%) for urgent/critical labels, Youden J otherwise; dropped: " + ", ".join(sorted(DROP))
json.dump(meta, open(HERE / "models" / "ecgnet_meta.json", "w"), indent=1)
