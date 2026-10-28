#!/usr/bin/env bash
# v18 (28 Oct 2026): v16 recipe plus a separate mi_posterior head (PTB-XL PMI/IPMI/IPLMI, PTB-DB "posterior"); 27 labels.
# Queued behind any running GPU job (wait_free). ~1 h GPU after a ~20 min cache build.
# One job at a time, watchdog on. Expected: cache build ~10 min CPU, base train ~40 min GPU, fine-tunes ~10 min; ~6 GB VRAM.
set -uo pipefail
cd "$(dirname "$0")"
PY=$PWD/.venv/bin/python
LOG=out/v18.log
log() { echo "$(date '+%F %T') $*" | tee -a "$LOG"; }
wait_free() {
  while true; do
    used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
    ours=$(pgrep -fa "distill_unet|lite_digitizer|finetune_digitized|render_bulk|score_digitizer|train_classifier_v2" | grep -vE "watchdog.sh|run_v" | wc -l)
    [ "$used" -lt 1500 ] && [ "$ours" -eq 0 ] && return
    log "waiting: GPU ${used} MiB in use, our jobs running: ${ours}"; sleep 60
  done
}
step() {
  local name=$1 pat=$2; shift 2
  wait_free; log "START $name"
  "$@" >> "out/v18_${name}.log" 2>&1 & local pid=$!
  sleep 5; ./watchdog.sh "$pat" & local wd=$!
  wait $pid; local rc=$?; kill $wd 2>/dev/null
  log "END $name (exit $rc)"
  grep -q "WATCHDOG STOP" out/watchdog.log 2>/dev/null && { log "watchdog stopped a step — halting"; exit 1; }
  [ $rc -ne 0 ] && { log "step $name failed — halting"; exit 1; }
}
rm -f out/ALL_JOBS_DONE18
until [ "$(sensors | awk '/Package id 0/ {gsub(/[+°C]/,"",$4); print int($4)}')" -lt 65 ]; do log "waiting for CPU to cool"; sleep 60; done
log "== v18 queue start: ptbdb $(find data/ptbdb -name "*.dat" | wc -l) acs $(find data/acs_chongqing -name "*.dat" | wc -l) sph $(find data/sph/records -name '*.h5' | wc -l) records on disk"
step build_cache_v8 train_classifier_v2 env CACHE_NAME=signals_v8.npz INCLUDE_CH21=0 $PY train_classifier_v2.py --build-cache
step train_v8 train_classifier_v2 env CACHE_NAME=signals_v8.npz OUT_NAME=ecgnet_v8.pt TORCH_THREADS=4 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 nice -n 5 $PY train_classifier_v2.py --epochs 25 --width 64
for s in 1 2 3; do
  step "finetune_v18_s$s" finetune_digitized env BASE_MODEL=out/ecgnet_v8.pt DIGITIZED_DIR=work/digitized_v7h OUT_TAG=v8_v18_s$s SEED=$s EPOCHS=40 OMP_NUM_THREADS=2 \
    $PY finetune_digitized.py
done
log "== v18 queue done; homidev is free"
touch out/ALL_JOBS_DONE18
DISPLAY=:0 notify-send "ECG engine v18 jobs finished" "homidev is free again." 2>/dev/null || true
