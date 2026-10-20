#!/usr/bin/env bash
# v7j (21 Oct 2026): re-fine-tune the 3 seeds with the old-infarct label remap + hard-negative weighting for the
# acute-infarction labels (train_classifier.label_vector / hard_negative_weight). Uses the v7h digitized signals.
# One job at a time, watchdog on. Expected ~10 min GPU, ~6 GB VRAM.
set -uo pipefail
cd "$(dirname "$0")"
PY=$PWD/.venv/bin/python
LOG=out/v7j.log
log() { echo "$(date '+%F %T') $*" | tee -a "$LOG"; }
wait_free() {
  while true; do
    used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
    ours=$(pgrep -fa "distill_unet|lite_digitizer|finetune_digitized|render_bulk|score_digitizer|train_classifier_v2" | grep -vE "watchdog.sh|run_v7" | wc -l)
    [ "$used" -lt 1500 ] && [ "$ours" -eq 0 ] && return
    log "waiting: GPU ${used} MiB in use, our jobs running: ${ours}"; sleep 60
  done
}
step() {
  local name=$1 pat=$2; shift 2
  wait_free; log "START $name"
  "$@" >> "out/v7j_${name}.log" 2>&1 & local pid=$!
  sleep 5; ./watchdog.sh "$pat" & local wd=$!
  wait $pid; local rc=$?; kill $wd 2>/dev/null
  log "END $name (exit $rc)"
  grep -q "WATCHDOG STOP" out/watchdog.log 2>/dev/null && { log "watchdog stopped a step — halting"; exit 1; }
  [ $rc -ne 0 ] && { log "step $name failed — halting"; exit 1; }
}
rm -f out/ALL_JOBS_DONE4
log "== v7j queue start"
for s in 1 2 3; do
  step "finetune_v7j_s$s" finetune_digitized env BASE_MODEL=out/ecgnet_v2.pt DIGITIZED_DIR=work/digitized_v7h OUT_TAG=v2_v7j_s$s SEED=$s EPOCHS=40 \
    $PY finetune_digitized.py
done
log "== v7j queue done; homidev is free"
touch out/ALL_JOBS_DONE4
DISPLAY=:0 notify-send "ECG engine v7j jobs finished" "homidev is free again." 2>/dev/null || true
