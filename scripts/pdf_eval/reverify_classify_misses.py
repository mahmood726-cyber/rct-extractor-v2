#!/usr/bin/env python
"""Classify every pdf_raw miss/point_only in the below-95% specialties by the
study design of its SOURCE PAPER (independent abstract markers), to separate:
  * by-design non-RCT decline  (paper is observational / meta-analysis / risk-
    factor regression -> the extractor correctly declines; gold over-included)
  * gold-harvest artifact       (European decimal, bootstrap-CI phrasing, the
    extractor matched a near-identical adjacent effect -> point_only)
  * genuine RCT pattern gap     (paper is a real RCT and the extractor missed a
    real arm-comparison effect)
This does NOT touch the extractor; it reads abstracts + the eval JSON only.
"""
from __future__ import annotations
import io, sys, json, glob, re
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
REPO = Path(__file__).resolve().parents[2]

BELOW = ["alzheimers", "pulmonary_hypertension", "cirrhosis",
         "kidney_transplant", "renal_cell_carcinoma"]

# abstract design markers
NONRCT = re.compile(
    r"retrospective|observational|cross-sectional|case[- ]control|real[- ]world|"
    r"registry|meta-analys|systematic review|pooled (?:odds|hazard|risk|estimate|analys)|"
    r"\bcohort\b|risk factor|predictor|multivariable|multivariate|"
    r"logistic regression|propensity|nationwide|claims database|electronic health",
    re.I)
RCT = re.compile(
    r"randomi[sz]ed (?:controlled )?trial|double[- ]blind|placebo[- ]controlled|"
    r"randomly (?:assigned|allocated)|1:1 allocation|open[- ]label.{0,30}randomi",
    re.I)


def load_abstracts():
    ab = {}
    for f in glob.glob(str(REPO / "data/pdf_eval/reverify/gold_*.jsonl")):
        for l in open(f, encoding="utf-8"):
            if not l.strip():
                continue
            r = json.loads(l)
            ab[r["pmcid"]] = r["abstract"]
    return ab


def design_of(abstract: str) -> str:
    nz = bool(NONRCT.search(abstract))
    rz = bool(RCT.search(abstract))
    if nz and not rz:
        return "non_rct"
    if nz and rz:
        return "mixed_or_MA"   # e.g. an MA that pools RCTs, or compares to RCTs
    if rz:
        return "rct"
    return "unclear"


def main():
    data = json.loads((REPO / "data/pdf_eval/reverify/eval_all30.json").read_text("utf-8"))
    ab = load_abstracts()
    by_sp = {}
    for p in data["papers"]:
        sp = p["specialty"]
        if sp not in BELOW:
            continue
        surf = p["surfaces"]["pdf_raw"]
        for g in surf["per_gold"]:
            if g["status"] == "correct":
                continue
            d = design_of(ab.get(p["pmcid"], ""))
            artifact = bool(g.get("matched_extracted"))  # point_only = near-match found
            bucket = ("artifact_or_pointmatch" if (artifact and d in ("rct", "unclear"))
                      else d)
            rec = by_sp.setdefault(sp, {})
            rec[bucket] = rec.get(bucket, 0) + 1
    print(f"{'specialty':26s} {'miss-buckets (by source-paper design)'}")
    grand = {}
    for sp in BELOW:
        b = by_sp.get(sp, {})
        for k, v in b.items():
            grand[k] = grand.get(k, 0) + v
        print(f"{sp:26s} {b}")
    print(f"\nTOTAL miss/point_only buckets across 5 below-95% specialties:\n  {grand}")


if __name__ == "__main__":
    main()
