# Release checklist — ECG Reader

Work through these **in order**. The app is not releasable until every box in sections A–C is ticked.

## A. Clinical gates (Homi)
- [ ] Phase 0 run on PTB-XL (`scripts/phase0.sh`) and review page checked against your own reading
- [ ] CRITICAL sensitivity acceptable for each critical pattern (D9 thresholds set)
- [ ] False-alert rate on normal ECGs acceptable
- [ ] `functions/src/rules/alertRules.ts` reviewed and approved (D4); change `RULES_VERSION` from `-proposed`
- [ ] Gap covered: VT/VF, asystole, hyperkalaemia, Brugada and torsades are **not in PTB-XL**. Add test images from another source (e.g. MIT-BIH VT strips, textbook-style examples) before signing off the CRITICAL list
- [ ] Optional: real de-identified ECG photos after the hospital policy check (D6)

## B. Firebase / backend (one time)
- [ ] Free a Google Cloud project slot (delete an unused project) or request a quota increase, then create the project (e.g. `ecg-reader-homilabs`)
- [ ] Upgrade it to **Blaze**, then set a **budget alert**
- [ ] `firebase use --add` → put the project id in `.firebaserc`
- [ ] Anthropic key: set a **monthly spend limit** in the Anthropic console, then `firebase functions:secrets:set ANTHROPIC_API_KEY`
- [ ] Check the Anthropic API data-retention setting for the organisation and use the strictest option (design 3.5)
- [ ] Enable **Anonymous** sign-in (Authentication → Sign-in method)
- [ ] Create Firestore (Native mode, region `asia-south1`) and add a **TTL policy** on collection `usage`, field `expireAt`
- [ ] App Check: register the Android app with **Play Integrity**; add the SHA-256 of the app signing key (Play Console) and of the upload key:
      `eb:29:50:a9:53:94:e8:76:af:fb:ea:84:43:2d:ea:6a:2e:00:4e:8c:f2:90:95:0f:e6:b6:25:ac:af:33:cd:12`
- [ ] Register a **debug token** for each test phone (App Check → Manage debug tokens)
- [ ] Remote Config (client): `ecg_enabled` (bool), `ecg_disabled_message`, `min_build` (int), `disclaimer_version` (int)
- [ ] Remote Config (server template): `ecg_enabled`, `ecg_daily_limit`, `ecg_disabled_message`
- [ ] `npm --prefix functions run deploy`
- [ ] Confirm in Cloud Logging that only metadata is logged (no image, no reading, no ids)

## C. App
- [ ] `cd app && flutterfire configure --project=<id> --platforms=android` (replaces the placeholder `lib/firebase_options.dart`, adds `google-services.json`)
- [ ] Add Crashlytics (analytics off) now that the real project exists
- [ ] Host the privacy policy (`docs/privacy-policy.md`) and pass its URL with `--dart-define=PRIVACY_URL=...` (default `https://homilabs.org/ecg-reader/privacy`)
- [ ] Final app name (D7) and icon
- [ ] Bump `version:` in `app/pubspec.yaml`
- [ ] `flutter build appbundle --release`
- [ ] Install from the internal test track on the Mi 9 Lite and Galaxy A12; run the manual test list below

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
