# Phase 0 results — engine-v2

- Images scored: 252  (records: 126)
- Model(s): engine-v2 ×252
- Prompt version(s): engine-v2
- Source: PTB-XL 1.0.3 (PhysioNet, CC-BY 4.0), rendered as paper ECGs (`render_ptbxl_to_images.py`).
- Expected tiers come from PTB-XL labels mapped in `render_ptbxl_to_images.py` and are themselves a proposal for Homi to review.
- **Not covered by PTB-XL:** VT/VF, asystole, hyperkalaemia, Brugada, torsades. These need other sources before the CRITICAL list is signed off.


### Variant: `photo` (126 images)

**1. CRITICAL sensitivity** (expected CRITICAL → got CRITICAL)

- All critical: 27/36 (75%)
- Complete heart block (3AVB): 9/14 (64%)
- ST-elevation injury (INJ*/STE_): 14/18 (78%)
- Acute MI (Stadium I): 5/6 (83%)
- Critical read as at least URGENT: 34/36 (94%)
- **Missed (below URGENT):** ptbxl08611 → ABNORMAL, ptbxl21243 → ABNORMAL

**2. False alerts on normal ECGs**

- Normal → URGENT/CRITICAL (false alarm): 1/30 (3%)
- Normal → ABNORMAL (over-call): 15/30 (50%)
- Normal → NO CRITICAL PATTERN (correct): 14/30 (47%)

**3. Readability and errors**

- UNREADABLE: 0/126 (0%)
- ERROR (no reading): 0/126 (0%)
- Time per reading: median 0.0 s, max 0.0 s

**4. At least the expected tier**

- CRITICAL: 27/36 (75%)
- URGENT: 30/30 (100%)
- ABNORMAL: 30/30 (100%)

**Confusion (rows = expected from PTB-XL labels, columns = app tier)**

| expected | CRITICAL | URGENT | ABNORMAL | NO_CRITICAL_PATTERN |
|---|---|---|---|---|
| CRITICAL | 27 | 7 | 2 | 0 |
| URGENT | 12 | 18 | 0 | 0 |
| ABNORMAL | 10 | 11 | 9 | 0 |
| NO_CRITICAL_PATTERN | 1 | 0 | 15 | 14 |

### Variant: `scan` (126 images)

**1. CRITICAL sensitivity** (expected CRITICAL → got CRITICAL)

- All critical: 28/36 (78%)
- Complete heart block (3AVB): 10/14 (71%)
- ST-elevation injury (INJ*/STE_): 15/18 (83%)
- Acute MI (Stadium I): 4/6 (67%)
- Critical read as at least URGENT: 33/36 (92%)
- **Missed (below URGENT):** ptbxl08611 → ABNORMAL, ptbxl18840 → ABNORMAL, ptbxl21243 → ABNORMAL

**2. False alerts on normal ECGs**

- Normal → URGENT/CRITICAL (false alarm): 2/30 (7%)
- Normal → ABNORMAL (over-call): 11/30 (37%)
- Normal → NO CRITICAL PATTERN (correct): 17/30 (57%)

**3. Readability and errors**

- UNREADABLE: 0/126 (0%)
- ERROR (no reading): 0/126 (0%)
- Time per reading: median 0.0 s, max 0.0 s

**4. At least the expected tier**

- CRITICAL: 28/36 (78%)
- URGENT: 30/30 (100%)
- ABNORMAL: 30/30 (100%)

**Confusion (rows = expected from PTB-XL labels, columns = app tier)**

| expected | CRITICAL | URGENT | ABNORMAL | NO_CRITICAL_PATTERN |
|---|---|---|---|---|
| CRITICAL | 28 | 5 | 3 | 0 |
| URGENT | 9 | 21 | 0 | 0 |
| ABNORMAL | 10 | 12 | 8 | 0 |
| NO_CRITICAL_PATTERN | 0 | 2 | 11 | 17 |
