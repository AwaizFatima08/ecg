# Digitizer feasibility — student-B-phase0

Ground truth: the PTB-XL signals each test image was drawn from. Metrics per lead, printed window only,
baseline removed, best lag within ±0.2 s. r = Pearson correlation (1 = perfect shape).
SNR in dB as in PhysioNet 2024 (higher is better; ~0 dB = no better than a flat line).

## scan: 126/126 images digitized

| lead | median r | r ≥ 0.9 | median SNR dB |
|---|---|---|---|
| I | 0.96 | 79% | 11.5 |
| II | 0.97 | 78% | 12.0 |
| III | 0.97 | 79% | 11.5 |
| aVR | 0.97 | 81% | 12.8 |
| aVL | 0.97 | 79% | 11.9 |
| aVF | 0.97 | 80% | 12.5 |
| V1 | 0.97 | 80% | 12.8 |
| V2 | 0.97 | 73% | 11.9 |
| V3 | 0.96 | 71% | 10.8 |
| V4 | 0.95 | 75% | 10.0 |
| V5 | 0.95 | 75% | 10.5 |
| V6 | 0.96 | 81% | 11.1 |
| **all** | **0.97** | **78%** | |

## photo: 126/126 images digitized

| lead | median r | r ≥ 0.9 | median SNR dB |
|---|---|---|---|
| I | 0.85 | 35% | 5.8 |
| II | 0.83 | 25% | 5.1 |
| III | 0.90 | 48% | 7.1 |
| aVR | 0.88 | 39% | 6.5 |
| aVL | 0.89 | 44% | 6.6 |
| aVF | 0.91 | 53% | 7.5 |
| V1 | 0.91 | 57% | 7.7 |
| V2 | 0.90 | 49% | 6.9 |
| V3 | 0.86 | 32% | 5.8 |
| V4 | 0.82 | 29% | 5.0 |
| V5 | 0.85 | 33% | 5.5 |
| V6 | 0.89 | 47% | 7.0 |
| **all** | **0.88** | **41%** | |

