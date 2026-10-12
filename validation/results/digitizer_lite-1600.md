# Digitizer feasibility — lite-1600

Ground truth: the PTB-XL signals each test image was drawn from. Metrics per lead, printed window only,
baseline removed, best lag within ±0.2 s. r = Pearson correlation (1 = perfect shape).
SNR in dB as in PhysioNet 2024 (higher is better; ~0 dB = no better than a flat line).

## scan: 126/126 images digitized

| lead | median r | r ≥ 0.9 | median SNR dB |
|---|---|---|---|
| I | 0.98 | 82% | 13.8 |
| II | 0.97 | 79% | 13.0 |
| III | 0.98 | 82% | 13.7 |
| aVR | 0.98 | 83% | 13.5 |
| aVL | 0.97 | 82% | 12.5 |
| aVF | 0.97 | 82% | 12.9 |
| V1 | 0.98 | 81% | 14.4 |
| V2 | 0.98 | 74% | 13.7 |
| V3 | 0.97 | 71% | 11.9 |
| V4 | 0.95 | 73% | 10.4 |
| V5 | 0.96 | 73% | 11.1 |
| V6 | 0.97 | 81% | 11.8 |
| **all** | **0.97** | **79%** | |

## photo: 126/126 images digitized

| lead | median r | r ≥ 0.9 | median SNR dB |
|---|---|---|---|
| I | 0.89 | 43% | 6.9 |
| II | 0.85 | 29% | 5.3 |
| III | 0.91 | 56% | 7.4 |
| aVR | 0.89 | 43% | 6.6 |
| aVL | 0.89 | 47% | 6.5 |
| aVF | 0.92 | 56% | 7.8 |
| V1 | 0.92 | 58% | 7.9 |
| V2 | 0.90 | 50% | 6.7 |
| V3 | 0.87 | 39% | 6.1 |
| V4 | 0.84 | 31% | 5.3 |
| V5 | 0.86 | 37% | 5.6 |
| V6 | 0.90 | 51% | 7.2 |
| **all** | **0.89** | **45%** | |

