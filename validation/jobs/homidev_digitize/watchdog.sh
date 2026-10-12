#!/usr/bin/env bash
# Hardware watchdog for ECG jobs on homidev: logs RAM/temps every 30 s and stops the job
# (kills processes matching $1) if available RAM < 3 GB, GPU > 80 C or CPU package > 80 C.
PAT="$1"; LOG=~/ecg-engine-job/out/watchdog.log
while pgrep -f "$PAT" > /dev/null; do
  avail=$(awk '/MemAvailable/ {print int($2/1048576)}' /proc/meminfo)
  gpu=$(nvidia-smi --query-gpu=temperature.gpu,utilization.gpu,memory.used --format=csv,noheader,nounits | tr -d ' ')
  gt=${gpu%%,*}
  cpu=$(sensors 2>/dev/null | awk '/Package id 0/ {gsub(/[+°C]/,"",$4); print int($4)}')
  echo "$(date +%T) ramAvailGB=$avail gpu(temp,util,memMB)=$gpu cpuC=${cpu:-?} load=$(cut -d' ' -f1 /proc/loadavg)" >> "$LOG"
  if [ "$avail" -lt 3 ] || [ "${gt:-0}" -gt 80 ] || [ "${cpu:-0}" -gt 80 ]; then
    echo "$(date +%T) WATCHDOG STOP: ramAvail=${avail}GB gpu=${gt}C cpu=${cpu}C" >> "$LOG"; pkill -f "$PAT"; exit 1
  fi
  sleep 30
done
