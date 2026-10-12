# Multan real prints — multan-teacher-v5

Images scored: 928 of 928. Source: ECG Images dataset of Cardiac Patients (Ch. Pervaiz Elahi Institute of Cardiology, Multan; Mendeley Data, CC BY 4.0). EDAN SE-3 prints, cropped to the grid.

| label | n | ≥ expected tier | CRITICAL | URGENT | ABNORMAL | no critical pattern | unreadable/error |
|---|---|---|---|---|---|---|---|
| mi (expect ≥ URGENT) | 239 | 191/239 (80%) | 111 | 80 | 48 | 0 | 0 |
| oldmi (expect ≥ ABNORMAL) | 172 | 172/172 (100%) | 102 | 54 | 16 | 0 | 0 |
| abnhb (expect ≥ ABNORMAL) | 233 | 223/233 (96%) | 45 | 109 | 69 | 10 | 0 |
| normal (expect ≥ NO_CRITICAL_PATTERN) | 284 | 56/284 (20%) | 4 | 42 | 182 | 56 | 0 |

**False alarms on normal prints (URGENT/CRITICAL): 46/284 (16%)**

Caveat: the dataset's labels are coarse and unverified per lead; 'abnormal heartbeat' and 'history of MI' prints may legitimately read as NO CRITICAL PATTERN. Homi's review of the page decides.
