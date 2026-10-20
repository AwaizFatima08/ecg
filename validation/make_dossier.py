#!/usr/bin/env python3
"""Phase 0 discrepancy dossier: records where the app's tier (engine run RUN) differs from PTB-XL on scan or photo.
Writes work/dossier.json (all data) and, with reads in work/dossier_reads.json, images/dossier_<RUN>.html + the
adjudication template validation/adjudication_template.csv. Phase 0 stays a test set: nothing here trains anything."""
import csv, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
RUN = sys.argv[1] if len(sys.argv) > 1 else "engine-v7i"
ORDER = {"NO_CRITICAL_PATTERN": 0, "ABNORMAL": 1, "URGENT": 2, "CRITICAL": 3}
man = {r["id"]: r for r in csv.DictReader(open(HERE / "images" / "manifest.csv"))}
dig = {(r["id"], r["variant"]): r for r in csv.DictReader(open(HERE / "results" / f"digitizer_student-B-v7g.csv"))}
app = {}
for l in open(HERE / "images" / f"readings_{RUN}.jsonl"):
    r = json.loads(l); rid, var = r["image"][:10], r["image"][11:].split(".")[0]
    app[(rid, var)] = r
MI = {"IMI", "ASMI", "AMI", "ALMI", "ILMI", "IPMI", "IPLMI", "LMI", "PMI", "INJAS", "INJAL", "INJIN", "INJLA", "INJIL"}
def category(m, ra):
    """Rough, automatic failure category; my read refines it."""
    codes = {c.split(":")[0] for c in m["codes"].split(";")}
    e, t = m["expected"], ra["alert"]["tier"]
    f = {x["code"] for x in ra["reading"]["findings"]}
    if ORDER[t] < ORDER[e]:
        if codes & MI and e == "CRITICAL" and "stemi_pattern" not in f: return "classifier miss: infarction pattern not detected"
        if {"3AVB", "2AVB"} & codes and "high_grade_av_block" not in f: return "heart block not detected (classifier + AV-block check)"
        return "under-call"
    if e == "NO_CRITICAL_PATTERN": return "over-call on a normal ECG: " + ", ".join(sorted(f)) if f else "over-call: safety net"
    return "over-call: " + ", ".join(sorted(f))
recs = []
for rid, m in man.items():
    tiers = {v: app[(rid, v)]["alert"]["tier"] for v in ("scan", "photo")}
    if all(t == m["expected"] for t in tiers.values()): continue
    entry = {"id": rid, "expected": m["expected"], "codes": m["codes"], "stadium": m["stadium"], "report": m["report"],
             "age": m["age"], "sex": m["sex"], "variants": {}}
    for v in ("scan", "photo"):
        ra = app[(rid, v)]; rd = ra["reading"]; d = dig.get((rid, v), {})
        entry["variants"][v] = {"tier": ra["alert"]["tier"], "rate": rd["rate_bpm"]["value"], "rhythm": rd["rhythm"]["label"],
            "intervals": rd["intervals"], "axis": rd["axis"]["label"],
            "findings": [f"{x['name']} ({x['confidence']:.2f})" for x in rd["findings"]],
            "reasons": [f"{x['tier']}: {x['text']}" for x in ra["alert"]["reasons"]],
            "digitizer_r": d.get("median_r"), "leadII_r": d.get("leadII_r"),
            "category": category(m, ra) if ra["alert"]["tier"] != m["expected"] else "agrees"}
    recs.append(entry)
(HERE / "work").mkdir(exist_ok=True)
json.dump(recs, open(HERE / "work" / "dossier.json", "w"), indent=1)
print(len(recs), "records")
for e in recs:
    v = e["variants"]
    print(f"{e['id']}  truth {e['expected']:19s} scan {v['scan']['tier']:19s} photo {v['photo']['tier']:19s} | {e['codes'][:45]:45s} | r {v['scan']['digitizer_r']}/{v['photo']['digitizer_r']} | {v['scan']['category'] if v['scan']['category']!='agrees' else v['photo']['category']}")
