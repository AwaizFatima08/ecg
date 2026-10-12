#!/usr/bin/env python3
"""Classifier v2: trained on PTB-XL (CC BY 4.0) + the ecg-arrhythmia dataset (Chapman-Shaoxing + Ningbo,
45,152 ECGs, CC BY 4.0, SNOMED labels) — about 66 k 12-lead ECGs, with hundreds of AV blocks, WPW and long QT
instead of PTB-XL's handful. Same architecture, labels and paper-view input as train_classifier.py, so the
rest of the pipeline (fine-tune on digitized signals, thresholds, Dart) is unchanged.

Held out, never trained on: the 126 Phase 0 records, the 200 selection records, PTB-XL fold 10 (test), and a
10 % record-hash split of ecg-arrhythmia (val/test).

  python train_classifier_v2.py --build-cache     # one-off: data/ -> work/signals_v2.npz (float16)
  python train_classifier_v2.py --epochs 25 --width 64
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import wfdb
from scipy.signal import resample_poly

from train_classifier import EcgNet, LABELS, MI_CODES, NAMES, ZERO_LIKELIHOOD_OK, auc, label_vector, paper_view

HERE = Path(__file__).resolve().parent
PTB = HERE / "data" / "ptbxl"
ARR = HERE / "data" / "ecg-arrhythmia"
CACHE = HERE / "work" / "signals_v2.npz"
LEADS = ["I", "II", "III", "AVR", "AVL", "AVF", "V1", "V2", "V3", "V4", "V5", "V6"]

# SNOMED code -> our label(s). Codes shared by several dataset acronyms (e.g. 164909002 = LBBB and fascicular
# blocks) are mapped to the broader label. Axis/rate statements are not mapped (measured, not classified).
SNOMED = {
    "27885002": ["second_or_third_degree_av_block"],  # 3AVB
    "195042002": ["second_or_third_degree_av_block"],  # 2AVB
    "54016002": ["second_or_third_degree_av_block"],   # 2AVB type 1
    "28189009": ["second_or_third_degree_av_block"],   # 2AVB type 2
    "270492004": ["first_degree_av_block"], "164947007": ["first_degree_av_block"],
    "164909002": ["lbbb"], "59118001": ["rbbb"], "698252002": ["nonspecific_ivcd"],
    "164865005": ["old_mi_q_waves"], "164917005": ["old_mi_q_waves"],
    "164930006": ["st_elevation_injury"],                # STE "ST extension"
    "429622005": ["st_depression_ischaemia"],            # STDD
    "428750005": ["t_wave_abnormality"], "164934002": ["t_wave_abnormality"], "59931005": ["t_wave_abnormality"],
    "164889003": ["atrial_fibrillation"], "164890007": ["atrial_flutter"],
    "426761007": ["svt"], "233896004": ["svt"], "233897008": ["svt"], "713422000": ["svt"],
    "17338001": ["pvcs"], "11157007": ["pvcs"], "251180001": ["pvcs"],
    "284470004": ["pacs"], "251173003": ["pacs"],
    "74390002": ["wpw_preexcitation"], "195060002": ["wpw_preexcitation"],
    "111975006": ["long_qt"], "164873001": ["lvh"], "89792004": ["rvh"], "251146004": ["low_voltage"],
}
# Rate-only rhythm statements (sinus brady/tachy, sinus arrhythmia), rotations and early repolarisation do not change the
# morphology the classifier learns; rate is measured separately. A record with only these (+ SR) counts as "normal".
BENIGN = {"426783006", "426177001", "427084000", "427393009", "251199005", "251198002", "428417006"}


def arr_label_vector(codes: set[str]) -> np.ndarray | None:
    y = np.zeros(len(NAMES), np.float32)
    known = False
    for c in codes:
        for lab in SNOMED.get(c, []):
            y[NAMES.index(lab)] = 1.0
            known = True
    if codes and codes <= BENIGN:
        y[NAMES.index("normal")] = 1.0
        known = True
    return y if known else None


def build_cache() -> None:
    X, Y, src, split = [], [], [], []
    # --- PTB-XL ---
    df = pd.read_csv(PTB / "ptbxl_database.csv", index_col="ecg_id")
    df["codes"] = df.scp_codes.apply(ast.literal_eval)
    held = {int(r["ecg_id"]) for r in csv.DictReader(open(HERE / "phase0_manifest.csv"))}
    selm = HERE / "work" / "selection" / "selection_manifest.csv"
    if selm.exists():
        held |= {int(r["ecg_id"]) for r in csv.DictReader(open(selm))}
    df = df[~df.index.isin(held)]
    t0 = time.time()
    for i, (ecg_id, r) in enumerate(df.iterrows()):
        rec = wfdb.rdrecord(str(PTB / r.filename_lr))
        names = [s.upper() for s in rec.sig_name]
        X.append(np.nan_to_num(rec.p_signal)[:1000, [names.index(l) for l in LEADS]].T.astype(np.float16))
        Y.append(label_vector(r.codes, r.infarction_stadium1 if isinstance(r.infarction_stadium1, str) else ""))
        src.append("ptbxl")
        split.append("test" if r.strat_fold == 10 else "val" if r.strat_fold == 9 else "train")
    print(f"PTB-XL: {len(X)} records ({time.time() - t0:.0f}s)", flush=True)
    # --- ecg-arrhythmia (500 Hz -> 100 Hz) ---
    n0, skipped = len(X), 0
    for line in open(ARR / "all_records.txt"):
        rel = line.strip()
        if not rel or not (ARR / f"{rel}.mat").exists():
            continue
        try:
            rec = wfdb.rdrecord(str(ARR / rel))
        except Exception:
            skipped += 1
            continue
        dx = next((c for c in rec.comments if c.startswith("Dx:")), "Dx:")
        codes = {c.strip() for c in dx[3:].split(",") if c.strip()}
        y = arr_label_vector(codes)
        if y is None or rec.fs != 500 or rec.sig_len < 5000:
            skipped += 1
            continue
        names = [s.upper() for s in rec.sig_name]
        sig = np.nan_to_num(rec.p_signal)[:5000, [names.index(l) for l in LEADS]]
        sig = resample_poly(sig, 1, 5, axis=0)[:1000]
        if sig.shape[0] < 1000 or not np.isfinite(sig).all():
            skipped += 1
            continue
        X.append(sig.T.astype(np.float16))
        Y.append(y)
        src.append("arr")
        h = int(hashlib.md5(rel.encode()).hexdigest()[:8], 16) % 100
        split.append("test" if h < 5 else "val" if h < 10 else "train")
    print(f"ecg-arrhythmia: {len(X) - n0} records, skipped {skipped} ({time.time() - t0:.0f}s)", flush=True)
    CACHE.parent.mkdir(exist_ok=True)
    np.savez(CACHE, x=np.stack(X), y=np.stack(Y), src=np.array(src), split=np.array(split))
    print("cache:", CACHE, np.stack(X).shape, flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-cache", action="store_true")
    ap.add_argument("--epochs", type=int, default=25)
    ap.add_argument("--width", type=int, default=64)
    ap.add_argument("--batch", type=int, default=128)
    a = ap.parse_args()
    if a.build_cache or not CACHE.exists():
        build_cache()
        if a.build_cache:
            return 0
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    torch.set_num_threads(8)
    d = np.load(CACHE)
    X, Y, src, split = d["x"], d["y"], d["src"], d["split"]
    tr, va, te = split == "train", split == "val", split == "test"
    print(f"train {tr.sum()}  val {va.sum()}  test {te.sum()}  (device {dev})", flush=True)
    print("train positives:", {n: int(Y[tr][:, k].sum()) for k, n in enumerate(NAMES)}, flush=True)

    model = EcgNet(len(NAMES), a.width).to(dev)
    pos = Y[tr].mean(0).clip(1e-4, None)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(np.sqrt((1 - pos) / pos), dtype=torch.float32, device=dev))
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-2)
    steps = int(a.epochs * (int(tr.sum()) // a.batch + 1))
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=3e-3, total_steps=steps)
    rng = np.random.default_rng(0)
    idx_tr = np.where(tr)[0]

    def predict(mask):
        model.eval()
        out = []
        ids = np.where(mask)[0]
        with torch.no_grad():
            for i in range(0, len(ids), 512):
                xb = X[ids[i:i + 512]].astype(np.float32)
                out.append(torch.sigmoid(model(torch.from_numpy(paper_view(xb, None)).to(dev))).cpu().numpy())
        return np.concatenate(out)

    best, best_state, t0 = -1.0, None, time.time()
    for ep in range(a.epochs):
        model.train()
        perm = rng.permutation(idx_tr)
        tl = 0.0
        for i in range(0, len(perm), a.batch):
            b = perm[i:i + a.batch]
            xb = torch.from_numpy(paper_view(X[b].astype(np.float32), rng)).to(dev)
            loss = loss_fn(model(xb), torch.from_numpy(Y[b]).to(dev))
            opt.zero_grad(); loss.backward(); opt.step(); sched.step()
            tl += loss.item() * len(b)
        pv = predict(va)
        m = float(np.nanmean([auc(Y[va][:, k], pv[:, k]) for k in range(len(NAMES))]))
        print(f"epoch {ep + 1:2d}  loss {tl / len(perm):.4f}  val macro-AUC {m:.4f}  ({time.time() - t0:.0f}s)", flush=True)
        if m > best:
            best, best_state = m, {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    model.load_state_dict(best_state)
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    torch.save({"state_dict": best_state, "labels": NAMES, "width": a.width}, out / "ecgnet_v2.pt")
    pt = predict(te)
    lines = ["# Classifier v2 (PTB-XL + ecg-arrhythmia), held-out test", "",
             f"train {tr.sum()}, val {va.sum()}, test {te.sum()}; width {a.width}; val macro-AUC {best:.4f}", "",
             "| label | test positives | AUC |", "|---|---|---|"]
    for k, n in enumerate(NAMES):
        lines.append(f"| {n} | {int(Y[te][:, k].sum())} | {auc(Y[te][:, k], pt[:, k]):.3f} |")
    (out / "classifier_v2_report.md").write_text("\n".join(lines) + "\n")
    json.dump({"labels": NAMES, "width": a.width, "val_macro_auc": best}, open(out / "ecgnet_v2_meta.json", "w"), indent=1)
    print("\n".join(lines), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
