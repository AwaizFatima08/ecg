# Fine-tune on digitized signals

Digitized records: 4600 (4000 train, 600 val); failed to digitize: 0
Digitized-val macro-AUC: base 0.9570 → fine-tuned 0.9606

| label | val positives | AUC | cut-off |
|---|---|---|---|
| st_elevation_injury | 30 | 0.984 | 0.187 |
| acute_or_recent_mi | 1 | 0.987 | 0.068 |
| old_mi_q_waves | 113 | 0.930 | 0.326 |
| st_depression_ischaemia | 63 | 0.923 | 0.088 |
| t_wave_abnormality | 49 | 0.936 | 0.210 |
| atrial_fibrillation | 47 | 0.974 | 0.141 |
| atrial_flutter | 7 | 0.970 | 0.000 |
| svt | 5 | 0.991 | 0.083 |
| pvcs | 45 | 0.989 | 0.137 |
| pacs | 20 | 0.891 | 0.231 |
| first_degree_av_block | 37 | 0.972 | 0.190 |
| second_or_third_degree_av_block | 1 | 0.993 | 0.300 |
| lbbb | 53 | 0.987 | 0.065 |
| rbbb | 55 | 0.988 | 0.164 |
| left_anterior_fascicular_block | 42 | 0.980 | 0.123 |
| nonspecific_ivcd | 21 | 0.796 | 2.000 |
| wpw_preexcitation | 7 | 0.934 | 0.001 |
| long_qt | 11 | 0.950 | 0.072 |
| lvh | 38 | 0.935 | 0.160 |
| rvh | 9 | 0.956 | 0.008 |
| paced_rhythm | 29 | 0.967 | 0.059 |
| low_voltage | 19 | 0.938 | 0.136 |
| normal | 189 | 0.959 | 0.308 |
