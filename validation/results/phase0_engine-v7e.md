# Phase 0 results — engine-v7e

- Images scored: 252  (records: 126)
- Model(s): engine-v7e ×252
- Prompt version(s): engine-v7e
- Source: PTB-XL 1.0.3 (PhysioNet, CC-BY 4.0), rendered as paper ECGs (`render_ptbxl_to_images.py`).
- Expected tiers come from PTB-XL labels mapped in `render_ptbxl_to_images.py` and are themselves a proposal for Homi to review.
- **Not covered by PTB-XL:** VT/VF, asystole, hyperkalaemia, Brugada, torsades. These need other sources before the CRITICAL list is signed off.


### Variant: `photo` (126 images)

**1. CRITICAL sensitivity** (expected CRITICAL → got CRITICAL)

- All critical: 29/36 (81%)
- Complete heart block (3AVB): 11/14 (79%)
- ST-elevation injury (INJ*/STE_): 15/18 (83%)
- Acute MI (Stadium I): 4/6 (67%)
- Critical read as at least URGENT: 33/36 (92%)
- **Missed (below URGENT):** ptbxl07835 → ABNORMAL, ptbxl08611 → ABNORMAL, ptbxl21243 → ABNORMAL

**2. False alerts on normal ECGs**

- Normal → URGENT/CRITICAL (false alarm): 3/30 (10%)
- Normal → ABNORMAL (over-call): 17/30 (57%)
- Normal → NO CRITICAL PATTERN (correct): 10/30 (33%)

**3. Readability and errors**

- UNREADABLE: 0/126 (0%)
- ERROR (no reading): 0/126 (0%)
- Time per reading: median 0.0 s, max 0.0 s

**4. At least the expected tier**

- CRITICAL: 29/36 (81%)
- URGENT: 26/30 (87%)
- ABNORMAL: 30/30 (100%)

**Confusion (rows = expected from PTB-XL labels, columns = app tier)**

| expected | CRITICAL | URGENT | ABNORMAL | NO_CRITICAL_PATTERN |
|---|---|---|---|---|
| CRITICAL | 29 | 4 | 3 | 0 |
| URGENT | 11 | 15 | 4 | 0 |
| ABNORMAL | 2 | 12 | 16 | 0 |
| NO_CRITICAL_PATTERN | 0 | 3 | 17 | 10 |

### Variant: `scan` (126 images)

**1. CRITICAL sensitivity** (expected CRITICAL → got CRITICAL)

- All critical: 31/36 (86%)
- Complete heart block (3AVB): 12/14 (86%)
- ST-elevation injury (INJ*/STE_): 15/18 (83%)
- Acute MI (Stadium I): 5/6 (83%)
- Critical read as at least URGENT: 35/36 (97%)
- **Missed (below URGENT):** ptbxl21243 → ABNORMAL

**2. False alerts on normal ECGs**

- Normal → URGENT/CRITICAL (false alarm): 2/30 (7%)
- Normal → ABNORMAL (over-call): 9/30 (30%)
- Normal → NO CRITICAL PATTERN (correct): 19/30 (63%)

**3. Readability and errors**

- UNREADABLE: 0/126 (0%)
- ERROR (no reading): 0/126 (0%)
- Time per reading: median 0.0 s, max 0.0 s

**4. At least the expected tier**

- CRITICAL: 31/36 (86%)
- URGENT: 29/30 (97%)
- ABNORMAL: 30/30 (100%)

**Confusion (rows = expected from PTB-XL labels, columns = app tier)**

| expected | CRITICAL | URGENT | ABNORMAL | NO_CRITICAL_PATTERN |
|---|---|---|---|---|
| CRITICAL | 31 | 4 | 1 | 0 |
| URGENT | 10 | 19 | 1 | 0 |
| ABNORMAL | 1 | 10 | 19 | 0 |
| NO_CRITICAL_PATTERN | 0 | 2 | 9 | 19 |
