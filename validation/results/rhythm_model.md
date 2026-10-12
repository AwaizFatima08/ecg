# Lethal-rhythm model (lead II, 10 s)

Held-out records: 14 of 56 (vfdb + cudb), plus 600 PTB-XL fold-10 lead II strips as 'other'.

| class | test windows | sensitivity | precision |
|---|---|---|---|
| other | 1698 | 0.96 | 0.98 |
| vt | 552 | 0.15 | 0.16 |
| vf | 875 | 0.53 | 0.48 |
| asystole | 56 | 0.16 | 0.26 |

Any lethal rhythm detected when present: 0.98
False lethal-rhythm alarm on 'other' windows: 0.038 (PTB-XL strips only: 0.002)
