#!/usr/bin/env python3
"""End-to-end test of the on-device engine on the Phase 0 images.

photo --(Open-ECG-Digitizer)--> 12-lead signal --(ecgnet + rate measurement)--> EcgReading JSON
     --(functions/src/rules/alertRules.ts, via scripts/applyRules.ts)--> alert tier --> run_eval.py

Writes images/readings_<run>.jsonl in the same format as the old Claude reader, so the
existing report and review page are reused unchanged.

  engines/Open-ECG-Digitizer/.venv/bin/python engine_e2e.py --run engine-v0
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
import torch
from scipy.signal import butter, filtfilt, find_peaks

from ecg_measure import measure
from train_rhythm import RhythmNet, prep as rhythm_prep
from train_classifier import COLUMN, EcgNet, paper_view

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# classifier label -> (kind, code, category, display name)
MAP = {
    "st_elevation_injury": ("finding", "stemi_pattern", "st_elevation", "ST elevation (injury pattern)"),
    "acute_or_recent_mi": ("finding", "stemi_pattern", "st_elevation", "Acute / recent infarction pattern"),
    "old_mi_q_waves": ("finding", "pathological_q_waves", "other", "Q waves / old infarction pattern"),
    "st_depression_ischaemia": ("finding", "st_depression", "st_depression", "ST depression / ischaemia"),
    "t_wave_abnormality": ("finding", "t_wave_inversion", "t_wave", "T-wave abnormality"),
    "atrial_fibrillation": ("rhythm", "atrial_fibrillation", "rhythm", "Atrial fibrillation"),
    "atrial_flutter": ("rhythm", "atrial_flutter", "rhythm", "Atrial flutter"),
    "svt": ("rhythm", "svt", "rhythm", "Supraventricular tachycardia"),
    "pvcs": ("finding", "pvcs", "rhythm", "Ventricular ectopics"),
    "pacs": ("finding", "pacs", "rhythm", "Atrial ectopics"),
    "first_degree_av_block": ("finding", "first_degree_av_block", "conduction", "First-degree AV block"),
    "second_or_third_degree_av_block": ("finding", "high_grade_av_block", "conduction", "Second/third-degree AV block"),
    "lbbb": ("finding", "lbbb", "conduction", "Left bundle branch block"),
    "rbbb": ("finding", "rbbb", "conduction", "Right bundle branch block"),
    "left_anterior_fascicular_block": ("finding", "left_anterior_fascicular_block", "conduction", "Left anterior fascicular block"),
    "nonspecific_ivcd": ("finding", "nonspecific_ivcd", "conduction", "Intraventricular conduction delay"),
    "wpw_preexcitation": ("finding", "wpw_preexcitation", "conduction", "Pre-excitation (WPW)"),
    "long_qt": ("finding", "long_qt", "other", "Long QT"),
    "lvh": ("finding", "lvh", "other", "Left ventricular hypertrophy"),
    "rvh": ("finding", "rvh", "other", "Right ventricular hypertrophy"),
    "paced_rhythm": ("rhythm", "paced_rhythm", "rhythm", "Paced rhythm"),
    "low_voltage": ("finding", "low_voltage", "other", "Low QRS voltage"),
}


def load_digitized(f: Path) -> np.ndarray | None:
    pred = np.genfromtxt(f, delimiter=",", skip_header=1)
    if pred.ndim != 2 or pred.shape[1] < 12:
        return None
    pred = pred / 1000.0
    t_src = np.linspace(0, 10, pred.shape[0], endpoint=False)
    t_dst = np.arange(1000) / 100
    x = np.zeros((12, 1000), np.float32)
    cover = []
    for j in range(12):
        col = pred[:, j]
        ok = ~np.isnan(col)
        cover.append(ok.mean())
        if ok.sum() > 10:
            x[j] = np.interp(t_dst, t_src[ok], col[ok])
    if np.mean(cover) < 0.1:
        return None
    return x


def heart_rate(lead2: np.ndarray) -> tuple[float | None, float, bool | None]:
    """R-peak rate from the 10 s lead II strip. Returns (bpm, confidence, regular)."""
    b, a = butter(2, [5 / 50, 30 / 50], btype="band")
    y = filtfilt(b, a, lead2)
    e = np.abs(np.gradient(y))
    peaks, _ = find_peaks(e, distance=25, height=np.percentile(e, 98) * 0.4)
    if len(peaks) < 3:
        return None, 0.0, None
    rr = np.diff(peaks) / 100
    rr = rr[(rr > 0.25) & (rr < 2.5)]
    if len(rr) < 2:
        return None, 0.0, None
    bpm = 60 / np.median(rr)
    cv = rr.std() / rr.mean()
    return float(round(bpm)), 0.8 if cv < 0.25 else 0.6, bool(cv < 0.12)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="engine-v0")
    ap.add_argument("--digitized", type=Path, default=HERE / "engines" / "out")
    ap.add_argument("--model", default=str(HERE / "models" / "ecgnet.pt"), help="checkpoint, or comma-separated list for an ensemble")
    ap.add_argument("--no-rhythm", action="store_true", help="disable the lethal-rhythm (VT/VF/asystole) model")
    ap.add_argument("--meta", type=Path, default=HERE / "models" / "ecgnet_meta.json")
    a = ap.parse_args()

    meta = json.load(open(a.meta))
    models = []
    for mp in str(a.model).split(","):  # comma-separated list = ensemble (mean probability)
        ck = torch.load(mp, map_location="cpu")
        m_ = EcgNet(len(ck["labels"]), ck["width"])
        m_.load_state_dict(ck["state_dict"])
        models.append(m_.eval())
    labels, thr = ck["labels"], meta["thresholds"]
    rhythm_net = None
    if (HERE / "models" / "rhythm.pt").exists() and not a.no_rhythm:
        rk = torch.load(HERE / "models" / "rhythm.pt", map_location="cpu")
        rhythm_net = RhythmNet(); rhythm_net.load_state_dict(rk["state_dict"]); rhythm_net.eval()

    readings = []
    for f in sorted(a.digitized.glob("*_timeseries_canonical.csv")):
        image = f.name.replace("_timeseries_canonical.csv", ".jpg")
        x = load_digitized(f)
        if x is None:
            reading = {
                "image_quality": {"readable": False, "issues": ["other"], "confidence": 0.1},
                "calibration": {"paper_speed_mm_s": None, "gain_mm_mv": None, "assumed": True},
                "layout": "other", "rate_bpm": {"value": None, "confidence": 0},
                "rhythm": {"code": "cannot_assess", "label": "Cannot assess", "regular": None, "confidence": 0},
                "intervals": {"pr_ms": None, "qrs_ms": None, "qt_ms": None, "qtc_ms": None},
                "axis": {"label": "cannot_assess", "confidence": 0}, "findings": [],
                "model_notes": "Digitizer could not extract the trace.",
            }
            readings.append({"image": image, "model": a.run, "promptVersion": a.run, "ms": 0, "reading": reading})
            continue
        with torch.no_grad():
            xin = torch.from_numpy(paper_view(x[None], None))
            p = np.mean([torch.sigmoid(m_(xin)).numpy()[0] for m_ in models], 0)
        m = measure(x)
        bpm = m.get("rate_bpm")
        regular = m.get("rr_regular")
        rconf = 0.8 if bpm is not None and regular else (0.6 if bpm is not None else 0.0)
        findings, rhythm = [], None
        fired = set()
        for k, n in enumerate(labels):
            if n == "normal" or p[k] < thr[n]:
                continue
            fired.add(n)
            kind, code, cat, name = MAP[n]
            conf = float(min(0.95, 0.5 + 0.5 * p[k]))
            if kind == "rhythm":
                if rhythm is None or conf > rhythm["confidence"]:
                    rhythm = {"code": code, "label": name, "regular": regular, "confidence": conf}
            else:
                findings.append({"code": code, "name": name, "leads": [], "category": cat, "confidence": conf})
        af_like = bool(fired & {"atrial_fibrillation", "atrial_flutter"})
        # Lethal-rhythm model on the lead II strip (VT / VF / asystole). Any of them is CRITICAL, so the alarm
        # fires on P(lethal) >= 0.5 and names the most likely one; the subtype itself is less reliable.
        if rhythm_net is not None:
            with torch.no_grad():
                pr = torch.softmax(rhythm_net(torch.from_numpy(rhythm_prep(x[1][None]))), 1).numpy()[0]
            if 1 - pr[0] >= 0.5:
                k = int(np.argmax(pr[1:])) + 1
                code = ["", "ventricular_tachycardia", "ventricular_fibrillation", "asystole"][k]
                rhythm = {"code": code, "label": "Possible VT / VF or asystole (lethal-rhythm check)",
                          "regular": regular, "confidence": float(min(0.95, 1 - pr[0]))}
        # Heart block: more P waves than QRS with a slow ventricular rate (not in AF/flutter). URGENT, not
        # CRITICAL on its own: 2 % false positives on normal ECGs in the PTB-XL check.
        slow = bpm is not None and bpm < 55
        # [PROPOSED, Homi to confirm] a slow (< 55), regular ventricular rhythm with more P waves than QRS is a
        # high-grade/complete block even when the classifier also calls AF, provided the P waves are regular (fibrillatory
        # waves are not), so the AF call only suppresses the faster, second-degree case (fibrillatory waves look like P waves).
        # Found on ptbxl00959 (complete heart block, escape 40/min, read as AF + URGENT), 13 Oct 2026.
        if m.get("av_block_suspected") and (not af_like or (slow and m.get("atria_regular"))):
            # [PROPOSED, Homi to confirm] with a slow ventricular rate (< 55) the block is likely high-grade/complete
            # -> CRITICAL; PTB-XL check: 25 % of complete blocks, 0.2 % of normals, 3.3 % of sinus bradycardias.
            findings.append({"code": "high_grade_av_block" if slow else "second_degree_av_block_mobitz2",
                             "category": "conduction", "leads": ["II"],
                             "name": f"Possible {'high-grade / complete' if slow else 'second-degree'} AV block "
                                     f"(atrial rate {m.get('atrial_rate_bpm')}, ventricular {bpm}/min)",
                             "confidence": 0.6})
        # QTc: a long value is only trusted when the long-QT classifier agrees (measurement alone over-calls).
        qtc = m.get("qtc_ms")
        if qtc is not None and qtc >= 470 and "long_qt" not in fired:
            qtc = None
        # Safety net: never a blank result when the model is not confident the ECG is normal.
        if not findings and rhythm is None and p[labels.index("normal")] < thr["normal"]:
            findings.append({"code": "other", "category": "other", "leads": [], "confidence": 0.6,
                             "name": "Abnormal-looking ECG without a specific pattern identified — review it yourself"})
        if rhythm is None:
            code = "sinus_rhythm"
            if bpm is not None and bpm > 100:
                code = "sinus_tachycardia"
            elif bpm is not None and bpm < 60:
                code = "sinus_bradycardia"
            rhythm = {"code": code, "label": code.replace("_", " ").capitalize(), "regular": regular, "confidence": 0.6}
        reading = {
            "image_quality": {"readable": True, "issues": [], "confidence": 0.8},
            "calibration": {"paper_speed_mm_s": None, "gain_mm_mv": None, "assumed": True},
            "layout": "12-lead standard",
            "rate_bpm": {"value": bpm, "confidence": rconf},
            "rhythm": rhythm,
            "intervals": {"pr_ms": None if af_like else m.get("pr_ms"), "qrs_ms": m.get("qrs_ms"),
                          "qt_ms": m.get("qt_ms") if qtc is not None else None, "qtc_ms": qtc},
            "axis": {"label": m.get("axis_label", "cannot_assess"), "confidence": 0.7 if "axis_label" in m else 0},
            "findings": findings,
            "model_notes": "On-device engine: digitized trace, classifier, rule-based intervals/axis and AV-block check.",
        }
        readings.append({"image": image, "model": a.run, "promptVersion": a.run, "ms": 0, "reading": reading})

    tmp = HERE / "images" / f"readings_{a.run}.raw.jsonl"
    tmp.write_text("\n".join(json.dumps(r) for r in readings) + "\n")
    out = HERE / "images" / f"readings_{a.run}.jsonl"
    subprocess.run(["npx", "tsx", "scripts/applyRules.ts", str(tmp), str(out)], cwd=ROOT / "functions", check=True)
    print(f"{len(readings)} readings -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
