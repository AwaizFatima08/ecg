# Phase 0 results — engine-v7l

- Images scored: 252  (records: 126)
- Model(s): engine-v7l ×252
- Prompt version(s): engine-v7l
- Source: PTB-XL 1.0.3 (PhysioNet, CC-BY 4.0), rendered as paper ECGs (`render_ptbxl_to_images.py`).
- Expected tiers come from PTB-XL labels mapped in `render_ptbxl_to_images.py` and are themselves a proposal for Homi to review.
- **Not covered by PTB-XL:** VT/VF, asystole, hyperkalaemia, Brugada, torsades. These need other sources before the CRITICAL list is signed off.


### Variant: `photo` (126 images)

**1. CRITICAL sensitivity** (expected CRITICAL → got CRITICAL)

- All critical: 31/36 (86%)
- Complete heart block (3AVB): 12/14 (86%)
- ST-elevation injury (INJ*/STE_): 17/18 (94%)
- Acute MI (Stadium I): 3/6 (50%)
- Critical read as at least URGENT: 34/36 (94%)
- **Missed (below URGENT):** ptbxl07835 → ABNORMAL, ptbxl08624 → ABNORMAL

**2. False alerts on normal ECGs**

- Normal → URGENT/CRITICAL (false alarm): 2/30 (7%)
- Normal → ABNORMAL (over-call): 18/30 (60%)
- Normal → NO CRITICAL PATTERN (correct): 10/30 (33%)

**3. Readability and errors**

- UNREADABLE: 0/126 (0%)
- ERROR (no reading): 0/126 (0%)
- Time per reading: median 0.0 s, max 0.0 s

**4. At least the expected tier**

- CRITICAL: 31/36 (86%)
- URGENT: 28/30 (93%)
- ABNORMAL: 30/30 (100%)

**Confusion (rows = expected from PTB-XL labels, columns = app tier)**

| expected | CRITICAL | URGENT | ABNORMAL | NO_CRITICAL_PATTERN |
|---|---|---|---|---|
| CRITICAL | 31 | 3 | 2 | 0 |
| URGENT | 16 | 12 | 2 | 0 |
| ABNORMAL | 2 | 8 | 20 | 0 |
| NO_CRITICAL_PATTERN | 0 | 2 | 18 | 10 |

### Variant: `scan` (126 images)

**1. CRITICAL sensitivity** (expected CRITICAL → got CRITICAL)

- All critical: 33/36 (92%)
- Complete heart block (3AVB): 14/14 (100%)
- ST-elevation injury (INJ*/STE_): 16/18 (89%)
- Acute MI (Stadium I): 5/6 (83%)
- Critical read as at least URGENT: 33/36 (92%)
- **Missed (below URGENT):** ptbxl08611 → ABNORMAL, ptbxl08624 → ABNORMAL, ptbxl18840 → ABNORMAL

**2. False alerts on normal ECGs**

- Normal → URGENT/CRITICAL (false alarm): 1/30 (3%)
- Normal → ABNORMAL (over-call): 9/30 (30%)
- Normal → NO CRITICAL PATTERN (correct): 20/30 (67%)

**3. Readability and errors**

- UNREADABLE: 0/126 (0%)
- ERROR (no reading): 0/126 (0%)
- Time per reading: median 0.0 s, max 0.0 s

**4. At least the expected tier**

- CRITICAL: 33/36 (92%)
- URGENT: 30/30 (100%)
- ABNORMAL: 30/30 (100%)

**Confusion (rows = expected from PTB-XL labels, columns = app tier)**

| expected | CRITICAL | URGENT | ABNORMAL | NO_CRITICAL_PATTERN |
|---|---|---|---|---|
| CRITICAL | 33 | 0 | 3 | 0 |
| URGENT | 12 | 18 | 0 | 0 |
| ABNORMAL | 2 | 7 | 21 | 0 |
| NO_CRITICAL_PATTERN | 0 | 1 | 9 | 20 |
