#!/usr/bin/env bash
# Phase 0 reading-engine test (design-v1 Section 10).
#   scripts/phase0.sh [run-name] [extra readImages.ts args, e.g. --limit 10 --only scan]
# Renders the PTB-XL set if missing, reads every image with Claude, scores, writes the report.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUN="${1:-$(date +%Y-%m-%d)}"; shift || true
[ -f "$ROOT/secrets/anthropic.env" ] || { echo "Missing secrets/anthropic.env (see secrets/README.md)"; exit 2; }
set -a; . "$ROOT/secrets/anthropic.env"; set +a
cd "$ROOT/validation"
[ -f images/manifest.csv ] || .venv/bin/python render_ptbxl_to_images.py
(cd "$ROOT/functions" && npx tsx scripts/readImages.ts "$ROOT/validation/images" "$ROOT/validation/images/readings_$RUN.jsonl" "$@")
.venv/bin/python run_eval.py "images/readings_$RUN.jsonl" --run "$RUN"
