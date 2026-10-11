# ECG Reader — Design Document v1 (DRAFT)

**Project:** ECG Reader (working title) — HomiLabs
**Owner / clinical validator:** Dr. Humayun Shahzad (Homi)
**Build tool:** Claude Code, on homi-nas
**Suggested location in repo:** `ecg_reader/docs/design-v1.md`
**Status:** Draft for review. Items marked **[CONFIRMED]** were stated by Homi. Items marked **[PROPOSED]** are my suggestions and are NOT decided until Homi confirms them. Section 12 lists everything that needs a decision.

---

## 1. Purpose

A tool for **doctors** that reads a **scanned or photographed paper ECG**, returns a structured interpretation, and raises an **alert level** if the findings look critical. Optionally, the doctor can add clinical context (complaints, BP, other findings) and the app checks whether the ECG is consistent with an emergency.

It is **clinical decision support for qualified clinicians**. It does not diagnose, and the doctor's own reading always prevails.

## 2. Confirmed requirements [CONFIRMED]

1. Input is a **scan or photo of a printed ECG**, not a direct digital feed (paper ECGs are the norm in Pakistan and many other countries).
2. Users are **doctors**; the app is **universal**, not tied to FFWTH or any organization.
3. **Guest mode only. No login, no accounts.**
4. **Nothing is saved.** An ECG is uploaded, interpreted, and not retained. Stateless per upload.
5. The app gives a **result and a critical alert** where relevant.
6. **Optional** clinical-context step: after the ECG reading the doctor may enter complaints, blood pressure and other findings; the app then raises or confirms the alert level based on whether the ECG fits the clinical picture. Doctors who rely on their own judgment can skip it.
7. The interpretation approach is open. Homi can read ECGs and will **validate** the logic personally.
8. Suggested reference approach: use existing public ECG portals/datasets with already-interpreted ECGs as reference material.

## 3. Critique and risks (read before building)

These are the points where I think the plan needs care. Each has a proposed mitigation built into this document.

**3.1 The hardest part is reading the ECG image, not building the app.**
Photos of printed ECGs vary wildly: lighting, skew, glare, thermal paper fading, different lead layouts, different grid scales. Whether any model can read them reliably enough is **unknown today**. Building the whole app first and discovering the reading is poor would waste weeks.
*Mitigation:* **Phase 0** (Section 10) tests the reading engine on real ECGs with a simple script **before any app code is written**. If it fails, we stop cheaply.

**3.2 "Build the model's memory from portals" does not work the way it sounds.**
A general vision model does not "learn" from a folder of example ECGs at runtime. Reference portals and datasets are useful for **(a) building a test set to measure accuracy** and **(b) writing better instructions and rule checklists**, not as a memory the app consults.
*Mitigation:* use PTB-XL (and similar) to create a **validation set**, not a memory. See Section 8.

**3.3 The dangerous error is a false "normal".**
A missed STEMI or complete heart block costs far more than an over-called one. A tool that sometimes says "normal" will be trusted exactly when it is wrong.
*Mitigation:* asymmetric design. There is **no plain "Normal" output**; the lowest tier is "No critical pattern detected on this image" with limitations shown. "Unreadable image" is a first-class result. The alert level can only be **escalated** by clinical context, never lowered (Section 7).

**3.4 Guest mode plus a paid AI backend is an abuse and cost risk.**
Anyone who finds the app can hammer the backend with no login to throttle them.
*Mitigation:* Firebase App Check (Play Integrity), anonymous sign-in for rate limiting, hard spending cap at the AI provider. This slightly bends "no memory" (a usage counter, no ECG data). **Needs Homi's confirmation** (Section 12, D1).

**3.5 Patient identity is printed on the ECG.**
Most printed ECGs carry the patient's name, age or hospital ID in the header. Sending that to a third-party API is a privacy problem even if we store nothing.
*Mitigation:* the crop step asks the doctor to crop to the trace area; the app shows a reminder; metadata is stripped; the backend never logs images. Provider data-retention terms must be checked and set to the strictest option before launch.

**3.6 Medical-app and regulatory exposure.**
An app that interprets ECGs is close to what regulators treat as a medical device, and Google Play has specific health-app declarations. This is not a reason to stop, but it needs deliberate positioning (clinician-only decision support, clear disclaimer, no patient-facing claims) and a check of DRAP guidance and Play Console health-app policy before publishing.

**3.7 Scope creep to resist.**
Out of scope for V1 and not to be absorbed quietly: saving history, accounts, PDF reports, Urdu UI, patient-facing mode, FFWTH/HMIS integration, ECG teaching mode, multi-ECG comparison, direct machine connectivity. Each is a possible later version.

## 4. Product scope

### V1 includes
- Capture or pick an image of a printed 12-lead (or rhythm strip) ECG
- Basic on-device quality checks and crop
- AI-assisted interpretation returned in a fixed structure
- Alert level (5 tiers) with plain reasons
- Optional clinical-context form that can escalate the alert
- Mandatory first-run disclaimer; persistent "Decision support only" label on results
- English UI only **[PROPOSED]**

### V1 excludes
Everything in 3.7, plus any storage of ECGs or results.

## 5. Architecture overview [PROPOSED]

```
Flutter app (Android)
   │  1. capture / pick → crop → compress (~1600px JPEG, strip EXIF)
   │  2. HTTPS call with Firebase App Check token
   ▼
Firebase Cloud Function: interpretEcg   (stateless, no image logging)
   │  3. validate request, rate-limit
   │  4. send image + instructions to vision model (provider-agnostic wrapper)
   │  5. receive structured JSON, validate against schema
   │  6. run deterministic alert rules (Section 7)
   ▼
JSON result → app renders result screen
   │
   └─ Optional: clinical context → Cloud Function: reassessWithContext
         (no image resent; sends the stored-in-memory-on-device findings JSON + context)
         → rules engine can only escalate → updated alert
```

Key points:
- The AI provider key lives **only** in the Cloud Function, never in the app.
- The alert logic is **deterministic code**, not the model's opinion. The model reads and describes; the rules engine decides the tier. This is auditable and testable by Homi.
- Re-assessment with context does **not** resend the image. The app holds the findings JSON in memory for the session and discards it when the user leaves the result screen.
- The provider is wrapped behind one interface so it can be swapped. Claude (vision) is a candidate; Phase 0 should compare at least two options if budget allows.

## 6. Firebase usage

| Service | Use | Notes |
|---|---|---|
| Cloud Functions (2nd gen) | `interpretEcg`, `reassessWithContext` | TypeScript or Python. Image never written to disk or logs. Request body logging disabled. |
| App Check (Play Integrity) | Block non-genuine apps | Required because there is no login. |
| Authentication | **Anonymous sign-in only** | Invisible to the doctor. Gives a stable ID for rate limiting. Not a login. |
| Firestore | Tiny usage counter: `usage/{anonUid}_{yyyymmdd}` with a count | Contains **no ECG data, no results, no patient data**. Optional; see D1. |
| Remote Config | Kill switch, minimum app version, rate-limit values, disclaimer version | Lets us disable the feature remotely if a safety issue appears. |
| Crashlytics | Crash reports | Analytics **off**, consistent with other LiveHealthy apps. No ECG content in any report. |
| Cloud Storage | **Not used** | Deliberately absent: nothing is stored. |
| Hosting | Optional later, for a privacy-policy page | Can also live on homilabs.org. |

A **separate Firebase project** for this app, matching the pattern used in the LiveHealthy apps **[PROPOSED]**.

## 7. Alert logic

### 7.1 Alert tiers

| Tier | Meaning | Colour/UI |
|---|---|---|
| **CRITICAL** | Pattern consistent with immediate life threat | Red, full-width banner, "Act now" wording |
| **URGENT** | Significant abnormality needing prompt review | Orange |
| **ABNORMAL** | Abnormal, not time-critical on this image alone | Amber |
| **NO CRITICAL PATTERN SEEN** | Nothing alarming detected; **not** a statement of normality | Neutral, limitations always visible |
| **UNREADABLE / LOW QUALITY** | Image cannot be interpreted reliably | Grey, with retake guidance |

### 7.2 Patterns that map to CRITICAL (starting list for Homi to edit)
Homi owns this list. Proposed starting set: ST-elevation patterns meeting STEMI criteria, ventricular tachycardia/fibrillation, asystole or pulseless-looking baseline, complete (third-degree) heart block, severe bradycardia, very fast supraventricular or atrial rhythms with wide complexes or pre-excitation, markedly prolonged QT, pattern suggestive of severe hyperkalaemia, Brugada type 1 pattern.
URGENT and ABNORMAL lists to be drafted together in Phase 0 once Homi has seen real model output.

### 7.3 Clinical-context escalation (optional step)
Fields **[PROPOSED]**, kept short on purpose:
- Age, sex
- Presenting complaint (quick-pick chips: chest pain, breathlessness, syncope/near-syncope, palpitations, dizziness, other, plus free text)
- BP (systolic/diastolic), heart rate, SpO₂
- Known conditions (quick-pick: hypertension, diabetes, known heart disease, CKD)

Rules:
1. Final tier = **max(ECG-only tier, context-escalated tier)**. Context can **raise** the tier, never lower it.
2. Example escalations: ABNORMAL ECG + chest pain + hypotension → CRITICAL; any ST/T abnormality + ongoing chest pain → at least URGENT; syncope + conduction abnormality → at least URGENT.
3. Every escalation shows the reason in plain words ("Escalated because: chest pain with ST changes").
4. BP and vitals thresholds should **match those locked in the LiveHealthy Vitals design doc** where they overlap, for consistency across the suite.
5. The rules table lives in one reviewable file (`alert_rules`), so Homi can read and edit it without touching the rest of the code.

## 8. The reading engine and validation

### 8.1 Model output contract (JSON)
The model must return only this structure; the function rejects anything else and retries once.

```json
{
  "image_quality": { "readable": true, "issues": ["glare", "skew"], "confidence": 0.0 },
  "layout": "12-lead standard | rhythm strip | other",
  "rate_bpm": { "value": 0, "confidence": 0.0 },
  "rhythm": { "label": "", "regular": true, "confidence": 0.0 },
  "intervals": { "pr_ms": null, "qrs_ms": null, "qt_ms": null, "qtc_ms": null },
  "axis": { "label": "", "confidence": 0.0 },
  "findings": [
    { "name": "", "leads": ["V2","V3"], "category": "st_elevation | st_depression | t_wave | conduction | rhythm | other", "confidence": 0.0 }
  ],
  "model_notes": "short free text, shown only as supporting detail"
}
```

Rules for the instructions given to the model:
- Report only what is visible; say "cannot assess" instead of guessing.
- Provide the calibration it assumes (paper speed, mV/mm) if visible on the print, or state that it is assumed.
- Never output a diagnosis sentence as the headline; the tier comes from the rules engine.

### 8.2 Validation set (this is where the reference portals are actually used)
- **PTB-XL** (open access on PhysioNet): large, cardiologist-annotated 12-lead ECGs. These are digital signals, so **render them as paper-style images** (grid, standard layout), then add realistic degradation (skew, blur, uneven lighting, phone-photo noise) to imitate real scans.
- Optionally the MIT-BIH Arrhythmia Database for rhythm strips.
- **Homi's own de-identified real printed ECGs**, photographed with a normal phone, the closest thing to real use. Confirm hospital policy and patient-privacy requirements before using any real patient ECG, even de-identified.
- Test set must include **hard negatives** (normal ECGs, artefact, near-misses) so we measure false alarms as well as misses.

### 8.3 Acceptance criteria
- Measure **sensitivity for each CRITICAL pattern first**, then false-alert rate, then readability handling.
- Targets are set by **Homi after seeing Phase 0 results**, not guessed in advance. If the critical-pattern sensitivity is not good enough, the project does not proceed to a public release; it can still ship as a limited tool with explicit limitations, or be paused.

## 9. Frontend design (Flutter, Android) [PROPOSED]

Stack is consistent with HomiLabs: Flutter/Dart. Keep the UI plain and fast; doctors are busy.

### Screens
1. **First-run disclaimer** (must accept; versioned via Remote Config): clinician-only, decision support, not a diagnosis, do not upload identifiable patient details.
2. **Home**: two big buttons, *Scan ECG* and *Choose from gallery*. Small link to About/Disclaimer.
3. **Capture**: camera with a guide frame, a hint to place the ECG flat with even light, glare/blur warning.
4. **Crop and confirm**: crop to the trace area (removes the printed patient header), rotate, preview. Image compressed and EXIF stripped here.
5. **Analyzing**: progress state with timeout and retry; handles weak connectivity gracefully.
6. **Result**: alert banner on top, then rate, rhythm, intervals, axis, listed findings with lead names and confidence, a visible "image quality" line and the standing label "Decision support only". Buttons: *Add clinical context (optional)* and *New ECG*.
7. **Clinical context** (optional): the short form from 7.3, then returns to the Result screen with the updated tier and escalation reasons.
8. **About / Disclaimer / Privacy**: states plainly that nothing is stored.

### Behaviour notes
- Findings JSON lives **in memory only**; leaving the result screen discards it. No local database, no gallery copy of the cropped image.
- Needs internet. If offline, say so clearly instead of failing silently.
- No screenshots restriction is required, but the result screen should not auto-save anything.
- Language: English only for V1 **[PROPOSED]**. (Other HomiLabs apps are bilingual; this one is a doctor tool, so I suggest English first. Decision D3.)

### Suggested structure
```
ecg_reader/
  docs/design-v1.md
  app/ (Flutter)
    lib/
      main.dart
      screens/        (disclaimer, home, capture, crop, analyzing, result, context)
      widgets/        (alert_banner, finding_tile, ...)
      services/       (ecg_api.dart, image_prep.dart, app_check.dart)
      models/         (ecg_result.dart, clinical_context.dart, alert_tier.dart)
  functions/ (Cloud Functions)
    src/
      interpretEcg.ts
      reassessWithContext.ts
      provider/       (visionProvider.ts, one adapter per model vendor)
      rules/          (alertRules.ts  ← Homi-readable)
      schema/         (ecgResult.schema.json)
  validation/
    render_ptbxl_to_images.py
    run_eval.py
    results/          (reports only; no patient data committed)
```

## 10. Build plan (incremental: build one piece, verify, then move on)

| Phase | What | Verification gate (Homi) |
|---|---|---|
| **0** | Reading-engine test: script that sends validation ECG images to the model with the Section 8.1 contract, and produces a table of results | Homi reviews real outputs against his own reading and decides go / no-go, and finalises the CRITICAL list |
| **1** | Cloud Function `interpretEcg` with schema validation, App Check, rate limit, no-logging checks | Test calls from a script; confirm nothing is logged or stored |
| **2** | Alert rules engine (`alertRules`) with unit tests | Homi reads the rules table and approves; tests pass |
| **3** | Flutter skeleton: disclaimer, home, capture, crop, image prep | Runs on a real phone; images compressed and EXIF stripped |
| **4** | Wire app to function; Result screen | End-to-end with test ECGs; tiers display correctly |
| **5** | Optional clinical-context flow (`reassessWithContext` + form) | Escalation-only rule verified with test cases |
| **6** | Hardening: offline, timeouts, kill switch, spending cap, privacy page | Failure-mode checklist passed |
| **7** | Closed testing with a few doctors; Play Console health declarations; DRAP/policy check | Feedback reviewed; release decision |

Do not start a phase until the previous gate is passed.

## 11. Working agreements for Claude Code

- **Pause and ask** if anything in this document is unclear or conflicts with something else. Do not proceed on an assumption.
- **One piece at a time**: build, verify, then move on. No multi-feature changes in one step.
- **Complete file replacements** rather than patches, unless a file's convention says otherwise.
- **Flag scope creep** directly rather than absorbing it. Anything in Section 3.7 is out until Homi adds it.
- Nothing counts as decided until Homi confirms it in writing. Treat all **[PROPOSED]** items as open until then.
- **Never** add storage of ECG images or results, analytics, or any logging of request bodies.
- **Session close:** git commit and push, local snapshot, and Google Drive sync.
- Create the project folder and git repo before any code is written.

## 12. Open decisions for Homi

| ID | Question | My recommendation |
|---|---|---|
| D1 | Allow anonymous sign-in plus a tiny usage counter (no ECG data) to rate-limit guest users? Without it, abuse protection is weaker. | Yes. It does not break "no saving of ECGs". |
| D2 | Which AI provider(s) to test in Phase 0? | Test at least two vision models on the same set, keep the provider behind one interface. |
| D3 | English only for V1, or bilingual? | English only first. |
| D4 | Final list of CRITICAL / URGENT / ABNORMAL patterns | Homi to edit the 7.2 starting list after Phase 0. |
| D5 | Which context fields to include in the optional step | Keep the short list in 7.3. |
| D6 | Real de-identified ECGs from your hospital for validation: permitted under your hospital's rules? | Check policy first; PTB-XL alone is enough to start. |
| D7 | App name and where it sits (standalone, or part of a clinician series separate from LiveHealthy, which is patient-facing) | Standalone, clinician-oriented, since LiveHealthy targets the public. |
| D8 | Release posture: public Play Store, or limited release to verified doctors first | Limited/closed testing first. |
| D9 | Phase 0 go/no-go thresholds | Set after seeing real results. |

## 13. Sources for reference data
- PTB-XL, a large publicly available electrocardiography dataset (PhysioNet), open access
- MIT-BIH Arrhythmia Database (PhysioNet)
- Check each dataset's licence terms before use or redistribution.
