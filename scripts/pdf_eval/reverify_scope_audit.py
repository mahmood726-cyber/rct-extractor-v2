#!/usr/bin/env python
"""Scope-exclusion audit + miss classification for an ARBITRARY eval JSON.

Two questions, both TRUTH-FIRST and independent of the extractor under test:

(A) MISS CLASSIFICATION. For every pdf_raw miss/point_only, classify the SOURCE
    PAPER design from its abstract markers (non_rct / mixed_or_MA / rct / unclear).
    A miss against a genuine-RCT paper is a real extractor pattern gap; a miss
    against an observational/MA paper is corpus contamination the gold harvester
    under-flagged, not an extractor fault.

(B) SCOPE-EXCLUSION STRESS TEST. The gold harvester FLAGS some tuples
    out_of_scope (non-RCT design markers) so they are not scored. This audits
    whether those exclusions are "doing too much work" to reach 95%:
      * as_is_rate      = correct / in_scope            (the reported gate)
      * stress_rate     = correct / (in_scope + oos)    (if NO tuple were excluded)
      * oos_on_rct      = # OOS tuples whose abstract is a genuine RCT self-id
                          with NO non-RCT marker  -> these would be WRONGLY excluded
    If as_is>=95% but stress<95% AND oos is large, the pass leans on exclusions;
    we then check oos_on_rct: if ~0, the excluded tuples really are non-RCT
    (legitimate), so the lean is benign; if >0, exclusions are over-aggressive.

Reads gold_<sp>.jsonl for abstracts (so OOS reasons + design re-derivable).

Usage:
  python scripts/pdf_eval/reverify_scope_audit.py <eval.json> <gold_glob> [out.json]
  e.g. ... eval_targets.json "data/pdf_eval/reverify/gold_*.jsonl"
"""
from __future__ import annotations
import io, sys, json, glob, re
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
REPO = Path(__file__).resolve().parents[2]

NONRCT = re.compile(
    r"retrospective|observational|cross-sectional|case[- ]control|real[- ]world|"
    r"registry|meta-analys|systematic review|pooled (?:odds|hazard|risk|estimate|analys)|"
    r"\bcohort\b|risk factor|predictor|multivariable|multivariate|"
    r"logistic regression|propensity|nationwide|claims database|electronic health|"
    r"mendelian randomi", re.I)
RCT = re.compile(
    r"randomi[sz]ed (?:controlled )?trial|double[- ]blind|placebo[- ]controlled|"
    r"randomly (?:assigned|allocated)|1:1 allocation|open[- ]label.{0,30}randomi|"
    r"\d+[- ]arm (?:trial|study)|were randomi[sz]ed to", re.I)


def design_of(abstract: str) -> str:
    nz, rz = bool(NONRCT.search(abstract)), bool(RCT.search(abstract))
    if nz and not rz:
        return "non_rct"
    if nz and rz:
        return "mixed_or_MA"
    if rz:
        return "rct"
    return "unclear"


def load_gold(gold_glob):
    """pmcid -> {abstract, gold_effects} from the gold jsonl files."""
    g = {}
    for f in glob.glob(str(REPO / gold_glob)):
        for l in open(f, encoding="utf-8"):
            if not l.strip():
                continue
            r = json.loads(l)
            g[r["pmcid"]] = r
    return g


def main():
    eval_path = REPO / sys.argv[1]
    gold_glob = sys.argv[2]
    out_path = REPO / (sys.argv[3] if len(sys.argv) > 3
                       else "data/pdf_eval/reverify/scope_audit.json")
    data = json.loads(eval_path.read_text("utf-8"))
    gold = load_gold(gold_glob)

    # (A) miss classification per specialty
    miss = {}
    # (B) scope stress per specialty
    scope = {}
    for p in data["papers"]:
        sp = p["specialty"]
        ab = gold.get(p["pmcid"], {}).get("abstract", "")
        surf = p["surfaces"].get("pdf_raw")
        s = scope.setdefault(sp, {"in_scope": 0, "correct": 0, "oos": 0,
                                  "oos_on_rct": 0, "oos_reasons": {}})
        if surf:
            for g in surf["per_gold"]:
                s["in_scope"] += 1
                if g["status"] == "correct":
                    s["correct"] += 1
                    continue
                d = design_of(ab)
                artifact = bool(g.get("matched_extracted"))
                bucket = ("artifact_or_pointmatch"
                          if (artifact and d in ("rct", "unclear")) else d)
                m = miss.setdefault(sp, {})
                m[bucket] = m.get(bucket, 0) + 1
        # out-of-scope tuples: re-derive design of their source paper
        for o in p.get("out_of_scope", []):
            s["oos"] += 1
            reason = (o.get("reason") or "?")
            s["oos_reasons"][reason] = s["oos_reasons"].get(reason, 0) + 1
            # genuine-RCT abstract with NO non-RCT marker => wrongly excluded
            if RCT.search(ab) and not NONRCT.search(ab):
                s["oos_on_rct"] += 1

    # report
    print("=== (A) MISS CLASSIFICATION (source-paper design of each miss) ===")
    for sp in sorted(miss):
        print(f"  {sp:30s} {miss[sp]}")
    if not miss:
        print("  (no misses anywhere)")

    print("\n=== (B) SCOPE-EXCLUSION STRESS TEST ===")
    print(f"{'specialty':30s} {'in_scope':>8} {'oos':>4} {'as_is%':>7} "
          f"{'stress%':>7} {'oos_on_rct':>10} {'lean'}")
    audit_rows = []
    for sp in sorted(scope):
        s = scope[sp]
        insc = s["in_scope"]
        if insc == 0:
            continue
        as_is = s["correct"] / insc
        stress = s["correct"] / (insc + s["oos"]) if (insc + s["oos"]) else 0
        # "lean" = pass relies on exclusions: passes as-is but fails stress
        leans = (as_is >= 0.95 > stress)
        flag = ""
        if leans and s["oos_on_rct"] > 0:
            flag = "OVER-AGGRESSIVE?"
        elif leans:
            flag = "leans-but-OOS-legit"
        print(f"{sp:30s} {insc:8d} {s['oos']:4d} {as_is*100:6.1f}% "
              f"{stress*100:6.1f}% {s['oos_on_rct']:10d}  {flag}")
        audit_rows.append({"specialty": sp, "in_scope": insc, "oos": s["oos"],
                           "as_is_rate": as_is, "stress_rate": stress,
                           "oos_on_rct": s["oos_on_rct"], "leans": leans,
                           "oos_reasons": s["oos_reasons"]})

    out_path.write_text(json.dumps({"miss_classification": miss,
                                    "scope_audit": audit_rows}, indent=2), "utf-8")
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
