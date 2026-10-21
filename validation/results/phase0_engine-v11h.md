# Phase 0 results — engine-v11h

- Images scored: 252  (records: 126)
- Model(s): engine-v11h ×252
- Prompt version(s): engine-v11h
- Source: PTB-XL 1.0.3 (PhysioNet, CC-BY 4.0), rendered as paper ECGs (`render_ptbxl_to_images.py`).
- Expected tiers come from PTB-XL labels mapped in `render_ptbxl_to_images.py` and are themselves a proposal for Homi to review.
- **Not covered by PTB-XL:** VT/VF, asystole, hyperkalaemia, Brugada, torsades. These need other sources before the CRITICAL list is signed off.


### Variant: `photo` (126 images)

**1. CRITICAL sensitivity** (expected CRITICAL → got CRITICAL)

- All critical: 31/36 (86%)
- Complete heart block (3AVB): 12/14 (86%)
- ST-elevation injury (INJ*/STE_): 17/18 (94%)
- Acute MI (Stadium I): 3/6 (50%)
- Critical read as at least URGENT: 32/36 (89%)
- **Missed (below URGENT):** ptbxl04827 → ABNORMAL, ptbxl07835 → ABNORMAL, ptbxl08611 → ABNORMAL, ptbxl08624 → ABNORMAL

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
- URGENT: 25/30 (83%)
- ABNORMAL: 30/30 (100%)

**Confusion (rows = expected from PTB-XL labels, columns = app tier)**

| expected | CRITICAL | URGENT | ABNORMAL | NO_CRITICAL_PATTERN |
|---|---|---|---|---|
| CRITICAL | 31 | 1 | 4 | 0 |
| URGENT | 10 | 15 | 5 | 0 |
| ABNORMAL | 1 | 9 | 20 | 0 |
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
- Normal → ABNORMAL (over-call): 10/30 (33%)
- Normal → NO CRITICAL PATTERN (correct): 19/30 (63%)

**3. Readability and errors**

- UNREADABLE: 0/126 (0%)
- ERROR (no reading): 0/126 (0%)
- Time per reading: median 0.0 s, max 0.0 s

**4. At least the expected tier**

- CRITICAL: 32/36 (89%)
- URGENT: 27/30 (90%)
- ABNORMAL: 30/30 (100%)

**Confusion (rows = expected from PTB-XL labels, columns = app tier)**

| expected | CRITICAL | URGENT | ABNORMAL | NO_CRITICAL_PATTERN |
|---|---|---|---|---|
| CRITICAL | 32 | 0 | 4 | 0 |
| URGENT | 8 | 19 | 3 | 0 |
| ABNORMAL | 2 | 6 | 22 | 0 |
| NO_CRITICAL_PATTERN | 0 | 1 | 10 | 19 |
