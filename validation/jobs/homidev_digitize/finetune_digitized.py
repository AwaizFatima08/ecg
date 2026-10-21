#!/usr/bin/env python3
"""Fine-tune the ECG classifier on digitized signals and set cut-offs on digitized data.

Inputs:  work/digitized/<id>_timeseries_canonical.csv  (Open-ECG-Digitizer output)
         work/bulk_manifest.csv                         (id, ecg_id, split)
         models/ecgnet.pt                               (base model trained on clean PTB-XL)
Outputs: out/ecgnet_digitized.pt, out/ecgnet_digitized_meta.json, out/finetune_report.md,
         out/digitized_signals.npz (float16, for reuse on homi-nas)

Training batches mix digitized records with clean records (folds 1-8, Phase 0 records excluded),
half and half, so the model keeps what it learned and adapts to digitization error.
"""
from __future__ import annotations

import ast
import csv
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from train_classifier_v2 import thermal_pause  # noqa: E402
from train_classifier import DB, NAMES, EcgNet, auc, label_vector, load, paper_view, hard_negative_weight

import os
HERE = Path(__file__).resolve().parent
WORK, OUT = HERE / "work", HERE / "out"
DIGI_DIR = HERE / os.environ.get("DIGITIZED_DIR", "work/digitized")
TAG = os.environ.get("OUT_TAG", "digitized")
SEED = int(os.environ.get("SEED", "1"))
BASE_MODEL = HERE / os.environ.get("BASE_MODEL", "models/ecgnet.pt")  # base checkpoint to fine-tune
EPOCHS = int(os.environ.get("EPOCHS", "25"))
from threshold_policy import DROP, thresholds as policy_thresholds  # noqa: E402


def load_digitized(f: Path) -> np.ndarray | None:
    if not f.exists():
        return None
    pred = np.genfromtxt(f, delimiter=",", skip_header=1)
    if pred.ndim != 2 or pred.shape[1] < 12:
        return None
    pred = pred / 1000.0
    t_src = np.linspace(0, 10, pred.shape[0], endpoint=False)
    t_dst = np.arange(1000) / 100
    x = np.zeros((12, 1000), np.float32)
    cover = []
    for j in range(12):
        ok = ~np.isnan(pred[:, j])
        cover.append(ok.mean())
        if ok.sum() > 10:
            x[j] = np.interp(t_dst, t_src[ok], pred[ok, j])
    return x if np.mean(cover) >= 0.1 else None


def thresholds(names, Y, P, old):
    return policy_thresholds(names, Y, P)


def main() -> int:
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    print("device:", dev, torch.cuda.get_device_name(0) if dev == "cuda" else "", flush=True)
    thermal_pause(hot=70, cool=64)  # loading 17k PTB-XL records is CPU-heavy; start cool
    OUT.mkdir(exist_ok=True)
    df = pd.read_csv(DB / "ptbxl_database.csv", index_col="ecg_id")
    df["codes"] = df.scp_codes.apply(ast.literal_eval)
    Yall = {i: label_vector(c, s if isinstance(s, str) else "") for i, c, s in zip(df.index, df.codes, df.infarction_stadium1)}
    Wall = {i: hard_negative_weight(c, s if isinstance(s, str) else "") for i, c, s in zip(df.index, df.codes, df.infarction_stadium1)}
    HN = [NAMES.index("st_elevation_injury"), NAMES.index("acute_or_recent_mi")]

    man = list(csv.DictReader(open(WORK / "bulk_manifest.csv")))
    Xd, Yd, split, ids, Wd = [], [], [], [], []
    failed = 0
    for r in man:
        x = load_digitized(DIGI_DIR / f"{r['id']}_timeseries_canonical.csv")
        if x is None:
            failed += 1; continue
        Xd.append(x); Yd.append(Yall[int(r["ecg_id"])]); split.append(r["split"]); ids.append(int(r["ecg_id"]))
        Wd.append(Wall[int(r["ecg_id"])])
    Xd, Yd, split, Wd = np.stack(Xd), np.stack(Yd), np.array(split), np.array(Wd, np.float32)
    np.savez_compressed(OUT / f"{TAG}_signals.npz", x=Xd.astype(np.float16), y=Yd, split=split, ecg_id=np.array(ids))
    print(f"digitized usable: {len(Xd)}  failed: {failed}", flush=True)

    held = {int(r["ecg_id"]) for r in csv.DictReader(open(HERE / "phase0_manifest.csv"))}
    clean_df = df[(df.strat_fold <= 8) & ~df.index.isin(held)]
    Xc = load(clean_df)
    Yc = np.stack([Yall[i] for i in clean_df.index])
    Wc = np.array([Wall[i] for i in clean_df.index], np.float32)

    ck = torch.load(BASE_MODEL, map_location="cpu")
    names = ck["labels"]
    model = EcgNet(len(names), ck["width"]); model.load_state_dict(ck["state_dict"]); model.to(dev)
    old_meta = {"thresholds": {}}

    tr, va = split == "train", split == "val"
    Xt, Yt, Xv, Yv, Wt = Xd[tr], Yd[tr], Xd[va], Yd[va], Wd[tr]
    pos = Yt.mean(0).clip(1e-3, None)
    bce = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(np.sqrt((1 - pos) / pos), dtype=torch.float32, device=dev), reduction="none")

    def loss_fn(logits, yb, wb):
        # wb: per-sample hard-negative weight applied to the two acute-infarction columns only
        w = torch.ones_like(logits); w[:, HN] = wb[:, None]
        return (bce(logits, yb) * w).mean()
    opt = torch.optim.AdamW(model.parameters(), lr=5e-4, weight_decay=1e-2)
    rng = np.random.default_rng(SEED)
    torch.manual_seed(SEED)
    epochs, half = EPOCHS, 32

    def predict(X):
        model.eval(); out = []
        with torch.no_grad():
            for i in range(0, len(X), 512):
                out.append(torch.sigmoid(model(torch.from_numpy(paper_view(X[i:i + 512], None)).to(dev))).cpu().numpy())
        return np.concatenate(out)

    def macro(Y, P):
        return float(np.nanmean([auc(Y[:, k], P[:, k]) for k in range(len(names)) if names[k] not in DROP]))

    base = macro(Yv, predict(Xv))
    print(f"base model on digitized val: macro-AUC {base:.4f}", flush=True)
    best, best_state, t0 = base, {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}, time.time()
    steps = len(Xt) // half
    for ep in range(epochs):
        model.train()
        pd_, pc = rng.permutation(len(Xt)), rng.permutation(len(Xc))
        for s in range(steps):
            idd, idc = pd_[s * half:(s + 1) * half], pc[s * half:(s + 1) * half]
            xb = np.concatenate([paper_view(Xt[idd], rng), paper_view(Xc[idc], rng)])
            yb = np.concatenate([Yt[idd], Yc[idc]])
            wb = np.concatenate([Wt[idd], Wc[idc]])
            loss = loss_fn(model(torch.from_numpy(xb).to(dev)), torch.from_numpy(yb).to(dev), torch.from_numpy(wb).to(dev))
            opt.zero_grad(); loss.backward(); opt.step()
            if s % 25 == 0:
                thermal_pause()
        m = macro(Yv, predict(Xv))
        print(f"epoch {ep + 1:2d}  digitized-val macro-AUC {m:.4f}  ({time.time() - t0:.0f}s)", flush=True)
        if m > best:
            best, best_state = m, {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    model.load_state_dict(best_state)
    Pv = predict(Xv)
    thr = thresholds(names, Yv, Pv, old_meta["thresholds"])
    torch.save({"state_dict": best_state, "labels": names, "width": ck["width"]}, OUT / f"ecgnet_{TAG}.pt")
    json.dump({"labels": names, "thresholds": thr, "digitized_val_macro_auc": best, "base_macro_auc": base,
               "policy": "cut-offs set on digitized validation records: >=90% sensitivity for urgent/critical labels, "
                         "Youden J otherwise; dropped: " + ", ".join(sorted(DROP))},
              open(OUT / f"ecgnet_{TAG}_meta.json", "w"), indent=1)
    lines = [f"# Fine-tune on digitized signals", "", f"Digitized records: {len(Xd)} ({tr.sum()} train, {va.sum()} val); "
             f"failed to digitize: {failed}", f"Digitized-val macro-AUC: base {base:.4f} → fine-tuned {best:.4f}", "",
             "| label | val positives | AUC | cut-off |", "|---|---|---|---|"]
    for k, n in enumerate(names):
        lines.append(f"| {n} | {int(Yv[:, k].sum())} | {auc(Yv[:, k], Pv[:, k]):.3f} | {thr[n]:.3f} |")
    (OUT / f"finetune_{TAG}_report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
