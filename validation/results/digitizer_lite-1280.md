# Digitizer feasibility — lite-1280

Ground truth: the PTB-XL signals each test image was drawn from. Metrics per lead, printed window only,
baseline removed, best lag within ±0.2 s. r = Pearson correlation (1 = perfect shape).
SNR in dB as in PhysioNet 2024 (higher is better; ~0 dB = no better than a flat line).

## scan: 10/126 images digitized

| lead | median r | r ≥ 0.9 | median SNR dB |
|---|---|---|---|
| I | 0.17 | 30% | -1.5 |
| II | 0.93 | 70% | 8.4 |
| III | 0.32 | 30% | -0.9 |
| aVR | 0.21 | 30% | -1.6 |
| aVL | 0.11 | 30% | -1.9 |
| aVF | 0.30 | 30% | -0.8 |
| V1 | 0.19 | 30% | -1.8 |
| V2 | 0.14 | 30% | -1.7 |
| V3 | 0.23 | 20% | -0.5 |
| V4 | 0.37 | 20% | 0.1 |
| V5 | 0.66 | 40% | 2.1 |
| V6 | 0.49 | 30% | 1.1 |
| **all** | **0.23** | **32%** | |

## photo: 10/126 images digitized

| lead | median r | r ≥ 0.9 | median SNR dB |
|---|---|---|---|
| I | 0.39 | 10% | -0.1 |
| II | 0.49 | 0% | 0.1 |
| III | 0.27 | 10% | -0.4 |
| aVR | 0.25 | 10% | -1.2 |
| aVL | 0.16 | 0% | -1.5 |
| aVF | 0.29 | 10% | -0.5 |
| V1 | 0.54 | 0% | 1.0 |
| V2 | 0.13 | 0% | -1.7 |
| V3 | 0.36 | 0% | 0.5 |
| V4 | 0.46 | 0% | 0.4 |
| V5 | 0.51 | 10% | 0.9 |
| V6 | 0.56 | 0% | 1.4 |
| **all** | **0.37** | **4%** | |

