# Digitizer feasibility — lite-1024

Ground truth: the PTB-XL signals each test image was drawn from. Metrics per lead, printed window only,
baseline removed, best lag within ±0.2 s. r = Pearson correlation (1 = perfect shape).
SNR in dB as in PhysioNet 2024 (higher is better; ~0 dB = no better than a flat line).

## scan: 5/126 images digitized

| lead | median r | r ≥ 0.9 | median SNR dB |
|---|---|---|---|
| I | 0.92 | 60% | 7.7 |
| II | 0.94 | 80% | 9.2 |
| III | 0.95 | 60% | 9.9 |
| aVR | 0.93 | 80% | 9.1 |
| aVL | 0.93 | 60% | 8.1 |
| aVF | 0.95 | 80% | 10.1 |
| V1 | 0.93 | 80% | 8.4 |
| V2 | 0.93 | 80% | 8.7 |
| V3 | 0.92 | 60% | 7.9 |
| V4 | 0.92 | 60% | 8.2 |
| V5 | 0.92 | 80% | 8.4 |
| V6 | 0.93 | 80% | 9.0 |
| **all** | **0.93** | **72%** | |

## photo: 5/126 images digitized

| lead | median r | r ≥ 0.9 | median SNR dB |
|---|---|---|---|
| I | 0.86 | 0% | 6.2 |
| II | 0.81 | 20% | 4.7 |
| III | 0.87 | 20% | 6.0 |
| aVR | 0.84 | 0% | 5.6 |
| aVL | 0.83 | 20% | 5.1 |
| aVF | 0.89 | 20% | 6.5 |
| V1 | 0.89 | 40% | 6.9 |
| V2 | 0.85 | 40% | 5.5 |
| V3 | 0.82 | 0% | 5.3 |
| V4 | 0.77 | 0% | 4.0 |
| V5 | 0.75 | 20% | 3.7 |
| V6 | 0.79 | 20% | 4.5 |
| **all** | **0.83** | **17%** | |

