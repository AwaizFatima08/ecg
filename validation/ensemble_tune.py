#!/usr/bin/env python3
"""Ensemble of classifiers: average probabilities; set per-label cut-offs on the DIGITIZED validation
records (fold 9; same policy as retune_thresholds.py). Never uses Phase 0 or the selection set.

  python ensemble_tune.py models/student/ecgnet_student_s1.pt,... models/student/student_s1_signals.npz out_meta.json
"""
import json, sys
import numpy as np, torch
from train_classifier import EcgNet, auc, paper_view
from threshold_policy import DROP, thresholds as policy_thresholds

paths, npz, out = sys.argv[1].split(","), sys.argv[2], sys.argv[3]
d = np.load(npz)
va = d["split"] == "val"
X, Y = d["x"][va].astype(np.float32), d["y"][va]
models = []
for p in paths:
    ck = torch.load(p, map_location="cpu")
    m = EcgNet(len(ck["labels"]), ck["width"]); m.load_state_dict(ck["state_dict"]); m.eval(); models.append(m)
labels = ck["labels"]
with torch.no_grad():
    P = np.mean([np.concatenate([torch.sigmoid(m(torch.from_numpy(paper_view(X[i:i + 256], None)))).numpy()
                                 for i in range(0, len(X), 256)]) for m in models], 0)
thr = policy_thresholds(labels, Y, P)
macro = float(np.nanmean([auc(Y[:, k], P[:, k]) for k in range(len(labels)) if labels[k] not in DROP]))
json.dump({"labels": labels, "thresholds": thr, "ensemble_val_macro_auc": macro, "members": paths}, open(out, "w"), indent=1)
print(f"ensemble of {len(models)}: digitized-val macro-AUC {macro:.4f} -> {out}")
