# Phase 0 results — engine-lite

- Images scored: 252  (records: 126)
- Model(s): engine-lite ×252
- Prompt version(s): engine-lite
- Source: PTB-XL 1.0.3 (PhysioNet, CC-BY 4.0), rendered as paper ECGs (`render_ptbxl_to_images.py`).
- Expected tiers come from PTB-XL labels mapped in `render_ptbxl_to_images.py` and are themselves a proposal for Homi to review.
- **Not covered by PTB-XL:** VT/VF, asystole, hyperkalaemia, Brugada, torsades. These need other sources before the CRITICAL list is signed off.


### Variant: `photo` (126 images)

**1. CRITICAL sensitivity** (expected CRITICAL → got CRITICAL)

- All critical: 27/36 (75%)
- Complete heart block (3AVB): 8/14 (57%)
- ST-elevation injury (INJ*/STE_): 16/18 (89%)
- Acute MI (Stadium I): 3/6 (50%)
- Critical read as at least URGENT: 32/36 (89%)
- **Missed (below URGENT):** ptbxl04827 → ABNORMAL, ptbxl07835 → ABNORMAL, ptbxl08611 → ABNORMAL, ptbxl21243 → ABNORMAL

**2. False alerts on normal ECGs**

- Normal → URGENT/CRITICAL (false alarm): 13/30 (43%)
- Normal → ABNORMAL (over-call): 14/30 (47%)
- Normal → NO CRITICAL PATTERN (correct): 3/30 (10%)

**3. Readability and errors**

- UNREADABLE: 0/126 (0%)
- ERROR (no reading): 0/126 (0%)
- Time per reading: median 0.0 s, max 0.0 s

**4. At least the expected tier**

- CRITICAL: 27/36 (75%)
- URGENT: 27/30 (90%)
- ABNORMAL: 30/30 (100%)

**Confusion (rows = expected from PTB-XL labels, columns = app tier)**

| expected | CRITICAL | URGENT | ABNORMAL | NO_CRITICAL_PATTERN |
|---|---|---|---|---|
| CRITICAL | 27 | 5 | 4 | 0 |
| URGENT | 20 | 7 | 3 | 0 |
| ABNORMAL | 13 | 10 | 7 | 0 |
| NO_CRITICAL_PATTERN | 9 | 4 | 14 | 3 |

### Variant: `scan` (126 images)

**1. CRITICAL sensitivity** (expected CRITICAL → got CRITICAL)

- All critical: 29/36 (81%)
- Complete heart block (3AVB): 10/14 (71%)
- ST-elevation injury (INJ*/STE_): 15/18 (83%)
- Acute MI (Stadium I): 5/6 (83%)
- Critical read as at least URGENT: 34/36 (94%)
- **Missed (below URGENT):** ptbxl08611 → ABNORMAL, ptbxl21243 → ABNORMAL

**2. False alerts on normal ECGs**

- Normal → URGENT/CRITICAL (false alarm): 4/30 (13%)
- Normal → ABNORMAL (over-call): 7/30 (23%)
- Normal → NO CRITICAL PATTERN (correct): 19/30 (63%)

**3. Readability and errors**

- UNREADABLE: 0/126 (0%)
- ERROR (no reading): 0/126 (0%)
- Time per reading: median 0.0 s, max 0.0 s

**4. At least the expected tier**

- CRITICAL: 29/36 (81%)
- URGENT: 28/30 (93%)
- ABNORMAL: 30/30 (100%)

**Confusion (rows = expected from PTB-XL labels, columns = app tier)**

| expected | CRITICAL | URGENT | ABNORMAL | NO_CRITICAL_PATTERN |
|---|---|---|---|---|
| CRITICAL | 29 | 5 | 2 | 0 |
| URGENT | 11 | 17 | 2 | 0 |
| ABNORMAL | 10 | 9 | 11 | 0 |
| NO_CRITICAL_PATTERN | 0 | 4 | 7 | 19 |
