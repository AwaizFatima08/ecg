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
import os
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import wfdb
from scipy.signal import resample_poly

from train_classifier import EcgNet, LABELS, MI_CODES, NAMES, TERRITORY, ZERO_LIKELIHOOD_OK, auc, label_vector, paper_view

HERE = Path(__file__).resolve().parent
PTB = HERE / "data" / "ptbxl"
ARR = HERE / "data" / "ecg-arrhythmia"
CACHE = HERE / "work" / os.environ.get("CACHE_NAME", "signals_v2.npz")
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
    # Challenge-2021 Georgia codes (22 Oct 2026): regional ischaemia statements -> the ischaemia label
    "425623009": ["st_depression_ischaemia"], "425419005": ["st_depression_ischaemia"], "426434006": ["st_depression_ischaemia"],
    # CPSC-2018 / Georgia codes added 22 Oct 2026 (census of the complete set)
    "164884008": ["pvcs"], "427172004": ["pvcs"], "413844008": ["old_mi_q_waves"], "445118002": ["left_anterior_fascicular_block"],
    "164931005": ["st_elevation_injury"],  # CPSC "ST elevation" — subject to the ischaemic-context rule below
    # territory codes (28 Oct 2026): CPSC-extra "MI in anterior leads" / anterior MI / inferior MI
    "164861001": ["old_mi_q_waves", "mi_anterior"], "54329005": ["old_mi_q_waves", "mi_anterior"], "73795002": ["old_mi_q_waves", "mi_inferior"],
}
# PTB Diagnostic ECG Database (ptbdb, ODC-By 1.0): 549 records, 1000 Hz, header "Acute infarction (localization): ..."
PTBDB = HERE / "data" / "ptbdb"
# Challenge-2021 (Georgia + CPSC 2018 + CPSC extra; CC BY 4.0) — same WFDB layout and SNOMED "Dx:" comments as ecg-arrhythmia.
CH21 = HERE / "data" / "challenge2021"
# ACS-Chongqing (Du et al., Sci Data 2026, CC0): 19,955 angiography-confirmed ECGs, WFDB 500 Hz 10 s, labels in CSV/*.csv.
ACS = HERE / "data" / "acs_chongqing"
# SPH (Liu et al., Sci Data 2022, CC0): 25,770 ECGs, HDF5 "ecg" (12, N) mV at 500 Hz, AHA statements "code;code+modifier".
SPH = HERE / "data" / "sph"
UNKNOWN = -1.0  # label value for "not assessed by this dataset" (masked out of the loss)
SPH_MAP = {  # AHA code -> our label; modifiers: 332 Old, 362 Depression, 363 Elevation, 346 rapid ventricular response
    "1": ["normal"], "30": ["pacs"], "31": ["pacs"], "50": ["atrial_fibrillation"], "51": ["atrial_flutter"], "54": ["svt"],
    "60": ["pvcs"], "82": ["first_degree_av_block"], "83": ["second_or_third_degree_av_block"],
    "84": ["second_or_third_degree_av_block"], "85": ["second_or_third_degree_av_block"],
    "86": ["second_or_third_degree_av_block"], "88": ["second_or_third_degree_av_block"],
    "101": ["left_anterior_fascicular_block"], "104": ["lbbb"], "106": ["rbbb"], "108": ["wpw_preexcitation"],
    "125": ["low_voltage"], "142": ["lvh"], "143": ["rvh"], "146": ["st_depression_ischaemia"], "147": ["t_wave_abnormality"],
    "148": ["long_qt"], "153": ["t_wave_abnormality"], "160": ["old_mi_q_waves"], "161": ["old_mi_q_waves"],
    "162": ["old_mi_q_waves"], "163": ["old_mi_q_waves"], "164": ["old_mi_q_waves"], "165": ["old_mi_q_waves", "mi_anterior"],
    "166": ["old_mi_q_waves", "mi_anterior"], "167": ["old_mi_q_waves"],
}
SPH_MAP["160"] = ["old_mi_q_waves", "mi_anterior"]; SPH_MAP["161"] = ["old_mi_q_waves", "mi_inferior"]


def territory_from_text(txt: str) -> np.ndarray:
    """PTB-DB localization text -> (anterior, inferior, lateral) flags; posterior counts as lateral."""
    t = txt.lower()
    return np.array([float("anter" in t), float("infer" in t), float(any(k in t for k in ("later", "poster")))], np.float32)
SPH_MI = {"160", "161", "162", "163", "164", "165", "166", "167"}


def sph_label_vector(aha: str) -> np.ndarray:
    """AHA statements -> full label vector (SPH statements are comprehensive, so absent = negative). ST deviation (145)
    with the Depression modifier -> ischaemia label; with Elevation -> injury only if an MI statement co-occurs
    (Homi 21 Oct: old infarct / early repolarisation are not emergencies)."""
    y = np.zeros(len(NAMES), np.float32)
    stmts = [st.strip() for st in aha.replace(",", ";").split(";") if st.strip()]
    codes = {st.split("+")[0] for st in stmts}
    for st in stmts:
        parts = st.split("+"); code, mods = parts[0], set(parts[1:])
        for lab in SPH_MAP.get(code, []):
            y[NAMES.index(lab)] = 1.0
        if code == "145":
            if "362" in mods:
                y[NAMES.index("st_depression_ischaemia")] = 1.0
            if "363" in mods and codes & SPH_MI:
                y[NAMES.index("st_elevation_injury")] = 1.0
    return y


def acs_label_vector(r: dict) -> np.ndarray:
    """ACS-Chongqing CSV row -> label vector with UNKNOWN for everything the dataset does not assess. STEMI -> injury +
    acute MI; OMI (occlusion MI) -> acute MI; NSTEMI / UA -> acute MI unknown (the ECG need not show it), injury 0 only
    for UA; non-ACS (angiography-negative) -> injury 0, acute 0; paced flag -> paced_rhythm."""
    y = np.full(len(NAMES), UNKNOWN, np.float32)
    r = {k.strip().lstrip("\ufeff").upper(): (v or "").strip() for k, v in r.items() if k}
    stemi, nstemi, ua, omi = (r.get("STEMI") == "1", r.get("NSTEMI") == "1", r.get("UA") == "1", r.get("OMI") == "1")
    i, a = NAMES.index("st_elevation_injury"), NAMES.index("acute_or_recent_mi")
    if stemi:
        y[i] = 1.0; y[a] = 1.0
    elif omi:
        y[a] = 1.0
    elif nstemi:
        y[a] = UNKNOWN; y[i] = UNKNOWN
    elif ua:
        y[i] = 0.0
    else:  # angiography-negative
        y[i] = 0.0; y[a] = 0.0
    y[NAMES.index("paced_rhythm")] = 1.0 if r.get("PACED") == "1" else 0.0
    # territory from the culprit vessel (STEMI / OMI rows only); angiography-negative rows are territory negatives
    if stemi or omi:
        lad = any(r.get(v) == "1" for v in ("LM", "PLAD", "MLAD", "DLAD", "DB"))
        rca = any(r.get(v) == "1" for v in ("PRCA", "MRCA", "DRCA"))
        lcx = any(r.get(v) == "1" for v in ("PLCX", "MLCX", "DLCX", "OM"))
        if lad or rca or lcx:
            y[NAMES.index("mi_anterior")], y[NAMES.index("mi_inferior")], y[NAMES.index("mi_lateral")] = float(lad), float(rca), float(lcx)
    elif not (nstemi or ua):
        for n in TERRITORY:
            y[NAMES.index(n)] = 0.0
    return y
# Rate-only rhythm statements (sinus brady/tachy, sinus arrhythmia), rotations and early repolarisation do not change the
# morphology the classifier learns; rate is measured separately. A record with only these (+ SR) counts as "normal".
BENIGN = {"426783006", "426177001", "427084000", "427393009", "251199005", "251198002", "428417006", "426627000"}
KNOWN_NEUTRAL = {"67741000119109", "39732003", "47665007", "713426002", "164867002"}  # LAE, axis, IRBBB, abnormal QRS: known but no label


# SNOMED "ST elevation" (164930006) is a morphology statement that includes early repolarisation; Georgia-trained v8
# became less sensitive to real infarcts (22 Oct 2026). It counts as acute injury only when an ischaemia / T-wave /
# infarct statement co-occurs; otherwise the record is a (benign) negative for the injury label.
STE_CODES = {"164930006", "164931005"}
STE_CONTEXT = {"429622005", "428750005", "164934002", "59931005", "425623009", "425419005", "426434006",
               "164865005", "164917005", "57054005", "413444003", "54329005", "73795002", "164861001", "413844008"}


def arr_label_vector(codes: set[str]) -> np.ndarray | None:
    y = np.zeros(len(NAMES), np.float32)
    known = False
    for c in codes:
        if c in STE_CODES and not (codes & STE_CONTEXT):
            known = True  # ST elevation without ischaemic context: not injury (early-repolarisation-like negative)
            continue
        for lab in SNOMED.get(c, []):
            y[NAMES.index(lab)] = 1.0
            known = True
    if codes and codes <= BENIGN:
        y[NAMES.index("normal")] = 1.0
        known = True
    if codes and codes <= (BENIGN | KNOWN_NEUTRAL):
        known = True  # e.g. sinus rhythm + left axis: a negative for every label, not "normal"
    # SNOMED infarct / injury codes without a territory code: territory not assessed (masked), not "no territory"
    if (y[NAMES.index("old_mi_q_waves")] or y[NAMES.index("st_elevation_injury")] or y[NAMES.index("acute_or_recent_mi")]) \
            and not any(y[NAMES.index(n)] for n in TERRITORY):
        for n in TERRITORY:
            y[NAMES.index(n)] = UNKNOWN
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
    # --- Challenge-2021 subsets present on disk (500 Hz -> 100 Hz, first 10 s) ---
    n0, skipped = len(X), 0
    ch21 = os.environ.get("INCLUDE_CH21", "1")
    subs = () if ch21 == "0" else (("georgia", "cpsc_2018", "cpsc_2018_extra") if ch21 == "1" else tuple(ch21.split(",")))
    for sub in subs:
        for mat in sorted((CH21 / sub).rglob("*.mat")) if (CH21 / sub).exists() else []:
            rel = str(mat.with_suffix(""))
            try:
                rec = wfdb.rdrecord(rel)
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
            if any(l not in names for l in LEADS):
                skipped += 1
                continue
            sig = np.nan_to_num(rec.p_signal)[:5000, [names.index(l) for l in LEADS]]
            sig = resample_poly(sig, 1, 5, axis=0)[:1000]
            if sig.shape[0] < 1000 or not np.isfinite(sig).all():
                skipped += 1
                continue
            X.append(sig.T.astype(np.float16))
            Y.append(y)
            src.append("ch21")
            h = int(hashlib.md5(mat.name.encode()).hexdigest()[:8], 16) % 100
            split.append("test" if h < 5 else "val" if h < 10 else "train")
    print(f"challenge-2021: {len(X) - n0} records, skipped {skipped} ({time.time() - t0:.0f}s)", flush=True)
    # --- ACS-Chongqing (CC0): WFDB 500 Hz, labels from CSV; its own train/test split is kept (test -> our test) ---
    n0, skipped = len(X), 0
    if (ACS / "CSV").exists():
        for csvname, sp in (("train.csv", "train"),):  # test.csv carries no labels (withheld benchmark set)
            for r in csv.DictReader(open(ACS / "CSV" / csvname, encoding="utf-8-sig")):
                rk = {k.strip().upper(): v.strip() for k, v in r.items() if k}
                rel = next((p for p in ACS.rglob(rk["ECG_ROW_RECORD"])), None)
                if rel is None:
                    skipped += 1; continue
                try:
                    rec = wfdb.rdrecord(str(rel.with_suffix("")))
                except Exception:
                    skipped += 1; continue
                names = [s.upper() for s in rec.sig_name]
                if rec.fs != 500 or rec.sig_len < 5000 or any(l not in names for l in LEADS):
                    skipped += 1; continue
                sig = resample_poly(np.nan_to_num(rec.p_signal)[:5000, [names.index(l) for l in LEADS]], 1, 5, axis=0)[:1000]
                if sig.shape[0] < 1000 or not np.isfinite(sig).all():
                    skipped += 1; continue
                X.append(sig.T.astype(np.float16)); Y.append(acs_label_vector(r)); src.append("acs")
                h = int(hashlib.md5(rk["PATIENT_ID"].encode()).hexdigest()[:8], 16) % 100
                split.append("test" if h < 5 else "val" if h < 10 else "train")
    print(f"acs-chongqing: {len(X) - n0} records, skipped {skipped} ({time.time() - t0:.0f}s)", flush=True)
    # --- SPH (CC0): HDF5 mV at 500 Hz, first 10 s; AHA statements ---
    n0, skipped = len(X), 0
    if (SPH / "metadata.csv").exists():
        import h5py
        for r in csv.DictReader(open(SPH / "metadata.csv")):
            f = SPH / "records" / f"{r['ECG_ID']}.h5"
            try:
                with h5py.File(f) as hf:
                    x = hf["ecg"][:, :5000].astype(np.float32)
            except Exception:
                skipped += 1; continue
            if x.shape != (12, 5000):
                skipped += 1; continue
            sig = resample_poly(x.T, 1, 5, axis=0)[:1000]
            if sig.shape[0] < 1000 or not np.isfinite(sig).all():
                skipped += 1; continue
            X.append(sig.T.astype(np.float16)); Y.append(sph_label_vector(r["AHA_Code"])); src.append("sph")
            h = int(hashlib.md5(r["Patient_ID"].encode()).hexdigest()[:8], 16) % 100
            split.append("test" if h < 5 else "val" if h < 10 else "train")
    print(f"sph: {len(X) - n0} records, skipped {skipped} ({time.time() - t0:.0f}s)", flush=True)
    # --- PTB Diagnostic DB (ODC-By): 1000 Hz -> 100 Hz, first 10 s; MI territory from the header, healthy controls as normal ---
    n0, skipped = len(X), 0
    if (PTBDB / "RECORDS").exists():
        for line in open(PTBDB / "RECORDS"):
            rel = line.strip().rstrip("/")
            if not rel or not (PTBDB / f"{rel}.dat").exists():
                continue
            try:
                rec = wfdb.rdrecord(str(PTBDB / rel))
            except Exception:
                skipped += 1; continue
            names = [s.upper() for s in rec.sig_name]
            if rec.fs != 1000 or rec.sig_len < 10000 or any(l not in names for l in LEADS):
                skipped += 1; continue
            hdr = {c.split(":", 1)[0].strip(): c.split(":", 1)[1].strip() for c in rec.comments if ":" in c}
            reason = hdr.get("Reason for admission", "")
            y = np.full(len(NAMES), UNKNOWN, np.float32)
            if reason == "Healthy control":
                y[:] = 0.0; y[NAMES.index("normal")] = 1.0
            elif reason == "Myocardial infarction":
                terr = np.zeros(3, np.float32)
                for key in ("Acute infarction (localization)", "Former infarction (localization)"):
                    v = hdr.get(key, "")
                    if v and v not in ("no", "n/a", "unknown"):
                        terr = np.maximum(terr, territory_from_text(v))
                if terr.sum() == 0:
                    skipped += 1; continue
                for k, n in enumerate(TERRITORY):
                    y[NAMES.index(n)] = terr[k]
                y[NAMES.index("mi_posterior")] = float(any("poster" in hdr.get(key, "").lower()
                                                        for key in ("Acute infarction (localization)", "Former infarction (localization)")))
                y[NAMES.index("old_mi_q_waves")] = 1.0
                y[NAMES.index("normal")] = 0.0
            else:
                skipped += 1; continue
            sig = resample_poly(np.nan_to_num(rec.p_signal)[:10000, [names.index(l) for l in LEADS]], 1, 10, axis=0)[:1000]
            if sig.shape[0] < 1000 or not np.isfinite(sig).all():
                skipped += 1; continue
            X.append(sig.T.astype(np.float16)); Y.append(y); src.append("ptbdb")
            h = int(hashlib.md5(rel.split("/")[0].encode()).hexdigest()[:8], 16) % 100  # split by patient
            split.append("test" if h < 15 else "val" if h < 30 else "train")
    print(f"ptbdb: {len(X) - n0} records, skipped {skipped} ({time.time() - t0:.0f}s)", flush=True)
    CACHE.parent.mkdir(exist_ok=True)
    np.savez(CACHE, x=np.stack(X), y=np.stack(Y), src=np.array(src), split=np.array(split))
    print("cache:", CACHE, np.stack(X).shape, flush=True)


def cpu_temp() -> int:
    import subprocess
    try:
        out = subprocess.run(["sensors"], capture_output=True, text=True, timeout=5).stdout
        for line in out.splitlines():
            if line.startswith("Package id 0"):
                return int(float(line.split()[3].strip("+°C")))
    except Exception:
        pass
    return 0


def thermal_pause(hot: int = 74, cool: int = 66) -> None:
    """homidev's CPU package idles at ~63 C and spikes past 80 C under augmentation load (watchdog limit 80 C, two
    stops on 22 Oct 2026): pause the loop when it passes `hot` until it is back under `cool`."""
    if cpu_temp() >= hot:
        t0 = time.time()
        while cpu_temp() > cool and time.time() - t0 < 600:
            time.sleep(10)


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
    torch.set_num_threads(int(os.environ.get("TORCH_THREADS", "4")))  # 8 threads of CPU augmentation pushed the package to 83 C (22 Oct)
    d = np.load(CACHE)
    X, Y, src, split = d["x"], d["y"], d["src"], d["split"]
    tr, va, te = split == "train", split == "val", split == "test"
    print(f"train {tr.sum()}  val {va.sum()}  test {te.sum()}  (device {dev})", flush=True)
    print("train positives:", {n: int((Y[tr][:, k] == 1).sum()) for k, n in enumerate(NAMES)}, flush=True)
    print("sources:", {s_: int((src[tr] == s_).sum()) for s_ in np.unique(src)}, flush=True)

    model = EcgNet(len(NAMES), a.width).to(dev)
    known = Y[tr] >= 0
    pos = np.where(known, Y[tr], 0).sum(0) / known.sum(0).clip(1, None)
    pos = pos.clip(1e-4, None)
    bce = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(np.sqrt((1 - pos) / pos), dtype=torch.float32, device=dev), reduction="none")

    def loss_fn(logits, yb):  # UNKNOWN (-1) labels are masked out of the loss
        m = (yb >= 0).float()
        return (bce(logits, yb.clamp(min=0)) * m).sum() / m.sum().clamp(min=1)
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
            if (i // a.batch) % 25 == 0:
                thermal_pause()
        pv = predict(va)
        m = float(np.nanmean([auc(Y[va][:, k][Y[va][:, k] >= 0], pv[:, k][Y[va][:, k] >= 0]) for k in range(len(NAMES))]))
        print(f"epoch {ep + 1:2d}  loss {tl / len(perm):.4f}  val macro-AUC {m:.4f}  ({time.time() - t0:.0f}s)", flush=True)
        if m > best:
            best, best_state = m, {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    model.load_state_dict(best_state)
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    torch.save({"state_dict": best_state, "labels": NAMES, "width": a.width}, out / os.environ.get("OUT_NAME", "ecgnet_v2.pt"))
    pt = predict(te)
    lines = ["# Classifier v2 (PTB-XL + ecg-arrhythmia), held-out test", "",
             f"train {tr.sum()}, val {va.sum()}, test {te.sum()}; width {a.width}; val macro-AUC {best:.4f}", "",
             "| label | test positives | AUC |", "|---|---|---|"]
    for k, n in enumerate(NAMES):
        kk = Y[te][:, k] >= 0
        lines.append(f"| {n} | {int((Y[te][:, k] == 1).sum())} | {auc(Y[te][:, k][kk], pt[:, k][kk]):.3f} |")
    (out / "classifier_v2_report.md").write_text("\n".join(lines) + "\n")
    json.dump({"labels": NAMES, "width": a.width, "val_macro_auc": best}, open(out / "ecgnet_v2_meta.json", "w"), indent=1)
    print("\n".join(lines), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
