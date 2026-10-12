#!/usr/bin/env python3
"""Generates test vectors so the Dart port (app/lib/engine) can be checked against the Python reference."""
import json
from pathlib import Path
import numpy as np
from scipy.signal import butter, filtfilt, find_peaks
from lite_digitizer import gaussian_smooth

OUT = Path(__file__).resolve().parent.parent / "app" / "test" / "vectors"
rng = np.random.default_rng(3)
t = np.arange(1000) / 100
x = np.sin(2 * np.pi * 1.2 * t) + 0.3 * np.sin(2 * np.pi * 8 * t) + 0.1 * rng.normal(size=1000)
v = {"x": x.tolist()}
for name, (lo, hi) in {"qrs": (5, 30), "p": (2, 15)}.items():
    b, a = butter(2, [lo / 50, hi / 50], btype="band")
    v[f"filtfilt_{name}"] = filtfilt(b, a, x).tolist()
e = np.abs(np.gradient(x))
v["e"] = e.tolist()
v["peaks_height_distance"] = find_peaks(e, distance=25, height=float(np.percentile(e, 98) * 0.4))[0].tolist()
v["peaks_prominence"] = find_peaks(x, distance=20, prominence=0.3)[0].tolist()
xs = np.sort(rng.uniform(0, 1500, 40)); ys = 0.0001 * xs ** 2 + 0.2 * xs + 3 + rng.normal(0, 0.5, 40)
v["poly_x"], v["poly_y"], v["poly_c"] = xs.tolist(), ys.tolist(), np.polyfit(xs, ys, 2).tolist()
v["gauss_sigma"] = 7.3
v["gauss"] = gaussian_smooth(x, 7.3).tolist()
v["movavg_n"] = 57
v["movavg"] = np.convolve(x, np.ones(57) / 57, mode="same").tolist()
v["movavg_n2"] = 60
v["movavg2"] = np.convolve(x, np.ones(60) / 60, mode="same").tolist()
(OUT / "dsp.json").write_text(json.dumps(v))
print("wrote", OUT / "dsp.json")

# ---- measurements on real digitized ECGs ----
from engine_e2e import load_digitized
from ecg_measure import measure
recs = []
for f in sorted((Path(__file__).resolve().parent / "engines" / "out_lite_1600").glob("*_timeseries_canonical.csv"))[:20]:
    x = load_digitized(f)
    if x is None:
        continue
    m = measure(x)
    keys = ["rate_bpm", "rr_regular", "pr_ms", "qrs_ms", "qt_ms", "qtc_ms", "axis_deg", "axis_label", "atrial_rate_bpm", "av_block_suspected"]
    recs.append({"name": f.name, "x": np.round(x.astype(np.float64), 6).tolist(),
                 "m": {k: (bool(m[k]) if isinstance(m.get(k), (bool, np.bool_)) else m.get(k)) for k in keys}})
(OUT / "measure.json").write_text(json.dumps(recs))
print("measure vectors:", len(recs))
