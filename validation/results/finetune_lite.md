# Fine-tune on digitized signals

Digitized records: 4600 (4000 train, 600 val); failed to digitize: 0
Digitized-val macro-AUC: base 0.9268 → fine-tuned 0.9429

| label | val positives | AUC | cut-off |
|---|---|---|---|
| st_elevation_injury | 30 | 0.973 | 0.187 |
| acute_or_recent_mi | 1 | 0.945 | 0.068 |
| old_mi_q_waves | 113 | 0.916 | 0.317 |
| st_depression_ischaemia | 63 | 0.899 | 0.068 |
| t_wave_abnormality | 49 | 0.909 | 0.242 |
| atrial_fibrillation | 47 | 0.963 | 0.019 |
| atrial_flutter | 7 | 0.963 | 0.000 |
| svt | 5 | 0.990 | 0.322 |
| pvcs | 45 | 0.973 | 0.408 |
| pacs | 20 | 0.831 | 0.044 |
| first_degree_av_block | 37 | 0.971 | 0.073 |
| second_or_third_degree_av_block | 1 | 0.890 | 0.300 |
| lbbb | 53 | 0.972 | 0.043 |
| rbbb | 55 | 0.983 | 0.037 |
| left_anterior_fascicular_block | 42 | 0.972 | 0.137 |
| nonspecific_ivcd | 21 | 0.803 | 2.000 |
| wpw_preexcitation | 7 | 0.921 | 0.000 |
| long_qt | 11 | 0.955 | 0.090 |
| lvh | 38 | 0.929 | 0.112 |
| rvh | 9 | 0.909 | 0.031 |
| paced_rhythm | 29 | 0.976 | 0.147 |
| low_voltage | 19 | 0.947 | 0.126 |
| normal | 189 | 0.955 | 0.326 |
