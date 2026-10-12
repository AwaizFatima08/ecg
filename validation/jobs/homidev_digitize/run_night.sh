#!/usr/bin/env bash
# Overnight queue for the on-device ECG engine (homidev). Strictly ONE job at a time.
# Before each step: wait until homidev's GPU is free of other work (homi-nas asset jobs have priority).
# Every step runs under watchdog.sh (stops the step if RAM < 3 GB or GPU/CPU > 80 C).
# At the end: out/ALL_JOBS_DONE + a desktop notification.
set -uo pipefail
cd "$(dirname "$0")"
PY=$PWD/.venv/bin/python
LOG=out/night.log
mkdir -p out
log() { echo "$(date '+%F %T') $*" | tee -a "$LOG"; }

wait_free() {
  # GPU memory in use by anything other than an idle ComfyUI (~0.3 GB) means someone else is working.
  while true; do
    used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
    ours=$(pgrep -fa "distill_unet|lite_digitizer|finetune_digitized|render_bulk|score_digitizer" | grep -vE "watchdog.sh|run_night.sh" | wc -l)
    if [ "$used" -lt 1500 ] && [ "$ours" -eq 0 ]; then return; fi
    log "waiting: GPU ${used} MiB in use, our jobs running: ${ours}"
    sleep 120
  done
}

step() {  # step <name> <pattern-for-watchdog> <command...>
  local name=$1 pat=$2; shift 2
  wait_free
  log "START $name"
  "$@" >> "out/night_${name}.log" 2>&1 &
  local pid=$!
  sleep 5
  ./watchdog.sh "$pat" &
  local wd=$!
  wait $pid
  local rc=$?
  kill $wd 2>/dev/null
  log "END $name (exit $rc)"
  if grep -q "WATCHDOG STOP" out/watchdog.log 2>/dev/null; then
    log "watchdog stopped a step — halting the queue for safety"; exit 1
  fi
}

rm -f out/ALL_JOBS_DONE
log "== night queue start"

# 0. let the running student finish first
while pgrep -f "distill_unet.py --dims 12,24,48,64,96" > /dev/null; do sleep 60; done
log "student A (12,24,48,64,96 / 12k steps) finished"

# 1. model-selection set: 200 fold-10 records (not trained on, not Phase 0), scan + photo
step render_selection render_bulk $PY render_bulk.py --selection 200 --out work/selection/images

# 2. larger student, trained longer
step distill_B distill_unet $PY distill_unet.py --dims 16,32,64,128,160,160 --steps 30000

# 3. score teacher and both students on the selection set
for m in teacher A B; do
  case $m in
    teacher) arg="" ;;
    A) arg="--student out/student_12_24_48_64_96.pt" ;;
    B) arg="--student out/student_16_32_64_128_160_160.pt" ;;
  esac
  step "sel_digitize_$m" lite_digitizer $PY lite_digitizer.py work/selection/images work/selection/out_$m --size 1600 $arg
  step "sel_score_$m" score_digitizer $PY score_digitizer.py work/selection/selection_manifest.csv work/selection/out_$m "$m"
done

# 4. choose the student with the best photo median r (accuracy first; on a tie the smaller one)
CHOSEN=$($PY - <<'EOF'
import re
best = None
for line in open("out/digitizer_scores.tsv"):
    f = line.rstrip("\n").split("\t")
    if f[0] not in ("A", "B"):
        continue
    r = float(re.search(r"photo: median r ([0-9.]+)", line).group(1))
    if best is None or r > best[1] + 0.002:
        best = (f[0], r)
print({"A": "out/student_12_24_48_64_96.pt", "B": "out/student_16_32_64_128_160_160.pt"}[best[0]])
EOF
)
echo "$CHOSEN" > out/chosen_student.txt
log "chosen student: $CHOSEN"

# 5. re-digitize the 4,600 training ECGs with the chosen student
step train_digitize lite_digitizer $PY lite_digitizer.py work/images work/digitized_student --size 1600 --student "$CHOSEN"

# 6. three classifiers (different seeds) on student-digitized + clean signals -> ensemble
for s in 1 2 3; do
  step "finetune_s$s" finetune_digitized env DIGITIZED_DIR=work/digitized_student OUT_TAG=student_s$s SEED=$s EPOCHS=40 \
    $PY finetune_digitized.py
done

# 7. digitize the selection and Phase 0 sets with the chosen student (for the final evaluation on homi-nas)
step sel_digitize_chosen lite_digitizer $PY lite_digitizer.py work/selection/images work/selection/out_chosen --size 1600 --student "$CHOSEN"
step phase0_digitize lite_digitizer $PY lite_digitizer.py phase0/images phase0/out_student --size 1600 --student "$CHOSEN"

log "== all ECG jobs done; homidev is free"
touch out/ALL_JOBS_DONE
DISPLAY=:0 notify-send "ECG engine jobs finished" "homidev is free again." 2>/dev/null || true
