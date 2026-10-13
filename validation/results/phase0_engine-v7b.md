# Phase 0 results — engine-v7b

- Images scored: 252  (records: 126)
- Model(s): engine-v7b ×252
- Prompt version(s): engine-v7b
- Source: PTB-XL 1.0.3 (PhysioNet, CC-BY 4.0), rendered as paper ECGs (`render_ptbxl_to_images.py`).
- Expected tiers come from PTB-XL labels mapped in `render_ptbxl_to_images.py` and are themselves a proposal for Homi to review.
- **Not covered by PTB-XL:** VT/VF, asystole, hyperkalaemia, Brugada, torsades. These need other sources before the CRITICAL list is signed off.


### Variant: `photo` (126 images)

**1. CRITICAL sensitivity** (expected CRITICAL → got CRITICAL)

- All critical: 26/36 (72%)
- Complete heart block (3AVB): 9/14 (64%)
- ST-elevation injury (INJ*/STE_): 14/18 (78%)
- Acute MI (Stadium I): 4/6 (67%)
- Critical read as at least URGENT: 34/36 (94%)
- **Missed (below URGENT):** ptbxl07835 → ABNORMAL, ptbxl21243 → ABNORMAL

**2. False alerts on normal ECGs**

- Normal → URGENT/CRITICAL (false alarm): 6/30 (20%)
- Normal → ABNORMAL (over-call): 11/30 (37%)
- Normal → NO CRITICAL PATTERN (correct): 13/30 (43%)

**3. Readability and errors**

- UNREADABLE: 0/126 (0%)
- ERROR (no reading): 0/126 (0%)
- Time per reading: median 0.0 s, max 0.0 s

**4. At least the expected tier**

- CRITICAL: 26/36 (72%)
- URGENT: 30/30 (100%)
- ABNORMAL: 30/30 (100%)

**Confusion (rows = expected from PTB-XL labels, columns = app tier)**

| expected | CRITICAL | URGENT | ABNORMAL | NO_CRITICAL_PATTERN |
|---|---|---|---|---|
| CRITICAL | 26 | 8 | 2 | 0 |
| URGENT | 16 | 14 | 0 | 0 |
| ABNORMAL | 2 | 14 | 14 | 0 |
| NO_CRITICAL_PATTERN | 0 | 6 | 11 | 13 |

### Variant: `scan` (126 images)

**1. CRITICAL sensitivity** (expected CRITICAL → got CRITICAL)

- All critical: 29/36 (81%)
- Complete heart block (3AVB): 10/14 (71%)
- ST-elevation injury (INJ*/STE_): 15/18 (83%)
- Acute MI (Stadium I): 5/6 (83%)
- Critical read as at least URGENT: 35/36 (97%)
- **Missed (below URGENT):** ptbxl21243 → ABNORMAL

**2. False alerts on normal ECGs**

- Normal → URGENT/CRITICAL (false alarm): 2/30 (7%)
- Normal → ABNORMAL (over-call): 8/30 (27%)
- Normal → NO CRITICAL PATTERN (correct): 20/30 (67%)

**3. Readability and errors**

- UNREADABLE: 0/126 (0%)
- ERROR (no reading): 0/126 (0%)
- Time per reading: median 0.0 s, max 0.0 s

**4. At least the expected tier**

- CRITICAL: 29/36 (81%)
- URGENT: 30/30 (100%)
- ABNORMAL: 30/30 (100%)

**Confusion (rows = expected from PTB-XL labels, columns = app tier)**

| expected | CRITICAL | URGENT | ABNORMAL | NO_CRITICAL_PATTERN |
|---|---|---|---|---|
| CRITICAL | 29 | 6 | 1 | 0 |
| URGENT | 10 | 20 | 0 | 0 |
| ABNORMAL | 2 | 12 | 16 | 0 |
| NO_CRITICAL_PATTERN | 0 | 2 | 8 | 20 |
