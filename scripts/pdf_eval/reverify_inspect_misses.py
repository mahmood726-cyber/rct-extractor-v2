#!/usr/bin/env python
"""Dump missed / point_only gold tuples for a specialty (pdf_raw surface) so the
re-verifier can classify each: genuine pattern gap vs by-design non-RCT decline
vs PDF-layer artifact. Reads the merged eval JSON."""
from __future__ import annotations
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def main():
    sp = sys.argv[1]
    eval_path = REPO / (sys.argv[2] if len(sys.argv) > 2
                        else "data/pdf_eval/reverify/eval_all30.json")
    data = json.loads(eval_path.read_text("utf-8"))
    for p in data["papers"]:
        if p["specialty"] != sp:
            continue
        surf = p["surfaces"]["pdf_raw"]
        bad = [g for g in surf["per_gold"] if g["status"] != "correct"]
        if not bad:
            continue
        meta = p["pdf_meta"]
        print(f"\n=== {p['pmcid']} (pdf={meta.get('method')}, "
              f"chars={meta.get('chars')}, extracted={surf['n_extracted']}) ===")
        for g in bad:
            gg = g["gold"]
            print(f"  [{g['status']}] {gg['effect_type']} {gg['point_estimate']} "
                  f"({gg['ci_lower']}-{gg['ci_upper']})")
            print(f"     quote: {gg.get('quote_context','')[:200]}")
            if g.get("matched_extracted"):
                e = g["matched_extracted"]
                print(f"     matched-extracted: {e.get('type')} {e.get('point')} "
                      f"({e.get('ci_lower')}-{e.get('ci_upper')}) :: "
                      f"{(e.get('source_text') or '')[:120]}")


if __name__ == "__main__":
    main()
