# Digitizer feasibility — lite-portable

Ground truth: the PTB-XL signals each test image was drawn from. Metrics per lead, printed window only,
baseline removed, best lag within ±0.2 s. r = Pearson correlation (1 = perfect shape).
SNR in dB as in PhysioNet 2024 (higher is better; ~0 dB = no better than a flat line).

## scan: 5/126 images digitized

| lead | median r | r ≥ 0.9 | median SNR dB |
|---|---|---|---|
| I | 0.97 | 80% | 12.5 |
| II | 0.97 | 80% | 12.7 |
| III | 0.99 | 80% | 15.2 |
| aVR | 0.96 | 80% | 11.6 |
| aVL | 0.97 | 80% | 11.5 |
| aVF | 0.98 | 80% | 13.1 |
| V1 | 0.97 | 80% | 12.7 |
| V2 | 0.97 | 80% | 12.1 |
| V3 | 0.97 | 80% | 12.7 |
| V4 | 0.96 | 60% | 11.4 |
| V5 | 0.97 | 80% | 12.1 |
| V6 | 0.97 | 80% | 12.1 |
| **all** | **0.97** | **78%** | |

## photo: 5/126 images digitized

| lead | median r | r ≥ 0.9 | median SNR dB |
|---|---|---|---|
| I | 0.89 | 40% | 7.1 |
| II | 0.84 | 40% | 5.4 |
| III | 0.90 | 60% | 7.4 |
| aVR | 0.90 | 60% | 7.7 |
| aVL | 0.85 | 40% | 5.5 |
| aVF | 0.93 | 80% | 8.5 |
| V1 | 0.90 | 40% | 7.0 |
| V2 | 0.88 | 40% | 6.3 |
| V3 | 0.90 | 60% | 7.2 |
| V4 | 0.84 | 20% | 5.6 |
| V5 | 0.88 | 40% | 6.8 |
| V6 | 0.88 | 40% | 6.6 |
| **all** | **0.89** | **47%** | |

