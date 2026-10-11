#!/usr/bin/env python3
"""Phase 0 scoring (design-v1 Sections 8.3 and 10).

Reads validation/images/manifest.csv (expected tiers from PTB-XL labels) and a
JSONL file written by functions/scripts/readImages.ts, then writes:

  validation/results/phase0_<run>.md     metrics only (committed; no images)
  validation/images/review_<run>.html    side-by-side review page for Homi
                                         (local only: it shows the images)

Order of importance (design 8.3): sensitivity for CRITICAL first, then false
alerts on normal ECGs, then unreadable handling.

  .venv/bin/python run_eval.py images/readings_<run>.jsonl --run <run>
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
TIERS = ["CRITICAL", "URGENT", "ABNORMAL", "NO_CRITICAL_PATTERN", "UNREADABLE", "ERROR"]
SEV = {"NO_CRITICAL_PATTERN": 0, "UNREADABLE": 1, "ABNORMAL": 2, "URGENT": 3, "CRITICAL": 4, "ERROR": -1}
STEMI_LIKE = {"INJAS", "INJAL", "INJIN", "INJLA", "INJIL", "STE_"}


def pct(n: int, d: int) -> str:
    return f"{n}/{d} ({100 * n / d:.0f}%)" if d else "—"


def load(manifest: Path, jsonl: Path):
    man = {r["id"]: r for r in csv.DictReader(open(manifest))}
    rows = []
    for line in open(jsonl):
        if not line.strip():
            continue
        j = json.loads(line)
        rid, variant = j["image"].rsplit(".", 1)[0].rsplit("_", 1)
        m = man.get(rid)
        if not m:
            continue
        got = "ERROR" if j.get("error") else j["alert"]["tier"]
        rows.append({**m, "variant": variant, "got": got, "j": j})
    # keep the last result per image
    last = {}
    for r in rows:
        last[(r["id"], r["variant"])] = r
    return list(last.values())


def metrics(rows: list[dict]) -> list[str]:
    out = []
    by_var = defaultdict(list)
    for r in rows:
        by_var[r["variant"]].append(r)
    for variant in sorted(by_var):
        rs = by_var[variant]
        out.append(f"\n### Variant: `{variant}` ({len(rs)} images)\n")
        crit = [r for r in rs if r["expected"] == "CRITICAL"]
        out.append("**1. CRITICAL sensitivity** (expected CRITICAL → got CRITICAL)\n")
        out.append(f"- All critical: {pct(sum(r['got'] == 'CRITICAL' for r in crit), len(crit))}")
        heart_block = [r for r in crit if "3AVB" in r["codes"]]
        stemi = [r for r in crit if any(c.split(':')[0] in STEMI_LIKE for c in r["codes"].split(';'))]
        acute_mi = [r for r in crit if r["stadium"] == "Stadium I"]
        out.append(f"- Complete heart block (3AVB): {pct(sum(r['got'] == 'CRITICAL' for r in heart_block), len(heart_block))}")
        out.append(f"- ST-elevation injury (INJ*/STE_): {pct(sum(r['got'] == 'CRITICAL' for r in stemi), len(stemi))}")
        out.append(f"- Acute MI (Stadium I): {pct(sum(r['got'] == 'CRITICAL' for r in acute_mi), len(acute_mi))}")
        out.append(f"- Critical read as at least URGENT: {pct(sum(SEV[r['got']] >= 3 for r in crit), len(crit))}")
        missed = [r for r in crit if SEV[r["got"]] < 3]
        if missed:
            out.append(f"- **Missed (below URGENT):** " + ", ".join(f"{r['id']} → {r['got']}" for r in missed))

        norm = [r for r in rs if r["expected"] == "NO_CRITICAL_PATTERN"]
        out.append("\n**2. False alerts on normal ECGs**\n")
        out.append(f"- Normal → URGENT/CRITICAL (false alarm): {pct(sum(SEV[r['got']] >= 3 for r in norm), len(norm))}")
        out.append(f"- Normal → ABNORMAL (over-call): {pct(sum(r['got'] == 'ABNORMAL' for r in norm), len(norm))}")
        out.append(f"- Normal → NO CRITICAL PATTERN (correct): {pct(sum(r['got'] == 'NO_CRITICAL_PATTERN' for r in norm), len(norm))}")

        out.append("\n**3. Readability and errors**\n")
        out.append(f"- UNREADABLE: {pct(sum(r['got'] == 'UNREADABLE' for r in rs), len(rs))}")
        out.append(f"- ERROR (no reading): {pct(sum(r['got'] == 'ERROR' for r in rs), len(rs))}")
        ms = [r["j"].get("ms", 0) for r in rs if r["got"] != "ERROR"]
        if ms:
            out.append(f"- Time per reading: median {statistics.median(ms) / 1000:.1f} s, max {max(ms) / 1000:.1f} s")

        out.append("\n**4. At least the expected tier**\n")
        for exp in ["CRITICAL", "URGENT", "ABNORMAL"]:
            g = [r for r in rs if r["expected"] == exp]
            out.append(f"- {exp}: {pct(sum(SEV[r['got']] >= SEV[exp] for r in g), len(g))}")

        out.append("\n**Confusion (rows = expected from PTB-XL labels, columns = app tier)**\n")
        cols = [t for t in TIERS if any(r["got"] == t for r in rs)]
        out.append("| expected | " + " | ".join(cols) + " |")
        out.append("|---|" + "---|" * len(cols))
        for exp in ["CRITICAL", "URGENT", "ABNORMAL", "NO_CRITICAL_PATTERN"]:
            c = Counter(r["got"] for r in rs if r["expected"] == exp)
            out.append(f"| {exp} | " + " | ".join(str(c.get(t, 0)) for t in cols) + " |")
    return out


def review_html(rows: list[dict], path: Path, run: str):
    order = {"CRITICAL": 0, "URGENT": 1, "ABNORMAL": 2, "NO_CRITICAL_PATTERN": 3}
    rows = sorted(rows, key=lambda r: (order.get(r["expected"], 9), r["id"], r["variant"]))
    colour = {"CRITICAL": "#c62828", "URGENT": "#ef6c00", "ABNORMAL": "#b8860b", "NO_CRITICAL_PATTERN": "#546e7a", "UNREADABLE": "#757575", "ERROR": "#000"}
    parts = [f"""<!doctype html><meta charset=utf-8><title>Phase 0 review {run}</title>
<style>body{{font:14px system-ui;margin:16px;background:#fafafa}}.c{{background:#fff;border:1px solid #ddd;border-radius:8px;margin:12px 0;padding:12px}}
img{{width:100%;max-width:1100px;cursor:zoom-in}}.t{{display:inline-block;color:#fff;padding:2px 8px;border-radius:4px;font-weight:600}}
.miss{{border:3px solid #c62828}}td{{vertical-align:top;padding:2px 8px}}code{{font-size:12px}}</style>
<h1>Phase 0 review — {html.escape(run)}</h1>
<p>Each card: rendered PTB-XL ECG, PTB-XL cardiologist labels and report, the model's reading, and the tier from the rules engine.
Cards with a red border are expected CRITICAL but scored below URGENT. Click an image to open it full size.</p>"""]
    for r in rows:
        j = r["j"]
        miss = r["expected"] == "CRITICAL" and SEV[r["got"]] < 3
        parts.append(f"<div class='c{' miss' if miss else ''}'><b>{r['id']}</b> · {r['variant']} · age {r['age']} {r['sex']} · "
                     f"expected <span class=t style='background:{colour.get(r['expected'])}'>{r['expected']}</span> → "
                     f"app <span class=t style='background:{colour.get(r['got'])}'>{r['got']}</span>")
        img = f"{r['id']}_{r['variant']}.jpg"
        parts.append(f"<br><a href='{img}' target=_blank><img src='{img}' loading=lazy></a>")
        parts.append(f"<table><tr><td><b>PTB-XL labels</b></td><td><code>{html.escape(r['codes'])}</code> {html.escape(r['stadium'])}</td></tr>"
                     f"<tr><td><b>PTB-XL report</b></td><td>{html.escape(r['report'])}</td></tr>")
        if j.get("error"):
            parts.append(f"<tr><td><b>Error</b></td><td>{html.escape(j['error'])}</td></tr>")
        else:
            rd = j["reading"]
            iv = rd["intervals"]
            parts.append(
                f"<tr><td><b>Model</b></td><td>rate {rd['rate_bpm']['value']} · {html.escape(rd['rhythm']['label'])} · "
                f"PR {iv['pr_ms']} QRS {iv['qrs_ms']} QTc {iv['qtc_ms']} · axis {rd['axis']['label']} · quality {rd['image_quality']['confidence']:.2f} "
                f"{html.escape(', '.join(rd['image_quality']['issues']))}</td></tr>")
            fs = "<br>".join(f"{html.escape(f['name'])} <code>{f['code']}</code> [{', '.join(f['leads'])}] {f['confidence']:.2f}" for f in rd["findings"]) or "—"
            parts.append(f"<tr><td><b>Findings</b></td><td>{fs}</td></tr>")
            rs = "<br>".join(f"{a['tier']}: {html.escape(a['text'])}" for a in j["alert"]["reasons"]) or "—"
            parts.append(f"<tr><td><b>Tier reasons</b></td><td>{rs}</td></tr>")
            parts.append(f"<tr><td><b>Notes</b></td><td>{html.escape(rd['model_notes'])}</td></tr>")
        parts.append("</table></div>")
    path.write_text("\n".join(parts))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl", type=Path)
    ap.add_argument("--manifest", type=Path, default=HERE / "images" / "manifest.csv")
    ap.add_argument("--run", default=date.today().isoformat())
    a = ap.parse_args()
    rows = load(a.manifest, a.jsonl)
    if not rows:
        print("no matching results", file=sys.stderr)
        return 1
    models = Counter(r["j"].get("model") for r in rows)
    prompts = Counter(r["j"].get("promptVersion") for r in rows if r["j"].get("promptVersion"))
    md = [f"# Phase 0 results — {a.run}", "",
          f"- Images scored: {len(rows)}  (records: {len({r['id'] for r in rows})})",
          f"- Model(s): {', '.join(f'{k} ×{v}' for k, v in models.items())}",
          f"- Prompt version(s): {', '.join(prompts)}",
          "- Source: PTB-XL 1.0.3 (PhysioNet, CC-BY 4.0), rendered as paper ECGs (`render_ptbxl_to_images.py`).",
          "- Expected tiers come from PTB-XL labels mapped in `render_ptbxl_to_images.py` and are themselves a proposal for Homi to review.",
          "- **Not covered by PTB-XL:** VT/VF, asystole, hyperkalaemia, Brugada, torsades. These need other sources before the CRITICAL list is signed off.",
          ""]
    md += metrics(rows)
    (HERE / "results").mkdir(exist_ok=True)
    out = HERE / "results" / f"phase0_{a.run}.md"
    out.write_text("\n".join(md) + "\n")
    review = a.manifest.parent / f"review_{a.run}.html"
    review_html(rows, review, a.run)
    print("\n".join(md))
    print(f"\nreport: {out}\nreview page: {review}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
