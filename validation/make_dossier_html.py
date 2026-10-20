#!/usr/bin/env python3
"""Phase 0 discrepancy dossier -> images/dossier_<run>.html (+ adjudication_template.csv). Needs work/dossier.json
(make_dossier.py) and work/dossier_reads.json (Claude's reads, 21 Oct 2026)."""
import csv, html, json, sys, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent
RUN = sys.argv[1] if len(sys.argv) > 1 else "engine-v7i"
recs = json.load(open(HERE / "work" / "dossier.json"))
reads = json.load(open(HERE / "work" / "dossier_reads.json"))
RULES = json.load(open(HERE / "work" / "rule_text.json")) if (HERE / "work" / "rule_text.json").exists() else {}
COL = {"CRITICAL": "#c62828", "URGENT": "#ef6c00", "ABNORMAL": "#f9a825", "NO_CRITICAL_PATTERN": "#2e7d32"}
def tier(t): return f"<span class=t style='background:{COL.get(t, '#555')}'>{t}</span>"
def bucket(cat):
    c = cat.lower()
    if "lethal" in c: return "lethal-rhythm model false positive"
    if "rule m6" in c or "rule m7" in c: return "rule vs reference (rate rules M6/M7)"
    if "av-block measurement" in c or "av block measurement" in c or "p detector" in c: return "AV-block measurement false positive"
    if "measurement failure" in c or "qrs read" in c or "qtc not measured" in c: return "interval measurement error"
    if "under-call" in c or "miss" in c: return "classifier miss (under-call)"
    if "over-call" in c or "false" in c or "safety net" in c or "fired" in c: return "classifier false positive (over-call)"
    return "other"
E = html.escape
out = [f"<!doctype html><meta charset=utf-8><title>Phase 0 discrepancy dossier {RUN}</title><style>"
       "body{font:14px system-ui;margin:16px;background:#fafafa}.c{background:#fff;border:1px solid #ddd;border-radius:8px;margin:14px 0;padding:12px;page-break-inside:avoid}"
       "img{width:100%;max-width:1100px}.t{display:inline-block;color:#fff;padding:2px 8px;border-radius:4px;font-weight:600}td,th{vertical-align:top;padding:3px 8px;text-align:left}"
       ".adj{border:2px dashed #999;padding:8px;margin-top:8px}.adj span{display:inline-block;margin-right:18px}.dbt{background:#fff3e0;padding:2px 6px;border-radius:4px}"
       "table.sum td,table.sum th{border-bottom:1px solid #eee}</style>",
       f"<h1>Phase 0 discrepancy dossier — {RUN}</h1>",
       "<p>Records where the app's tier differs from the PTB-XL tier on the scan or the photo render. Reference = PTB-XL cardiologist labels "
       "(codes with likelihood %, free-text report). 'Claude read' is an aid for Homi's adjudication, not a clinical opinion. "
       "Phase 0 is a test set: nothing in it is used for training. For each record tick one adjudication and the tier you would give.</p>"]
buckets = collections.Counter(); deb = 0
for e in recs:
    r = reads.get(e["id"]); 
    if r: buckets[bucket(r[1])] += 1; deb += bool(r[3])
out.append(f"<h2>Summary</h2><p>{len(recs)} of 126 records flagged ({sum(1 for e in recs if any(v['tier']!=e['expected'] for v in e['variants'].values()))}); "
           f"{deb} have a PTB-XL label or rule-definition question rather than a clear engine error.</p><table class=sum><tr><th>Failure bucket (from Claude's read)</th><th>records</th></tr>"
           + "".join(f"<tr><td>{E(k)}</td><td>{v}</td></tr>" for k, v in buckets.most_common()) + "</table>")
out.append("<h2>Records</h2>")
rows = []
for i, e in enumerate(recs, 1):
    r = reads.get(e["id"], ("", "", "", False))
    v = e["variants"]
    out.append(f"<div class=c><h3>{i}. {e['id']} — {E(e['age'])} {E(e['sex'])} · PTB-XL {tier(e['expected'])} · app scan {tier(v['scan']['tier'])} photo {tier(v['photo']['tier'])}"
               + (" <span class=dbt>label / rule question</span>" if r[3] else "") + "</h3>")
    out.append(f"<a href='{e['id']}_scan.jpg' target=_blank><img src='{e['id']}_scan.jpg' loading=lazy></a>")
    out.append("<table>")
    out.append(f"<tr><th>PTB-XL</th><td><code>{E(e['codes'])}</code>{' · stadium ' + E(e['stadium']) if e['stadium'] and e['stadium'] != 'unknown' else ''}<br><i>{E(e['report'])}</i></td></tr>")
    for var in ("scan", "photo"):
        s = v[var]; iv = s["intervals"]
        out.append(f"<tr><th>App ({var})</th><td>{tier(s['tier'])} · rate {s['rate']} · {E(str(s['rhythm']))} · PR {iv['pr_ms']} QRS {iv['qrs_ms']} QTc {iv['qtc_ms']} · axis {s['axis']} · digitizer r {s['digitizer_r']}"
                   f"<br>findings: {E(', '.join(s['findings']) or '—')}<br>tier reasons: {E('; '.join(s['reasons']) or '—')}</td></tr>")
    out.append(f"<tr><th>Claude read</th><td>{E(r[0])}</td></tr><tr><th>Failure</th><td><b>{E(bucket(r[1]))}</b> — {E(r[1])}</td></tr><tr><th>Claude tier</th><td>{E(r[2])}</td></tr></table>")
    out.append("<div class=adj><b>Adjudication (Homi):</b> <span>☐ app wrong</span><span>☐ PTB-XL wrong</span><span>☐ both defensible</span><span>☐ rule change needed</span> &nbsp; "
               "<b>Tier:</b> <span>☐ CRITICAL</span><span>☐ URGENT</span><span>☐ ABNORMAL</span><span>☐ NO_CRITICAL_PATTERN</span><br>Note: ______________________________________________</div></div>")
    rows.append({"id": e["id"], "ptbxl_tier": e["expected"], "app_scan": v["scan"]["tier"], "app_photo": v["photo"]["tier"], "claude_tier": r[2], "label_or_rule_question": "yes" if r[3] else "",
                 "failure_bucket": bucket(r[1]), "homi_verdict": "", "homi_tier": "", "homi_note": ""})
(HERE / "images" / f"dossier_{RUN}.html").write_text("\n".join(out))
with open(HERE / "adjudication_template.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print("wrote", HERE / "images" / f"dossier_{RUN}.html", "and adjudication_template.csv;", dict(buckets))
