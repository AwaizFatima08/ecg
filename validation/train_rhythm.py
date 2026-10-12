#!/usr/bin/env python3
"""Lethal-rhythm model on the 10 s lead II strip: VT / VF (incl. ventricular flutter) / asystole / other.

PTB-XL has no VT, VF or asystole, so this model is trained on:
  - PhysioNet MIT-BIH Malignant Ventricular Ectopy DB (vfdb) and CU Ventricular Tachyarrhythmia DB (cudb),
    ODC-By 1.0 — rhythm-annotated episodes cut into 10 s windows (both channels, as lead-II stand-ins);
  - PTB-XL lead II (CC BY 4.0) as the large "other" class (normal and common abnormal rhythms), so that
    ordinary ECGs do not trigger false VT/VF alarms.
Split by RECORD (no window of a test record is ever trained on). Inputs get the same digitization-like
augmentation as the 12-lead classifier. Output: models/rhythm.pt + results/rhythm_model.md.
"""
from __future__ import annotations

import ast
import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import wfdb
from scipy.signal import resample_poly

HERE = Path(__file__).resolve().parent
CLASSES = ["other", "vt", "vf", "asystole"]
VF_LABELS = {"(VF", "(VFL", "(VFIB"}
OTHER_LABELS = {"(N", "(BI", "(B", "(AFIB", "(AF", "(NOD", "(SVTA", "(PM", "(HGEA", "(VER", "(SBR", "(T"}


def intervals_vfdb(rec, ann):
    """Rhythm intervals from aux_note changes: [(start, end, label)]."""
    pts = [(s, a.strip().rstrip("\x00")) for s, a in zip(ann.sample, ann.aux_note) if a.strip()]
    out = []
    for i, (s, lab) in enumerate(pts):
        e = pts[i + 1][0] if i + 1 < len(pts) else rec.sig_len
        out.append((s, e, lab))
    return out


def intervals_cudb(rec, ann):
    """CUDB: '[' ... ']' bracket VF/flutter episodes; aux notes give other rhythms."""
    out = intervals_vfdb(rec, ann)
    starts = [s for s, sym in zip(ann.sample, ann.symbol) if sym == "["]
    ends = [s for s, sym in zip(ann.sample, ann.symbol) if sym == "]"]
    vf = []
    for s in starts:
        e = next((x for x in ends if x > s), rec.sig_len)
        vf.append((s, e, "(VF"))
    # remove VF spans from other intervals by taking VF as priority (windows overlapping both are skipped later)
    return out + vf


def label_of(lab: str) -> int | None:
    if lab in VF_LABELS:
        return 2
    if lab == "(VT":
        return 1
    if lab == "(ASYS":
        return 3
    if lab in OTHER_LABELS:
        return 0
    return None  # NOISE and unknown: skip


def windows_from_db(db: str):
    X, y, rec_ids = [], [], []
    for r in open(HERE / f"data/{db}/RECORDS").read().split():
        rec = wfdb.rdrecord(str(HERE / f"data/{db}/{r}"))
        try:
            ann = wfdb.rdann(str(HERE / f"data/{db}/{r}"), "atr")
        except Exception:
            continue
        ivs = intervals_cudb(rec, ann) if db == "cudb" else intervals_vfdb(rec, ann)
        fs = rec.fs
        win, step = 10 * fs, 5 * fs
        sig = np.nan_to_num(rec.p_signal)
        for s, e, lab in ivs:
            c = label_of(lab)
            if c is None:
                continue
            # skip windows that overlap a VF bracket when labelled otherwise (cudb)
            for a in range(s, e - win + 1, step if c else 4 * step):
                if c == 0 and any(vs <= a + win and ve >= a for vs, ve, vl in ivs if vl in VF_LABELS):
                    continue
                for ch in range(sig.shape[1]):
                    x = resample_poly(sig[a:a + win, ch], 2, 5)[:1000]  # 250 -> 100 Hz
                    if len(x) == 1000:
                        X.append(x.astype(np.float32)); y.append(c); rec_ids.append(f"{db}/{r}")
    return np.array(X), np.array(y), np.array(rec_ids)


def ptbxl_lead2(n_per_fold: int = 1500):
    df = pd.read_csv(HERE / "data/ptbxl/ptbxl_database.csv", index_col="ecg_id")
    held = {int(r["ecg_id"]) for r in csv.DictReader(open(HERE / "images/manifest.csv"))}
    df = df[~df.index.isin(held)]
    out = {}
    for name, folds in {"train": range(1, 9), "test": [10]}.items():
        d = df[df.strat_fold.isin(folds)].sample(n=n_per_fold if name == "train" else 600, random_state=3)
        xs = []
        for f in d.filename_lr:
            rec = wfdb.rdrecord(str(HERE / "data/ptbxl" / f))
            names = [s.upper() for s in rec.sig_name]
            xs.append(np.nan_to_num(rec.p_signal)[:1000, names.index("II")].astype(np.float32))
        out[name] = np.stack(xs)
    return out


def augment(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    x = x * rng.uniform(0.6, 1.4, (len(x), 1))
    t = np.linspace(0, 1, 1000)[None, :]
    x = x + rng.normal(0, 0.05, (len(x), 1)) * np.sin(2 * np.pi * rng.uniform(0.05, 0.5, (len(x), 1)) * t * 10)
    x = x + rng.normal(0, rng.uniform(0.005, 0.04, (len(x), 1)), x.shape)
    sign = rng.choice([-1, 1], (len(x), 1))  # lead polarity varies between channels/records
    return (x * sign).astype(np.float32)


def prep(x: np.ndarray) -> np.ndarray:
    x = x - np.median(x, axis=1, keepdims=True)
    return np.clip(x, -5, 5)[:, None, :].astype(np.float32)


class RhythmNet(nn.Module):
    def __init__(self, n=4, w=32):
        super().__init__()
        def blk(i, o, s):
            return nn.Sequential(nn.Conv1d(i, o, 7, s, 3, bias=False), nn.BatchNorm1d(o), nn.ReLU(),
                                 nn.Conv1d(o, o, 7, 1, 3, bias=False), nn.BatchNorm1d(o), nn.ReLU())
        self.f = nn.Sequential(blk(1, w, 2), blk(w, 2 * w, 2), blk(2 * w, 2 * w, 2), blk(2 * w, 4 * w, 2), blk(4 * w, 4 * w, 2))
        self.h = nn.Sequential(nn.Dropout(0.3), nn.Linear(8 * w, n))

    def forward(self, x):
        z = self.f(x)
        return self.h(torch.cat([z.mean(-1), z.amax(-1)], 1))


def main():
    torch.set_num_threads(4)
    rng = np.random.default_rng(0)
    Xs, ys, rs = [], [], []
    for db in ("vfdb", "cudb"):
        X, y, r = windows_from_db(db)
        Xs.append(X); ys.append(y); rs.append(r)
    X, y, r = np.concatenate(Xs), np.concatenate(ys), np.concatenate(rs)
    recs = sorted(set(r))
    rng2 = np.random.default_rng(42)
    test_recs = set(rng2.choice(recs, size=max(1, len(recs) // 4), replace=False))
    te = np.array([x in test_recs for x in r])
    p = ptbxl_lead2()
    Xtr = np.concatenate([X[~te], p["train"]]); ytr = np.concatenate([y[~te], np.zeros(len(p["train"]), int)])
    Xte = np.concatenate([X[te], p["test"]]); yte = np.concatenate([y[te], np.zeros(len(p["test"]), int)])
    print("train counts", np.bincount(ytr, minlength=4), "test counts", np.bincount(yte, minlength=4),
          "test records", len(test_recs), flush=True)
    model = RhythmNet()
    cw = torch.tensor((len(ytr) / (4 * np.bincount(ytr, minlength=4).clip(1))) ** 0.5, dtype=torch.float32)
    loss_fn = nn.CrossEntropyLoss(weight=cw)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-2)
    for ep in range(30):
        model.train()
        idx = rng.permutation(len(Xtr))
        for i in range(0, len(idx), 128):
            b = idx[i:i + 128]
            xb = torch.from_numpy(prep(augment(Xtr[b], rng)))
            loss = loss_fn(model(xb), torch.from_numpy(ytr[b]))
            opt.zero_grad(); loss.backward(); opt.step()
        if (ep + 1) % 5 == 0:
            print(f"epoch {ep + 1} loss {loss.item():.3f}", flush=True)
    model.eval()
    with torch.no_grad():
        P = torch.softmax(model(torch.from_numpy(prep(Xte))), 1).numpy()
    pred = P.argmax(1)
    lines = ["# Lethal-rhythm model (lead II, 10 s)", "",
             f"Held-out records: {len(test_recs)} of {len(recs)} (vfdb + cudb), plus 600 PTB-XL fold-10 lead II strips as 'other'.", "",
             "| class | test windows | sensitivity | precision |", "|---|---|---|---|"]
    for k, c in enumerate(CLASSES):
        tp = ((pred == k) & (yte == k)).sum(); n = (yte == k).sum(); pp = (pred == k).sum()
        lines.append(f"| {c} | {n} | {tp / max(1, n):.2f} | {tp / max(1, pp):.2f} |")
    lethal = yte > 0
    fa = ((pred > 0) & (yte == 0)).sum() / max(1, (yte == 0).sum())
    ptb_fa = ((pred[-len(p['test']):] > 0)).mean()
    lines += ["", f"Any lethal rhythm detected when present: {((pred > 0) & lethal).sum() / max(1, lethal.sum()):.2f}",
              f"False lethal-rhythm alarm on 'other' windows: {fa:.3f} (PTB-XL strips only: {ptb_fa:.3f})"]
    (HERE / "results/rhythm_model.md").write_text("\n".join(lines) + "\n")
    torch.save({"state_dict": model.state_dict(), "classes": CLASSES}, HERE / "models/rhythm.pt")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
