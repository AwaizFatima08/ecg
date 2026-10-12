#!/usr/bin/env python3
"""On-device engine, step 2: signal -> findings. Small 1-D CNN trained on PTB-XL.

Design choices (see docs/engine-plan.md):
- Input = what a digitized paper ECG gives: 12 leads x 10 s at 100 Hz, but in the
  standard 3x4 print each lead is only visible for its 2.5 s column (lead II also
  has the full 10 s rhythm strip). Hidden parts are zeroed and a 13th channel
  carries the visibility mask, so the network learns the paper format.
- Augmentation imitates digitization error: amplitude scaling, baseline drift,
  small time jitter, noise and short dropouts.
- Labels: PTB-XL statements mapped to the finding codes the rules engine uses.
- The 126 Phase 0 test records (validation/images/manifest.csv) are never trained on.
- Split: strat_fold 1-8 train, 9 validation, 10 test (PTB-XL recommendation).
- Small model (~0.5-1 M parameters) so it can run on a phone (exported later).

  python train_classifier.py --epochs 30
"""
from __future__ import annotations

import argparse
import ast
import csv
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import wfdb

HERE = Path(__file__).resolve().parent
DB = HERE / "data" / "ptbxl"
OUT = HERE / "models"
LEADS = ["I", "II", "III", "AVR", "AVL", "AVF", "V1", "V2", "V3", "V4", "V5", "V6"]
COLUMN = [0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3]

# Output label -> PTB-XL statements (likelihood >= 50, or rhythm/form statements which carry 0).
LABELS: dict[str, list[str]] = {
    "st_elevation_injury": ["INJAS", "INJAL", "INJIN", "INJLA", "INJIL", "STE_"],
    "acute_or_recent_mi": [],  # filled from infarction_stadium1 == "Stadium I" with an MI statement
    "old_mi_q_waves": ["IMI", "ASMI", "AMI", "ALMI", "ILMI", "LMI", "IPLMI", "IPMI", "PMI", "QWAVE"],
    "st_depression_ischaemia": ["STD_", "ISCAL", "ISCIN", "ISCIL", "ISCAS", "ISCLA", "ISCAN", "ISC_"],
    "t_wave_abnormality": ["NDT", "NST_", "INVT", "LOWT", "NT_", "TAB_"],
    "atrial_fibrillation": ["AFIB"],
    "atrial_flutter": ["AFLT"],
    "svt": ["SVTAC", "PSVT"],
    "pvcs": ["PVC", "BIGU", "TRIGU"],
    "pacs": ["PAC", "SVARR"],
    "first_degree_av_block": ["1AVB"],
    "second_or_third_degree_av_block": ["2AVB", "3AVB"],
    "lbbb": ["CLBBB"],
    "rbbb": ["CRBBB"],
    "left_anterior_fascicular_block": ["LAFB"],
    "nonspecific_ivcd": ["IVCD"],
    "wpw_preexcitation": ["WPW"],
    "long_qt": ["LNGQT"],
    "lvh": ["LVH", "VCLVH"],
    "rvh": ["RVH"],
    "paced_rhythm": ["PACE"],
    "low_voltage": ["LVOLT"],
    "normal": ["NORM"],
}
MI_CODES = set(LABELS["old_mi_q_waves"]) - {"QWAVE"}
ZERO_LIKELIHOOD_OK = {"AFIB", "AFLT", "SVTAC", "PSVT", "PVC", "BIGU", "TRIGU", "PAC", "SVARR", "PACE", "LVOLT"}
NAMES = list(LABELS)


def label_vector(codes: dict, stadium: str) -> np.ndarray:
    keys = {k for k, v in codes.items() if v >= 50 or k in ZERO_LIKELIHOOD_OK}
    y = np.zeros(len(NAMES), np.float32)
    for i, n in enumerate(NAMES):
        if n == "acute_or_recent_mi":
            y[i] = float(stadium == "Stadium I" and bool(keys & MI_CODES))
        else:
            y[i] = float(bool(keys & set(LABELS[n])))
    return y


def load(df: pd.DataFrame) -> np.ndarray:
    X = np.zeros((len(df), 12, 1000), np.float32)
    for i, f in enumerate(df.filename_lr):
        rec = wfdb.rdrecord(str(DB / f))
        names = [s.upper() for s in rec.sig_name]
        sig = np.nan_to_num(rec.p_signal)[:, [names.index(l) for l in LEADS]].T
        X[i] = sig[:, :1000]
    return X


def paper_view(x: np.ndarray, rng: np.random.Generator | None) -> np.ndarray:
    """(B,12,1000) mV -> (B,13,1000): 3x4 visibility + mask channel; optional digitization-like noise."""
    B = x.shape[0]
    mask = np.zeros((12, 1000), np.float32)
    for j in range(12):
        c = COLUMN[j]
        mask[j, c * 250:(c + 1) * 250] = 1
    mask[1, :] = 1  # lead II rhythm strip
    x = x.copy()
    if rng is not None:
        x *= rng.uniform(0.85, 1.15, (B, 12, 1))                                  # gain error
        t = np.linspace(0, 1, 1000)[None, None, :]
        x += rng.normal(0, 0.05, (B, 12, 1)) * np.sin(2 * np.pi * rng.uniform(0.05, 0.5, (B, 12, 1)) * t * 10)  # drift
        x += rng.normal(0, rng.uniform(0.005, 0.03, (B, 1, 1)), x.shape)          # noise
        if rng.random() < 0.5:                                                     # printer low-pass (EDAN: 25 Hz)
            from scipy.signal import butter, filtfilt
            b_, a_ = butter(2, rng.uniform(18, 45) / 50.0)
            x = filtfilt(b_, a_, x, axis=2).astype(np.float32)
        for b in range(B):                                                         # time jitter + dropouts
            s = int(rng.integers(-5, 6))
            x[b] = np.roll(x[b], s, axis=1)
            if rng.random() < 0.3:
                j, p = int(rng.integers(12)), int(rng.integers(0, 950))
                x[b, j, p:p + int(rng.integers(5, 40))] = 0
    # baseline per visible segment removed, as a digitizer cannot know DC offset
    out = np.zeros((B, 13, 1000), np.float32)
    for j in range(12):
        vis = mask[j] > 0
        seg = x[:, j, vis]
        out[:, j, vis] = seg - np.median(seg, axis=1, keepdims=True)
    out[:, 12, :] = mask.mean(0)
    return np.clip(out, -5, 5)


class Block(nn.Module):
    def __init__(self, cin: int, cout: int, stride: int):
        super().__init__()
        self.c1 = nn.Conv1d(cin, cout, 7, stride, 3, bias=False)
        self.b1 = nn.BatchNorm1d(cout)
        self.c2 = nn.Conv1d(cout, cout, 7, 1, 3, bias=False)
        self.b2 = nn.BatchNorm1d(cout)
        self.skip = nn.Sequential() if cin == cout and stride == 1 else nn.Sequential(
            nn.Conv1d(cin, cout, 1, stride, bias=False), nn.BatchNorm1d(cout))
        self.act = nn.ReLU()

    def forward(self, x):
        return self.act(self.b2(self.c2(self.act(self.b1(self.c1(x))))) + self.skip(x))


class EcgNet(nn.Module):
    def __init__(self, n_out: int, w: int = 48):
        super().__init__()
        self.stem = nn.Sequential(nn.Conv1d(13, w, 15, 2, 7, bias=False), nn.BatchNorm1d(w), nn.ReLU())
        self.body = nn.Sequential(Block(w, w, 1), Block(w, 2 * w, 2), Block(2 * w, 2 * w, 1),
                                  Block(2 * w, 4 * w, 2), Block(4 * w, 4 * w, 1), Block(4 * w, 4 * w, 2))
        self.head = nn.Sequential(nn.Dropout(0.3), nn.Linear(8 * w, n_out))

    def forward(self, x):
        h = self.body(self.stem(x))
        return self.head(torch.cat([h.mean(-1), h.amax(-1)], 1))


def auc(y: np.ndarray, p: np.ndarray) -> float:
    pos, neg = p[y == 1], p[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    order = np.argsort(np.concatenate([pos, neg]))
    ranks = np.empty(len(order)); ranks[order] = np.arange(1, len(order) + 1)
    return float((ranks[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--limit", type=int, default=0, help="debug: use only N training records")
    a = ap.parse_args()
    torch.set_num_threads(4)
    rng = np.random.default_rng(0)

    df = pd.read_csv(DB / "ptbxl_database.csv", index_col="ecg_id")
    df["codes"] = df.scp_codes.apply(ast.literal_eval)
    held_out = {int(r["ecg_id"]) for r in csv.DictReader(open(HERE / "images" / "manifest.csv"))}
    Y = np.stack([label_vector(c, s if isinstance(s, str) else "") for c, s in zip(df.codes, df.infarction_stadium1)])
    tr = (df.strat_fold <= 8).values & ~df.index.isin(held_out)
    va = (df.strat_fold == 9).values & ~df.index.isin(held_out)
    te = (df.strat_fold == 10).values & ~df.index.isin(held_out)
    if a.limit:
        tr = tr & (np.cumsum(tr) <= a.limit)
    print(f"train {tr.sum()}  val {va.sum()}  test {te.sum()}  (held out for Phase 0: {len(held_out)})", flush=True)
    t0 = time.time()
    Xtr, Xva, Xte = load(df[tr]), load(df[va]), load(df[te])
    print(f"loaded in {time.time() - t0:.0f}s", flush=True)
    Ytr, Yva, Yte = Y[tr], Y[va], Y[te]

    model = EcgNet(len(NAMES))
    print("parameters:", sum(p.numel() for p in model.parameters()), flush=True)
    pos = Ytr.mean(0).clip(1e-3, None)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(np.sqrt((1 - pos) / pos), dtype=torch.float32))
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-2)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=3e-3, total_steps=a.epochs * (len(Xtr) // a.batch + 1))

    def predict(X):
        model.eval()
        out = []
        with torch.no_grad():
            for i in range(0, len(X), 256):
                out.append(torch.sigmoid(model(torch.from_numpy(paper_view(X[i:i + 256], None)))).numpy())
        return np.concatenate(out)

    best, best_state = -1.0, None
    for ep in range(a.epochs):
        model.train()
        perm = rng.permutation(len(Xtr))
        tl = 0.0
        for i in range(0, len(perm), a.batch):
            idx = perm[i:i + a.batch]
            xb = torch.from_numpy(paper_view(Xtr[idx], rng))
            loss = loss_fn(model(xb), torch.from_numpy(Ytr[idx]))
            opt.zero_grad(); loss.backward(); opt.step(); sched.step()
            tl += loss.item() * len(idx)
        pv = predict(Xva)
        m = np.nanmean([auc(Yva[:, k], pv[:, k]) for k in range(len(NAMES))])
        print(f"epoch {ep + 1:2d}  loss {tl / len(Xtr):.4f}  val macro-AUC {m:.4f}  ({time.time() - t0:.0f}s)", flush=True)
        if m > best:
            best, best_state = m, {k: v.clone() for k, v in model.state_dict().items()}

    model.load_state_dict(best_state)
    pt = predict(Xte)
    OUT.mkdir(exist_ok=True)
    torch.save({"state_dict": best_state, "labels": NAMES, "width": 48}, OUT / "ecgnet.pt")
    # Per-label threshold on validation: keep sensitivity >= 0.9 (asymmetric, safety first).
    pv = predict(Xva)
    thr = {}
    for k, n in enumerate(NAMES):
        ys, ps = Yva[:, k], pv[:, k]
        if ys.sum() == 0:
            thr[n] = 0.5; continue
        cand = np.sort(ps[ys == 1])
        thr[n] = float(cand[int(0.1 * len(cand))]) if len(cand) >= 10 else 0.3
    json.dump({"labels": NAMES, "thresholds": thr, "val_macro_auc": best}, open(OUT / "ecgnet_meta.json", "w"), indent=1)

    lines = ["| label | test positives | AUC | sensitivity @thr | specificity @thr |", "|---|---|---|---|---|"]
    for k, n in enumerate(NAMES):
        y, p = Yte[:, k], pt[:, k]
        a_ = auc(y, p)
        pred = p >= thr[n]
        sens = (pred & (y == 1)).sum() / max(1, (y == 1).sum())
        spec = (~pred & (y == 0)).sum() / max(1, (y == 0).sum())
        lines.append(f"| {n} | {int(y.sum())} | {a_:.3f} | {sens:.2f} | {spec:.2f} |")
    rep = "\n".join(["# Classifier on clean PTB-XL signals (paper 3x4 view), test fold 10", "",
                     f"Validation macro-AUC {best:.4f}. Thresholds set on fold 9 for ≥90% sensitivity.", ""] + lines)
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "classifier_clean.md").write_text(rep + "\n")
    print(rep)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
