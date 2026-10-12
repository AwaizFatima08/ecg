# Digitizer feasibility — lite-1600-partial

Ground truth: the PTB-XL signals each test image was drawn from. Metrics per lead, printed window only,
baseline removed, best lag within ±0.2 s. r = Pearson correlation (1 = perfect shape).
SNR in dB as in PhysioNet 2024 (higher is better; ~0 dB = no better than a flat line).

## scan: 18/126 images digitized

| lead | median r | r ≥ 0.9 | median SNR dB |
|---|---|---|---|
| I | 0.98 | 78% | 14.1 |
| II | 0.97 | 78% | 12.9 |
| III | 0.99 | 78% | 15.3 |
| aVR | 0.97 | 78% | 11.8 |
| aVL | 0.97 | 78% | 11.8 |
| aVF | 0.97 | 78% | 12.5 |
| V1 | 0.98 | 78% | 13.9 |
| V2 | 0.98 | 78% | 13.6 |
| V3 | 0.98 | 72% | 12.7 |
| V4 | 0.96 | 67% | 11.1 |
| V5 | 0.97 | 72% | 11.9 |
| V6 | 0.97 | 78% | 11.8 |
| **all** | **0.97** | **76%** | |

## photo: 18/126 images digitized

| lead | median r | r ≥ 0.9 | median SNR dB |
|---|---|---|---|
| I | 0.90 | 44% | 7.2 |
| II | 0.75 | 28% | 2.8 |
| III | 0.90 | 56% | 6.9 |
| aVR | 0.89 | 44% | 6.9 |
| aVL | 0.91 | 50% | 7.3 |
| aVF | 0.90 | 50% | 7.4 |
| V1 | 0.92 | 67% | 8.4 |
| V2 | 0.92 | 67% | 7.4 |
| V3 | 0.86 | 44% | 5.5 |
| V4 | 0.85 | 28% | 5.8 |
| V5 | 0.88 | 39% | 6.5 |
| V6 | 0.92 | 56% | 7.4 |
| **all** | **0.90** | **48%** | |

