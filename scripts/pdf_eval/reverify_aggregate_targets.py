#!/usr/bin/env python
"""Aggregate a re-verification eval JSON into a per-specialty pdf_raw table for an
ARBITRARY specialty set (generalises reverify_aggregate.py, which hardcoded the
NEW30). Specialties are taken from whatever appears in the eval JSON.

`correct` = right effect type AND point AND both CI bounds within tolerance
(identical definition to run_pdf_eval.py). Gate is correct / in-scope gold.

Usage:
  python scripts/pdf_eval/reverify_aggregate_targets.py <eval.json> [out_summary.json]
"""
from __future__ import annotations
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SURFACE = "pdf_raw"


def agg(papers):
    b = defaultdict(lambda: {"papers": 0, "n_gold": 0, "correct": 0,
                             "point_only": 0, "missed": 0, "oos": 0})
    for p in papers:
        d = b[p["specialty"]]
        d["papers"] += 1
        d["oos"] += p.get("n_out_of_scope", 0)
        surf = p["surfaces"].get(SURFACE)
        if not surf:
            continue
        for g in surf["per_gold"]:
            d["n_gold"] += 1
            d[g["status"]] += 1
    return b


def main():
    eval_path = REPO / sys.argv[1]
    out_path = REPO / (sys.argv[2] if len(sys.argv) > 2
                       else "data/pdf_eval/reverify/reverify_targets_summary.json")
    data = json.loads(eval_path.read_text("utf-8"))
    b = agg(data["papers"])
    specs = sorted(b.keys())

    rows, n_hit, tot_gold, tot_correct = [], 0, 0, 0
    print(f"{'specialty':30s} {'papers':>6} {'gold':>5} {'correct':>8} "
          f"{'point':>6} {'miss':>5} {'oos':>4} {'pdf_raw%':>9}")
    for sp in specs:
        d = b[sp]
        if d["n_gold"] == 0:
            print(f"{sp:30s} {d['papers']:6d} {0:5d} {'NO GOLD':>8}")
            rows.append({"specialty": sp, "papers": d["papers"], "gold": 0,
                         "correct": 0, "point_only": 0, "missed": 0,
                         "out_of_scope": d["oos"], "pdf_raw_rate": None})
            continue
        rate = d["correct"] / d["n_gold"]
        if rate >= 0.95:
            n_hit += 1
        tot_gold += d["n_gold"]
        tot_correct += d["correct"]
        flag = "" if rate >= 0.95 else "  <-- BELOW 95%"
        print(f"{sp:30s} {d['papers']:6d} {d['n_gold']:5d} {d['correct']:8d} "
              f"{d['point_only']:6d} {d['missed']:5d} {d['oos']:4d} "
              f"{rate*100:8.1f}%{flag}")
        rows.append({"specialty": sp, "papers": d["papers"], "gold": d["n_gold"],
                     "correct": d["correct"], "point_only": d["point_only"],
                     "missed": d["missed"], "out_of_scope": d["oos"],
                     "pdf_raw_rate": rate})

    overall = tot_correct / tot_gold if tot_gold else 0.0
    print(f"\n>=95% on pdf_raw: {n_hit}/{len([r for r in rows if r['gold']>0])}")
    print(f"overall pdf_raw correct: {tot_correct}/{tot_gold} = {overall*100:.2f}%")

    out_path.write_text(json.dumps({
        "surface": SURFACE, "n_hit_95": n_hit,
        "n_total": len([r for r in rows if r["gold"] > 0]),
        "overall_correct": tot_correct, "overall_gold": tot_gold,
        "overall_rate": overall, "rows": rows}, indent=2), "utf-8")
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
