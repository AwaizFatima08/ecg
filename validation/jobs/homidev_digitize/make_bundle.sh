#!/usr/bin/env bash
# Assembles the self-contained job folder (on homi-nas) at validation/jobs/homidev_digitize/bundle/
set -euo pipefail
J="$(cd "$(dirname "$0")" && pwd)"; V="$J/../.."; B="$J/bundle"; D="$V/engines/Open-ECG-Digitizer"
mkdir -p "$B/models" "$B/digitizer" "$B/data"
cp "$J"/run.sh "$J"/render_bulk.py "$J"/finetune_digitized.py "$B/"
cp "$V"/render_ptbxl_to_images.py "$V"/train_classifier.py "$B/"
cp "$V"/images/manifest.csv "$B/phase0_manifest.csv"
cp "$V"/models/ecgnet.pt "$V"/models/ecgnet_meta.json "$B/models/"
rsync -a --delete "$D/src" "$D/weights" "$D/LICENSE" "$B/digitizer/"
sed -e "s#device: 'cuda:0'#device: 'cuda:0'#g" \
    -e "s#images_path: .*#images_path: '../work/images'#" \
    -e "s#output_path: .*#output_path: '../work/digitized'#" \
    "$D/src/config/homilabs_ptbxl.yml" | sed "s#device: 'cpu'#device: 'cuda:0'#g" > "$B/digitizer/src/config/homidev_bulk.yml"
rsync -a --delete --exclude 'records500' "$V/data/ptbxl" "$B/data/"
du -sh "$B"
