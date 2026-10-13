"""Per-label decision cut-offs (shared by retune_thresholds, ensemble_tune and the homidev fine-tune).

Policy v2 (13 Oct 2026):
- labels with fewer than MIN_POS positives in the calibration set: fixed 0.3 — a percentile of 7 samples is
  meaningless and produced near-zero cut-offs (WPW 0.001) that fired on almost every ECG;
- urgent/critical labels (HIGH_SENS): the 10th percentile of positives (>= 90 % sensitivity), floored at FLOOR;
- everything else: Youden's J, floored at FLOOR;
- DROP labels never fire.
Policy v3 (13 Oct 2026, approved by Homi): st_depression_ischaemia leaves HIGH_SENS (Youden's J instead of the
>= 90 % sensitivity rule) — 48 of 54 Multan false alarms were ST depression alone, critical detection unchanged.
"""
import numpy as np

HIGH_SENS = {"st_elevation_injury", "acute_or_recent_mi", "atrial_fibrillation",
             "atrial_flutter", "svt", "second_or_third_degree_av_block", "long_qt", "wpw_preexcitation"}
DROP = {"nonspecific_ivcd"}
MIN_POS, FLOOR, RARE_FIXED = 20, 0.05, 0.3


def thresholds(labels, Y, P):
    thr = {}
    for k, n in enumerate(labels):
        y, p = Y[:, k], P[:, k]
        if n in DROP:
            thr[n] = 2.0
        elif y.sum() < MIN_POS:
            thr[n] = RARE_FIXED
        elif n in HIGH_SENS:
            s = np.sort(p[y == 1])
            thr[n] = max(FLOOR, float(s[int(0.1 * len(s))]))
        else:
            c = np.unique(p)
            best = max(c, key=lambda t: ((p >= t) & (y == 1)).sum() / y.sum() + ((p < t) & (y == 0)).sum() / (y == 0).sum())
            thr[n] = max(FLOOR, float(best))
    return thr


def fix_existing(thr: dict, positives: dict | None = None) -> dict:
    """Apply the floors to an existing threshold dict (positives: label -> count in the calibration set)."""
    out = {}
    for n, t in thr.items():
        if n in DROP:
            out[n] = 2.0
        elif positives is not None and positives.get(n, 0) < MIN_POS:
            out[n] = RARE_FIXED
        else:
            out[n] = max(FLOOR, t)
    return out
