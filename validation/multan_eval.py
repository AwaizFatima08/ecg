#!/usr/bin/env python3
"""Scores engine readings on the Multan real-print set (images_multan/manifest.csv: id, label, expected).

The dataset has only four coarse labels, so the scoring is "at least the expected tier":
  mi      -> at least URGENT   (acute MI prints; ideally CRITICAL)
  oldmi   -> at least ABNORMAL
  abnhb   -> at least ABNORMAL
  normal  -> NO_CRITICAL_PATTERN (false alarms = URGENT/CRITICAL)

Writes results/multan_<run>.md and images_multan/review_<run>.html (side-by-side, for Homi's review).

  .venv/bin/python multan_eval.py images/readings_multan-teacher.jsonl --run multan-teacher
"""
import argparse
import csv
import html
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEV = {"NO_CRITICAL_PATTERN": 0, "UNREADABLE": 1, "ABNORMAL": 2, "URGENT": 3, "CRITICAL": 4, "ERROR": -1}
TIERS = ["CRITICAL", "URGENT", "ABNORMAL", "NO_CRITICAL_PATTERN", "UNREADABLE", "ERROR"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl", type=Path)
    ap.add_argument("--run", required=True)
    a = ap.parse_args()
    man = {r["id"]: r for r in csv.DictReader(open(HERE / "images_multan" / "manifest.csv"))}
    rows = {}
    for line in open(a.jsonl):
        if not line.strip():
            continue
        j = json.loads(line)
        rid = j["image"].rsplit(".", 1)[0]
        if rid in man:
            rows[rid] = {**man[rid], "got": "ERROR" if j.get("error") else j["alert"]["tier"], "j": j}
    rows = list(rows.values())
    md = [f"# Multan real prints — {a.run}", "",
          f"Images scored: {len(rows)} of {len(man)}. Source: ECG Images dataset of Cardiac Patients (Ch. Pervaiz Elahi "
          "Institute of Cardiology, Multan; Mendeley Data, CC BY 4.0). EDAN SE-3 prints, cropped to the grid.", "",
          "| label | n | ≥ expected tier | CRITICAL | URGENT | ABNORMAL | no critical pattern | unreadable/error |",
          "|---|---|---|---|---|---|---|---|"]
    for lab in ["mi", "oldmi", "abnhb", "normal"]:
        g = [r for r in rows if r["label"] == lab]
        if not g:
            continue
        exp = g[0]["expected"]
        ok = sum(SEV[r["got"]] >= SEV[exp] for r in g) if exp != "NO_CRITICAL_PATTERN" else sum(r["got"] == exp for r in g)
        c = Counter(r["got"] for r in g)
        md.append(f"| {lab} (expect ≥ {exp}) | {len(g)} | {ok}/{len(g)} ({100 * ok / len(g):.0f}%) | {c['CRITICAL']} | {c['URGENT']} | "
                  f"{c['ABNORMAL']} | {c['NO_CRITICAL_PATTERN']} | {c['UNREADABLE'] + c['ERROR']} |")
    norm = [r for r in rows if r["label"] == "normal"]
    if norm:
        fa = sum(SEV[r["got"]] >= 3 for r in norm)
        md += ["", f"**False alarms on normal prints (URGENT/CRITICAL): {fa}/{len(norm)} ({100 * fa / len(norm):.0f}%)**"]
    md += ["", "Caveat: the dataset's labels are coarse and unverified per lead; 'abnormal heartbeat' and 'history of MI' "
           "prints may legitimately read as NO CRITICAL PATTERN. Homi's review of the page decides."]
    (HERE / "results").mkdir(exist_ok=True)
    out = HERE / "results" / f"multan_{a.run}.md"
    out.write_text("\n".join(md) + "\n")

    colour = {"CRITICAL": "#c62828", "URGENT": "#ef6c00", "ABNORMAL": "#b8860b", "NO_CRITICAL_PATTERN": "#546e7a", "UNREADABLE": "#757575", "ERROR": "#000"}
    order = {"mi": 0, "oldmi": 1, "abnhb": 2, "normal": 3}
    parts = [f"<!doctype html><meta charset=utf-8><title>Multan review {html.escape(a.run)}</title>"
             "<style>body{font:14px system-ui;margin:16px;background:#fafafa}.c{background:#fff;border:1px solid #ddd;border-radius:8px;margin:12px 0;padding:12px}"
             "img{width:100%;max-width:1100px}.t{display:inline-block;color:#fff;padding:2px 8px;border-radius:4px;font-weight:600}td{vertical-align:top;padding:2px 8px}</style>"
             f"<h1>Multan real prints — {html.escape(a.run)}</h1><p>Dataset label vs the app's tier. Click an image to open it full size.</p>"]
    for r in sorted(rows, key=lambda r: (order[r["label"]], r["id"])):
        j = r["j"]
        parts.append(f"<div class=c><b>{r['id']}</b> · dataset label <b>{r['label']}</b> (expect ≥ {r['expected']}) → "
                     f"app <span class=t style='background:{colour[r['got']]}'>{r['got']}</span>"
                     f"<br><a href='{r['id']}.jpg' target=_blank><img src='{r['id']}.jpg' loading=lazy></a><table>")
        if j.get("error"):
            parts.append(f"<tr><td><b>Error</b></td><td>{html.escape(j['error'])}</td></tr>")
        else:
            rd = j["reading"]; iv = rd["intervals"]
            parts.append(f"<tr><td><b>Engine</b></td><td>rate {rd['rate_bpm']['value']} · {html.escape(rd['rhythm']['label'])} · "
                         f"PR {iv['pr_ms']} QRS {iv['qrs_ms']} QTc {iv['qtc_ms']} · axis {rd['axis']['label']}</td></tr>")
            fs = "<br>".join(f"{html.escape(f['name'])} <code>{f['code']}</code> {f['confidence']:.2f}" for f in rd["findings"]) or "—"
            parts.append(f"<tr><td><b>Findings</b></td><td>{fs}</td></tr>")
            rs = "<br>".join(f"{x['tier']}: {html.escape(x['text'])}" for x in j["alert"]["reasons"]) or "—"
            parts.append(f"<tr><td><b>Tier reasons</b></td><td>{rs}</td></tr>")
        parts.append("</table></div>")
    (HERE / "images_multan" / f"review_{a.run}.html").write_text("\n".join(parts))
    print("\n".join(md))
    print(f"\nreport: {out}\nreview page: {HERE / 'images_multan' / f'review_{a.run}.html'}")


if __name__ == "__main__":
    main()
