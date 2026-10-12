#!/usr/bin/env bash
# Job 2: digitize the already-rendered training images with the LITE digitizer (the one the phone
# runs), on the GPU with 4 workers, then fine-tune the classifier on those signals.
set -euo pipefail
cd "$(dirname "$0")"
LOG=out/job_lite.log; mkdir -p out work/digitized_lite; exec > >(tee -a "$LOG") 2>&1
echo "== $(date '+%F %T') lite job start"
USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
if [ "$USED" -gt 1500 ]; then echo "GPU busy: ${USED} MiB. Not starting."; exit 3; fi
PY=$PWD/.venv/bin/python
echo "== lite digitize (resumable; 2 workers)"
for i in 0 3; do  # 2 workers: 4 x 5.8 GB does not fit in 16 GB
  $PY lite_digitizer.py work/images work/digitized_lite --size 1600 --shard $i/4 >> out/lite_w$i.log 2>&1 &
done
wait $(jobs -p)  # only the workers: a bare "wait" also waits for the tee process substitution and never returns
echo "digitized: $(ls work/digitized_lite/*_timeseries_canonical.csv | wc -l)"; grep -h FAIL out/lite_w*.log | head -20 || true
echo "== fine-tune on lite signals"
DIGITIZED_DIR=work/digitized_lite OUT_TAG=lite $PY finetune_digitized.py
echo "== $(date '+%F %T') done"
