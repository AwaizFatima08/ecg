# Phase 0 results — engine-v7m

- Images scored: 252  (records: 126)
- Model(s): engine-v7m ×252
- Prompt version(s): engine-v7m
- Source: PTB-XL 1.0.3 (PhysioNet, CC-BY 4.0), rendered as paper ECGs (`render_ptbxl_to_images.py`).
- Expected tiers come from PTB-XL labels mapped in `render_ptbxl_to_images.py` and are themselves a proposal for Homi to review.
- **Not covered by PTB-XL:** VT/VF, asystole, hyperkalaemia, Brugada, torsades. These need other sources before the CRITICAL list is signed off.


### Variant: `photo` (126 images)

**1. CRITICAL sensitivity** (expected CRITICAL → got CRITICAL)

- All critical: 28/36 (78%)
- Complete heart block (3AVB): 10/14 (71%)
- ST-elevation injury (INJ*/STE_): 16/18 (89%)
- Acute MI (Stadium I): 2/6 (33%)
- Critical read as at least URGENT: 32/36 (89%)
- **Missed (below URGENT):** ptbxl07835 → ABNORMAL, ptbxl08611 → ABNORMAL, ptbxl08624 → ABNORMAL, ptbxl21243 → ABNORMAL

**2. False alerts on normal ECGs**

- Normal → URGENT/CRITICAL (false alarm): 2/30 (7%)
- Normal → ABNORMAL (over-call): 18/30 (60%)
- Normal → NO CRITICAL PATTERN (correct): 10/30 (33%)

**3. Readability and errors**

- UNREADABLE: 0/126 (0%)
- ERROR (no reading): 0/126 (0%)
- Time per reading: median 0.0 s, max 0.0 s

**4. At least the expected tier**

- CRITICAL: 28/36 (78%)
- URGENT: 26/30 (87%)
- ABNORMAL: 30/30 (100%)

**Confusion (rows = expected from PTB-XL labels, columns = app tier)**

| expected | CRITICAL | URGENT | ABNORMAL | NO_CRITICAL_PATTERN |
|---|---|---|---|---|
| CRITICAL | 28 | 4 | 4 | 0 |
| URGENT | 11 | 15 | 4 | 0 |
| ABNORMAL | 2 | 8 | 20 | 0 |
| NO_CRITICAL_PATTERN | 0 | 2 | 18 | 10 |

### Variant: `scan` (126 images)

**1. CRITICAL sensitivity** (expected CRITICAL → got CRITICAL)

- All critical: 32/36 (89%)
- Complete heart block (3AVB): 13/14 (93%)
- ST-elevation injury (INJ*/STE_): 15/18 (83%)
- Acute MI (Stadium I): 5/6 (83%)
- Critical read as at least URGENT: 32/36 (89%)
- **Missed (below URGENT):** ptbxl08611 → ABNORMAL, ptbxl08624 → ABNORMAL, ptbxl18840 → ABNORMAL, ptbxl21243 → ABNORMAL

**2. False alerts on normal ECGs**

- Normal → URGENT/CRITICAL (false alarm): 1/30 (3%)
- Normal → ABNORMAL (over-call): 9/30 (30%)
- Normal → NO CRITICAL PATTERN (correct): 20/30 (67%)

**3. Readability and errors**

- UNREADABLE: 0/126 (0%)
- ERROR (no reading): 0/126 (0%)
- Time per reading: median 0.0 s, max 0.0 s

**4. At least the expected tier**

- CRITICAL: 32/36 (89%)
- URGENT: 29/30 (97%)
- ABNORMAL: 30/30 (100%)

**Confusion (rows = expected from PTB-XL labels, columns = app tier)**

| expected | CRITICAL | URGENT | ABNORMAL | NO_CRITICAL_PATTERN |
|---|---|---|---|---|
| CRITICAL | 32 | 0 | 4 | 0 |
| URGENT | 11 | 18 | 1 | 0 |
| ABNORMAL | 2 | 7 | 21 | 0 |
| NO_CRITICAL_PATTERN | 0 | 1 | 9 | 20 |
