# ECG Reader (working title) — HomiLabs

Clinical decision support for doctors: reads a scanned or photographed **paper ECG**,
returns a structured interpretation and an alert tier. Guest mode, nothing stored.

- Design: [docs/design-v1.md](docs/design-v1.md) (v1 DRAFT — open decisions in Section 12)
- Current phase: **Phase 0 — reading-engine test** (no app code until the Phase 0 gate is passed)

## Layout
```
docs/         design and decision records
app/          Flutter app (Phase 3+)
functions/    Firebase Cloud Functions (Phase 1+)
validation/   Phase 0 scripts; results/ holds reports only — no ECG images or patient data
scripts/      backup.sh (local mirror + snapshot + Google Drive)
```

## Session close
`git commit && git push`, then `scripts/backup.sh`.
