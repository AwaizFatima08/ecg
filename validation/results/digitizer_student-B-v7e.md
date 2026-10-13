# Digitizer feasibility — student-B-v7e

Ground truth: the PTB-XL signals each test image was drawn from. Metrics per lead, printed window only,
baseline removed, best lag within ±0.2 s. r = Pearson correlation (1 = perfect shape).
SNR in dB as in PhysioNet 2024 (higher is better; ~0 dB = no better than a flat line).

## scan: 126/126 images digitized

| lead | median r | r ≥ 0.9 | median SNR dB |
|---|---|---|---|
| I | 0.95 | 98% | 10.6 |
| II | 0.96 | 94% | 10.9 |
| III | 0.96 | 95% | 11.0 |
| aVR | 0.97 | 98% | 12.2 |
| aVL | 0.97 | 96% | 12.0 |
| aVF | 0.97 | 97% | 12.4 |
| V1 | 0.97 | 98% | 12.4 |
| V2 | 0.96 | 90% | 11.4 |
| V3 | 0.95 | 87% | 10.1 |
| V4 | 0.94 | 86% | 9.9 |
| V5 | 0.95 | 90% | 10.1 |
| V6 | 0.96 | 98% | 11.4 |
| **all** | **0.96** | **94%** | |

## photo: 126/126 images digitized

| lead | median r | r ≥ 0.9 | median SNR dB |
|---|---|---|---|
| I | 0.89 | 44% | 7.0 |
| II | 0.85 | 30% | 5.7 |
| III | 0.92 | 61% | 7.9 |
| aVR | 0.90 | 48% | 7.1 |
| aVL | 0.91 | 53% | 7.4 |
| aVF | 0.92 | 60% | 8.1 |
| V1 | 0.93 | 66% | 8.3 |
| V2 | 0.91 | 56% | 7.6 |
| V3 | 0.89 | 41% | 6.6 |
| V4 | 0.85 | 30% | 5.5 |
| V5 | 0.86 | 37% | 6.0 |
| V6 | 0.91 | 53% | 7.4 |
| **all** | **0.90** | **48%** | |

