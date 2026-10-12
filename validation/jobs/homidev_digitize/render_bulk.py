#!/usr/bin/env python3
"""Render a large PTB-XL training/calibration set as paper ECG images (scan or photo look).

Excludes the 126 Phase 0 records. Oversamples rare labels so the fine-tuning set
contains every heart block, ST-elevation injury, WPW, flutter, long QT, etc.

  python render_bulk.py --n-train 4000 --n-val 600 --out work/images
"""
from __future__ import annotations

import argparse
import ast
import csv
import sys
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import wfdb

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from render_ptbxl_to_images import LEADS, app_prep, photo, render  # noqa: E402

DB = HERE / "data" / "ptbxl"
RARE = {"3AVB", "2AVB", "INJAS", "INJAL", "INJIN", "INJLA", "INJIL", "STE_", "WPW", "AFLT", "SVTAC", "PSVT",
        "LNGQT", "PACE", "CLBBB", "CRBBB", "RVH", "LVOLT", "BIGU", "TRIGU"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-train", type=int, default=4000)
    ap.add_argument("--n-val", type=int, default=600)
    ap.add_argument("--out", type=Path, default=HERE / "work" / "images")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--limit", type=int, default=0, help="test: render only N records")
    ap.add_argument("--selection", type=int, default=0,
                    help="render a model-SELECTION set of N records from fold 10 instead (never trained on, "
                         "not in Phase 0); writes <out>/../selection_manifest.csv")
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    a.out.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(DB / "ptbxl_database.csv", index_col="ecg_id")
    df["codes"] = df.scp_codes.apply(ast.literal_eval)
    held = {int(r["ecg_id"]) for r in csv.DictReader(open(HERE / "phase0_manifest.csv"))}
    df = df[~df.index.isin(held)]
    rare = df.codes.apply(lambda c: bool(set(c) & RARE))

    def pick(pool: pd.DataFrame, n: int) -> pd.DataFrame:
        r = pool[rare.loc[pool.index]]
        rest = pool.drop(r.index)
        k = max(0, n - len(r))
        return pd.concat([r, rest.sample(n=min(k, len(rest)), random_state=int(rng.integers(1 << 31)))])

    if a.selection:
        pool = df[df.strat_fold == 10]
        r = pool[rare.loc[pool.index]]
        r = r.sample(n=min(len(r), a.selection // 2), random_state=7)
        rest = pool.drop(r.index).sample(n=a.selection - len(r), random_state=7)
        sel = pd.concat([r, rest]).assign(split="selection")
    else:
        sel = pd.concat([pick(df[df.strat_fold <= 8], a.n_train).assign(split="train"),
                         pick(df[df.strat_fold == 9], a.n_val).assign(split="val")])
    print(f"selected {len(sel)} records ({(sel.split == 'train').sum()} train, {(sel.split == 'val').sum()} val)", flush=True)
    if a.limit:
        sel = pd.concat([sel[sel.split == "train"].head(a.limit), sel[sel.split == "val"].head(a.limit)])
    rows = []
    for k, (ecg_id, r) in enumerate(sel.iterrows(), 1):
        name = f"ptbxl{ecg_id:05d}"
        if a.selection:  # both versions of every record, named like Phase 0 (<id>_scan / <id>_photo)
            if not (a.out / f"{name}_photo.jpg").exists():
                rec = wfdb.rdrecord(str(DB / r.filename_lr))
                names = [s.upper() for s in rec.sig_name]
                sig = np.nan_to_num(rec.p_signal)[:, [names.index(l.upper()) for l in LEADS]]
                paper = render(sig, rec.fs)
                cv2.imwrite(str(a.out / f"{name}_scan.jpg"), app_prep(paper), [cv2.IMWRITE_JPEG_QUALITY, 90])
                cv2.imwrite(str(a.out / f"{name}_photo.jpg"), app_prep(photo(paper, rng)),
                            [cv2.IMWRITE_JPEG_QUALITY, int(rng.integers(70, 90))])
            rows.append({"id": name, "ecg_id": ecg_id, "split": r.split})
            continue
        if not (a.out / f"{name}.jpg").exists():
            rec = wfdb.rdrecord(str(DB / r.filename_lr))
            names = [s.upper() for s in rec.sig_name]
            sig = np.nan_to_num(rec.p_signal)[:, [names.index(l.upper()) for l in LEADS]]
            paper = render(sig, rec.fs)
            img = photo(paper, rng) if rng.random() < 0.7 else paper  # 70 % phone-photo look
            cv2.imwrite(str(a.out / f"{name}.jpg"), app_prep(img), [cv2.IMWRITE_JPEG_QUALITY, int(rng.integers(70, 92))])
        rows.append({"id": name, "ecg_id": ecg_id, "split": r.split})
        if k % 200 == 0:
            print(f"rendered {k}/{len(sel)}", flush=True)
    man_name = "selection_manifest.csv" if a.selection else "bulk_manifest.csv"
    with open(a.out.parent / man_name, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "ecg_id", "split"])
        w.writeheader(); w.writerows(rows)
    print(f"done: {len(rows)} images ({(sel.split == 'train').sum()} train, {(sel.split == 'val').sum()} val)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
