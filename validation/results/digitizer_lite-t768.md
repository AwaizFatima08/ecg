# Digitizer feasibility — lite-t768

Ground truth: the PTB-XL signals each test image was drawn from. Metrics per lead, printed window only,
baseline removed, best lag within ±0.2 s. r = Pearson correlation (1 = perfect shape).
SNR in dB as in PhysioNet 2024 (higher is better; ~0 dB = no better than a flat line).

## scan: 5/126 images digitized

| lead | median r | r ≥ 0.9 | median SNR dB |
|---|---|---|---|
| I | 0.97 | 80% | 12.8 |
| II | 0.97 | 80% | 12.0 |
| III | 0.99 | 80% | 15.4 |
| aVR | 0.94 | 80% | 10.0 |
| aVL | 0.95 | 80% | 10.5 |
| aVF | 0.98 | 80% | 13.4 |
| V1 | 0.97 | 80% | 12.1 |
| V2 | 0.97 | 80% | 11.4 |
| V3 | 0.97 | 80% | 12.3 |
| V4 | 0.96 | 60% | 11.2 |
| V5 | 0.97 | 80% | 11.9 |
| V6 | 0.97 | 80% | 11.9 |
| **all** | **0.97** | **78%** | |

## photo: 5/126 images digitized

| lead | median r | r ≥ 0.9 | median SNR dB |
|---|---|---|---|
| I | 0.88 | 20% | 6.7 |
| II | 0.84 | 40% | 5.3 |
| III | 0.92 | 60% | 8.0 |
| aVR | 0.90 | 40% | 7.4 |
| aVL | 0.86 | 40% | 5.7 |
| aVF | 0.92 | 60% | 7.8 |
| V1 | 0.91 | 60% | 7.4 |
| V2 | 0.87 | 40% | 6.2 |
| V3 | 0.90 | 40% | 7.0 |
| V4 | 0.86 | 20% | 5.6 |
| V5 | 0.86 | 40% | 6.1 |
| V6 | 0.87 | 40% | 6.5 |
| **all** | **0.89** | **42%** | |

