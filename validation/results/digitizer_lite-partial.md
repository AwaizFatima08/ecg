# Digitizer feasibility — lite-partial

Ground truth: the PTB-XL signals each test image was drawn from. Metrics per lead, printed window only,
baseline removed, best lag within ±0.2 s. r = Pearson correlation (1 = perfect shape).
SNR in dB as in PhysioNet 2024 (higher is better; ~0 dB = no better than a flat line).

## scan: 10/126 images digitized

| lead | median r | r ≥ 0.9 | median SNR dB |
|---|---|---|---|
| I | 0.22 | 20% | -1.1 |
| II | 0.92 | 60% | 8.4 |
| III | 0.45 | 20% | 0.1 |
| aVR | 0.11 | 20% | -1.7 |
| aVL | 0.18 | 30% | -1.3 |
| aVF | 0.23 | 20% | -2.0 |
| V1 | 0.09 | 20% | -1.9 |
| V2 | 0.16 | 30% | -2.1 |
| V3 | 0.15 | 10% | -1.6 |
| V4 | 0.17 | 20% | -0.6 |
| V5 | 0.11 | 30% | -1.5 |
| V6 | 0.17 | 20% | -1.2 |
| **all** | **0.17** | **25%** | |

## photo: 10/126 images digitized

| lead | median r | r ≥ 0.9 | median SNR dB |
|---|---|---|---|
| I | 0.19 | 10% | -1.1 |
| II | 0.49 | 0% | 0.2 |
| III | 0.39 | 10% | 0.5 |
| aVR | 0.33 | 10% | -0.3 |
| aVL | 0.21 | 0% | -1.3 |
| aVF | 0.57 | 20% | -0.2 |
| V1 | 0.50 | 20% | 0.8 |
| V2 | 0.54 | 10% | 1.1 |
| V3 | 0.50 | 0% | 1.1 |
| V4 | 0.59 | 10% | 1.4 |
| V5 | 0.62 | 20% | 1.7 |
| V6 | 0.75 | 20% | 3.7 |
| **all** | **0.50** | **11%** | |

