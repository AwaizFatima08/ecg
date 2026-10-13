# Multan real prints — multan-student-v7b

Images scored: 928 of 928. Source: ECG Images dataset of Cardiac Patients (Ch. Pervaiz Elahi Institute of Cardiology, Multan; Mendeley Data, CC BY 4.0). EDAN SE-3 prints, cropped to the grid.

| label | n | ≥ expected tier | CRITICAL | URGENT | ABNORMAL | no critical pattern | unreadable/error |
|---|---|---|---|---|---|---|---|
| mi (expect ≥ URGENT) | 239 | 215/239 (90%) | 191 | 24 | 24 | 0 | 0 |
| oldmi (expect ≥ ABNORMAL) | 172 | 172/172 (100%) | 106 | 28 | 38 | 0 | 0 |
| abnhb (expect ≥ ABNORMAL) | 233 | 227/233 (97%) | 36 | 84 | 107 | 6 | 0 |
| normal (expect ≥ NO_CRITICAL_PATTERN) | 284 | 24/284 (8%) | 8 | 34 | 218 | 24 | 0 |

**False alarms on normal prints (URGENT/CRITICAL): 42/284 (15%)**

Caveat: the dataset's labels are coarse and unverified per lead; 'abnormal heartbeat' and 'history of MI' prints may legitimately read as NO CRITICAL PATTERN. Homi's review of the page decides.
