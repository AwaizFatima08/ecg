# Decisions log — ECG Reader

Status of the open decisions in [design-v1.md](design-v1.md) Section 12, plus decisions taken while building.
Nothing marked **OPEN** or **ASSUMED** is final until Homi confirms it in writing.

| ID | Question | Status | Notes |
|---|---|---|---|
| D1 | Anonymous sign-in + daily usage counter for rate limiting | **ASSUMED yes (built)** | Implemented as recommended: `usage/{anonUid}_{yyyymmdd}` = count only, 2-day TTL. Limit 30/day via Remote Config `ecg_daily_limit`. Remove if Homi says no. |
| D2 | AI provider(s) for Phase 0 | **DECIDED 12 Oct 2026: Claude only** | Model `claude-opus-5-5`, effort `high`. Provider is behind `VisionProvider`, so others can be added later. |
| D3 | English only for V1 | **ASSUMED (built English only)** | |
| D4 | Final CRITICAL / URGENT / ABNORMAL lists | **OPEN — Homi** | Starting tables are in `functions/src/rules/alertRules.ts` (all marked proposed). |
| D5 | Context fields | **ASSUMED (built design 7.3 list)** | Age, sex, complaints (+ ongoing chest pain), BP, HR, SpO₂, conditions. |
| D6 | Real de-identified hospital ECGs | **DECIDED 12 Oct 2026: later, after policy check** | Phase 0 uses PTB-XL only. |
| D7 | App name and placement | **OPEN** | Working title "ECG Reader", package `com.homilabs.ecg_reader`, standalone. |
| D8 | Release posture | **OPEN** (recommendation: closed testing first) | |
| D9 | Phase 0 go/no-go thresholds | **OPEN — after the first Phase 0 run** | |

## Decisions taken during the build (12 Oct 2026)

- **Build order:** Homi asked for the full build ("build, install, test, debug, prepare final version") and chose
  "build all phases now". The design's phase gates move to before release: the app is **not releasable** until
  Homi has reviewed Phase 0 results, the CRITICAL list (D4) and the rules file.
- **GitHub repo stays public** (Homi's choice). Never commit ECG images, datasets, keys or patient data.
- **Firebase project:** creating `ecg-reader-homilabs` failed: the Google account has reached its project quota.
  Until a project exists, everything runs against the local emulator (`demo-ecg-reader`).
- **Fixed codes in the model output:** each rhythm and finding carries a `code` from a fixed list
  (`functions/src/schema/ecgResult.ts`) as well as free text, so the rules engine never parses prose.
- **Asymmetric confidence:** CRITICAL patterns count from model confidence 0.30; everything else from 0.50.
- **Unreadable images:** the tier is UNREADABLE, unless a CRITICAL pattern is still seen. Then it is CRITICAL
  with a quality warning (never silently downgraded).
- **Context rules** use the LiveHealthy Vitals thresholds (BP very high above 180/120; SpO₂ critical below 90 %),
  plus proposed extras for Homi: SpO₂ below 85 → CRITICAL; chest pain at 40+, with diabetes or with known heart disease → at least URGENT.
- **No server-side refusal fallback to another model:** Phase 0 validates one specific model. A silent switch to
  another model would serve unvalidated readings, so a refusal fails visibly instead.
- **Server strips image metadata again** (EXIF/XMP/IPTC/comments) as defence in depth; the app already re-encodes without EXIF.
- **Region:** Cloud Functions in `asia-south1` (Mumbai), the closest to Pakistan.
- **Crashlytics:** deferred. It needs the real Firebase project's Gradle setup, and is added at the same time as `flutterfire configure`.
- **Launcher icon:** a simple ECG-wave glyph drawn in code (`store/icon-512.png`), a placeholder until Homi decides.
- **Release keystore:** `secrets/ecg-reader-release.jks` (local only; excluded from git and Google Drive).
