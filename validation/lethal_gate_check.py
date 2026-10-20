"""Lethal-rhythm gate: a VT/VF/asystole call must be consistent with the beat detector. Sensitivity on held-out vfdb/cudb
windows (same record split as train_rhythm.py) and false alarms on digitized PTB-XL / Multan traces, with and without the gate."""
import sys, pathlib, numpy as np, torch
sys.path.insert(0, '.')
from train_rhythm import windows_from_db, prep, RhythmNet
from ecg_measure import r_peaks, measure
from engine_e2e import load_digitized
rk = torch.load('models/rhythm.pt', map_location='cpu'); net = RhythmNet(); net.load_state_dict(rk['state_dict']); net.eval()
def lethal(x2):
    with torch.no_grad(): p = torch.softmax(net(torch.from_numpy(prep(x2[None]))), 1).numpy()[0]
    cls = ['other', 'vt', 'vf', 'asystole'][int(np.argmax(p))]
    if V == "E": return (1 - p[0]) if cls != 'other' else 0.0, cls   # E: the arg-max itself must be lethal
    return 1 - p[0], cls
import os
V = os.environ.get("GATE", "A")
def feats(x2):
    r = r_peaks(x2); n = len(r)
    rr = np.diff(r) / 100.0; rr = rr[(rr > 0.25) & (rr < 2.5)]
    rate = 60 / np.median(rr) if len(rr) >= 2 else None
    cv = float(rr.std() / rr.mean()) if len(rr) >= 2 else 1.0
    gap = float(np.diff(r).max() / 100.0) if n >= 2 else 10.0
    return n, rate, cv, gap
def gate(x2, cls, m=None):
    """True = the lethal call is plausible given the beats found on the strip. A sustained REGULAR rhythm under 120/min
    with narrow QRS is neither VT, VF nor asystole; everything else passes."""
    n, rate, cv, gap = feats(x2); qrs = (m or {}).get('qrs_ms')
    if V == "A":
        if cls == 'asystole': return n <= 3 or gap >= 3.0
        if cls == 'vf': return n < 4 or cv >= 0.25
        return rate is None or (rate >= 120 and (qrs is None or qrs >= 110))
    if V == "B":  # one rule for all classes: organised slow-ish regular narrow rhythm -> implausible
        organised = n >= 5 and rate is not None and rate < 120 and cv < 0.20 and gap < 2.5 and (qrs is not None and qrs < 120)
        return not organised
    if V == "F":
        amp = float(np.percentile(np.abs(x2 - np.median(x2)), 99))
        if cls == 'asystole': return n <= 4 or gap >= 2.0 or amp < 0.15   # flat strip (beats found are noise)
        wide = qrs is None or qrs >= 110
        if cls == 'vf': return wide and cv >= 0.15                         # VF is never a regular rhythm
        return wide and (rate is None or rate >= 90)
    if V in ("D", "E"):
        if cls == 'asystole': return n <= 4 or gap >= 2.0
        wide = qrs is None or qrs >= 110          # an organised narrow-QRS rhythm is neither VT nor VF
        if cls == 'vf': return wide and (cv >= 0.15 or rate is None or rate >= 150)
        return wide and (rate is None or rate >= 100)
    if V == "C":  # like B but QRS unknown counts as narrow only if rate < 100
        organised = n >= 5 and rate is not None and cv < 0.20 and gap < 2.5 and ((qrs is not None and qrs < 120 and rate < 120) or (qrs is None and rate < 100))
        return not organised
# --- held-out lethal windows ---
X, y, r = [], [], []
for db in ('vfdb', 'cudb'):
    a, b, c = windows_from_db(db); X.append(a); y.append(b); r.append(c)
X, y, r = np.concatenate(X), np.concatenate(y), np.concatenate(r)
recs = sorted(set(r)); rng2 = np.random.default_rng(1); test_recs = set(rng2.choice(recs, size=max(1, len(recs) // 4), replace=False))
te = np.array([x in test_recs for x in r]); Xt, yt = X[te], y[te]
print('held-out windows', len(Xt), 'lethal', int((yt > 0).sum()))
det = gated = 0; fa = fa_g = 0; n_other = 0
percls = {1: [0, 0, 0], 2: [0, 0, 0], 3: [0, 0, 0]}
for x2, lab in zip(Xt, yt):
    p, cls = lethal(x2); hit = p >= 0.5
    ok = hit and gate(x2, cls)
    if lab > 0:
        det += hit; gated += ok; percls[lab][0] += 1; percls[lab][1] += hit; percls[lab][2] += ok
    else: n_other += 1; fa += hit; fa_g += ok
print(f"GATE {V}: lethal windows detected: raw {det/(yt>0).sum():.3f}  gated {gated/(yt>0).sum():.3f}   per true class (n, raw, gated):", {['','vt','vf','asys'][k]: v for k, v in percls.items()})
print(f"false alarm on 'other' vfdb/cudb windows: raw {fa/n_other:.3f}  gated {fa_g/n_other:.3f}")
# --- digitized traces ---
for d in ('engines/out_phase0_student_v7g', 'engines/out_sel_v7h', 'engines/out_multan_v7h'):
    n = raw = g = 0; kept = []
    for f in sorted(pathlib.Path(d).glob('*_timeseries_canonical.csv')):
        x = load_digitized(f)
        if x is None: continue
        n += 1; p, cls = lethal(x[1])
        if p >= 0.5:
            raw += 1
            if gate(x[1], cls, measure(x)): g += 1; kept.append((f.name[:14], cls, round(float(p), 2)))
    print(f"{d}: traces {n}, lethal calls raw {raw} -> gated {g} {kept[:8]}")
