#!/usr/bin/env python3
"""Lite ECG digitizer — the reference implementation for the phone port.

Only the segmentation U-Net comes from Open-ECG-Digitizer (CC BY-SA 4.0). Everything after it is a
deliberately simple pipeline that relies on the app's crop step, so it can be ported to Dart:

  1. image -> RGB min-max normalised, long side resized to SIZE, padded to a multiple of 128
  2. U-Net -> softmax -> signal and grid probability maps
  3. deskew: rotation angle in [-8, 8] deg that maximises the variance of the grid's row/column profiles
  4. grid scale: period of the grid (autocorrelation of the grid map) -> pixels per mm
  5. rows: the 4 strongest bands of the signal map's horizontal profile (3 lead rows + rhythm strip)
  6. per row: trace y = probability-weighted centroid within the band, per x column
  7. time axis anchored on each row's right edge (10 s back from where the traces end)
  8. voltages: (baseline - y) / px_per_mm / 10 mV; columns split into 4 x 2.5 s

Output: (12, 1000) mV at 100 Hz, NaN where a lead is not printed; same layout as the full digitizer.

  python lite_digitizer.py images/ out/lite [--size 1280] [--onnx models/unet.onnx]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
DIGI = HERE / "engines" / "Open-ECG-Digitizer"
if not DIGI.exists():  # homidev job bundle layout
    DIGI = HERE / "digitizer"
LEADS = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]
GRID_3x4 = [["I", "aVR", "V1", "V4"], ["II", "aVL", "V2", "V5"], ["III", "aVF", "V3", "V6"]]
GRID_CLASS, SIGNAL_CLASS = 0, 2


class Segmenter:
    """U-Net wrapper: PyTorch (reference) or ONNX Runtime (what the phone runs)."""

    def __init__(self, onnx: Path | None = None, student: Path | None = None):
        self.onnx = None
        if onnx:
            import onnxruntime as ort
            self.onnx = ort.InferenceSession(str(onnx), providers=["CPUExecutionProvider"])
        else:
            import torch
            sys.path.insert(0, str(DIGI))
            from src.model.unet import UNet
            self.torch = torch
            if student:  # distilled small U-Net (jobs/homidev_digitize/distill_unet.py)
                ck = torch.load(student, map_location="cpu", weights_only=False)
                self.net = UNet(num_in_channels=3, num_out_channels=4, dims=ck["dims"], depth=ck["depth"])
                sd = ck["state_dict"]
            else:
                self.net = UNet(num_in_channels=3, num_out_channels=4, dims=[32, 64, 128, 256, 320, 320, 320, 320], depth=2)
                sd = torch.load(DIGI / "weights" / "unet_weights_07072025.pt", map_location="cpu", weights_only=False)
            sd = sd.get("state_dict", sd) if isinstance(sd, dict) else sd
            sd = {k.replace("_orig_mod.", "").replace("module.", ""): v for k, v in sd.items()}
            self.net.load_state_dict(sd)
            self.dev = "cuda" if torch.cuda.is_available() else "cpu"
            self.net.to(self.dev).eval()

    def tiled(self, x: np.ndarray, tile: int = 768, overlap: int = 64) -> np.ndarray:
        """Same as __call__ but on overlapping tiles (bounded memory on a phone). Each tile keeps only its
        centre (overlap/2 trimmed per inner side). Tile sizes are multiples of 128."""
        _, _, H, W = x.shape
        out = np.zeros((4, H, W), np.float32)
        step = tile - overlap
        ys = list(range(0, max(1, H - tile) + 1, step)) or [0]
        xs = list(range(0, max(1, W - tile) + 1, step)) or [0]
        if ys[-1] + tile < H:
            ys.append(H - tile)
        if xs[-1] + tile < W:
            xs.append(W - tile)
        for y0 in ys:
            for x0 in xs:
                th, tw = min(tile, H), min(tile, W)
                p = self(x[:, :, y0:y0 + th, x0:x0 + tw])
                a = overlap // 2 if y0 > 0 else 0
                b = overlap // 2 if x0 > 0 else 0
                out[:, y0 + a:y0 + th, x0 + b:x0 + tw] = p[:, a:, b:]
        return out

    def __call__(self, x: np.ndarray) -> np.ndarray:
        """x: (1,3,H,W) float32 in [0,1] -> (4,H,W) softmax probabilities."""
        if self.onnx:
            logits = self.onnx.run(None, {self.onnx.get_inputs()[0].name: x})[0][0]
        else:
            with self.torch.no_grad():
                logits = self.net(self.torch.from_numpy(x).to(self.dev))[0].cpu().numpy()
        e = np.exp(logits - logits.max(0, keepdims=True))
        return e / e.sum(0, keepdims=True)


def sparse(p: np.ndarray) -> np.ndarray:
    p = np.clip(p - p.mean(), 0, None)
    return p / (p.max() + 1e-9)


def rotate(img: np.ndarray, angle_deg: float) -> np.ndarray:
    """Bilinear rotation about the centre, zero fill (same maths as the Dart port)."""
    h, w = img.shape
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle_deg, 1.0)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderValue=0)


def best_rotation(grid: np.ndarray) -> float:
    """Angle in [-8, 8] deg maximising the variance of the grid's row + column profiles.
    Coarse 1 deg steps on a half-size map, then 0.25 deg around the best."""
    small = cv2.resize(grid, (grid.shape[1] // 2, grid.shape[0] // 2), interpolation=cv2.INTER_AREA)

    def score(a: float) -> float:
        r = rotate(small, a)
        return float(r.sum(1).var() + r.sum(0).var())

    coarse = max(np.arange(-8, 8.01, 1.0), key=score)
    return float(max(np.arange(coarse - 0.75, coarse + 0.76, 0.25), key=score))


def gaussian_smooth(x: np.ndarray, sigma: float) -> np.ndarray:
    r = max(1, int(3 * sigma))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    return np.convolve(np.pad(x, r, mode="edge"), k, mode="valid")


def grid_period(grid: np.ndarray, prior_ppm: float) -> float:
    """Pixels per mm. The trace width gives a prior (a 10 s print is about 255 mm wide); the 5 mm major-grid
    period is then searched within +/-25 % of 5*prior in the grid map's autocorrelation and refined to sub-pixel."""
    ests = []
    lo, hi = int(5 * prior_ppm * 0.75), int(np.ceil(5 * prior_ppm * 1.25))
    for prof in (grid.sum(0), grid.sum(1)):
        prof = prof - prof.mean()
        ac = np.correlate(prof, prof, mode="full")[len(prof) - 1:]
        ac /= ac[0] + 1e-9
        if hi + 1 >= len(ac) or lo < 2:
            continue
        lag = lo + int(np.argmax(ac[lo:hi + 1]))
        if ac[lag] < 0.05 or lag in (lo, hi):
            continue
        d = ac[lag - 1] - 2 * ac[lag] + ac[lag + 1]
        if d < 0:
            lag = lag + 0.5 * (ac[lag - 1] - ac[lag + 1]) / d
        ests.append(lag / 5)
    return float(np.median(ests)) if ests else prior_ppm


def ruler(profile: np.ndarray, ppm: float) -> np.ndarray | None:
    """Quadratic pixel->mm map (coefficients for np.polyval) from the 5 mm major grid lines of a band.

    Lines are numbered step by step (gaps allowed, near-duplicates dropped), then a quadratic is fitted
    with one outlier-rejection pass. Quadratic covers the gentle stretch of a phone photo's perspective."""
    from scipy.signal import find_peaks
    n = max(3, int(10 * ppm))
    p = profile - np.convolve(profile, np.ones(n) / n, mode="same")
    pk, _ = find_peaks(p, distance=max(2, int(3.5 * ppm)), prominence=max(1e-6, 0.15 * p.std()))
    if len(pk) < 6:
        return None
    step = float(np.median(np.diff(pk)))
    if not (3.5 * ppm < step < 6.5 * ppm):
        return None
    idx, xs = [0], [float(pk[0])]
    for q in pk[1:]:
        k = int(round((q - xs[-1]) / step))
        if k < 1:
            continue
        idx.append(idx[-1] + k)
        xs.append(float(q))
    xs, mm = np.array(xs), 5.0 * np.array(idx)
    c = np.polyfit(xs, mm, 2)
    keep = np.abs(np.polyval(c, xs) - mm) < 1.5
    if keep.sum() >= 6:
        c = np.polyfit(xs[keep], mm[keep], 2)
    return c


def segment(img_bgr: np.ndarray, seg: Segmenter, size: int = 1600, tile: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Image -> (signal, grid) probability maps at working resolution (sparse-normalised)."""
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB).astype(np.float32)
    rgb = (rgb - rgb.min()) / (rgb.max() - rgb.min() + 1e-9)
    h, w = rgb.shape[:2]
    s = size / max(h, w)
    rgb = cv2.resize(rgb, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    h, w = rgb.shape[:2]
    H, W = -(-h // 128) * 128, -(-w // 128) * 128
    pad = np.zeros((H, W, 3), np.float32)
    pad[:h, :w] = rgb
    xin = pad.transpose(2, 0, 1)[None]
    prob = (seg.tiled(xin, tile) if tile else seg(xin))[:, :h, :w]
    return sparse(prob[SIGNAL_CLASS]), sparse(prob[GRID_CLASS])


def digitize(img_bgr: np.ndarray, seg: Segmenter, size: int = 1600, tile: int = 0) -> tuple[np.ndarray | None, dict]:
    sig, grid = segment(img_bgr, seg, size, tile)
    return postprocess(sig, grid)


def postprocess(sig: np.ndarray, grid: np.ndarray) -> tuple[np.ndarray | None, dict]:
    """Probability maps -> (12, 1000) mV signals. Everything here is ported to Dart (lib/engine/digitizer.dart)."""
    info: dict = {}
    h, w = sig.shape
    ang = best_rotation(grid)
    info["rotation_deg"] = ang
    sig, grid = rotate(sig, ang), rotate(grid, ang)

    cols = np.where(sig.sum(0) > sig.sum(0).max() * 0.05)[0]
    if len(cols) < 10:
        return None, {**info, "error": "no trace found"}
    prior = (cols[-1] - cols[0]) / 258.0
    ppm = grid_period(grid, prior)
    info["px_per_mm"] = ppm
    if not ppm or ppm < 2:
        return None, {**info, "error": "grid not found"}

    # rows: horizontal profile of the signal map, smoothed over ~5 mm
    prof = gaussian_smooth(sig.sum(1), max(1.0, 2.5 * ppm))
    from scipy.signal import find_peaks
    pk, props = find_peaks(prof, distance=max(3, int(15 * ppm)), prominence=prof.max() * 0.05)
    if len(pk) < 4:
        return None, {**info, "error": f"found {len(pk)} rows, need 4"}
    pk = np.sort(pk[np.argsort(props["prominences"])[-4:]])
    info["rows_y"] = pk.tolist()
    bounds = [0] + [int((pk[i] + pk[i + 1]) / 2) for i in range(3)] + [h]

    out = np.full((12, 1000), np.nan, np.float32)
    total_px = 250 * ppm  # 10 s at 25 mm/s
    # Time axis from the rhythm strip (bottom row, full 10 s): on a 3x4+1R print every row shares it.
    rb = sig[bounds[3]:bounds[4]].sum(0)
    on = np.where(rb > rb.max() * 0.08)[0]
    if len(on) < 10:
        return None, {**info, "error": "rhythm strip not found"}
    X1 = int(on[-1])
    X0 = max(0, int(round(X1 - total_px)))  # anything left of 10 s is calibration pulse / labels
    info["x_range"] = (X0, X1)
    # Grid rulers: local pixel->mm maps from the printed grid, so perspective/stretch in a photo is undone.
    R = ruler(grid[bounds[3]:bounds[4]].sum(0), ppm)
    end_mm_r = float(np.polyval(R, X1)) if R is not None else None
    info["ruler"] = R is not None
    xc = (X0 + X1) / 2
    for row in range(4):
        band = sig[bounds[row]:bounds[row + 1]]
        gband = grid[bounds[row]:bounds[row + 1]]
        x0, x1 = X0, X1
        ys = np.arange(band.shape[0])[:, None]
        wsum = band.sum(0) + 1e-9
        y = (band * ys).sum(0) / wsum
        valid = band.max(0) > 0.15
        B = (R if row == 3 else ruler(gband.sum(0), ppm)) if R is not None else None
        if B is not None:
            # same physical vertical lines: shift this band's mm by whole 5 mm squares to match the rhythm strip
            off = 5.0 * round((np.polyval(R, xc) - np.polyval(B, xc)) / 5.0)
            xs = np.arange(0, band.shape[1])
            t = (np.polyval(B, xs) + off - (end_mm_r - 250.0)) / 25.0
        else:
            xs = np.arange(x0, x1 + 1)
            t = (xs - x0) / (25 * ppm)  # seconds
        # vertical scale from this band's horizontal grid lines
        Hc = ruler(gband.sum(1), ppm)
        ppm_y = abs(1.0 / np.polyval(np.polyder(Hc), band.shape[0] / 2)) if Hc is not None else ppm
        if not (0.7 * ppm < ppm_y < 1.4 * ppm):
            ppm_y = ppm
        v = -(y[xs] - np.median(y[xs][valid[xs]] if valid[xs].any() else y[xs])) / ppm_y / 10.0
        v[~valid[xs]] = np.nan
        samples = np.full(1000, np.nan, np.float32)
        ti = np.arange(1000) / 100.0
        ok = ~np.isnan(v)
        if ok.sum() > 10:
            samples = np.interp(ti, t[ok], v[ok], left=np.nan, right=np.nan).astype(np.float32)
        if row == 3:
            out[1] = samples  # rhythm strip: lead II, full 10 s
            continue
        for c in range(4):
            j = LEADS.index(GRID_3x4[row][c])
            if row == 1 and c == 0:  # lead II: the rhythm strip is used instead
                continue
            seg_ = np.full(1000, np.nan, np.float32)
            a, b = c * 250, (c + 1) * 250
            seg_[a:b] = samples[a:b] - np.nanmedian(samples[a:b]) if np.isfinite(samples[a:b]).any() else np.nan
            out[j] = seg_
    return out, info


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("images", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--size", type=int, default=1280)
    ap.add_argument("--onnx", type=Path)
    ap.add_argument("--student", type=Path, help="distilled student checkpoint (.pt)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--tile", type=int, default=0, help="tile size (multiple of 128); 0 = whole image")
    ap.add_argument("--shard", default="0/1", help="i/n: process every n-th file starting at i")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    seg = Segmenter(a.onnx, a.student)
    files = sorted(p for p in a.images.glob("*.jpg"))
    if a.limit:
        files = files[:a.limit]
    si, sn = map(int, a.shard.split("/"))
    files = files[si::sn]
    files = [f for f in files if not (a.out / (f.stem + "_timeseries_canonical.csv")).exists()]
    import time
    fails = 0
    t0 = time.time()
    for f in files:
        x, info = digitize(cv2.imread(str(f)), seg, a.size, a.tile)
        if x is None:
            fails += 1
            print("FAIL", f.name, info.get("error"))
            continue
        np.savetxt(a.out / (f.stem + "_timeseries_canonical.csv"), (x * 1000).T, delimiter=",",
                   header=",".join(LEADS), comments="")
    print(f"{len(files) - fails}/{len(files)} digitized, {(time.time() - t0) / max(1, len(files)):.1f} s/image")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
