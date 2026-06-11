#!/usr/bin/env python
"""Aggregate the re-verification eval JSON into a per-specialty pdf_raw table.

Reads the merged eval_results JSON produced by run_pdf_eval.py over the
re-acquired reverify gold, and emits:
  * per-specialty: papers, in-scope gold tuples, correct, point_only, missed,
    out-of-scope count, and pdf_raw correct%.
  * how many of the 30 reach >=95% on pdf_raw.
  * a JSON sidecar + a Markdown report (docs/PDF_REVERIFY_30.md).

`correct` = right effect type AND point AND both CI bounds, all within tolerance
(the same definition run_pdf_eval/generate_report use). The gate is correct/gold.
"""
from __future__ import annotations
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

NEW30 = [
    "prostate_cancer", "ovarian_cancer", "pancreatic_cancer", "gastric_cancer",
    "hepatocellular_carcinoma", "melanoma", "leukaemia", "lymphoma",
    "head_neck_cancer", "bladder_cancer", "renal_cell_carcinoma",
    "oesophageal_cancer", "dyslipidaemia", "venous_thromboembolism",
    "peripheral_artery_disease", "obesity", "thyroid", "osteoporosis",
    "kidney_transplant", "pulmonary_hypertension", "pcos", "parkinsons",
    "alzheimers", "multiple_sclerosis", "migraine", "schizophrenia",
    "cirrhosis", "osteoarthritis", "covid19", "sepsis",
]

SURFACE = "pdf_raw"


def agg(papers):
    b = defaultdict(lambda: {"papers": 0, "n_gold": 0, "correct": 0,
                             "point_only": 0, "missed": 0, "oos": 0})
    for p in papers:
        sp = p["specialty"]
        d = b[sp]
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
    eval_path = REPO / (sys.argv[1] if len(sys.argv) > 1
                        else "data/pdf_eval/reverify/eval_all30.json")
    data = json.loads(eval_path.read_text("utf-8"))
    papers = data["papers"]
    b = agg(papers)

    rows = []
    n_hit = 0
    tot_gold = tot_correct = 0
    for sp in NEW30:
        d = b.get(sp)
        if not d or d["n_gold"] == 0:
            rows.append((sp, 0, 0, 0, 0, 0, 0, None))
            continue
        rate = d["correct"] / d["n_gold"]
        if rate >= 0.95:
            n_hit += 1
        tot_gold += d["n_gold"]
        tot_correct += d["correct"]
        rows.append((sp, d["papers"], d["n_gold"], d["correct"],
                     d["point_only"], d["missed"], d["oos"], rate))

    overall = tot_correct / tot_gold if tot_gold else 0.0

    # ---- console ----
    print(f"{'specialty':28s} {'papers':>6} {'gold':>5} {'correct':>8} "
          f"{'point':>6} {'miss':>5} {'oos':>4} {'pdf_raw%':>9}")
    for (sp, pap, ng, c, po, mi, oos, rate) in rows:
        rstr = f"{rate*100:.1f}%" if rate is not None else "NO DATA"
        flag = "" if (rate is not None and rate >= 0.95) else "  <-- BELOW 95%"
        print(f"{sp:28s} {pap:6d} {ng:5d} {c:8d} {po:6d} {mi:5d} {oos:4d} "
              f"{rstr:>9}{flag}")
    print(f"\n>=95% on pdf_raw: {n_hit}/30")
    print(f"overall pdf_raw correct: {tot_correct}/{tot_gold} = {overall*100:.2f}%")

    out = REPO / "data/pdf_eval/reverify/reverify_summary.json"
    out.write_text(json.dumps({
        "surface": SURFACE,
        "n_hit_95": n_hit, "n_total": 30,
        "overall_correct": tot_correct, "overall_gold": tot_gold,
        "overall_rate": overall,
        "rows": [{"specialty": r[0], "papers": r[1], "gold": r[2],
                  "correct": r[3], "point_only": r[4], "missed": r[5],
                  "out_of_scope": r[6],
                  "pdf_raw_rate": r[7]} for r in rows],
    }, indent=2), "utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
