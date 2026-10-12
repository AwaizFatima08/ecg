# Digitizer feasibility — 2026-10-12

Ground truth: the PTB-XL signals each test image was drawn from. Metrics per lead, printed window only,
baseline removed, best lag within ±0.2 s. r = Pearson correlation (1 = perfect shape).
SNR in dB as in PhysioNet 2024 (higher is better; ~0 dB = no better than a flat line).

## scan: 126/126 images digitized

| lead | median r | r ≥ 0.9 | median SNR dB |
|---|---|---|---|
| I | 0.97 | 96% | 12.2 |
| II | 0.96 | 94% | 11.6 |
| III | 0.97 | 98% | 12.5 |
| aVR | 0.96 | 98% | 11.0 |
| aVL | 0.96 | 94% | 11.6 |
| aVF | 0.97 | 98% | 11.9 |
| V1 | 0.97 | 99% | 12.6 |
| V2 | 0.97 | 98% | 12.1 |
| V3 | 0.96 | 91% | 11.0 |
| V4 | 0.94 | 90% | 9.6 |
| V5 | 0.95 | 94% | 10.3 |
| V6 | 0.96 | 94% | 11.1 |
| **all** | **0.96** | **96%** | |

## photo: 126/126 images digitized

| lead | median r | r ≥ 0.9 | median SNR dB |
|---|---|---|---|
| I | 0.94 | 76% | 9.0 |
| II | 0.90 | 55% | 7.5 |
| III | 0.95 | 74% | 9.8 |
| aVR | 0.94 | 75% | 9.2 |
| aVL | 0.94 | 67% | 9.1 |
| aVF | 0.94 | 78% | 9.4 |
| V1 | 0.95 | 86% | 10.1 |
| V2 | 0.95 | 79% | 9.8 |
| V3 | 0.92 | 72% | 8.4 |
| V4 | 0.91 | 55% | 7.5 |
| V5 | 0.91 | 56% | 7.8 |
| V6 | 0.93 | 75% | 8.7 |
| **all** | **0.93** | **71%** | |

