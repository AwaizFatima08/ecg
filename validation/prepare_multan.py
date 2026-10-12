#!/usr/bin/env python3
"""Prepares the Multan "ECG Images dataset of Cardiac Patients" (Ch. Pervaiz Elahi Institute of Cardiology,
Mendeley Data, CC BY 4.0) as a REAL-WORLD test set for the engine.

Each print (EDAN SE-3, 3x4 + lead II rhythm strip) is cropped to its pink grid box — this removes the
header with the patient ID/date, as the app's crop step does — and saved at the app's working size.
Writes validation/images_multan/<class>_<n>.jpg and images_multan/manifest.csv (id, label, expected_min_tier).

The dataset's labels are coarse; expected tiers used for scoring (Homi to confirm):
  MI (acute)            -> at least URGENT (ideally CRITICAL)
  History of MI         -> at least ABNORMAL
  Abnormal heartbeat    -> at least ABNORMAL
  Normal                -> NO_CRITICAL_PATTERN
"""
import csv
import re
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
SRC = HERE / "data" / "multan"
OUT = HERE / "images_multan"
CLASSES = {
    "ECG Images of Myocardial Infarction Patients": ("mi", "URGENT"),
    "ECG Images of Patient that have History of MI": ("oldmi", "ABNORMAL"),
    "ECG Images of Patient that have abnormal heartbeat": ("abnhb", "ABNORMAL"),
    "Normal Person ECG Images": ("normal", "NO_CRITICAL_PATTERN"),
}


def grid_box(img: np.ndarray) -> tuple[int, int, int, int] | None:
    """Bounding box of the pink grid (thin dotted lines): robust percentiles of pinkish, non-white pixels."""
    b, g, r = [c.astype(int) for c in cv2.split(img)]
    pink = ((r + g + b) < 720) & (r - g > 15)
    if pink.mean() < 0.002:
        return None
    ys, xs = np.where(pink)
    x0, x1 = np.percentile(xs, [0.2, 99.8]).astype(int)
    y0, y1 = np.percentile(ys, [0.2, 99.8]).astype(int)
    if x1 - x0 < 0.5 * img.shape[1] or y1 - y0 < 0.4 * img.shape[0]:
        return None
    return int(x0), int(y0), int(x1), int(y1)


def main():
    OUT.mkdir(exist_ok=True)
    rows, skipped = [], 0
    for folder in sorted(SRC.iterdir()):
        if not folder.is_dir():
            continue
        key = re.sub(r"\s*\(.*$", "", folder.name)
        if key not in CLASSES:
            continue
        tag, expected = CLASSES[key]
        for f in sorted(folder.glob("*.jpg")):
            img = cv2.imread(str(f))
            box = grid_box(img) if img is not None else None
            if box is None:
                skipped += 1
                continue
            x0, y0, x1, y1 = box
            crop = img[y0:y1 + 1, x0:x1 + 1]
            s = 1600 / max(crop.shape[:2])
            crop = cv2.resize(crop, (int(crop.shape[1] * s), int(crop.shape[0] * s)), interpolation=cv2.INTER_AREA)
            n = re.search(r"\((\d+)\)", f.name)
            rid = f"{tag}_{n.group(1) if n else f.stem}"
            cv2.imwrite(str(OUT / f"{rid}.jpg"), crop, [cv2.IMWRITE_JPEG_QUALITY, 92])
            rows.append({"id": rid, "label": tag, "expected": expected, "source": f"{folder.name}/{f.name}"})
    with open(OUT / "manifest.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "label", "expected", "source"])
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} prepared, {skipped} skipped (grid not found)")


if __name__ == "__main__":
    main()
