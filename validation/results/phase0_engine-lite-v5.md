# Phase 0 results — engine-lite-v5

- Images scored: 252  (records: 126)
- Model(s): engine-lite-v5 ×252
- Prompt version(s): engine-lite-v5
- Source: PTB-XL 1.0.3 (PhysioNet, CC-BY 4.0), rendered as paper ECGs (`render_ptbxl_to_images.py`).
- Expected tiers come from PTB-XL labels mapped in `render_ptbxl_to_images.py` and are themselves a proposal for Homi to review.
- **Not covered by PTB-XL:** VT/VF, asystole, hyperkalaemia, Brugada, torsades. These need other sources before the CRITICAL list is signed off.


### Variant: `photo` (126 images)

**1. CRITICAL sensitivity** (expected CRITICAL → got CRITICAL)

- All critical: 24/36 (67%)
- Complete heart block (3AVB): 7/14 (50%)
- ST-elevation injury (INJ*/STE_): 15/18 (83%)
- Acute MI (Stadium I): 2/6 (33%)
- Critical read as at least URGENT: 33/36 (92%)
- **Missed (below URGENT):** ptbxl08611 → ABNORMAL, ptbxl08620 → ABNORMAL, ptbxl21243 → ABNORMAL

**2. False alerts on normal ECGs**

- Normal → URGENT/CRITICAL (false alarm): 6/30 (20%)
- Normal → ABNORMAL (over-call): 11/30 (37%)
- Normal → NO CRITICAL PATTERN (correct): 13/30 (43%)

**3. Readability and errors**

- UNREADABLE: 0/126 (0%)
- ERROR (no reading): 0/126 (0%)
- Time per reading: median 0.0 s, max 0.0 s

**4. At least the expected tier**

- CRITICAL: 24/36 (67%)
- URGENT: 30/30 (100%)
- ABNORMAL: 30/30 (100%)

**Confusion (rows = expected from PTB-XL labels, columns = app tier)**

| expected | CRITICAL | URGENT | ABNORMAL | NO_CRITICAL_PATTERN |
|---|---|---|---|---|
| CRITICAL | 24 | 9 | 3 | 0 |
| URGENT | 16 | 14 | 0 | 0 |
| ABNORMAL | 0 | 21 | 9 | 0 |
| NO_CRITICAL_PATTERN | 3 | 3 | 11 | 13 |

### Variant: `scan` (126 images)

**1. CRITICAL sensitivity** (expected CRITICAL → got CRITICAL)

- All critical: 19/36 (53%)
- Complete heart block (3AVB): 3/14 (21%)
- ST-elevation injury (INJ*/STE_): 14/18 (78%)
- Acute MI (Stadium I): 2/6 (33%)
- Critical read as at least URGENT: 34/36 (94%)
- **Missed (below URGENT):** ptbxl08620 → ABNORMAL, ptbxl21243 → ABNORMAL

**2. False alerts on normal ECGs**

- Normal → URGENT/CRITICAL (false alarm): 6/30 (20%)
- Normal → ABNORMAL (over-call): 5/30 (17%)
- Normal → NO CRITICAL PATTERN (correct): 19/30 (63%)

**3. Readability and errors**

- UNREADABLE: 0/126 (0%)
- ERROR (no reading): 0/126 (0%)
- Time per reading: median 0.0 s, max 0.0 s

**4. At least the expected tier**

- CRITICAL: 19/36 (53%)
- URGENT: 30/30 (100%)
- ABNORMAL: 30/30 (100%)

**Confusion (rows = expected from PTB-XL labels, columns = app tier)**

| expected | CRITICAL | URGENT | ABNORMAL | NO_CRITICAL_PATTERN |
|---|---|---|---|---|
| CRITICAL | 19 | 15 | 2 | 0 |
| URGENT | 12 | 18 | 0 | 0 |
| ABNORMAL | 1 | 15 | 14 | 0 |
| NO_CRITICAL_PATTERN | 1 | 5 | 5 | 19 |
