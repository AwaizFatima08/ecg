#!/usr/bin/env bash
# ECG engine job for homidev (RTX 5060 Ti). Self-contained: everything stays in this folder.
# Touches nothing else on homidev (no ComfyUI, Ollama, LM Studio, receiver or models).
#   ./run.sh            full job: setup, render, digitize (GPU), fine-tune (GPU)
#   ./run.sh finetune   only the fine-tune step (after a completed digitize)
set -euo pipefail
cd "$(dirname "$0")"
LOG=out/job.log; mkdir -p out work; exec > >(tee -a "$LOG") 2>&1
echo "== $(date '+%F %T') start ($*)"

# GPU guard: refuse to run if another process holds the GPU.
USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
if [ "$USED" -gt 1500 ]; then
  echo "GPU busy: ${USED} MiB in use by another process. Not starting."; nvidia-smi; exit 3
fi

# Own Python 3.12 environment (uv installs a private Python; nothing system-wide).
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .uvenv && .uvenv/bin/pip install -q uv
  .uvenv/bin/uv python install 3.12
  .uvenv/bin/uv venv -q -p 3.12 .venv
  # CUDA 12.8 wheels: required for RTX 50-series (Blackwell).
  .uvenv/bin/uv pip install -q -p .venv/bin/python torch torchvision --index-url https://download.pytorch.org/whl/cu128
  .uvenv/bin/uv pip install -q -p .venv/bin/python numpy pandas wfdb scipy matplotlib pillow scikit-image tqdm yacs \
      pyyaml networkx scikit-learn opencv-python-headless torch-tps "ray[tune]"
fi
PY=$PWD/.venv/bin/python
$PY -c "import torch; assert torch.cuda.is_available(), 'CUDA not available'; print('GPU:', torch.cuda.get_device_name(0))"

if [ "${1:-}" != "finetune" ]; then
  echo "== render"; $PY render_bulk.py --n-train 4000 --n-val 600 --out work/images
  echo "== digitize"
  (cd digitizer && $PY -m src.digitize --config src/config/homidev_bulk.yml) | grep -vE "it/s\]$" || true
  echo "digitized: $(ls work/digitized/*_timeseries_canonical.csv 2>/dev/null | wc -l)"
fi
echo "== fine-tune"; $PY finetune_digitized.py
echo "== $(date '+%F %T') done. Results in out/"
