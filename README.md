# ECG Reader (working title) — HomiLabs

Clinical decision support for doctors: reads a scanned or photographed **paper ECG**, returns a structured
interpretation and an alert tier. Guest mode, nothing stored.

**Status (12 Oct 2026):** all phases built and tested against the local emulator. **Not releasable** until
Homi's clinical gates are passed: Phase 0 accuracy review, CRITICAL list, rules approval. See
[docs/release-checklist.md](docs/release-checklist.md) and [docs/decisions.md](docs/decisions.md).

- Design: [docs/design-v1.md](docs/design-v1.md)
- Alert rules (Homi-readable): [functions/src/rules/alertRules.ts](functions/src/rules/alertRules.ts)
- Model instructions: [functions/src/provider/prompt.ts](functions/src/provider/prompt.ts)

## Layout
```
docs/         design, decisions, release checklist, privacy policy draft
app/          Flutter app (Android) — com.homilabs.ecg_reader
functions/    Cloud Functions: interpretEcg, reassessWithContext (TypeScript, asia-south1)
validation/   Phase 0: render PTB-XL as paper ECGs, score readings (results/ = reports only)
scripts/      emulators.sh, phase0.sh, backup.sh
secrets/      API key + release keystore (never in git or Google Drive)
store/        Play Store graphics
```

## Common tasks
```bash
# Unit tests
(cd functions && npm test)          # rules engine, guards, handlers
(cd app && flutter test)            # image prep (EXIF strip, warnings), models

# Local backend for phone testing (mock reader, or Claude if secrets/anthropic.env exists)
scripts/emulators.sh

# App against the emulator (phone on the same Wi-Fi)
cd app && flutter run --dart-define=USE_EMULATOR=true --dart-define=EMULATOR_HOST=192.168.100.164

# Phase 0 reading-engine test (needs secrets/anthropic.env)
scripts/phase0.sh 2026-10-12-pilot --limit 20 --only scan    # small pilot first
scripts/phase0.sh 2026-10-12                                 # full set: 126 records x 2 images
```

Phase 0 writes `validation/results/phase0_<run>.md` (metrics, committed) and
`validation/images/review_<run>.html` (side-by-side review page with images; local only).

## Session close
`git commit && git push`, then `scripts/backup.sh` (local mirror + snapshot + Google Drive, no secrets, no ECG data).
