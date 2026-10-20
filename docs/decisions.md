# Decisions log — ECG Reader

Status of the open decisions in [design-v1.md](design-v1.md) Section 12, plus decisions taken while building.
Nothing marked **OPEN** or **ASSUMED** is final until Homi confirms it in writing.

| ID | Question | Status | Notes |
|---|---|---|---|
| D1 | Anonymous sign-in + daily usage counter for rate limiting | **ASSUMED yes (built)** | Implemented as recommended: `usage/{anonUid}_{yyyymmdd}` = count only, 2-day TTL. Limit 30/day via Remote Config `ecg_daily_limit`. Remove if Homi says no. |
| D2 | Reading engine | **DECIDED 12 Oct 2026 (revised): own on-device engine, no paid AI** | Homi: the app must stay free and ad-free, and per-reading API costs grow with installs. Claude is not used (no key bought). Engine = photo → signal digitization → measurements + small classifier, on the phone; feeds the same alert rules. The Claude adapter stays in the repo, unused. |
| D3 | English only for V1 | **ASSUMED (built English only)** | |
| D4 | Final CRITICAL / URGENT / ABNORMAL lists | **OPEN — Homi** | Starting tables are in `functions/src/rules/alertRules.ts` (all marked proposed). |
| D5 | Context fields | **ASSUMED (built design 7.3 list)** | Age, sex, complaints (+ ongoing chest pain), BP, HR, SpO₂, conditions. |
| D6 | Real de-identified hospital ECGs | **DECIDED 12 Oct 2026: later, after policy check** | Phase 0 uses PTB-XL only. |
| D7 | App name and placement | **OPEN** | Working title "ECG Reader", package `com.homilabs.ecg_reader`, standalone. |
| D8 | Release posture | **OPEN** (recommendation: closed testing first) | |
| D9 | Phase 0 go/no-go thresholds | **OPEN — after the first Phase 0 run** | |

## Release gates set by Homi (13 Oct 2026)
- **Accuracy target: as close to 100 % as achievable**, critical patterns first. No reader reaches 100 % (cardiologists
  disagree on a share of tracings), so the engine is tuned to be conservative: uncertainty escalates or says
  "review it yourself", never a false all-clear.
- **No publishing** until the engine's interpretations are reviewed by Homi **and then by at least two cardiologists**.
- **Reference books** (Hampton: *The ECG Made Easy*, *150 ECG Problems*; Luthra: *ECG Made Easy*; Warren summary) may be
  used to cross-check criteria and judgement calls (cite book and page). They are all-rights-reserved, so their text and
  ECG figures are **not** used as training or test data and are not copied into the app or repo.
- **Training data** (approved): PTB-XL (CC BY 4.0), the Multan *ECG Images dataset of Cardiac Patients* (Ch. Pervaiz Elahi
  Institute of Cardiology, Mendeley Data, CC BY 4.0) and PhysioNet VT/VF databases (vfdb, cudb).

## Engine rules approved by Homi (13 Oct 2026, "all agreed")
Homi approved in chat, after the morning report on v7d:
- **AF + slow block rule:** a slow (< 55/min) ventricular rhythm with regular P waves outnumbering the QRS is reported
  as high-grade / complete AV block (CRITICAL) even when the classifier also calls AF.
- **Slow cut-off 55/min** for escalating the measurement-based AV-block flag from URGENT (second-degree) to CRITICAL
  (high-grade). A complete block with an escape rate ≥ 55 (e.g. `ptbxl15368`, 58/min) stays URGENT.
- **Threshold policy v3** (ST-depression cut-off by Youden's J; ≥ 90 % sensitivity for the other critical labels).
- **QRS onset/offset velocity threshold 0.30** (calibrated on digitized traces).
- **R-peak gate** (second pass, 12–30 Hz slope energy) and whole-image U-Net on the phone.
- **Threshold policy v4 (13 Oct 2026, afternoon, "agreed"):** ST depression (URGENT on its own) gets the cut-off with
  ≥ 90 % *specificity* on the digitized validation fold (0.32; Youden had fallen to 0.12 after the digitizer fix and
  drove most new false alarms). Set on validation data only, then checked on the test sets (v7i).
- **21 Oct 2026 (adjudication, dossier v7i):** (1) rate rules **M6** (40–49/min → URGENT) and **M7** (AF/flutter ≥ 120/min
  → URGENT) are kept; where they outrank PTB-XL's tier map, the app's tier is the reference (`ptbxl00611`, `00658`, `03842`,
  `14792`, `03947`, `21675`). (2) **An old infarct is not an emergency**: Q waves / QS with persistent (aneurysmal) ST
  elevation and no acute features is URGENT at most, never CRITICAL — applies to `ptbxl08624` and to the over-calls
  `13556`, `05501`, `15858`, `07692`, `04576`, `14192`. Engine consequence: the "acute / recent infarction" and "ST
  elevation" labels must not fire on old-infarct morphology; training targets will be re-mapped accordingly.
These remain subject to the cardiologists' review before release (gate above).

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
