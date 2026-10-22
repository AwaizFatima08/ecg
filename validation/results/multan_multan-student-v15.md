# Multan real prints — multan-student-v15

Images scored: 928 of 928. Source: ECG Images dataset of Cardiac Patients (Ch. Pervaiz Elahi Institute of Cardiology, Multan; Mendeley Data, CC BY 4.0). EDAN SE-3 prints, cropped to the grid.

| label | n | ≥ expected tier | CRITICAL | URGENT | ABNORMAL | no critical pattern | unreadable/error |
|---|---|---|---|---|---|---|---|
| mi (expect ≥ URGENT) | 239 | 223/239 (93%) | 207 | 16 | 16 | 0 | 0 |
| oldmi (expect ≥ ABNORMAL) | 172 | 172/172 (100%) | 106 | 12 | 54 | 0 | 0 |
| abnhb (expect ≥ ABNORMAL) | 233 | 217/233 (93%) | 31 | 56 | 130 | 16 | 0 |
| normal (expect ≥ NO_CRITICAL_PATTERN) | 284 | 26/284 (9%) | 4 | 12 | 242 | 26 | 0 |

**False alarms on normal prints (URGENT/CRITICAL): 16/284 (6%)**

Caveat: the dataset's labels are coarse and unverified per lead; 'abnormal heartbeat' and 'history of MI' prints may legitimately read as NO CRITICAL PATTERN. Homi's review of the page decides.
