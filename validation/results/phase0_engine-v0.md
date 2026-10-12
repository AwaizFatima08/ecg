# Phase 0 results — engine-v0

- Images scored: 252  (records: 126)
- Model(s): engine-v0 ×252
- Prompt version(s): engine-v0
- Source: PTB-XL 1.0.3 (PhysioNet, CC-BY 4.0), rendered as paper ECGs (`render_ptbxl_to_images.py`).
- Expected tiers come from PTB-XL labels mapped in `render_ptbxl_to_images.py` and are themselves a proposal for Homi to review.
- **Not covered by PTB-XL:** VT/VF, asystole, hyperkalaemia, Brugada, torsades. These need other sources before the CRITICAL list is signed off.


### Variant: `photo` (126 images)

**1. CRITICAL sensitivity** (expected CRITICAL → got CRITICAL)

- All critical: 23/36 (64%)
- Complete heart block (3AVB): 5/14 (36%)
- ST-elevation injury (INJ*/STE_): 13/18 (72%)
- Acute MI (Stadium I): 6/6 (100%)
- Critical read as at least URGENT: 34/36 (94%)
- **Missed (below URGENT):** ptbxl08620 → ABNORMAL, ptbxl21243 → ABNORMAL

**2. False alerts on normal ECGs**

- Normal → URGENT/CRITICAL (false alarm): 4/30 (13%)
- Normal → ABNORMAL (over-call): 26/30 (87%)
- Normal → NO CRITICAL PATTERN (correct): 0/30 (0%)

**3. Readability and errors**

- UNREADABLE: 0/126 (0%)
- ERROR (no reading): 0/126 (0%)
- Time per reading: median 0.0 s, max 0.0 s

**4. At least the expected tier**

- CRITICAL: 23/36 (64%)
- URGENT: 26/30 (87%)
- ABNORMAL: 30/30 (100%)

**Confusion (rows = expected from PTB-XL labels, columns = app tier)**

| expected | CRITICAL | URGENT | ABNORMAL |
|---|---|---|---|
| CRITICAL | 23 | 11 | 2 |
| URGENT | 13 | 13 | 4 |
| ABNORMAL | 9 | 10 | 11 |
| NO_CRITICAL_PATTERN | 4 | 0 | 26 |

### Variant: `scan` (126 images)

**1. CRITICAL sensitivity** (expected CRITICAL → got CRITICAL)

- All critical: 22/36 (61%)
- Complete heart block (3AVB): 4/14 (29%)
- ST-elevation injury (INJ*/STE_): 13/18 (72%)
- Acute MI (Stadium I): 6/6 (100%)
- Critical read as at least URGENT: 32/36 (89%)
- **Missed (below URGENT):** ptbxl00959 → ABNORMAL, ptbxl08620 → ABNORMAL, ptbxl18840 → ABNORMAL, ptbxl21243 → ABNORMAL

**2. False alerts on normal ECGs**

- Normal → URGENT/CRITICAL (false alarm): 2/30 (7%)
- Normal → ABNORMAL (over-call): 24/30 (80%)
- Normal → NO CRITICAL PATTERN (correct): 4/30 (13%)

**3. Readability and errors**

- UNREADABLE: 0/126 (0%)
- ERROR (no reading): 0/126 (0%)
- Time per reading: median 0.0 s, max 0.0 s

**4. At least the expected tier**

- CRITICAL: 22/36 (61%)
- URGENT: 29/30 (97%)
- ABNORMAL: 30/30 (100%)

**Confusion (rows = expected from PTB-XL labels, columns = app tier)**

| expected | CRITICAL | URGENT | ABNORMAL | NO_CRITICAL_PATTERN |
|---|---|---|---|---|
| CRITICAL | 22 | 10 | 4 | 0 |
| URGENT | 10 | 19 | 1 | 0 |
| ABNORMAL | 7 | 9 | 14 | 0 |
| NO_CRITICAL_PATTERN | 0 | 2 | 24 | 4 |
