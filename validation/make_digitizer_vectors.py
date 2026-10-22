#!/usr/bin/env python3
"""Digitizer parity vectors for app/test/engine_digitizer_test.dart: U-Net probability maps (float32 .bin, not
committed - large) + the Python postprocess() result (expected.json). Re-run after any postprocess change.
  python make_digitizer_vectors.py [image names...]   # default: the cases already in expected.json
"""
import json, sys
from pathlib import Path
import cv2, numpy as np
from lite_digitizer import Segmenter, postprocess, segment

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "app" / "test" / "vectors" / "digitizer"
OUT.mkdir(parents=True, exist_ok=True)
exp = OUT / "expected.json"
cases = {c["name"]: c for c in json.load(open(exp))} if exp.exists() else {}
names = sys.argv[1:] or list(cases)
seg = None
for name in names:
    sig_f, grid_f = OUT / f"{name}_sig.bin", OUT / f"{name}_grid.bin"
    if name in cases and sig_f.exists():
        w, h = cases[name]["w"], cases[name]["h"]
        sig = np.fromfile(sig_f, np.float32).reshape(h, w)
        grid = np.fromfile(grid_f, np.float32).reshape(h, w)
    else:
        seg = seg or Segmenter(None, HERE / "models" / "onnx" / "student_16_32_64_128_160_160.pt")
        src = next(p for p in (HERE / "images" / f"{name}.jpg", HERE / "images_multan" / f"{name}.jpg", HERE / "private" / "homi_web8" / f"{name}.jpg") if p.exists())
        sig, grid = segment(cv2.imread(str(src)), seg, 1600, 0)
        sig.astype(np.float32).tofile(sig_f); grid.astype(np.float32).tofile(grid_f)
        h, w = sig.shape
    x, info = postprocess(sig, grid)
    assert x is not None, (name, info)
    cases[name] = {"name": name, "w": int(w), "h": int(h), "info": {k: (list(v) if isinstance(v, tuple) else v) for k, v in info.items()},
                   "x": [[None if np.isnan(v) else round(float(v), 6) for v in lead] for lead in x]}
    print(name, info)
json.dump(list(cases.values()), open(exp, "w"))
print("wrote", exp, len(cases), "cases")
