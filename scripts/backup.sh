#!/usr/bin/env bash
# Backs up ECG Reader:
#   1. Local mirror + snapshot (INCLUDING secrets/)
#      -> /mnt/storage/project_backups/ecg_backup/
#   2. Google Drive (rclone remote "gdrive:"), EXCLUDING secrets/, credentials
#      and any validation data/images.
#      https://drive.google.com/drive/folders/14Q4nfBdsqi0n_u2XIEZ-1Hz0GFOplGle
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"
LOCAL=/mnt/storage/project_backups/ecg_backup
DRIVE_FOLDER_ID=14Q4nfBdsqi0n_u2XIEZ-1Hz0GFOplGle
STAMP=$(date +%Y%m%d_%H%M)

EXCLUDES=(--exclude 'build/' --exclude '.dart_tool/' --exclude 'node_modules/'
          --exclude '.gradle/' --exclude '.idea/' --exclude '*.iml' --exclude '.cxx/'
          --exclude '.venv/')

echo "== Local mirror -> $LOCAL/current"
mkdir -p "$LOCAL"
rsync -a --delete "${EXCLUDES[@]}" --exclude 'validation/data/' --exclude 'validation/private/' "$SRC/" "$LOCAL/current/"

echo "== Local snapshot archive"
tar -C "$(dirname "$SRC")" -czf "$LOCAL/ecg_${STAMP}.tar.gz" \
  --exclude='*/build' --exclude='*/.dart_tool' --exclude='*/node_modules' --exclude='*/.gradle' \
  --exclude='*/.venv' --exclude='*/validation/data' --exclude='*/validation/images' \
  "$(basename "$SRC")"
# Keep the 10 newest snapshots.
ls -1t "$LOCAL"/ecg_*.tar.gz | tail -n +11 | xargs -r rm --

echo "== Google Drive (no secrets, no ECG data)"
rclone sync "$SRC" "gdrive:" --drive-root-folder-id "$DRIVE_FOLDER_ID" \
  "${EXCLUDES[@]}" --exclude '.git/**' --exclude 'secrets/**' --exclude '.env*' \
  --exclude '**/key.properties' --exclude '*.jks' --exclude '*.keystore' \
  --exclude '**/google-services.json' --exclude '**/local.properties' \
  --exclude 'validation/data/**' --exclude 'validation/private/**' --exclude 'validation/images/**' --exclude 'validation/real_ecgs/**' \
  --fast-list --transfers 8
echo "Backup complete ($STAMP)."
