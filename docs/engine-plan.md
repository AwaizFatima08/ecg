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

**v7 (13 Oct 2026, 05:10) — round 2: classifier v2 trained on PTB-XL + ecg-arrhythmia (53 k training ECGs; 176 second/
third-degree AV blocks, 138 WPW, 449 long QT, 965 ST-elevation injury vs a handful before; held-out macro-AUC 0.967),
fine-tuned on student-digitized ECGs (2 seeds; ensemble digitized-val macro-AUC 0.947), student-B digitizer:**

| Phase 0, scan / photo | v6 | **v7** |
|---|---|---|
| Critical → at least URGENT | 94 % / 97 % | **97 % / 94 %** (misses: `ptbxl21243`; photo also `ptbxl07835`) |
| Critical → CRITICAL | 64 % / 61 % | **81 % / 72 %** |
| Complete heart block → CRITICAL | 43 % / 43 % | **71 % / 64 %** |
| Normal → false URGENT/CRITICAL | 10 % / 20 % | 10 % / 20 % |
| Normal → "no critical pattern" | 57 % / 47 % | 67 % / 43 % |

| Multan real prints, **student-digitized (the phone path)** | v6 | v7 |
|---|---|---|
| acute-MI prints ≥ URGENT | 63 % (87 CRITICAL) | **90 % (191 CRITICAL)** |
| history-of-MI ≥ ABNORMAL | 100 % | 100 % |
| abnormal-heartbeat ≥ ABNORMAL | 94 % | 97 % |
| normal → false URGENT/CRITICAL | **11 %** | 19 % |
| normal → "no critical pattern" | **33 %** | 8 % |

v7 is the more sensitive operating point (recommended for the critical-first goal); v6 the more specific.
**v7b** = v7 with the ST-depression cut-off set by Youden's J instead of the ≥ 90 %-sensitivity rule (threshold policy v3
candidate, `models/v2/ensemble2_meta_v3.json`): every critical number is unchanged, false alarms on normals fall to 7 %
(Phase 0 scans) and 15 % (Multan), because 48 of v7's 54 Multan false alarms were ST depression alone. This choice was
confirmed on the test sets, so it needs re-confirmation by the cardiologists' review. **v7c** (3 seeds + policy v3, `models/v2/ensemble3_meta_v3.json`, digitized-val macro-AUC 0.947) — **the build now in the app**:

| | Phase 0 scan / photo | Multan real prints (student-digitized) |
|---|---|---|
| Critical → CRITICAL | **83 % / 78 %** | acute MI ≥ URGENT **90 %** (191/239 CRITICAL) |
| Critical → at least URGENT | 97 % / 94 % | history of MI ≥ ABNORMAL 100 %, abnormal heartbeat 97 % |
| Complete heart block → CRITICAL | **79 % / 71 %** | — |
| Normal → false URGENT/CRITICAL | **7 % / 10 %** | **6 %** (18/284) |
| Normal → "no critical pattern" | 60 % / 33 % | 8 % (85 % land in ABNORMAL — the remaining weakness) |

Still missed below URGENT on Phase 0: `ptbxl21243` (both variants) and `ptbxl07835` (photo). Both ensembles
are kept (`validation/models/student`, `validation/models/v2`). Which to ship is Homi's and the cardiologists' call.

**v7d (13 Oct 2026, morning) — measurement fixes found while checking the phone against Python on `ptbxl00959`
(complete heart block, atrial 98/min, escape 40/min):**
1. *R-peak gate.* The beat detector counted tall P waves as beats: six complete heart blocks in Phase 0 were read at
   87–171/min and now read 37–40/min. `r_peaks` keeps a second pass: only detections whose 12–30 Hz slope energy is
   ≥ 0.4 × the median of the five strongest beats count, and the first pass is trusted if that leaves < 3 beats or a
   median RR > 2 s (a few large PVCs). Checked with the new `validation/rate_check.py` (reference: wfdb XQRS on lead II
   upsampled to 500 Hz; raw XQRS at 100 Hz double-counts T waves): rate within 10 % of the reference on clean 3AVB
   69 → 100 %, SBRAD 97 → 100 %, student-digitized Phase 0 95 → 99 %, selection set 95 → 98 %, PVC 95 → 94 % (one record),
   NORM 100 → 100 %. `measure_check.py`: AV block suspected on complete blocks 31 → 56 %, normals unchanged at 2 %.
2. *Python-only bug.* In `av_relation` a spurious beat near sample 0 made the QRS-blanking slice end negative, which
   zeroed the whole lead (`resid[0:-1] = 0`) and silently disabled the AV-block check. The Dart port was already correct;
   Python now matches it. The Dart parity test includes `ptbxl00959_photo` (21 digitized ECGs).
3. *[PROPOSED] heart block despite an AF call.* On the phone the classifier also called AF (cut-off 0.08) on this record,
   which suppressed the measurement-based block → URGENT. Now a slow (< 55/min) ventricular rhythm with **regular** P waves
   outnumbering the QRS is reported as high-grade block (CRITICAL) even when AF is called; fibrillatory waves are not
   regular, so true AF is unaffected. Phase 0: `ptbxl10640_photo` (true URGENT) moves to CRITICAL (Mobitz-2 flag, 65/min);
   everything else, incl. all normals, unchanged. `ptbxl15368` (3AVB, escape 58/min) stays URGENT — the 55/min cut-off
   is **Homi's call**.
4. *Whole image on the phone.* With tiles of 768 px the U-Net output differed from Python's whole-image run (AV-block
   probability 0.25 vs 0.44 on this record). The phone now runs the U-Net on the whole 1600-px image (`segTile = 2048`):
   A12 reads in **35 s (was 51 s)** with no memory pressure. Digitizer accuracy on Phase 0 is the same either way
   (whole: scan median r 0.97 / 78 % ≥ 0.9, photo 0.88 / 41 %; tile 768: 0.97 / 79 %, 0.88 / 42 %), so the tile boundary
   only matters for borderline records; whole image is kept because it is faster and bit-for-bit the Python path.

Phase 0 v7d: identical to v7c except the row above (photo URGENT→CRITICAL 13 → 14). Multan v7d: acute MI ≥ URGENT
90 → **87 %** (191/239 CRITICAL unchanged), normal false alarms 6 → **7 %** (20/284), history of MI / abnormal heartbeat
unchanged. Every Multan change traces to three prints that the dataset repeats (`mi_2` ×8, `normal_56` ×2, `oldmi_5/91`,
`oldmi_7/93`): `mi_2` was read at 197/min because the old detector counted T waves — the URGENT it earned was a false
tachycardia on a 111/min sinus tachycardia, and its MI is a genuine classifier miss now visible as ABNORMAL;
`normal_56` is a badly digitized trace (flat start, one huge spike) on which the AV-block flag now fires. Requiring
regular P waves for that flag was tried and rejected: it removes the false alarms but drops complete-heart-block
detection from 56 % to 6 % (`measure_check.py`), because the P-wave stream after QRS-T subtraction is too noisy.

**Digitizer time-axis fixes (13 Oct 2026, afternoon; v7e/v7g, Python + Dart, parity on 5 images):** chasing the two
Phase 0 misses showed that the *time axis* of digitized traces was often wrong, which the per-lead correlation score
(computed after alignment in the old eval) had hidden. New check `validation/lag_check.py` (best lag of lead II and of
the 3×4 leads against the clean signal): before, only 68 % of rhythm strips and 63 % of leads were within 40 ms;
12 % of strips were ≥ 300 ms off; unaligned median r 0.65. Causes and fixes:
1. *Rhythm-strip end* was found with a threshold scaled to the tallest complex, so a flat tail (or any strip with
   very tall complexes, e.g. `ptbxl21243`) was cut short and the whole 10 s axis shifted (0.35 s on 21243). Threshold is
   now absolute (`> max(0.5, 2 % of max)`). Alone (v7e): scan traces with r ≥ 0.9 78 → 94 %, photo 41 → 48 %.
2. *Rows aligned to the strip by rounding to whole 5 mm squares* put entire rows 0.2 s off on photos (`ptbxl00959`,
   `00201`, `07835`, `01946`…). The strip's major grid lines are now **tracked upward slab by slab** through the grid map
   (a few px of tilt/keystone per slab, never a whole square), and each row's pixel→mm ruler is fitted to the tracked
   lines, so every row shares the strip's origin. Line profiles use the central 40 % of a band (tilted lines smear
   less). Result (v7g): 99 % of strips and 98 % of leads within 40 ms; unaligned median r 0.92 (scan 0.96 / photo 0.90).
   Tried and rejected: a comb-walk line finder (+1 sample bias on scans) and taking the column extremum instead of the
   centroid for steep strokes (restores R/S amplitude but lowers r).
3. Phase 0 tiers with the **unchanged** classifier (fine-tuned on the old, shifted traces): scan identical to v7d except
   `ptbxl11500` (complete block) URGENT → CRITICAL; photo moves both ways (3 critical records drop to ABNORMAL:
   `04827`, `08611`, `08624`; `10108`, `11500`, `18840` rise to CRITICAL). The classifier must be re-fine-tuned on
   correctly digitized traces before judging — that is the next homidev job (re-digitize the 4,600-record fine-tune set,
   the selection set and Multan with the fixed digitizer, re-fine-tune the 3 seeds, re-tune thresholds, re-export).
   `ptbxl00959_photo` (complete heart block) now digitizes at median lead r 0.84 (was 0.16).

**v7h (13 Oct 2026, 15:00) — classifier re-fine-tuned on correctly digitized traces (`run_v7h.sh` on homidev,
25 min GPU):** the 4,600 fine-tune renders, the selection set and Multan were re-digitized with the v7g digitizer and
the 3 seeds of classifier v2 re-fine-tuned (digitized-val macro-AUC per seed 0.955/0.955/0.954, was 0.946/0.944/0.945;
the *base* model alone rises 0.890 → 0.921 just from the corrected traces). Ensemble + policy v3 cut-offs on the
digitized val fold (`models/v7h/ensemble3_meta_v3.json`, macro-AUC 0.956) — **the build now in the app**
(`export_classifier_onnx.py`).

| | Phase 0 scan / photo | Multan real prints |
|---|---|---|
| Critical → CRITICAL | **86 % / 83 %** (v7d 83 / 78) | acute MI ≥ URGENT **90 %** (207/239 CRITICAL, v7d 191) |
| Critical → at least URGENT | 97 % / 97 % | history of MI ≥ ABNORMAL 100 %, abnormal heartbeat 98 % |
| Normal → false URGENT/CRITICAL | 7 % / **13 %** (v7d 7 / 10) | **13 %** (36/284; v7d 7 %) |
| Normal → "no critical pattern" | 60 % / 37 % | 5 % |

`ptbxl21243_photo` (the long-standing miss) is now CRITICAL; `ptbxl15368_scan`, `11500`, `10108`, `18840` rise to CRITICAL;
`ptbxl04827_photo` and `08624_photo` drop from CRITICAL to URGENT. **Open — Homi's threshold decision:** the policy-v3
Youden cut-off for ST depression fell from 0.22 to **0.12** on the new validation fold and drives most of the new false
alarms (22 of the 28 URGENT normals on Multan are ST depression alone; 6 ABNORMAL-truth Phase 0 records moved to URGENT).
On the validation fold: 0.12 → sens 83 % / spec 81 %; 0.22 → 78 / 86; 0.30 → 73 / 89; a "≥ 90 % specificity" rule gives
0.32 (73 / 90). Any change is set on validation data only and re-checked on the test sets afterwards.

**v7i (13 Oct 2026, 16:00) = v7h + threshold policy v4** (Homi: "resolve as suggested"): ST depression at ≥ 90 %
specificity on the digitized validation fold → cut-off 0.32 (was 0.12). Everything else identical to v7h.

| | v7h (Youden 0.12) | **v7i (0.32)** |
|---|---|---|
| Phase 0 critical → CRITICAL, scan / photo | 86 / 83 % | 86 / 83 % |
| Phase 0 critical → ≥ URGENT | 97 / 97 % | **89 / 89 %** |
| Phase 0 normal → false URGENT/CRITICAL | 7 / 13 % | 7 / 10 % |
| Multan acute MI ≥ URGENT (CRITICAL) | 90 % (207) | **87 %** (207) |
| Multan normal false alarms | 13 % | **7 %** |

The price: records that the classifier does not recognise as infarction were kept at URGENT only by the ST-depression
net — `ptbxl08611` (inferior MI, both variants), `ptbxl08624` (anteroseptal MI + injury, both), `ptbxl18840_scan`,
`ptbxl04827_photo` (IMI + complete block) now land at ABNORMAL; on Multan 8 acute-MI prints (one duplicated print,
`mi_2` ×8) drop from URGENT to ABNORMAL. These are classifier misses of the STEMI pattern, now visible rather than masked;
the next engineering target is the infarction labels themselves (acute MI / ST elevation sensitivity), not the ST-depression
cut-off. A middle setting (0.22, the v7c value: val sens 78 % / spec 86 %) remains an option for Homi.

**21 Oct 2026 — adjudication round 1 (no cardiologist available; Homi adjudicates, see `docs/reviews/dossier_phase0_v7i.pdf`,
`dossier_multan_v7i.pdf`, `docs/decisions.md`).** Fixes that are wrong under any reading, validated on training/selection
data and re-checked on the test sets as **v7k** (same models as v7i):
1. *Lethal-rhythm gate* (`ecg_measure.lethal_plausible`, Dart `lethalPlausible`): the VT/VF/asystole model fired on 2
   Phase 0 photos (SVT at 158/min called "VF"; a 67/min strip called "asystole"), 4 selection traces and 24 Multan prints
   (regular narrow tachycardias at 176–214/min). A call now has to agree with the beat detector: asystole needs ≤ 4
   beats, a ≥ 2 s gap or a flat strip; VF needs a wide/unknown QRS and an irregular rhythm; VT a wide/unknown QRS and
   rate ≥ 90. Digitized false lethal calls 30 → 2 of 1,580 (both one selection record with bizarre wide complexes);
   held-out vfdb/cudb any-lethal sensitivity 0.998 → 0.76 (VF 0.95, VT 0.78, "asystole" windows 0.24 — those carry
   agonal activity a printed flat line would not). `lethal_gate_check.py` documents gates A–F.
2. *AV-block measurement guard*: a small PR sd (≤ 40 ms over ≥ 3 beats) means the extra "P" candidates are T waves of
   a conducted rhythm. Clean 3AVB sensitivity unchanged (56 %), digitized Phase 0 normals flagged 3 → 1 of 60
   (`avb_guard_check.py`; a T-zone exclusion was rejected: 3AVB 56 → 44 %).
3. *Old infarct is not an emergency* (Homi): `train_classifier.label_vector` no longer counts an injury statement on a
   ventricular aneurysm or a stadium II-III/III infarct as `st_elevation_injury` (319 → 290 positives), and
   `hard_negative_weight` up-weights the acute-infarction loss on known-old infarcts (×3) and ischaemia-without-infarct
   records (×2) — the patterns the classifier confused with acute injury. Fine-tune queued as `run_v7j.sh`
   (homidev, ~10 min GPU) — **blocked: homidev's NVIDIA driver/library mismatch (needs a reboot)**.

v7k vs v7i: Phase 0 identical for critical records; normals → URGENT 3 → 2 (photo) / 2 → 1 (scan); Multan unchanged
(false alarms 7 %), abnormal-heartbeat prints CRITICAL 39 → 32 (the false VF/VT calls). Rate rules M6/M7 kept by Homi.

Devices on `ptbxl00959_photo` with v7d (all CRITICAL, 41/min, "Possible high-grade / complete AV block"): Galaxy A12 35 s,
Tab S9 FE ~10 s, Oppo Reno 14F 11 s, Mi 9 Lite correct (not timed; MIUI blocks UI dumps). S23 Ultra not available.

**v6 (13 Oct 2026, 04:30) — the phone pipeline: student-B U-Net (2.3 M params, 8.6 MB; selection-set median r 0.968 scan /
0.897 photo vs teacher 0.977 / 0.906) + 3-seed ensemble of classifiers fine-tuned on student-digitized ECGs
(digitized-val macro-AUC 0.945) + threshold policy v2 + QRS 0.30:**

| scan / photo | v5 | **v6** |
|---|---|---|
| Critical → at least URGENT | 94 % / 92 % | **94 % / 97 %** (photo: 1 miss, `ptbxl21243`) |
| Critical → CRITICAL | 53 % / 67 % | 64 % / 61 % |
| Complete heart block → CRITICAL | 21 % / 50 % | 43 % / 43 % |
| Normal → false URGENT/CRITICAL | 20 % / 20 % | **10 % / 20 %** |
| Normal → "no critical pattern" | 63 % / 47 % | 57 % / 47 % |

Multan real prints with v6 (teacher digitizer; `results/multan_multan-v6.md`): normal false alarms **16 % → 8 %**, normals
reading "no critical pattern" 26 % → 34 %; acute-MI prints ≥ URGENT **80 % → 57 %** (CRITICAL 88, URGENT 48, ABNORMAL
95) — the ensemble is more conservative on real prints; which trade-off is right is for Homi and the cardiologists.
On-device time with student B: Galaxy A12 **50 s** (was 340 s).

**v5 (13 Oct 2026, phone pipeline = lite digitizer + classifier fine-tuned on lite-digitized ECGs, corrected cut-offs)**

| scan / photo | v4 (broken cut-offs) | **v5 (corrected)** |
|---|---|---|
| Critical → CRITICAL | 81 % / 83 % | 53 % / 67 % |
| Critical → at least URGENT | 94 % / 92 % | **94 % / 92 %** |
| Complete heart block → CRITICAL | 71 % / 79 % | 21 % / 50 % |
| ST-elevation injury → CRITICAL | 83 % / 83 % | 78 % / 83 % |
| Normal → false URGENT/CRITICAL | 20 % / 23 % | 20 % / 20 % |

**A calibration bug was found and fixed (13 Oct 2026):** labels with very few validation examples (WPW 7, flutter 7,
long QT 11, acute MI 1) got near-zero cut-offs from the "≥ 90 % sensitivity" rule, so e.g. WPW fired on almost every
ECG. Through the AF+WPW rule (M3) this produced spurious CRITICAL alerts — including most of v4's apparent heart-block
"catches". `validation/threshold_policy.py` (v2) fixes rare labels at 0.3 and floors all cut-offs at 0.05. The v5 numbers are
the honest ones. Remaining false alarms on normals are mostly `st_depression` (4/30 per variant) and `long_qt`.

**Real paper prints (Multan dataset, 928 EDAN SE-3 prints, teacher digitizer, corrected cut-offs;
`validation/results/multan_multan-teacher-v5.md`, review page `images_multan/review_multan-teacher-v5.html`):**

| dataset label | n | ≥ expected tier | CRITICAL | URGENT | ABNORMAL | no critical pattern |
|---|---|---|---|---|---|---|
| acute MI (≥ URGENT) | 239 | 80 % | 111 | 80 | 48 | 0 |
| history of MI (≥ ABNORMAL) | 172 | 100 % | 102 | 54 | 16 | 0 |
| abnormal heartbeat (≥ ABNORMAL) | 233 | 96 % | 45 | 109 | 69 | 10 |
| normal | 284 | 20 % | 4 | 42 | 182 | 56 |

Normal prints are over-called: 16 % URGENT/CRITICAL (mostly `st_depression`) and 64 % ABNORMAL (atrial ectopics,
T-wave changes, and **broad QRS from the measurement**: 28 % of normal prints measure ≥ 120 ms, vs 13 % of PTB-XL
photos and 1 % of clean PTB-XL signals — the digitized trace blurs QRS edges, and EDAN prints are low-passed at 25 Hz).
"History of MI" prints fire `stemi_pattern` in 62 % — Homi to judge on the review page whether these show real
persistent ST elevation. Fixes: **QRS detector calibrated** on 600 clean-vs-digitized pairs (`results/qrs_calibration_vs_clean.json`): the
velocity threshold moves from 0.15 to 0.30 (median bias 0 ms, 73 % sensitivity / 94 % specificity for QRS ≥ 120 ms
against the clean-signal measurement) — ABNORMAL over-calls on normals fall from 33 %→17 % (scans) and 47 %→33 %
(photos) on Phase 0, and Multan normals reading "no critical pattern" rise from 20 % to 26 %; critical detection unchanged
(94 % ≥ URGENT). Still planned: low-pass (20–40 Hz) augmentation in training to imitate printer filters, and the
round-2 classifier (66 k ECGs, strong "normal" class).

**Heart block is the weak point.** PTB-XL has 16 complete and 14 second-degree blocks, far too few to learn from.
The rule-based AV-block check reaches URGENT on most of them (9/14 scans); a slow-rate escalation to CRITICAL
(rate < 55: 25 % of complete blocks, 0.2 % of normals, 3.3 % of sinus bradycardias on clean PTB-XL) is implemented as
**[PROPOSED]** and makes no difference on the digitized Phase 0 set. Next: train on the PhysioNet/CinC Challenge 2021
12-lead data (≈ 88 k ECGs incl. hundreds of complete heart blocks, WPW and long QT) — see "Next steps".

**v3** (12 Oct 2026) adds rule-based measurements (`validation/ecg_measure.py`), an AV-block check and a safety net:

| v3, scan / photo | |
|---|---|
| Critical → CRITICAL | 78 % / 78 % |
| Critical → at least URGENT | 92 % / 94 % |
| Complete heart block → CRITICAL | 71 % / 71 % |
| Normal → false URGENT/CRITICAL | 10 % / 10 % |
| Normal → "no critical pattern" | 57 % / 43 % |

Measurements checked against PTB-XL labels on clean signals cut to the 3×4 print (`validation/measure_check.py`):
QRS ≥ 120 ms in 71 % of bundle branch blocks (1 % of normal ECGs); PR > 200 ms in 69 % of first-degree blocks (6 % of normals);
left axis in 91 % of LAFB (5 % of normals); QTc ≥ 500 ms in 52 % of long QT, but **also 6 % of normals**. So a long QTc
is only reported when the long-QT classifier agrees. The AV-block check (more P waves than QRS with a ventricular rate
under 70) flags 38 % of complete blocks and 2 % of normal ECGs, so it raises **URGENT**, not CRITICAL. In v3 it explains
the 2 extra normal false alarms (both photos at about 55/min). **Homi to decide** whether a ~2 % URGENT false alarm is an
acceptable price for the extra heart-block catches. A guard that suppresses the flag when a PR interval is measurable
removes the false alarms, but also drops heart-block detection from 38 % to 6 %, so it is not used.
Safety net: if the model is not confident the ECG is normal and no finding passes its cut-off, the engine reports
"Abnormal-looking ECG without a specific pattern — review it yourself" (ABNORMAL), never a blank result.

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
2. ~~Safety net~~, ~~AV-block check~~, ~~PR/QRS/QTc/axis measurements~~: done (v3). Still open: early inferior MI
   `ptbxl08611`, more heart-block data, and rare patterns (VT/VF, hyperkalaemia, Brugada) that PTB-XL lacks.
3. Challenge-2021 training round (CPSC, Georgia, Chapman-Shaoxing, Ningbo, PTB-XL; licence to be confirmed per
   source) for the rare critical classes; keep Phase 0 untouched, select on the 200-record selection set.
4. Homi's clinical review of the v5 review page (`validation/images/review_engine-v3.html`) and of the alert rules.
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
