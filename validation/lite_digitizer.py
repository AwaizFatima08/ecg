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
CHAIN = __import__('os').environ.get('CHAIN', '1') != '0'  # row rulers chained from the rhythm strip (13 Oct 2026); CHAIN=0 only for A/B tests
TRACK = __import__('os').environ.get('TRACK', '1') != '0'  # follow lines slab by slab instead of band-to-band matching
SLAB = 0.3  # fraction of a band's height trimmed top and bottom for vertical-line profiles (tilted lines smear less)
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


SCALE_TOLERANCE = 0.13  # |grid px/mm / (trace width / 258 mm) - 1|: 187 of 188 sampled good prints <= 0.11 (one scan 0.149), all 150 book pages >= 0.157 (28 Oct 2026)


def grid_period(grid: np.ndarray, prior_ppm: float) -> float:
    return grid_period_found(grid, prior_ppm)[0]


def grid_period_found(grid: np.ndarray, prior_ppm: float) -> tuple[float, bool]:
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
    return (float(np.median(ests)), True) if ests else (prior_ppm, False)


def grid_lines(profile: np.ndarray, ppm: float) -> tuple[np.ndarray, float] | None:
    """Pixel positions of the 5 mm major vertical lines in a band's grid profile, and their median spacing."""
    from scipy.signal import find_peaks
    n = max(3, int(10 * ppm))
    p = profile - np.convolve(profile, np.ones(n) / n, mode="same")
    pk, _ = find_peaks(p, distance=max(2, int(3.5 * ppm)), prominence=max(1e-6, 0.15 * p.std()))
    if len(pk) < 6:
        return None
    step = float(np.median(np.diff(pk)))
    if not (3.5 * ppm < step < 6.5 * ppm):
        return None
    return pk.astype(float), step


def ruler_from_lines(xs: np.ndarray, mm: np.ndarray) -> np.ndarray | None:
    if len(xs) < 6:
        return None
    c = np.polyfit(xs, mm, 2)
    keep = np.abs(np.polyval(c, xs) - mm) < 1.5
    if keep.sum() >= 6:
        c = np.polyfit(xs[keep], mm[keep], 2)
    return c


def ruler_chain(profile: np.ndarray, ppm: float, prev_xs: np.ndarray, prev_mm: np.ndarray) -> tuple | None:
    """Ruler for a band whose major lines are labelled by continuity with the adjacent band (same physical lines,
    < half a square apart on a photo), so there is no whole-square ambiguity between rows. [13 Oct 2026]"""
    g = grid_lines(profile, ppm)
    if g is None:
        return None
    pk, step = g
    # residual tilt / keystone shifts the lines a few px between adjacent bands: estimate that shift first (best
    # match of the two line sets within +-45 % of a step), then label each line by its shifted nearest neighbour
    best, d0 = -1, 0.0
    for d in np.arange(-0.45 * step, 0.45 * step, 1.0):
        dist = np.abs(prev_xs[None, :] - (pk[:, None] + d)).min(1)
        score = float((dist < 0.2 * step).sum())
        if score > best:
            best, d0 = score, d
    xs, mm = [], []
    for q in pk:
        k = int(np.argmin(np.abs(prev_xs - (q + d0))))
        if abs(prev_xs[k] - (q + d0)) < 0.3 * step:
            xs.append(q); mm.append(prev_mm[k])
    xs, mm = np.array(xs), np.array(mm)
    # mislabelled lines (clutter peaks, keystone at the edges): two passes of linear-fit outlier rejection
    for _ in range(2):
        if len(xs) < 6:
            return None
        l = np.polyfit(xs, mm, 1)
        keep = np.abs(np.polyval(l, xs) - mm) < 1.5
        xs, mm = xs[keep], mm[keep]
    c = ruler_from_lines(xs, mm)
    return (c, xs, mm) if c is not None else None


def track_lines(grid: np.ndarray, ppm: float, xs: np.ndarray, mm: np.ndarray, y_from: int, y_to: int,
                slab_px: int | None = None) -> list[tuple[int, np.ndarray, np.ndarray]]:
    """Follow the rhythm strip's major lines upward through the grid map in thin slabs, so a tilted or keystoned
    photo cannot swap a line for its neighbour (the per-slab shift is a few px, far below one square). Returns
    (slab centre y, xs, mm) for every slab, newest first. [13 Oct 2026]"""
    slab_px = slab_px or max(8, int(4 * ppm))
    step = 5.0 * ppm
    cur = {float(m): float(x) for x, m in zip(xs, mm)}
    miss = {float(m): 0 for m in mm}
    out = []
    y = y_from
    while y - slab_px >= y_to:
        prof = grid[y - slab_px:y].sum(0)
        n = max(3, int(10 * ppm))
        p = prof - np.convolve(prof, np.ones(n) / n, mode="same")
        from scipy.signal import find_peaks
        pk, _ = find_peaks(p, distance=max(2, int(3.5 * ppm)), prominence=max(1e-6, 0.15 * p.std()))
        pk = pk.astype(float)
        if len(pk):
            # global per-slab shift (tilt), then nearest-neighbour update of each tracked line
            keys = np.array(list(cur)); pos = np.array([cur[k] for k in keys])
            d0, best = 0.0, -1
            for d in np.arange(-0.25 * step, 0.25 * step + 0.5, 1.0):
                sc = int((np.abs(pk[None, :] - (pos[:, None] + d)).min(1) < 0.15 * step).sum())
                if sc > best:
                    best, d0 = sc, d
            for k, x in zip(keys, pos):
                j = int(np.argmin(np.abs(pk - (x + d0))))
                if abs(pk[j] - (x + d0)) < 0.25 * step:
                    cur[k] = float(pk[j]); miss[k] = 0
                else:
                    cur[k] = x + d0; miss[k] += 1
        for k in [k for k, v in miss.items() if v > 6]:
            cur.pop(k); miss.pop(k)
        y -= slab_px
        ks = np.array(sorted(cur, key=lambda k: cur[k]))
        out.append((y + slab_px // 2, np.array([cur[k] for k in ks]), ks))
    return out


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
    return ruler_from_lines(xs, mm)


def ruler_lines(profile: np.ndarray, ppm: float) -> tuple | None:
    """ruler() plus the (xs, mm) line list it was fitted on."""
    g = grid_lines(profile, ppm)
    if g is None:
        return None
    pk, step = g
    idx, xs = [0], [float(pk[0])]
    for q in pk[1:]:
        k = int(round((q - xs[-1]) / step))
        if k < 1:
            continue
        idx.append(idx[-1] + k)
        xs.append(float(q))
    xs, mm = np.array(xs), 5.0 * np.array(idx)
    c = ruler_from_lines(xs, mm)
    return (c, xs, mm) if c is not None else None


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
    ppm, grid_found = grid_period_found(grid, prior)
    info["px_per_mm"] = ppm
    if not ppm or ppm < 2:
        return None, {**info, "error": "grid not found"}
    # Scale self-check (28 Oct 2026): the grid's own scale must agree with the trace length (a standard print is
    # 10 s = about 258 mm wide). When it does not, the time axis and amplitudes cannot be trusted (book-page scans,
    # reduced or non-standard prints) and the engine must say so instead of showing a tier.
    info["scale_dev"] = abs(ppm / prior - 1)
    if not grid_found:
        return None, {**info, "error": "grid not found"}
    if info["scale_dev"] > SCALE_TOLERANCE:
        return None, {**info, "error": "grid scale does not match the trace length (not a standard 25 mm/s, 10 s print)"}

    # rows: horizontal profile of the signal map, smoothed over ~5 mm
    prof = gaussian_smooth(sig.sum(1), max(1.0, 2.5 * ppm))
    from scipy.signal import find_peaks
    pk, props = find_peaks(prof, distance=max(3, int(8 * ppm)), prominence=prof.max() * 0.05)
    # Layout from the number of trace rows (22 Oct 2026; Homi's web images): 4 = 3x4 + lead II strip, 3 = 3x4 without
    # a strip, 6 = 3x4 + three strips (strips ignored: their leads are not labelled reliably), 12 = 12x1 stacked leads.
    # Faint extra "rows" (labels, calibration marks) are dropped at 35 % prominence.
    strong = pk[props["prominences"] >= prof.max() * 0.35]
    pk = np.sort(strong if len(strong) in (3, 4, 6, 12) else pk)
    n = len(pk)
    if n == 4:
        layout, rows, strip_idx = "3x4+1", list(range(3)), 3
    elif n == 3:
        layout, rows, strip_idx = "3x4", list(range(3)), None
    elif n == 6:
        layout, rows, strip_idx = "3x4+3", list(range(3)), None
    elif n == 12:
        layout, rows, strip_idx = "12x1", list(range(12)), None
    else:
        return None, {**info, "error": f"unsupported layout: found {n} trace rows", "rows_found": int(n)}
    info["layout"] = layout
    info["rows_y"] = pk.tolist()
    # band boundaries: midpoints between consecutive rows; a strip row (n == 4) extends to the image bottom, the last
    # 3x4 row of a 3x4+3 print ends where the strips begin
    mids = [int((pk[i] + pk[i + 1]) / 2) for i in range(n - 1)]
    bounds = [0] + mids + [h]
    if layout == "3x4+3":
        bounds = [0, mids[0], mids[1], mids[2]]  # rows 0-2 only; the strips below are ignored
    used_rows = rows + ([strip_idx] if strip_idx is not None else [])

    out = np.full((12, 1000), np.nan, np.float32)
    total_px = 250 * ppm  # 10 s at 25 mm/s
    # Time axis from the reference row (the rhythm strip when present, else the last 3x4 / 12x1 row: every row of a print
    # shares the same 10 s axis).
    ref = strip_idx if strip_idx is not None else used_rows[-1]
    rb = sig[bounds[ref]:bounds[ref + 1]].sum(0)
    # Columns that hold trace: a flat tail is only ~trace-thickness pixels high, so the threshold must not scale with
    # the tallest complex (13 Oct 2026: ptbxl21243's 1.5 mV-wide complexes made rb.max() so large that the flat last
    # 0.35 s fell under an 8 % cut and the whole time axis shifted by 35 samples).
    on = np.where(rb > max(0.5, rb.max() * 0.02))[0]
    if len(on) < 10:
        return None, {**info, "error": "rhythm strip not found"}
    X1 = int(on[-1])
    X0 = max(0, int(round(X1 - total_px)))  # anything left of 10 s is calibration pulse / labels
    info["x_range"] = (X0, X1)
    # Grid rulers: local pixel->mm maps from the printed grid, so perspective/stretch in a photo is undone.
    def vprof(a, b):  # vertical-line profile from the central part of a band: tilted lines smear less [13 Oct 2026]
        hh = b - a
        return grid[a + int(hh * SLAB):b - int(hh * SLAB)].sum(0)
    RL = ruler_lines(vprof(bounds[ref], bounds[ref + 1]), ppm)
    R = RL[0] if RL is not None else None
    end_mm_r = float(np.polyval(R, X1)) if R is not None else None
    info["ruler"] = R is not None
    xc = (X0 + X1) / 2
    # Row rulers are chained upward from the rhythm strip (lines labelled by continuity), so every row shares the
    # strip's mm origin. Before 13 Oct 2026 each row had its own ruler aligned by rounding to whole 5 mm squares,
    # which put whole rows 0.2 s off on photos (ptbxl00959/00201/07835).
    chain = {}
    if RL is not None and CHAIN:
        if TRACK:
            ys = int((bounds[ref] + bounds[ref + 1]) / 2)
            tr = track_lines(grid, ppm, RL[1], RL[2], ys, 0)
            for row in [r for r in reversed(used_rows) if r != ref]:
                yc_row = (bounds[row] + bounds[row + 1]) / 2
                # lines tracked through this row's band, pooled over the band's central slabs
                pts = [(x, m) for (yy, xs_, mm_) in tr if abs(yy - yc_row) < (bounds[row + 1] - bounds[row]) * (0.5 - SLAB)
                       for x, m in zip(xs_, mm_)]
                if len(pts) < 6:
                    break
                xs_, mm_ = np.array([p[0] for p in pts]), np.array([p[1] for p in pts])
                c = ruler_from_lines(xs_, mm_)
                if c is None:
                    break
                chain[row] = c
        else:
            prev = (RL[1], RL[2])
            for row in [r for r in reversed(used_rows) if r != ref]:
                rc = ruler_chain(vprof(bounds[row], bounds[row + 1]), ppm, prev[0], prev[1])
                if rc is None:
                    break
                chain[row] = rc[0]
                prev = (rc[1], rc[2])
    info["chained_rows"] = sorted(chain)
    for row in used_rows:
        band = sig[bounds[row]:bounds[row + 1]]
        gband = grid[bounds[row]:bounds[row + 1]]
        x0, x1 = X0, X1
        ys = np.arange(band.shape[0])[:, None]
        wsum = band.sum(0) + 1e-9
        y = (band * ys).sum(0) / wsum
        valid = band.max(0) > 0.15
        B = (R if row == ref else chain.get(row, ruler(vprof(bounds[row], bounds[row + 1]), ppm))) if R is not None else None
        if B is not None:
            # chained rows share the reference row's origin (off = 0); an unchained row falls back to whole-square alignment
            off = 0.0 if (row == ref or row in chain) else 5.0 * round((np.polyval(R, xc) - np.polyval(B, xc)) / 5.0)
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
        if row == strip_idx:
            out[1] = samples  # rhythm strip: lead II, full 10 s
            continue
        if layout == "12x1":
            out[row] = samples - np.nanmedian(samples) if np.isfinite(samples).any() else samples
            continue
        for c in range(4):
            j = LEADS.index(GRID_3x4[row][c])
            if row == 1 and c == 0 and strip_idx is not None:  # lead II: the rhythm strip is used instead
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
