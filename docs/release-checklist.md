# Release checklist — ECG Reader

Work through these **in order**. The app is not releasable until every box in sections A–C is ticked.

## A. Clinical gates (Homi)
**Status 22 Oct 2026: closed testing (D8) approved by Homi with the two cardiologist reviews still pending; public release stays blocked on them.**
- [x] Engine interpretations self-reviewed by Homi (dossiers + adjudication, 21 Oct 2026; `validation/adjudication.csv`)
- [ ] Interpretations reviewed independently by **cardiologist 1** and **cardiologist 2**; disagreements resolved and logged
- [ ] No release before both reviews are complete (Homi, 13 Oct 2026)
- [x] Phase 0 run on PTB-XL and reviewed (v13b, 22 Oct 2026: critical → ≥ URGENT 64/66, 1 normal false alarm / 252)
- [ ] CRITICAL sensitivity acceptable for each critical pattern (D9 thresholds set)
- [x] False-alert rate on normal ECGs: Phase 0 1/252 renders ≥ URGENT; Multan 8/142 unique normal prints (3 CRITICAL) — accepted for closed testing
- [x] Rules approved by Homi (13 and 21 Oct 2026: rate rules M6/M7 kept, old infarct ≤ URGENT, AF+slow block, QRS 0.30, policy v5)
- [x] VT/VF/asystole: lethal-rhythm model on vfdb/cudb with the plausibility gate (v7k). Hyperkalaemia, Brugada, torsades: **not detected by the engine** — stated in the About screen limits
- [ ] Optional: real de-identified ECG photos after the hospital policy check (D6)

## B. Firebase / backend (one time)
- [x] Firebase project `ecg-reader-homilabs` created (12 Oct 2026; Analytics and Gemini off)
- [x] Blaze plan + budget (done by Homi, 12 Oct 2026)
- [x] `.firebaserc` default = `ecg-reader-homilabs`
- [x] ~~Anthropic key~~ — not needed: on-device engine (D2 revised)
- [x] Anonymous sign-in enabled, auto clean-up after 30 days
- [x] Firestore created (asia-south1, production rules deployed)
- [ ] Add a **TTL policy** on collection `usage`, field `expireAt`
- [ ] App Check: register the Android app with **Play Integrity**; add the SHA-256 of the app signing key (Play Console) and of the upload key:
      `eb:29:50:a9:53:94:e8:76:af:fb:ea:84:43:2d:ea:6a:2e:00:4e:8c:f2:90:95:0f:e6:b6:25:ac:af:33:cd:12`
- [ ] Register a **debug token** for each test phone (App Check → Manage debug tokens)
- [ ] Remote Config (client): `ecg_enabled` (bool), `ecg_disabled_message`, `min_build` (int), `disclaimer_version` (int)
- [ ] Remote Config (server template): `ecg_enabled`, `ecg_daily_limit`, `ecg_disabled_message`
- [ ] `npm --prefix functions run deploy`
- [ ] Confirm in Cloud Logging that only metadata is logged (no image, no reading, no ids)

## C. App
- [x] `flutterfire configure` done (Android app registered)
- [ ] Add Crashlytics (analytics off) now that the real project exists
- [x] Privacy policy hosted at https://medicalapps.homilabs.org/ecg-reader/privacy/ (app default; source in /mnt/storage/projects/medicalapps_site)
- [ ] Final app name (D7) and icon
- [x] Bump `version:` in `app/pubspec.yaml` (1.0.0+2, 22 Oct 2026)
- [x] `flutter build appbundle --release` — 22 Oct 2026, v1.0.0+2 (engine v13b): `dist/ecg-reader-1.0.0+2.aab` (134.5 MB) and `dist/ecg-reader-1.0.0+2-arm64-release.apk` (94 MB), signed with the HomiLabs key (SHA-256 eb29…cd12)
- [~] Release APK installed fresh on the Oppo Reno 14F (22 Oct): disclaimer with both boxes, gallery → crop → quality warning on a blurred image → reading CRITICAL in 9 s, no image files left in app storage; A12 / Mi 9 Lite pending

## D. Play Console
- [ ] Health apps declaration: clinician decision support; not a medical device claim; no patient-facing use
- [ ] Data safety: images sent for processing, not stored; no data shared for ads; anonymous ID for rate limiting
- [ ] Target audience: adults (professional use)
- [ ] DRAP guidance check (design 3.6)
- [ ] Closed testing with a few doctors first (D8)

## Manual test list (each release)
1. First run shows the disclaimer; both boxes required.
2. Gallery → crop → confirm shows the size and the patient-details reminder.
3. Camera opens with the guide frame; torch toggles; permission-denied message is clear.
4. Blurred / dark / glare photo shows warnings on the confirm screen.
5. Reading returns a tier banner, reasons, measurements, findings, quality line and the "decision support only" label.
6. Clinical context can only raise the tier and shows "Raised from … by the clinical details".
7. Back from the result asks before discarding; **New ECG** returns home.
8. Airplane mode: a clear "no internet" message, and Try again works after reconnecting.
9. Remote Config `ecg_enabled=false` disables both buttons with the message.
10. No image files remain in the app's storage after a reading (`adb shell run-as com.homilabs.ecg_reader find . -name '*.jpg'`).
