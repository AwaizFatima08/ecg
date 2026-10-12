# Digitizer feasibility — lite-int8

Ground truth: the PTB-XL signals each test image was drawn from. Metrics per lead, printed window only,
baseline removed, best lag within ±0.2 s. r = Pearson correlation (1 = perfect shape).
SNR in dB as in PhysioNet 2024 (higher is better; ~0 dB = no better than a flat line).

## scan: 1/126 images digitized

| lead | median r | r ≥ 0.9 | median SNR dB |
|---|---|---|---|
| I | 0.97 | 100% | 12.7 |
| II | 0.98 | 100% | 13.3 |
| III | 0.99 | 100% | 16.9 |
| aVR | 0.97 | 100% | 12.2 |
| aVL | 0.96 | 100% | 10.9 |
| aVF | 0.99 | 100% | 15.7 |
| V1 | 0.98 | 100% | 13.2 |
| V2 | 0.97 | 100% | 12.3 |
| V3 | 0.96 | 100% | 10.4 |
| V4 | 0.96 | 100% | 11.1 |
| V5 | 0.98 | 100% | 13.5 |
| V6 | 0.99 | 100% | 16.8 |
| **all** | **0.97** | **100%** | |

## photo: 1/126 images digitized

| lead | median r | r ≥ 0.9 | median SNR dB |
|---|---|---|---|
| I | 0.69 | 0% | 3.1 |
| II | 0.86 | 0% | 5.7 |
| III | 0.92 | 100% | 7.9 |
| aVR | 0.78 | 0% | 4.3 |
| aVL | 0.86 | 0% | 5.7 |
| aVF | 0.94 | 100% | 8.5 |
| V1 | 0.70 | 0% | 3.0 |
| V2 | 0.87 | 0% | 6.2 |
| V3 | 0.73 | 0% | 3.4 |
| V4 | 0.70 | 0% | 2.8 |
| V5 | 0.91 | 100% | 7.8 |
| V6 | 0.94 | 100% | 9.6 |
| **all** | **0.86** | **33%** | |

