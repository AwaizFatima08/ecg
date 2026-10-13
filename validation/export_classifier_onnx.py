#!/usr/bin/env python3
"""Export EcgNet checkpoints to ONNX for the app (input [N, 13, 1000] paper view, output logits [N, labels]).
  python export_classifier_onnx.py models/v2/ecgnet_v2_v7h_s1.pt ../app/assets/models/ecgnet_v2_s1.onnx ..."""
import sys
import numpy as np, torch
from train_classifier import EcgNet
args = sys.argv[1:]
for src, dst in zip(args[::2], args[1::2]):
    ck = torch.load(src, map_location="cpu")
    m = EcgNet(len(ck["labels"]), ck["width"]); m.load_state_dict(ck["state_dict"]); m.eval()
    x = torch.zeros(1, 13, 1000)
    torch.onnx.export(m, x, dst, input_names=["input"], output_names=["logits"], opset_version=17,
                      dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}}, dynamo=False)
    import onnxruntime as ort
    s = ort.InferenceSession(dst, providers=["CPUExecutionProvider"])
    xr = torch.randn(2, 13, 1000)
    a = m(xr).detach().numpy(); b = s.run(None, {"input": xr.numpy()})[0]
    print(f"{src} -> {dst}: max |torch - onnx| = {np.abs(a - b).max():.2e}, labels {len(ck['labels'])}")
