# Digitizer feasibility — student-B-t768

Ground truth: the PTB-XL signals each test image was drawn from. Metrics per lead, printed window only,
baseline removed, best lag within ±0.2 s. r = Pearson correlation (1 = perfect shape).
SNR in dB as in PhysioNet 2024 (higher is better; ~0 dB = no better than a flat line).

## scan: 126/126 images digitized

| lead | median r | r ≥ 0.9 | median SNR dB |
|---|---|---|---|
| I | 0.97 | 80% | 12.3 |
| II | 0.97 | 79% | 12.0 |
| III | 0.97 | 80% | 11.9 |
| aVR | 0.98 | 82% | 13.3 |
| aVL | 0.97 | 81% | 12.1 |
| aVF | 0.98 | 81% | 12.8 |
| V1 | 0.98 | 81% | 13.3 |
| V2 | 0.97 | 74% | 12.1 |
| V3 | 0.96 | 72% | 11.1 |
| V4 | 0.95 | 75% | 9.8 |
| V5 | 0.95 | 75% | 10.5 |
| V6 | 0.96 | 82% | 11.1 |
| **all** | **0.97** | **79%** | |

## photo: 126/126 images digitized

| lead | median r | r ≥ 0.9 | median SNR dB |
|---|---|---|---|
| I | 0.87 | 37% | 6.2 |
| II | 0.84 | 27% | 5.2 |
| III | 0.89 | 49% | 6.8 |
| aVR | 0.88 | 40% | 6.3 |
| aVL | 0.88 | 45% | 6.6 |
| aVF | 0.90 | 52% | 7.3 |
| V1 | 0.92 | 57% | 7.9 |
| V2 | 0.90 | 51% | 7.2 |
| V3 | 0.87 | 37% | 6.0 |
| V4 | 0.84 | 28% | 5.2 |
| V5 | 0.85 | 35% | 5.5 |
| V6 | 0.89 | 48% | 6.8 |
| **all** | **0.88** | **42%** | |

