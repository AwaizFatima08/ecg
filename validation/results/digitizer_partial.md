# Digitizer feasibility — partial

Ground truth: the PTB-XL signals each test image was drawn from. Metrics per lead, printed window only,
baseline removed, best lag within ±0.2 s. r = Pearson correlation (1 = perfect shape).
SNR in dB as in PhysioNet 2024 (higher is better; ~0 dB = no better than a flat line).

## scan: 21/126 images digitized

| lead | median r | r ≥ 0.9 | median SNR dB |
|---|---|---|---|
| I | 0.97 | 95% | 11.7 |
| II | 0.96 | 90% | 11.5 |
| III | 0.97 | 95% | 12.0 |
| aVR | 0.95 | 100% | 10.6 |
| aVL | 0.95 | 76% | 10.0 |
| aVF | 0.97 | 100% | 12.0 |
| V1 | 0.97 | 100% | 12.6 |
| V2 | 0.97 | 100% | 13.3 |
| V3 | 0.96 | 95% | 11.2 |
| V4 | 0.95 | 100% | 10.5 |
| V5 | 0.95 | 100% | 10.4 |
| V6 | 0.96 | 100% | 11.4 |
| **all** | **0.96** | **96%** | |

## photo: 13/126 images digitized

| lead | median r | r ≥ 0.9 | median SNR dB |
|---|---|---|---|
| I | 0.94 | 77% | 9.1 |
| II | 0.90 | 54% | 7.5 |
| III | 0.94 | 69% | 9.6 |
| aVR | 0.92 | 77% | 8.2 |
| aVL | 0.93 | 69% | 8.5 |
| aVF | 0.91 | 62% | 7.6 |
| V1 | 0.95 | 85% | 9.9 |
| V2 | 0.95 | 69% | 9.8 |
| V3 | 0.92 | 77% | 8.7 |
| V4 | 0.88 | 38% | 6.8 |
| V5 | 0.90 | 46% | 7.3 |
| V6 | 0.93 | 77% | 8.8 |
| **all** | **0.92** | **67%** | |

