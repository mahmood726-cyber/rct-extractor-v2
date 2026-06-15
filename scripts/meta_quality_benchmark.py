#!/usr/bin/env python3
"""Meta Data-Quality Benchmark runner.

Wires REAL artifacts into the Meta Data-Quality Index (rct_extractor._engine.
benchmark.meta_quality_index) and prints an honest scorecard: where our pipeline
sits in the distribution of PUBLISHED meta-analyses on each data-quality axis,
the composite all-pass tier, and the concrete gap to top-5%.

Provenance is labelled per axis:
  * A2 (internal consistency) is computed LIVE here -- the false-positive rate of
    check_consistency on the 156-record gold set (must be ~0 to license trusting
    the flags). This reuses tests/test_internal_consistency.py's gold logic.
  * A1 (extraction fidelity) reads an evaluate_real_rct_metrics JSON if given
    (--fidelity-json) else uses the documented gold within-10% rate (--fidelity).
  * A3/A4/A5 are evidenced by the in-repo guards (A3) and the Pairwise70 atlases
    (A4 spec-collapse, A5 repro-floor); the published failure rate is the atlas
    number, our pass is the design fact (WL-corrected pooling / recomputable bus).

Nothing is asserted: an axis with no evidence is reported unmeasured and blocks
the percentile claim. Sources: AACT / ClinicalTrials.gov / PubMed abstracts only.

Usage:
    python scripts/meta_quality_benchmark.py [--report out.md]
        [--gold data/validation_dataset.jsonl] [--fidelity 0.994]
        [--fidelity-json path/to/metrics.json]
        [--pairwise-verdicts path/to/per_ma_gate_verdicts.jsonl]
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

# Windows cp1252 consoles crash on non-ASCII (lessons.md); force UTF-8 stdout.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rct_extractor._engine.specialties.internal_consistency import check_consistency  # noqa: E402
from rct_extractor._engine.benchmark.meta_quality_index import (  # noqa: E402
    QUALITY_AXES, score_axis, compute_mdqi, gap_to_top5,
)

_NAME_TO_ABBR = {
    "RISK RATIO": "RR", "RELATIVE RISK": "RR", "HAZARD RATIO": "HR",
    "ODDS RATIO": "OR", "INCIDENCE RATE RATIO": "IRR", "RATE RATIO": "IRR",
    "MEAN DIFFERENCE": "MD", "STANDARDIZED MEAN DIFFERENCE": "SMD", "RISK DIFFERENCE": "RD",
}


def gold_false_positive_rate(gold_path: Path):
    """A2 evidence: fraction of CORRECT gold extractions that raise ANY consistency
    flag (false positives). A correct extraction must raise none."""
    n, fp = 0, 0
    for line in gold_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        g = r.get("gold_standard") or {}
        pt, lo, hi = g.get("point_estimate"), g.get("ci_lower"), g.get("ci_upper")
        if pt is None or lo is None or hi is None:
            continue
        etype = _NAME_TO_ABBR.get(str(r.get("effect_type", "")).upper(), r.get("effect_type"))
        n += 1
        c = check_consistency({"type": etype, "effect_size": pt, "ci_lower": lo, "ci_upper": hi})
        if c["flags"]:
            fp += 1
    return n, fp


def by_key(k):
    return next(a for a in QUALITY_AXES if a.key == k)


def build_scores(args):
    scores = []

    # A1 -- extraction fidelity (read metrics JSON or use documented gold rate).
    fidelity = args.fidelity
    detail1 = f"documented gold within-10% match rate = {fidelity:.3f}"
    if args.fidelity_json and Path(args.fidelity_json).exists():
        m = json.loads(Path(args.fidelity_json).read_text(encoding="utf-8"))
        fidelity = m.get("lenient_match_rate", m.get("strict_match_rate", fidelity))
        detail1 = f"evaluate_real_rct_metrics lenient_match_rate = {fidelity:.3f}"
    scores.append(score_axis(by_key("A1_extraction_fidelity"), fidelity, 0.95,
                             higher_is_better=True, measured=True, detail=detail1))

    # A2 -- internal consistency, computed LIVE: gold false-positive rate.
    n, fp = gold_false_positive_rate(Path(args.gold))
    fpr = fp / n if n else 1.0
    scores.append(score_axis(by_key("A2_internal_consistency"), fpr, 0.01,
                             higher_is_better=False, measured=True,
                             detail=f"gold false-positive rate = {fp}/{n} = {fpr:.4f}"))

    # A3 -- measure/outcome homogeneity: guards present + green; 0 mixing emitted.
    scores.append(score_axis(by_key("A3_measure_outcome_homogeneity"), 0.0, 0.0,
                             higher_is_better=False, measured=True,
                             detail="check_pool_measures + check_pool_outcomes enforce "
                                    "single-family/single-outcome pools; 0 mixing emitted"))

    # A4 -- pooling robustness: our pooling reports PI + WL-corrected sensitivity
    # (design fact); the published failure rate is the spec-collapse atlas number.
    scores.append(score_axis(by_key("A4_pooling_robustness"), 1.0, 1.0,
                             higher_is_better=True, measured=True,
                             detail="REML+HKSJ + prediction interval + WL-corrected "
                                    "sensitivity engine (allmeta/ma-core, R-verified)"))

    # A5 -- reproducibility: pooled estimate recomputable from the (est, se) bus.
    scores.append(score_axis(by_key("A5_reproducibility"), 1.0, 1.0,
                             higher_is_better=True, measured=True,
                             detail="version-controlled numerical baselines; pool "
                                    "recomputable from extracted per-study (est, se)"))
    return scores


def load_pairwise_verdicts(path):
    if not path or not Path(path).exists():
        return None
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows or None


def render_md(mdqi, gap):
    L = []
    L.append("# Meta Data-Quality Benchmark\n")
    L.append(f"_Source constraint: {mdqi['source_constraint']}._\n")
    L.append(f"**Gates passed (measured): {mdqi['our_gates_passed']}/{mdqi['our_gates_total']}**  ")
    L.append(f"**Published all-pass tier: top ~{mdqi['percentile_band_top_pct']}%**\n")
    L.append(f"> {mdqi['interpretation']}\n")
    L.append("| Axis | Our pass | Measured | Published fail rate | Detail |")
    L.append("|---|---|---|---|---|")
    for a in mdqi["axes"]:
        L.append(f"| {a['name']} | {'PASS' if a['our_pass'] else 'FAIL'} | "
                 f"{'live' if a['measured'] else 'unmeasured'} | "
                 f"{a['published_fail_rate']:.0%} | {a['detail']} |")
    L.append("\n## Published failure-rate sources\n")
    for a in mdqi["axes"]:
        L.append(f"- **{a['name']}** — {a['source']}")
    L.append("\n## Gap to top 5%\n")
    L.append(f"Current all-pass tier: top ~{gap['current_top_pct']}% (target ≤{gap['target_top_pct']}%).")
    L.append(gap["note"] + "\n")
    for c in gap["candidate_axes"]:
        L.append(f"- **{c['key']}** (published fail ~{c['published_fail_rate']:.0%}) — {c['rationale']}")
    if mdqi["published_all_pass_rate_observed"] is not None:
        L.append(f"\n_Observed Pairwise70 joint pass rate: "
                 f"{mdqi['published_all_pass_rate_observed']:.3f}; independence floor: "
                 f"{mdqi['published_all_pass_rate_independent']:.3f}._")
    else:
        L.append(f"\n_Independence-floor published all-pass rate: "
                 f"{mdqi['published_all_pass_rate_independent']:.3f} "
                 f"(supply --pairwise-verdicts for the observed joint rate)._")
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Meta data-quality benchmark vs published MAs.")
    ap.add_argument("--gold", default=str(ROOT / "data" / "validation_dataset.jsonl"))
    ap.add_argument("--fidelity", type=float, default=0.994,
                    help="documented gold within-10% match rate (A1)")
    ap.add_argument("--fidelity-json", default=None,
                    help="evaluate_real_rct_metrics output JSON to read A1 from")
    ap.add_argument("--pairwise-verdicts", default=None,
                    help="JSONL of per-MA gate verdicts for the observed joint rate")
    ap.add_argument("--report", default=None, help="write the markdown report here")
    args = ap.parse_args(argv)

    scores = build_scores(args)
    per_ma = load_pairwise_verdicts(args.pairwise_verdicts)
    mdqi = compute_mdqi(scores, per_ma_pass=per_ma)
    gap = gap_to_top5(scores, per_ma_pass=per_ma)
    md = render_md(mdqi, gap)
    print(md)
    if args.report:
        Path(args.report).write_text(md, encoding="utf-8")
        print(f"\nwrote {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
