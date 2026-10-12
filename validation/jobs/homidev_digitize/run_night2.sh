#!/usr/bin/env bash
# Second overnight queue (runs only after run_night.sh has written out/ALL_JOBS_DONE). One job at a time, watchdog on.
#   1. classifier v2 on PTB-XL + ecg-arrhythmia (66 k ECGs; GPU, ~30 min incl. cache build on 28 cores)
#   2. fine-tune 3 seeds of v2 on the student-digitized 4,600 (ensemble)
# Expected: ~1 h GPU, ~6 GB VRAM, ~8 GB RAM peak (cache 1.6 GB float16).
set -uo pipefail
cd "$(dirname "$0")"
PY=$PWD/.venv/bin/python
LOG=out/night2.log
log() { echo "$(date '+%F %T') $*" | tee -a "$LOG"; }
wait_free() {
  while true; do
    used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
    ours=$(pgrep -fa "distill_unet|lite_digitizer|finetune_digitized|render_bulk|score_digitizer|train_classifier_v2" | grep -vE "watchdog.sh|run_night" | wc -l)
    [ "$used" -lt 1500 ] && [ "$ours" -eq 0 ] && return
    log "waiting: GPU ${used} MiB in use, our jobs running: ${ours}"; sleep 120
  done
}
step() {
  local name=$1 pat=$2; shift 2
  wait_free; log "START $name"
  "$@" >> "out/night2_${name}.log" 2>&1 & local pid=$!
  sleep 5; ./watchdog.sh "$pat" & local wd=$!
  wait $pid; local rc=$?; kill $wd 2>/dev/null
  log "END $name (exit $rc)"
  grep -q "WATCHDOG STOP" out/watchdog.log 2>/dev/null && { log "watchdog stopped a step — halting"; exit 1; }
}
log "== night queue 2 start"
until [ -f out/ALL_JOBS_DONE ]; do sleep 120; done
rm -f out/ALL_JOBS_DONE2
[ -s data/ecg-arrhythmia/all_records.txt ] || { log "ecg-arrhythmia data missing — abort"; exit 1; }
step build_cache_v2 train_classifier_v2 $PY train_classifier_v2.py --build-cache
step train_v2 train_classifier_v2 $PY train_classifier_v2.py --epochs 25 --width 64
for s in 1 2 3; do
  step "finetune_v2_s$s" finetune_digitized env BASE_MODEL=out/ecgnet_v2.pt DIGITIZED_DIR=work/digitized_student OUT_TAG=v2_student_s$s SEED=$s EPOCHS=40 \
    $PY finetune_digitized.py
done
log "== night queue 2 done; homidev is free"
touch out/ALL_JOBS_DONE2
DISPLAY=:0 notify-send "ECG engine jobs (round 2) finished" "homidev is free again." 2>/dev/null || true
