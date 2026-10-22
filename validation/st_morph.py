"""Per-lead ST/Q/T morphology on the median beat (100 Hz, digitized traces). Experiment 22 Oct 2026: separate acute
injury (ST elevation with upright T, reciprocal depression) from an old infarct with persistent ST elevation
(QS / deep Q with inverted T, no reciprocal change) — Homi: an old infarct is not an emergency."""
import numpy as np
from ecg_measure import r_peaks, median_beats, FS

LEADS = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]
RECIP = {0: [2, 5], 4: [2, 5], 2: [0, 4], 5: [0, 4], 1: [4], 6: [], 7: [], 8: [], 9: [], 10: [2, 5], 11: [2, 5]}


def st_morphology(x: np.ndarray) -> dict | None:
    r = r_peaks(x[1])
    if len(r) < 3:
        return None
    pre, post = 35, 60
    mb = median_beats(x, r, pre, post)
    valid = ~np.isnan(mb[:, 0])
    if valid.sum() < 6:
        return None
    vel = np.sqrt(np.nansum(np.diff(mb[valid], axis=1) ** 2, axis=0))
    vel = np.convolve(vel, np.ones(2) / 2, mode="same")
    peak = int(np.argmax(vel[pre - 8:pre + 8])) + pre - 8
    thr = 0.30 * vel[peak] + np.median(vel[:15])
    on = peak
    while on > 5 and vel[on - 1] > thr:
        on -= 1
    off = peak
    while off < len(vel) - 2 and vel[off + 1] > thr:
        off += 1
    off += 1
    leads = {}
    for j in range(12):
        if not valid[j]:
            continue
        b = mb[j]
        base = float(np.median(b[max(0, on - 12):max(1, on - 2)]))
        qrs = b[on:off] - base
        rmax = float(qrs.max()) if len(qrs) else 0.0
        # initial negative deflection: samples from onset until the first positive crossing
        q_depth = 0.0
        k = 0
        while on + k < off and qrs[k] <= 0.02:
            q_depth = min(q_depth, float(qrs[k])); k += 1
        q_dur = k * 1000 / FS
        qs = rmax < 0.1 and float(qrs.min()) < -0.2
        st = float(b[min(off + 6, len(b) - 1)] - base)          # J + 60 ms
        tseg = b[min(off + 10, len(b) - 1):min(off + 40, len(b))] - base
        t_amp = float(tseg[np.argmax(np.abs(tseg))]) if len(tseg) else 0.0
        leads[j] = {"st": st, "q": q_depth, "q_dur": q_dur, "qs": qs, "r": rmax, "t": t_amp}
    ste = [j for j, d in leads.items() if d["st"] >= 0.10 and j != 3]
    out = {"leads": leads, "ste_leads": ste, "qrs_on": on, "qrs_off": off}
    if ste:
        q_in_ste = [leads[j]["qs"] or (leads[j]["q"] <= -0.1 and leads[j]["q_dur"] >= 30) for j in ste]
        t_inv = [leads[j]["t"] < -0.05 for j in ste]
        recip = [leads[k]["st"] for j in ste for k in RECIP.get(j, []) if k in leads]
        out.update({"ste_frac_q": float(np.mean(q_in_ste)), "ste_frac_tinv": float(np.mean(t_inv)),
                    "recip_min_st": float(min(recip)) if recip else 0.0, "ste_max": float(max(leads[j]["st"] for j in ste))})
    return out


def chronic_pattern(m: dict | None) -> bool:
    """True when every ST-elevated lead carries a Q/QS wave with an inverted T and there is no reciprocal depression."""
    if not m or not m.get("ste_leads"):
        return False
    return m["ste_frac_q"] >= 0.99 and m["ste_frac_tinv"] >= 0.5 and m["recip_min_st"] > -0.05
