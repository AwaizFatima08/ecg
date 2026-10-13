# Multan real prints — multan-v7

Images scored: 928 of 928. Source: ECG Images dataset of Cardiac Patients (Ch. Pervaiz Elahi Institute of Cardiology, Multan; Mendeley Data, CC BY 4.0). EDAN SE-3 prints, cropped to the grid.

| label | n | ≥ expected tier | CRITICAL | URGENT | ABNORMAL | no critical pattern | unreadable/error |
|---|---|---|---|---|---|---|---|
| mi (expect ≥ URGENT) | 239 | 207/239 (87%) | 167 | 40 | 32 | 0 | 0 |
| oldmi (expect ≥ ABNORMAL) | 172 | 172/172 (100%) | 100 | 46 | 26 | 0 | 0 |
| abnhb (expect ≥ ABNORMAL) | 233 | 227/233 (97%) | 42 | 95 | 90 | 6 | 0 |
| normal (expect ≥ NO_CRITICAL_PATTERN) | 284 | 40/284 (14%) | 8 | 42 | 194 | 40 | 0 |

**False alarms on normal prints (URGENT/CRITICAL): 50/284 (18%)**

Caveat: the dataset's labels are coarse and unverified per lead; 'abnormal heartbeat' and 'history of MI' prints may legitimately read as NO CRITICAL PATTERN. Homi's review of the page decides.
