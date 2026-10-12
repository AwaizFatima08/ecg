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

**End to end, through the alert rules** (`validation/results/phase0_engine-v1.md`):

| | engine-v0 (90 %-sensitivity cut-offs) | engine-v1 (re-tuned cut-offs) |
|---|---|---|
| Critical → CRITICAL, scan / photo | 61 % / 64 % | **83 % / 83 %** |
| Critical → at least URGENT, scan / photo | 89 % / 94 % | 92 % / 94 % |
| ST-elevation injury → CRITICAL | 72 % | 89 % |
| Complete heart block → CRITICAL | 29–36 % | 64 % |
| Normal → false URGENT/CRITICAL, scan / photo | 7 % / 13 % | 17 % / **50 %** |
| Normal → "no critical pattern" | 0–13 % | 0 % |

**Reading:** the approach works; ST-elevation and acute-MI detection is already strong. Two problems remain:
1. **Domain shift.** The cut-offs and the classifier were tuned on clean signals; digitized photos shift the
   scores, which makes normal ECGs look abnormal. Fix: build a digitized training/calibration set (render + digitize
   a few thousand PTB-XL records), fine-tune the classifier on it, and set the cut-offs on digitized data.
2. **Heart block.** PTB-XL has about 30 second- and third-degree AV blocks. Fix: a dedicated rule-based
   AV-dissociation detector (P waves vs QRS timing on the 10 s lead II strip), plus more data later.

Not yet measured by the engine: PR/QRS/QT intervals and axis (null in v1; the classifier covers bundle-branch
patterns and long QT indirectly). Not covered by PTB-XL at all: VT/VF, asystole, hyperkalaemia, Brugada.

## Next steps (in order)
1. **Digitized dataset**: render PTB-XL folds 1–9 as photos (as in Phase 0) and digitize them. At about 20 s per image
   on homi-nas's CPU this takes days; on a CUDA GPU it is minutes to hours. Options: CUDA PyTorch for the GTX 1050 Ti
   on homi-nas, or homidev's RTX 5060 Ti (outside homidev's approved asset use, so Homi's call).
2. Fine-tune the classifier on digitized signals; set cut-offs on the digitized validation fold; re-run Phase 0.
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
