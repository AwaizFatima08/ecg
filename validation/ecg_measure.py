#!/usr/bin/env python3
"""Rule-based ECG measurements for the on-device engine (to be ported to Dart/Kotlin).

Input: x (12, 1000) in mV at 100 Hz, leads I II III aVR aVL aVF V1..V6, as recovered from
a standard 3x4 print: lead II is valid for the full 10 s; every other lead only inside its
2.5 s column (I/II/III 0-2.5 s, aVR/aVL/aVF 2.5-5 s, V1-V3 5-7.5 s, V4-V6 7.5-10 s).

Outputs (all may be None when not measurable):
  rate_bpm, rr_regular, pr_ms, qrs_ms, qt_ms, qtc_ms, axis_deg, axis_label,
  atrial_rate_bpm, av_block_suspected (bool), conduction_ratio (P:QRS), quality notes.

Method: R peaks on lead II -> median beat per lead (only beats inside that lead's window) ->
QRS onset/offset from the multi-lead spatial velocity, P wave before QRS onset, T end by the
tangent method on lead II -> intervals; axis from net QRS area in I and aVF.
Heart block: P waves are searched on lead II after subtracting the median QRS-T complex;
more P waves than QRS complexes with a slow ventricular rate => AV block suspected.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, filtfilt, find_peaks

FS = 100
COLUMN = [0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3]


def _bp(x, lo, hi):
    b, a = butter(2, [lo / (FS / 2), hi / (FS / 2)], btype="band")
    return filtfilt(b, a, x)


def r_peaks(lead2: np.ndarray) -> np.ndarray:
    y = _bp(lead2, 5, 30)
    e = np.abs(np.gradient(y))
    pk, _ = find_peaks(e, distance=int(0.25 * FS), height=np.percentile(e, 98) * 0.4)
    if len(pk) == 0:
        return pk
    # move each detection to the dominant extremum of the raw QRS (+/- 60 ms)
    out = []
    for p in pk:
        a, b = max(0, p - 6), min(len(lead2), p + 7)
        seg = lead2[a:b] - np.median(lead2)
        out.append(a + int(np.argmax(np.abs(seg))))
    return np.unique(np.array(out))


def _window(j: int) -> tuple[int, int]:
    if j == 1:
        return 0, 1000
    c = COLUMN[j]
    return c * 250, (c + 1) * 250


def median_beats(x: np.ndarray, r: np.ndarray, pre: int = 35, post: int = 60):
    """Median beat per lead around R (pre/post samples). Returns (12, pre+post) with NaN where no beat."""
    L = pre + post
    out = np.full((12, L), np.nan)
    for j in range(12):
        w0, w1 = _window(j)
        beats = [x[j, p - pre:p + post] for p in r if p - pre >= w0 and p + post <= w1]
        if beats:
            m = np.median(np.stack(beats), 0)
            out[j] = m - np.median(m[:10])  # PR-segment-ish baseline
    return out


def measure(x: np.ndarray) -> dict:
    res: dict = {"notes": []}
    r = r_peaks(x[1])
    if len(r) < 3:
        res["notes"].append("too few beats on lead II")
        return res
    rr = np.diff(r) / FS
    rr = rr[(rr > 0.25) & (rr < 2.5)]
    if len(rr) < 2:
        return res
    rr_med = float(np.median(rr))
    cv = float(rr.std() / rr.mean())
    res["rate_bpm"] = round(60 / rr_med)
    res["rr_regular"] = cv < 0.12
    res["rr_cv"] = round(cv, 3)

    pre, post = 35, 60
    mb = median_beats(x, r, pre, post)
    valid = ~np.isnan(mb[:, 0])
    if valid.sum() < 3:
        res["notes"].append("too few leads with complete beats")
        return res
    # QRS onset/offset from spatial velocity across available leads
    vel = np.sqrt(np.nansum(np.diff(mb[valid], axis=1) ** 2, axis=0))
    vel = np.convolve(vel, np.ones(2) / 2, mode="same")
    peak = int(np.argmax(vel[pre - 8:pre + 8])) + pre - 8
    # 0.30 (was 0.15): calibrated on 600 clean-vs-digitized pairs — digitized traces blur QRS edges and read ~20 ms
    # too wide at 0.15; 0.30 gives zero median bias, 73 % sensitivity / 94 % specificity for QRS >= 120 ms [PROPOSED]
    thr = 0.30 * vel[peak] + np.median(vel[:15])
    on = peak
    while on > 5 and vel[on - 1] > thr:
        on -= 1
    off = peak
    while off < len(vel) - 2 and vel[off + 1] > thr:
        off += 1
    off += 1
    qrs = (off - on) * 1000 / FS
    if 40 <= qrs <= 220:
        res["qrs_ms"] = int(round(qrs))

    ii = mb[1]
    # P wave: largest deflection 60-300 ms before QRS onset on lead II (and V1 if available)
    a, b = max(0, on - 30), max(0, on - 5)
    if b - a > 5:
        seg = ii[a:b]
        p_idx = a + int(np.argmax(np.abs(seg - np.median(ii[:5]))))
        p_amp = abs(ii[p_idx] - np.median(ii[:5]))
        qrs_amp = np.nanmax(np.abs(ii[on:off])) if off > on else 0
        if qrs_amp > 0 and p_amp > 0.04 and p_amp < 0.6 * qrs_amp:
            # P onset: walk back until amplitude falls below 20 % of P peak
            ponset = p_idx
            while ponset > 0 and abs(ii[ponset - 1] - np.median(ii[:5])) > 0.2 * p_amp:
                ponset -= 1
            pr = (on - ponset) * 1000 / FS
            if 80 <= pr <= 400:
                res["pr_ms"] = int(round(pr))
    # T end on lead II with the tangent method (needs a beat long enough: re-cut with longer post)
    long_post = min(int(rr_med * FS) - 10, 70)
    beats = [x[1, p - pre:p + long_post] for p in r if p - pre >= 0 and p + long_post <= 1000]
    if len(beats) >= 2 and long_post > 30:
        lb = np.median(np.stack(beats), 0)
        lb = lb - np.median(lb[:10])
        t0 = off + 8
        if t0 < len(lb) - 5:
            tseg = lb[t0:]
            tp = t0 + int(np.argmax(np.abs(tseg)))
            if abs(lb[tp]) > 0.05:
                d = np.gradient(lb)
                k = tp + int(np.argmax(np.abs(d[tp:])) if tp < len(lb) - 2 else 0)
                slope = d[k]
                if abs(slope) > 1e-4:
                    tend = k - lb[k] / slope  # tangent hits baseline
                    qt = (tend - on) * 1000 / FS
                    if 240 <= qt <= 650:
                        res["qt_ms"] = int(round(qt))
                        res["qtc_ms"] = int(round(qt / np.sqrt(rr_med)))
    # Axis from net QRS area in I and aVF
    if valid[0] and valid[5]:
        ni = float(np.sum(mb[0, on:off]))
        nf = float(np.sum(mb[5, on:off]))
        ang = float(np.degrees(np.arctan2(nf, ni)))
        res["axis_deg"] = round(ang)
        res["axis_label"] = ("normal" if -30 <= ang <= 90 else "left" if -90 <= ang < -30
                             else "right" if 90 < ang <= 180 else "extreme")
    res.update(av_relation(x[1], r, mb[1], on, off, pre))
    return res


def av_relation(lead2: np.ndarray, r: np.ndarray, beat: np.ndarray, on: int, off: int, pre: int) -> dict:
    """Search P waves on lead II after removing QRS-T; detect AV dissociation / dropped beats."""
    out: dict = {}
    if np.isnan(beat).any():
        return out
    resid = lead2 - np.median(lead2)
    L = len(beat)
    for p in r:  # subtract the median QRS-T at every beat
        a, b = p - pre, p - pre + L
        if a >= 0 and b <= len(resid):
            resid[a:b] -= beat
    # blank the QRS itself (subtraction is imperfect there)
    for p in r:
        resid[max(0, p - pre + on - 2):min(len(resid), p - pre + off + 2)] = 0
    y = _bp(resid, 2, 15)
    qrs_amp = np.percentile(np.abs(lead2 - np.median(lead2)), 99)
    h = max(0.04, 0.12 * qrs_amp)
    pk, prop = find_peaks(np.abs(y), distance=int(0.3 * FS), height=h, prominence=h * 0.7)
    if len(pk) < 4:
        return out
    pp = np.diff(pk) / FS
    pp = pp[(pp > 0.3) & (pp < 2.0)]
    if len(pp) < 3:
        return out
    a_rate = 60 / float(np.median(pp))
    a_reg = float(pp.std() / pp.mean()) < 0.15
    v_rate = 60 / float(np.median(np.diff(r) / FS))
    # PR for each QRS: last P within 0.6 s before R
    prs = []
    for q in r:
        before = pk[(pk < q - 4) & (pk > q - 60)]
        if len(before):
            prs.append((q - before[-1]) / FS)
    pr_sd = float(np.std(prs)) if len(prs) >= 3 else 0.0
    out["atrial_rate_bpm"] = round(a_rate)
    out["conduction_ratio"] = round(a_rate / v_rate, 2)
    out["pr_sd_ms"] = round(pr_sd * 1000)
    out["atria_regular"] = a_reg
    # More P waves than QRS complexes with a slow ventricular rate = second/third-degree AV block
    # suspected (PTB-XL check: the extra "wandering PR" test missed most complete blocks).
    # Guard against T waves (or other repolarisation residue) counted as P waves: those sit at a
    # fixed delay after each QRS, whereas truly dissociated P waves fall anywhere in the cycle.
    phases = []
    for pk_i in pk:
        prev = r[r < pk_i]
        if len(prev) and pk_i - prev[-1] < 2.5 * FS:
            phases.append((pk_i - prev[-1]) / FS)
    locked = False
    if len(phases) >= 4:
        ph = np.array(phases)
        locked = np.mean(np.abs(ph - np.median(ph)) < 0.06) >= 0.6
    out["p_locked_to_qrs"] = bool(locked)
    out["av_block_suspected"] = bool(a_rate / v_rate >= 1.4 and v_rate < 70 and 55 <= a_rate <= 150 and not locked)
    return out
