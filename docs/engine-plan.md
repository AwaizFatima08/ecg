# On-device reading engine — plan and first results

Decision D2 (12 Oct 2026): ECG Reader uses its **own engine**, no paid AI, so the app stays free and ad-free
at any scale. This page records the design, the first measurements and the next steps.

## Pipeline
1. **Photo → signal** — [Open-ECG-Digitizer](https://github.com/Ahus-AIM/Open-ECG-Digitizer)
   (Ahus hospital, Norway; npj Digital Medicine 2026). U-Net segmentation + perspective correction +
   grid detection + layout matching. Licence **CC BY-SA 4.0** (see "Licence" below).
2. **Signal → findings** — our own small 1-D CNN (`validation/train_classifier.py`, 1.76 M parameters,
   about 7 MB), trained on PTB-XL in the printed 3×4 format (each lead visible for 2.5 s, lead II for 10 s).
   Heart rate comes from R-peak detection on the lead II strip.
3. **Findings → alert tier** — the existing, unchanged rules (`functions/src/rules/alertRules.ts`).

## Results so far (Phase 0 set: 126 PTB-XL records, each as a clean scan and as a phone-photo imitation)

**Digitizer** (`validation/results/digitizer_2026-10-12.md`): every image digitized (252/252).
Median correlation with the true signal: **0.96 on scans, 0.93 on photos**.

**Classifier on clean signals**, PTB-XL test fold (`validation/results/classifier_clean.md`): macro-AUC 0.96.
ST-elevation injury 0.97, AF 0.98, LBBB/RBBB ≈1.0, PVCs 0.99, LVH 0.96. Weak: nonspecific IVCD 0.74.

**End to end, through the alert rules** (`validation/results/phase0_engine-v*.md`):

| | v0 (clean, 90 % cut-offs) | v1 (clean, re-tuned) | **v2 (fine-tuned on digitized)** |
|---|---|---|---|
| Critical → CRITICAL, scan / photo | 61 % / 64 % | 83 % / 83 % | 78 % / 75 % |
| Critical → at least URGENT, scan / photo | 89 % / 94 % | 92 % / 94 % | **92 % / 94 %** |
| ST-elevation injury → CRITICAL, scan / photo | 72 % | 89 % | 83 % / 78 % |
| Complete heart block → CRITICAL, scan / photo | 29–36 % | 64 % | 71 % / 64 % |
| Normal → false URGENT/CRITICAL, scan / photo | 7 % / 13 % | 17 % / 50 % | **7 % / 3 %** |
| Normal → "no critical pattern", scan / photo | 13 % / 0 % | 0 % | **57 % / 47 %** |

**v2** (12 Oct 2026): 4,600 PTB-XL records were rendered (70 % photo look) and digitized on homidev's RTX 5060 Ti in
2 h 45 min, with 0 failures. The classifier was then fine-tuned on digitized + clean signals, and the cut-offs were set on
digitized validation data (`validation/results/finetune_digitized.md`). The domain-shift problem is largely solved:
false alarms on normal ECGs fell from 50 % to 3 % on photos, while critical → at least URGENT stayed at 92–94 %.

Critical cases still below URGENT in v2 (for Homi's review):
- `ptbxl08611`: early inferior MI (ST elevation III/aVF, reciprocal depression). **A real miss**; the engine reported pre-excitation instead.
- `ptbxl21243`: AF + PVCs + old MI + conduction disease + injury labels. The engine returned **no findings**, a serious failure mode.
- `ptbxl18840`: labelled injury (50 % likelihood) but the PTB-XL report only says anterior T abnormality. The engine found T inversion. Debatable.

Not yet measured by the engine: PR/QRS/QT intervals and axis (null in v1; the classifier covers bundle-branch
patterns and long QT indirectly). Not covered by PTB-XL at all: VT/VF, asystole, hyperkalaemia, Brugada.

## Next steps (in order)
1. ~~Digitized dataset + fine-tune~~: done (v2). Homi approved homidev's GPU for this job (12 Oct 2026);
   the job runs in `~/ecg-engine-job/` only (`validation/jobs/homidev_digitize/`).
2. Safety net for "abnormal-looking but nothing found": if the classifier's "normal" score is low but no finding
   passes its cut-off, report at least ABNORMAL with "review the ECG yourself" (fixes the `ptbxl21243` pattern).
3. AV-dissociation / heart-block detector; interval measurements (PR, QRS, QTc) from the lead II strip.
4. Phone port (below), then closed testing with doctors.

## Running it on the phone
- The U-Net is 90 MB (float32). Converted to TFLite/ONNX with int8 quantisation it would be about 25 MB; inference at
  about 2000 px may take several seconds on a mid-range phone. The classifier (7 MB, about 2 MB int8) is quick.
- About 1,500 lines of PyTorch post-processing (perspective, grid size, cropping, layout matching, trace
  extraction) must be re-implemented in Dart/Kotlin. This is the largest piece of work.
- Interim option, if needed: run the same Python engine on Cloud Run (CPU). Cost is roughly $0.001–0.002 per
  reading, and the free tier covers a few thousand readings a month, but the image would leave the phone again.

## Licence
Open-ECG-Digitizer is CC BY-SA 4.0. Using it in a free app is allowed, with attribution: credit the authors and the paper
in the app's About screen and on the website. Our changes to their code or weights must be shared under the same
licence; publishing them in a public repo satisfies this. Our own classifier and app code are separate works.
PTB-XL is CC BY 4.0: attribution is required in About and on the website.
