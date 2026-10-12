#!/usr/bin/env python3
"""Knowledge distillation: train a small U-Net ("student") to reproduce the Open-ECG-Digitizer U-Net
("teacher", 22.6 M params, ~263 GFLOPs per 768 px tile) so the phone can run it in seconds.

Training data: the rendered training images in work/images (never the Phase 0 test images).
Each step: random 512x512 crops at the phone's working scale (long side 1600 px), teacher softmax
computed on the fly on the GPU, student trained with KL divergence (soft targets) plus extra weight
on signal pixels, which are rare but matter most.

  python distill_unet.py --dims 12,24,48,64,96 --steps 20000
Outputs: out/student_<dims>.pt and out/student_<dims>.onnx
"""
from __future__ import annotations

import argparse
import random
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as F

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "digitizer"))
from src.model.unet import UNet  # noqa: E402

SIGNAL = 2


def load_teacher(dev):
    t = UNet(3, 4, 2, [32, 64, 128, 256, 320, 320, 320, 320])
    sd = torch.load(HERE / "digitizer" / "weights" / "unet_weights_07072025.pt", map_location="cpu", weights_only=False)
    sd = sd.get("state_dict", sd) if isinstance(sd, dict) else sd
    t.load_state_dict({k.replace("_orig_mod.", "").replace("module.", ""): v for k, v in sd.items()})
    return t.to(dev).eval()


def load_image(p: Path, size=1600) -> np.ndarray:
    """Kept as uint8 in the cache (a float copy of one image is ~23 MB; uint8 is ~6 MB)."""
    rgb = cv2.cvtColor(cv2.imread(str(p)), cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    s = size / max(h, w)
    if s != 1:
        rgb = cv2.resize(rgb, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    return rgb





def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dims", default="12,24,48,64,96")
    ap.add_argument("--depth", type=int, default=1)
    ap.add_argument("--steps", type=int, default=20000)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--crop", type=int, default=512)
    a = ap.parse_args()
    dims = [int(v) for v in a.dims.split(",")]
    tag = "_".join(map(str, dims))
    dev = "cuda"
    torch.set_num_threads(4)
    cv2.setNumThreads(2)
    torch.backends.cudnn.benchmark = True
    teacher = load_teacher(dev)
    student = UNet(3, 4, a.depth, dims).to(dev)
    print(f"student {dims} depth {a.depth}: {sum(p.numel() for p in student.parameters()) / 1e6:.2f} M params", flush=True)
    files = sorted((HERE / "work" / "images").glob("*.jpg"))
    rng = random.Random(0)
    opt = torch.optim.AdamW(student.parameters(), lr=2e-3, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=3e-3, total_steps=a.steps)
    cache: dict[int, np.ndarray] = {}
    t0 = time.time()
    for step in range(1, a.steps + 1):
        xs = []
        for _ in range(a.batch):
            i = rng.randrange(len(files))
            if i not in cache:
                if len(cache) > 150:  # ~0.9 GB of uint8 images; homidev has 16 GB shared with the desktop
                    cache.pop(next(iter(cache)))
                cache[i] = load_image(files[i])
            im = cache[i]
            h, w = im.shape[:2]
            full_lo, full_hi = float(im.min()), float(im.max())
            y0, x0 = rng.randint(0, max(0, h - a.crop)), rng.randint(0, max(0, w - a.crop))
            c = np.zeros((a.crop, a.crop, 3), np.float32)
            patch = (im[y0:y0 + a.crop, x0:x0 + a.crop].astype(np.float32) - full_lo) / (full_hi - full_lo + 1e-9)
            c[:patch.shape[0], :patch.shape[1]] = patch
            if rng.random() < 0.5:  # mild photometric jitter so the student is not brittle
                c = np.clip(c * rng.uniform(0.8, 1.1) + rng.uniform(-0.05, 0.05), 0, 1)
            xs.append(c.transpose(2, 0, 1))
        x = torch.from_numpy(np.stack(xs)).to(dev)
        with torch.no_grad():
            tp = torch.softmax(teacher(x), 1)
        ls = F.log_softmax(student(x), 1)
        kl = (tp * (torch.log(tp + 1e-8) - ls)).sum(1)            # per-pixel KL
        w = 1.0 + 9.0 * tp[:, SIGNAL]                               # trace pixels count 10x
        loss = (kl * w).mean()
        opt.zero_grad()
        loss.backward()
        opt.step()
        sched.step()
        if step % 500 == 0:
            with torch.no_grad():
                agree = (ls.argmax(1) == tp.argmax(1)).float().mean().item()
                sig_t = tp.argmax(1) == SIGNAL
                sig_iou = ((ls.argmax(1) == SIGNAL) & sig_t).sum().item() / max(1, ((ls.argmax(1) == SIGNAL) | sig_t).sum().item())
            print(f"step {step}  loss {loss.item():.4f}  pixel agreement {agree:.3f}  signal IoU {sig_iou:.3f}  ({time.time() - t0:.0f}s)", flush=True)
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    student.eval().cpu()
    torch.save({"state_dict": student.state_dict(), "dims": dims, "depth": a.depth}, out / f"student_{tag}.pt")
    torch.onnx.export(student, torch.zeros(1, 3, 256, 256), out / f"student_{tag}.onnx", input_names=["image"],
                      output_names=["logits"], dynamic_axes={"image": {2: "h", 3: "w"}, "logits": {2: "h", 3: "w"}},
                      opset_version=17, dynamo=False)
    print("saved", out / f"student_{tag}.pt", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
