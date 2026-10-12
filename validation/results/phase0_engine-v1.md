# Phase 0 results — engine-v1

- Images scored: 252  (records: 126)
- Model(s): engine-v0 ×252
- Prompt version(s): engine-v1
- Source: PTB-XL 1.0.3 (PhysioNet, CC-BY 4.0), rendered as paper ECGs (`render_ptbxl_to_images.py`).
- Expected tiers come from PTB-XL labels mapped in `render_ptbxl_to_images.py` and are themselves a proposal for Homi to review.
- **Not covered by PTB-XL:** VT/VF, asystole, hyperkalaemia, Brugada, torsades. These need other sources before the CRITICAL list is signed off.


### Variant: `photo` (126 images)

**1. CRITICAL sensitivity** (expected CRITICAL → got CRITICAL)

- All critical: 30/36 (83%)
- Complete heart block (3AVB): 9/14 (64%)
- ST-elevation injury (INJ*/STE_): 16/18 (89%)
- Acute MI (Stadium I): 6/6 (100%)
- Critical read as at least URGENT: 34/36 (94%)
- **Missed (below URGENT):** ptbxl08620 → ABNORMAL, ptbxl21243 → ABNORMAL

**2. False alerts on normal ECGs**

- Normal → URGENT/CRITICAL (false alarm): 15/30 (50%)
- Normal → ABNORMAL (over-call): 15/30 (50%)
- Normal → NO CRITICAL PATTERN (correct): 0/30 (0%)

**3. Readability and errors**

- UNREADABLE: 0/126 (0%)
- ERROR (no reading): 0/126 (0%)
- Time per reading: median 0.0 s, max 0.0 s

**4. At least the expected tier**

- CRITICAL: 30/36 (83%)
- URGENT: 29/30 (97%)
- ABNORMAL: 30/30 (100%)

**Confusion (rows = expected from PTB-XL labels, columns = app tier)**

| expected | CRITICAL | URGENT | ABNORMAL |
|---|---|---|---|
| CRITICAL | 30 | 4 | 2 |
| URGENT | 22 | 7 | 1 |
| ABNORMAL | 14 | 7 | 9 |
| NO_CRITICAL_PATTERN | 15 | 0 | 15 |

### Variant: `scan` (126 images)

**1. CRITICAL sensitivity** (expected CRITICAL → got CRITICAL)

- All critical: 30/36 (83%)
- Complete heart block (3AVB): 9/14 (64%)
- ST-elevation injury (INJ*/STE_): 16/18 (89%)
- Acute MI (Stadium I): 6/6 (100%)
- Critical read as at least URGENT: 33/36 (92%)
- **Missed (below URGENT):** ptbxl08620 → ABNORMAL, ptbxl18840 → ABNORMAL, ptbxl21243 → ABNORMAL

**2. False alerts on normal ECGs**

- Normal → URGENT/CRITICAL (false alarm): 5/30 (17%)
- Normal → ABNORMAL (over-call): 25/30 (83%)
- Normal → NO CRITICAL PATTERN (correct): 0/30 (0%)

**3. Readability and errors**

- UNREADABLE: 0/126 (0%)
- ERROR (no reading): 0/126 (0%)
- Time per reading: median 0.0 s, max 0.0 s

**4. At least the expected tier**

- CRITICAL: 30/36 (83%)
- URGENT: 30/30 (100%)
- ABNORMAL: 30/30 (100%)

**Confusion (rows = expected from PTB-XL labels, columns = app tier)**

| expected | CRITICAL | URGENT | ABNORMAL |
|---|---|---|---|
| CRITICAL | 30 | 3 | 3 |
| URGENT | 19 | 11 | 0 |
| ABNORMAL | 10 | 7 | 13 |
| NO_CRITICAL_PATTERN | 4 | 1 | 25 |
