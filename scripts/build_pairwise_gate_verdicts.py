#!/usr/bin/env python3
"""Emit per-MA data-quality GATE verdicts for the Pairwise70 corpus, so the
meta-quality benchmark can use the REAL published-MA distribution instead of the
literature independence floor.

Currently sources the A4 (pooling-robustness) gate from spec-collapse-atlas'
per-MA results (473 Cochrane MAs): a review PASSES A4 iff it is NOT false-robust
(its naive-IV-RE robustness claim survives the weighted-likelihood correction).
Extend with A5 (repro-floor) / A2 (consistency over raw counts) when those atlases
expose per-MA verdicts keyed by review_id.

Output: JSONL, one row per MA: {"review_id": ..., "A4_pooling_robustness": bool}.
Feed to: python scripts/meta_quality_benchmark.py --pairwise-verdicts <out>

Usage:
    python scripts/build_pairwise_gate_verdicts.py \
        [--spec-collapse C:/Projects/spec-collapse-atlas/data/corpus_results.json] \
        [-o data/pairwise_gate_verdicts.jsonl]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SPEC = Path("C:/Projects/spec-collapse-atlas/data/corpus_results.json")


def build(spec_path: Path):
    rows = json.loads(spec_path.read_text(encoding="utf-8"))
    out = []
    n_false_robust = 0
    for r in rows:
        rid = r.get("review_id")
        if not rid:
            continue
        false_robust = bool(r.get("false_robust"))
        n_false_robust += int(false_robust)
        # A4 passes when the MA is NOT falsely robust (claim survives correction,
        # or was never claimed robust).
        out.append({"review_id": rid, "A4_pooling_robustness": not false_robust})
    return out, n_false_robust


def main(argv=None):
    ap = argparse.ArgumentParser(description="Per-MA gate verdicts from the Pairwise70 atlases.")
    ap.add_argument("--spec-collapse", default=str(DEFAULT_SPEC))
    ap.add_argument("-o", "--output", default=str(ROOT / "data" / "pairwise_gate_verdicts.jsonl"))
    args = ap.parse_args(argv)

    spec = Path(args.spec_collapse)
    if not spec.exists():
        raise SystemExit(f"spec-collapse results not found: {spec}\n"
                         f"(point --spec-collapse at corpus_results.json)")
    rows, n_fr = build(spec)
    Path(args.output).write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    a4_pass = sum(1 for r in rows if r["A4_pooling_robustness"])
    print(f"wrote {len(rows)} per-MA gate verdicts to {args.output}")
    print(f"A4 (pooling robustness): {a4_pass}/{len(rows)} pass "
          f"({a4_pass/len(rows):.1%}); {n_fr} false-robust "
          f"({n_fr/len(rows):.1%}) -- the real corpus marginal for A4.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
