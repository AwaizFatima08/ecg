# Phase 0 results — engine-v6

- Images scored: 252  (records: 126)
- Model(s): engine-v6 ×252
- Prompt version(s): engine-v6
- Source: PTB-XL 1.0.3 (PhysioNet, CC-BY 4.0), rendered as paper ECGs (`render_ptbxl_to_images.py`).
- Expected tiers come from PTB-XL labels mapped in `render_ptbxl_to_images.py` and are themselves a proposal for Homi to review.
- **Not covered by PTB-XL:** VT/VF, asystole, hyperkalaemia, Brugada, torsades. These need other sources before the CRITICAL list is signed off.


### Variant: `photo` (126 images)

**1. CRITICAL sensitivity** (expected CRITICAL → got CRITICAL)

- All critical: 22/36 (61%)
- Complete heart block (3AVB): 6/14 (43%)
- ST-elevation injury (INJ*/STE_): 13/18 (72%)
- Acute MI (Stadium I): 3/6 (50%)
- Critical read as at least URGENT: 35/36 (97%)
- **Missed (below URGENT):** ptbxl21243 → ABNORMAL

**2. False alerts on normal ECGs**

- Normal → URGENT/CRITICAL (false alarm): 6/30 (20%)
- Normal → ABNORMAL (over-call): 10/30 (33%)
- Normal → NO CRITICAL PATTERN (correct): 14/30 (47%)

**3. Readability and errors**

- UNREADABLE: 0/126 (0%)
- ERROR (no reading): 0/126 (0%)
- Time per reading: median 0.0 s, max 0.0 s

**4. At least the expected tier**

- CRITICAL: 22/36 (61%)
- URGENT: 30/30 (100%)
- ABNORMAL: 30/30 (100%)

**Confusion (rows = expected from PTB-XL labels, columns = app tier)**

| expected | CRITICAL | URGENT | ABNORMAL | NO_CRITICAL_PATTERN |
|---|---|---|---|---|
| CRITICAL | 22 | 13 | 1 | 0 |
| URGENT | 10 | 20 | 0 | 0 |
| ABNORMAL | 1 | 18 | 11 | 0 |
| NO_CRITICAL_PATTERN | 1 | 5 | 10 | 14 |

### Variant: `scan` (126 images)

**1. CRITICAL sensitivity** (expected CRITICAL → got CRITICAL)

- All critical: 23/36 (64%)
- Complete heart block (3AVB): 6/14 (43%)
- ST-elevation injury (INJ*/STE_): 14/18 (78%)
- Acute MI (Stadium I): 4/6 (67%)
- Critical read as at least URGENT: 34/36 (94%)
- **Missed (below URGENT):** ptbxl07835 → ABNORMAL, ptbxl21243 → ABNORMAL

**2. False alerts on normal ECGs**

- Normal → URGENT/CRITICAL (false alarm): 3/30 (10%)
- Normal → ABNORMAL (over-call): 10/30 (33%)
- Normal → NO CRITICAL PATTERN (correct): 17/30 (57%)

**3. Readability and errors**

- UNREADABLE: 0/126 (0%)
- ERROR (no reading): 0/126 (0%)
- Time per reading: median 0.0 s, max 0.0 s

**4. At least the expected tier**

- CRITICAL: 23/36 (64%)
- URGENT: 29/30 (97%)
- ABNORMAL: 30/30 (100%)

**Confusion (rows = expected from PTB-XL labels, columns = app tier)**

| expected | CRITICAL | URGENT | ABNORMAL | NO_CRITICAL_PATTERN |
|---|---|---|---|---|
| CRITICAL | 23 | 11 | 2 | 0 |
| URGENT | 5 | 24 | 1 | 0 |
| ABNORMAL | 2 | 14 | 14 | 0 |
| NO_CRITICAL_PATTERN | 0 | 3 | 10 | 17 |
