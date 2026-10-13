#!/usr/bin/env bash
# v7h queue (13 Oct 2026): re-digitize with the time-axis-fixed lite digitizer, then re-fine-tune the 3 seeds.
# One job at a time, watchdog on. Expected ~25 min GPU, ~6 GB VRAM, ~8 GB RAM.
set -uo pipefail
cd "$(dirname "$0")"
PY=$PWD/.venv/bin/python
LOG=out/v7h.log
log() { echo "$(date '+%F %T') $*" | tee -a "$LOG"; }
wait_free() {
  while true; do
    used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
    ours=$(pgrep -fa "distill_unet|lite_digitizer|finetune_digitized|render_bulk|score_digitizer|train_classifier_v2" | grep -vE "watchdog.sh|run_v7h|run_night" | wc -l)
    [ "$used" -lt 1500 ] && [ "$ours" -eq 0 ] && return
    log "waiting: GPU ${used} MiB in use, our jobs running: ${ours}"; sleep 60
  done
}
step() {
  local name=$1 pat=$2; shift 2
  wait_free; log "START $name"
  "$@" >> "out/v7h_${name}.log" 2>&1 & local pid=$!
  sleep 5; ./watchdog.sh "$pat" & local wd=$!
  wait $pid; local rc=$?; kill $wd 2>/dev/null
  log "END $name (exit $rc)"
  grep -q "WATCHDOG STOP" out/watchdog.log 2>/dev/null && { log "watchdog stopped a step — halting"; exit 1; }
  [ $rc -ne 0 ] && { log "step $name failed — halting"; exit 1; }
}
rm -f out/ALL_JOBS_DONE3
log "== v7h queue start"
ST=out/student_16_32_64_128_160_160.pt
step train_digitize lite_digitizer $PY lite_digitizer.py work/images work/digitized_v7h --size 1600 --student $ST
step sel_digitize lite_digitizer $PY lite_digitizer.py work/selection/images work/sel_v7h --size 1600 --student $ST
step multan_digitize lite_digitizer $PY lite_digitizer.py work/multan work/multan_v7h --size 1600 --student $ST
for s in 1 2 3; do
  step "finetune_v7h_s$s" finetune_digitized env BASE_MODEL=out/ecgnet_v2.pt DIGITIZED_DIR=work/digitized_v7h OUT_TAG=v2_v7h_s$s SEED=$s EPOCHS=40 \
    $PY finetune_digitized.py
done
log "== v7h queue done; homidev is free"
touch out/ALL_JOBS_DONE3
DISPLAY=:0 notify-send "ECG engine v7h jobs finished" "homidev is free again." 2>/dev/null || true
