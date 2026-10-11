#!/usr/bin/env python3
"""Phase 0 test set: pick PTB-XL records, fetch them, render paper-style ECG images.

design-v1 Section 8.2. PTB-XL (PhysioNet, CC-BY 4.0) holds digital signals, so each
record is drawn as a printed 12-lead ECG (3x4 + lead II rhythm strip, 25 mm/s,
10 mm/mV, pink grid) and then saved twice:
  <id>_scan.jpg   clean flat-bed scan
  <id>_photo.jpg  phone-photo imitation (perspective, rotation, uneven light,
                  blur, faded thermal print, noise, JPEG)

Outputs (never committed, never synced to Drive):
  validation/data/ptbxl/records100/...   downloaded signals
  validation/images/                     rendered images
  validation/images/manifest.csv         id, expected tier, PTB-XL labels and report

Usage:
  .venv/bin/python render_ptbxl_to_images.py            # default sample (~120 records)
  .venv/bin/python render_ptbxl_to_images.py --per-group 10 --seed 7
"""
from __future__ import annotations

import argparse
import ast
import csv
import sys
import urllib.request
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import wfdb

HERE = Path(__file__).resolve().parent
DATA = HERE / "data" / "ptbxl"
OUT = HERE / "images"
MIRROR = "https://physionet-open.s3.amazonaws.com/ptb-xl/1.0.3"

# PTB-XL label -> the tier our rules SHOULD reach at minimum (Homi to review).
CRITICAL = {"3AVB", "INJAS", "INJAL", "INJIN", "INJLA", "INJIL", "STE_"}
URGENT = {"2AVB", "PSVT", "SVTAC", "LNGQT", "STD_", "ISCAL", "ISCIN", "ISCIL", "ISCAS", "ISCLA", "ISCAN", "ISC_"}
ABNORMAL = {
    "AFIB", "AFLT", "CLBBB", "CRBBB", "1AVB", "LVH", "RVH", "LAFB", "LPFB", "WPW", "PVC", "PAC",
    "BIGU", "TRIGU", "PACE", "IMI", "ASMI", "AMI", "ALMI", "ILMI", "LMI", "IPLMI", "IPMI", "PMI",
    "NDT", "NST_", "INVT", "LOWT", "QWAVE", "LVOLT", "IVCD", "STACH", "SBRAD", "LAO/LAE", "RAO/RAE",
}
# Codes that describe a normal trace.
BENIGN = {"NORM", "SR", "SARRH"}

LEADS = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]
GRID = [["I", "aVR", "V1", "V4"], ["II", "aVL", "V2", "V5"], ["III", "aVF", "V3", "V6"]]


def expected_tier(codes: dict, stadium: str) -> str:
    keys = {k for k, v in codes.items() if v >= 50 or k in {"SR", "AFIB", "AFLT", "STACH", "SBRAD", "PACE", "PSVT", "SVTAC", "BIGU", "TRIGU"}}
    if keys & CRITICAL or (stadium == "Stadium I" and keys & {"IMI", "ASMI", "AMI", "ALMI", "ILMI", "LMI", "IPLMI", "IPMI", "PMI"}):
        return "CRITICAL"
    if keys & URGENT:
        return "URGENT"
    if keys & ABNORMAL:
        return "ABNORMAL"
    if keys and keys <= BENIGN and "NORM" in keys:
        return "NO_CRITICAL_PATTERN"
    return "UNKNOWN"


def select(per_group: int, seed: int) -> pd.DataFrame:
    df = pd.read_csv(DATA / "ptbxl_database.csv", index_col="ecg_id")
    df["codes"] = df.scp_codes.apply(ast.literal_eval)
    df["expected"] = [expected_tier(c, s) for c, s in zip(df.codes, df.infarction_stadium1.fillna(""))]
    df = df[df.validated_by_human & (df.expected != "UNKNOWN")]
    test = df[df.strat_fold == 10]
    picks = []
    rng = np.random.default_rng(seed)
    for tier in ["CRITICAL", "URGENT", "ABNORMAL", "NO_CRITICAL_PATTERN"]:
        # Critical patterns are rare: draw them from all folds; others from the test fold.
        pool = df[df.expected == tier] if tier == "CRITICAL" else test[test.expected == tier]
        n = min(len(pool), per_group if tier != "CRITICAL" else int(per_group * 1.2))
        if tier == "CRITICAL":  # always include every complete heart block
            must = pool[pool.codes.apply(lambda c: "3AVB" in c)]
            rest = pool.drop(must.index)
            pick = pd.concat([must, rest.sample(n=max(0, n - len(must)), random_state=int(rng.integers(1 << 31)))])
        else:
            pick = pool.sample(n=n, random_state=int(rng.integers(1 << 31)))
        picks.append(pick)
    return pd.concat(picks)


def fetch(rel: str) -> Path:
    base = DATA / rel
    for ext in (".hea", ".dat"):
        p = base.with_suffix(ext)
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(f"{MIRROR}/{rel}{ext}", p)
    return base


# ---------------------------------------------------------------- rendering
PX_PER_MM = 8  # 250 mm wide paper -> ~2000 px before the app-style downscale


def render(sig: np.ndarray, fs: int) -> np.ndarray:
    """Draw a printed 12-lead ECG. sig: (samples, 12) in mV."""
    w_mm, h_mm = 280, 200
    W, H = w_mm * PX_PER_MM, h_mm * PX_PER_MM
    img = np.full((H, W, 3), (248, 247, 252), np.uint8)  # paper (BGR)
    minor, major = (205, 196, 245), (150, 140, 235)
    for x in range(0, w_mm + 1):
        cv2.line(img, (x * PX_PER_MM, 0), (x * PX_PER_MM, H), major if x % 5 == 0 else minor, 2 if x % 5 == 0 else 1)
    for y in range(0, h_mm + 1):
        cv2.line(img, (0, y * PX_PER_MM), (W, y * PX_PER_MM), major if y % 5 == 0 else minor, 2 if y % 5 == 0 else 1)

    x0_mm, col_mm = 15, 62.5  # 2.5 s per column at 25 mm/s
    rows_mm = [35, 75, 115, 165]  # baselines of three rows + rhythm strip
    ink = (40, 30, 30)

    def trace(x: np.ndarray, start_mm: float, base_mm: float, seconds: float, t0: float):
        n0, n1 = int(t0 * fs), int((t0 + seconds) * fs)
        seg = x[n0:n1]
        t = np.arange(len(seg)) / fs
        xs = (start_mm + t * 25) * PX_PER_MM
        ys = (base_mm - seg * 10) * PX_PER_MM
        pts = np.stack([xs, ys], 1).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(img, [pts], False, ink, 2, cv2.LINE_AA)

    def cal(base_mm: float):  # 1 mV, 0.2 s calibration pulse
        p = [(5, base_mm), (6, base_mm), (6, base_mm - 10), (11, base_mm - 10), (11, base_mm), (13, base_mm)]
        pts = (np.array(p) * PX_PER_MM).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(img, [pts], False, ink, 2, cv2.LINE_AA)

    for r, row in enumerate(GRID):
        cal(rows_mm[r])
        for c, lead in enumerate(row):
            i = LEADS.index(lead)
            trace(sig[:, i], x0_mm + c * col_mm, rows_mm[r], 2.5, c * 2.5)
            cv2.putText(img, lead, (int((x0_mm + c * col_mm + 1) * PX_PER_MM), int((rows_mm[r] - 12) * PX_PER_MM)),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.1, ink, 2, cv2.LINE_AA)
    cal(rows_mm[3])
    trace(sig[:, 1], x0_mm, rows_mm[3], 10, 0)
    cv2.putText(img, "II", (int((x0_mm + 1) * PX_PER_MM), int((rows_mm[3] - 12) * PX_PER_MM)),
                cv2.FONT_HERSHEY_SIMPLEX, 1.1, ink, 2, cv2.LINE_AA)
    cv2.putText(img, "25 mm/s   10 mm/mV   0.5-40 Hz", (int(15 * PX_PER_MM), int(195 * PX_PER_MM)),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, ink, 2, cv2.LINE_AA)
    return img


def photo(img: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Imitate a phone photo of a printed ECG."""
    h, w = img.shape[:2]
    # faded thermal print: lift blacks a little
    out = cv2.addWeighted(img, 1 - rng.uniform(0.05, 0.25), np.full_like(img, 245), rng.uniform(0.05, 0.25), 0)
    # perspective + rotation on a darker "desk" background
    pad = int(0.06 * w)
    canvas = np.full((h + 2 * pad, w + 2 * pad, 3), rng.integers(60, 120), np.uint8)
    canvas[pad:pad + h, pad:pad + w] = out
    H2, W2 = canvas.shape[:2]
    j = lambda s: rng.uniform(-s, s) * W2
    src = np.float32([[pad, pad], [pad + w, pad], [pad + w, pad + h], [pad, pad + h]])
    dst = src + np.float32([[j(.02), j(.02)], [j(.02), j(.02)], [j(.02), j(.02)], [j(.02), j(.02)]])
    M = cv2.getPerspectiveTransform(src, dst)
    canvas = cv2.warpPerspective(canvas, M, (W2, H2), borderMode=cv2.BORDER_REPLICATE)
    R = cv2.getRotationMatrix2D((W2 / 2, H2 / 2), rng.uniform(-4, 4), 1.0)
    canvas = cv2.warpAffine(canvas, R, (W2, H2), borderMode=cv2.BORDER_REPLICATE)
    # uneven lighting + a soft glare spot
    yy, xx = np.mgrid[0:H2, 0:W2].astype(np.float32)
    grad = 1 - rng.uniform(0.1, 0.35) * (xx / W2 if rng.random() < .5 else yy / H2)
    gx, gy = rng.uniform(.2, .8) * W2, rng.uniform(.2, .8) * H2
    glare = rng.uniform(0, 60) * np.exp(-(((xx - gx) ** 2 + (yy - gy) ** 2) / (2 * (0.12 * W2) ** 2)))
    f = canvas.astype(np.float32) * grad[..., None] + glare[..., None]
    # blur + sensor noise
    f = cv2.GaussianBlur(f, (0, 0), rng.uniform(0.6, 1.6))
    f += rng.normal(0, rng.uniform(2, 6), f.shape)
    return np.clip(f, 0, 255).astype(np.uint8)


def app_prep(img: np.ndarray) -> np.ndarray:
    """Same as the app: long edge 1600 px."""
    h, w = img.shape[:2]
    s = 1600 / max(h, w)
    return cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-group", type=int, default=30)
    ap.add_argument("--seed", type=int, default=12)
    a = ap.parse_args()

    sel = select(a.per_group, a.seed)
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    rows = []
    for k, (ecg_id, r) in enumerate(sel.iterrows(), 1):
        rid = f"ptbxl{ecg_id:05d}"
        rec = wfdb.rdrecord(str(fetch(r.filename_lr)))
        sig = np.nan_to_num(rec.p_signal)
        names = [s.upper() for s in rec.sig_name]  # PTB-XL spells AVR/AVL/AVF
        order = [names.index(l.upper()) for l in LEADS]
        sig = sig[:, order]
        paper = render(sig, rec.fs)
        cv2.imwrite(str(OUT / f"{rid}_scan.jpg"), app_prep(paper), [cv2.IMWRITE_JPEG_QUALITY, 90])
        cv2.imwrite(str(OUT / f"{rid}_photo.jpg"), app_prep(photo(paper, rng)), [cv2.IMWRITE_JPEG_QUALITY, int(rng.integers(70, 90))])
        codes = {kk: v for kk, v in r.codes.items()}
        rows.append({
            "id": rid, "ecg_id": ecg_id, "expected": r.expected,
            "codes": ";".join(f"{kk}:{int(v)}" for kk, v in codes.items()),
            "stadium": r.infarction_stadium1 if isinstance(r.infarction_stadium1, str) else "",
            "report": str(r.report).replace("\n", " ")[:300],
            "age": r.age, "sex": "male" if r.sex == 0 else "female",
        })
        print(f"[{k}/{len(sel)}] {rid} {r.expected}", flush=True)

    with open(OUT / "manifest.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)
    print(pd.Series([x["expected"] for x in rows]).value_counts().to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
