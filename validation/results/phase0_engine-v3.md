# Phase 0 results — engine-v3

- Images scored: 252  (records: 126)
- Model(s): engine-v3 ×252
- Prompt version(s): engine-v3
- Source: PTB-XL 1.0.3 (PhysioNet, CC-BY 4.0), rendered as paper ECGs (`render_ptbxl_to_images.py`).
- Expected tiers come from PTB-XL labels mapped in `render_ptbxl_to_images.py` and are themselves a proposal for Homi to review.
- **Not covered by PTB-XL:** VT/VF, asystole, hyperkalaemia, Brugada, torsades. These need other sources before the CRITICAL list is signed off.


### Variant: `photo` (126 images)

**1. CRITICAL sensitivity** (expected CRITICAL → got CRITICAL)

- All critical: 28/36 (78%)
- Complete heart block (3AVB): 10/14 (71%)
- ST-elevation injury (INJ*/STE_): 14/18 (78%)
- Acute MI (Stadium I): 5/6 (83%)
- Critical read as at least URGENT: 34/36 (94%)
- **Missed (below URGENT):** ptbxl08611 → ABNORMAL, ptbxl21243 → ABNORMAL

**2. False alerts on normal ECGs**

- Normal → URGENT/CRITICAL (false alarm): 3/30 (10%)
- Normal → ABNORMAL (over-call): 14/30 (47%)
- Normal → NO CRITICAL PATTERN (correct): 13/30 (43%)

**3. Readability and errors**

- UNREADABLE: 0/126 (0%)
- ERROR (no reading): 0/126 (0%)
- Time per reading: median 0.0 s, max 0.0 s

**4. At least the expected tier**

- CRITICAL: 28/36 (78%)
- URGENT: 29/30 (97%)
- ABNORMAL: 30/30 (100%)

**Confusion (rows = expected from PTB-XL labels, columns = app tier)**

| expected | CRITICAL | URGENT | ABNORMAL | NO_CRITICAL_PATTERN |
|---|---|---|---|---|
| CRITICAL | 28 | 6 | 2 | 0 |
| URGENT | 13 | 16 | 1 | 0 |
| ABNORMAL | 11 | 10 | 9 | 0 |
| NO_CRITICAL_PATTERN | 1 | 2 | 14 | 13 |

### Variant: `scan` (126 images)

**1. CRITICAL sensitivity** (expected CRITICAL → got CRITICAL)

- All critical: 28/36 (78%)
- Complete heart block (3AVB): 10/14 (71%)
- ST-elevation injury (INJ*/STE_): 15/18 (83%)
- Acute MI (Stadium I): 4/6 (67%)
- Critical read as at least URGENT: 33/36 (92%)
- **Missed (below URGENT):** ptbxl08611 → ABNORMAL, ptbxl18840 → ABNORMAL, ptbxl21243 → ABNORMAL

**2. False alerts on normal ECGs**

- Normal → URGENT/CRITICAL (false alarm): 3/30 (10%)
- Normal → ABNORMAL (over-call): 10/30 (33%)
- Normal → NO CRITICAL PATTERN (correct): 17/30 (57%)

**3. Readability and errors**

- UNREADABLE: 0/126 (0%)
- ERROR (no reading): 0/126 (0%)
- Time per reading: median 0.0 s, max 0.0 s

**4. At least the expected tier**

- CRITICAL: 28/36 (78%)
- URGENT: 29/30 (97%)
- ABNORMAL: 30/30 (100%)

**Confusion (rows = expected from PTB-XL labels, columns = app tier)**

| expected | CRITICAL | URGENT | ABNORMAL | NO_CRITICAL_PATTERN |
|---|---|---|---|---|
| CRITICAL | 28 | 5 | 3 | 0 |
| URGENT | 10 | 19 | 1 | 0 |
| ABNORMAL | 11 | 11 | 8 | 0 |
| NO_CRITICAL_PATTERN | 0 | 3 | 10 | 17 |
