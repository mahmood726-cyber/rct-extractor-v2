#!/usr/bin/env python3
"""Score the two fields that decide whether a pooled estimate is correct:

  1. TOP-1 / primary-outcome selection -- does the extractor's chosen primary
     effect (``best_match``) match the Cochrane reference effect for the study's
     primary outcome, in value?
  2. DIRECTION -- does that effect point the same way (relative to the null) as
     the Cochrane reference? A disagreement here is a SIGN FLIP: the single worst
     error a meta-analysis feed can commit (benefit reported as harm).

The Cochrane value (``cochrane_effect``, from the published review) is the
authoritative truth; the extractor is scored against it. This is the measurement
the headline recall number never captured (audit gap 35): recall asks "did we
find *some* stated effect?"; this asks "did we pick the *right* one, pointing the
*right* way?".

Usage:
    python scripts/score_primary_direction.py \
        --results gold_data/baseline_results.json \
        --gold gold_data/gold_v2.jsonl \
        --output output/primary_direction_scorecard.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rct_extractor.api import effect_direction, _RATIO_TYPES, _DIFF_TYPES  # noqa: E402


def _extractor_kind(effect_type: Optional[str]) -> Optional[str]:
    et = str(effect_type or "").upper()
    if et in _RATIO_TYPES:
        return "ratio"
    if et in _DIFF_TYPES:
        return "diff"
    return None


def _cochrane_kind(cochrane_effect: Optional[float], outcome_type: str) -> Optional[str]:
    """ratio vs difference for the Cochrane value. A non-positive value CANNOT be a
    ratio (ratios are always > 0), so it is a difference regardless of the (sometimes
    wrong) outcome-type label; otherwise trust the label."""
    if cochrane_effect is None:
        return None
    if cochrane_effect <= 0:
        return "diff"
    return "diff" if outcome_type == "continuous" else "ratio"


def _load_outcome_types(gold_path: Optional[Path]) -> Dict[str, str]:
    """study_id -> 'binary' | 'continuous', from the gold jsonl (best effort)."""
    types: Dict[str, str] = {}
    if not gold_path or not gold_path.exists():
        return types
    for line in gold_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        sid = rec.get("study_id")
        if not sid:
            continue
        ot = str(rec.get("cochrane_outcome_type") or "").lower()
        if ot in ("binary", "continuous"):
            types[sid] = ot
        else:
            exp = str(rec.get("expected_effect_type") or "").upper()
            types[sid] = "continuous" if exp in ("MD", "SMD", "WMD") else "binary"
    return types


# Ratios within +-5% of 1 (|log| < log(1.05)) are treated as directionally NULL for
# SCORING: a reference that close to the null cannot confidently establish a side to
# "flip" against. Differences use an exact-0 null only (their scale/units are unknown,
# so no relative band can be applied safely). This down-weights borderline cases; it
# does NOT touch the strict geometric `direction` field the API emits.
_RATIO_NULL_LOG = math.log(1.05)


def _scoring_direction(value: Optional[float], kind: Optional[str]) -> Optional[str]:
    if value is None or kind is None:
        return None
    if kind == "ratio":
        if value <= 0:
            return None
        if abs(math.log(value)) < _RATIO_NULL_LOG:
            return "null"
        return "increase" if value > 1.0 else "decrease"
    # diff
    if value > 0:
        return "increase"
    if value < 0:
        return "decrease"
    return "null"


def _value_matches(ext: float, coch: float, is_diff: bool,
                   ratio_log_tol: float = math.log(1.25),
                   diff_rel_tol: float = 0.25, diff_abs_floor: float = 0.1) -> bool:
    """Is the extractor's primary value close enough to the Cochrane value?
    Ratios compared on the log scale (within +-25%); differences within 25%
    (relative) with a small absolute floor so near-zero references are fair."""
    if is_diff:
        return abs(ext - coch) <= max(diff_rel_tol * abs(coch), diff_abs_floor)
    if ext <= 0 or coch <= 0:
        return False
    return abs(math.log(ext) - math.log(coch)) <= ratio_log_tol


def score_record(rec: Dict[str, Any], outcome_types: Dict[str, str]) -> Dict[str, Any]:
    """Score one study. Returns per-study verdict fields."""
    sid = rec.get("study_id")
    outcome_type = outcome_types.get(sid, "binary")
    coch = rec.get("cochrane_effect")
    best = rec.get("best_match") or {}
    ext_val = best.get("effect_size")
    ext_type = best.get("type")

    coch_kind = _cochrane_kind(coch, outcome_type)
    ext_kind = _extractor_kind(ext_type) if ext_val is not None else None
    coch_dir = _scoring_direction(coch, coch_kind)
    ext_dir = _scoring_direction(ext_val, ext_kind) if ext_val is not None else None

    if ext_val is None or not best:
        selection = "no_extraction"
    elif coch is None:
        selection = "no_reference"
    elif coch_kind and ext_kind and coch_kind != ext_kind:
        # The extractor picked a different KIND of effect than the review's primary
        # (e.g. an OR where the outcome is a continuous mean difference). The primary
        # is mis-selected; a value comparison would be meaningless.
        selection = "measure_mismatch"
    else:
        selection = "value_match" if _value_matches(ext_val, coch, coch_kind == "diff") else "value_mismatch"

    # Direction is only comparable when both sides are the SAME kind of measure.
    if selection == "measure_mismatch":
        direction = "measure_mismatch"
    elif coch_dir is None or ext_dir is None:
        direction = "undetermined"
    elif coch_dir == ext_dir:
        direction = "agree"
    elif "null" in (coch_dir, ext_dir):
        direction = "null_boundary"   # one side is exactly at the null
    else:
        direction = "sign_flip"

    return {
        "study_id": sid, "outcome_type": outcome_type,
        "cochrane_effect": coch, "cochrane_kind": coch_kind, "cochrane_direction": coch_dir,
        "extractor_type": ext_type, "extractor_value": ext_val,
        "extractor_kind": ext_kind, "extractor_direction": ext_dir,
        "selection": selection, "direction": direction,
    }


def summarize(scored: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(scored)
    sel = {k: 0 for k in ("value_match", "value_mismatch", "measure_mismatch",
                          "no_extraction", "no_reference")}
    dirn = {k: 0 for k in ("agree", "sign_flip", "null_boundary",
                           "measure_mismatch", "undetermined")}
    for s in scored:
        sel[s["selection"]] = sel.get(s["selection"], 0) + 1
        dirn[s["direction"]] = dirn.get(s["direction"], 0) + 1
    # Direction accuracy is measured only where BOTH sides are the SAME kind of
    # measure with a determinable, non-null direction -- the honest denominator for
    # a true sign flip (opposite direction of the same measure). Measure mismatches
    # are a separate selection failure, not a sign flip.
    determinable = dirn["agree"] + dirn["sign_flip"]
    return {
        "n_studies": n,
        "selection": sel,
        "top1_value_match_rate": (sel["value_match"] / n) if n else None,
        "direction": dirn,
        "direction_determinable": determinable,
        "direction_accuracy": (dirn["agree"] / determinable) if determinable else None,
        "sign_flip_rate": (dirn["sign_flip"] / determinable) if determinable else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results", type=Path, default=Path("gold_data/baseline_results.json"))
    parser.add_argument("--gold", type=Path, default=Path("gold_data/gold_v2.jsonl"))
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    if not args.results.exists():
        print(f"ERROR: results file not found: {args.results}", file=sys.stderr)
        return 1
    results = json.loads(args.results.read_text(encoding="utf-8"))
    if isinstance(results, dict):
        results = list(results.values())

    gold_path = args.gold if args.gold and args.gold.exists() else None
    if gold_path is None:
        for cand in (Path("data/frozen_eval_v1/frozen_gold.jsonl"), Path("gold_data/gold_50.jsonl")):
            if cand.exists():
                gold_path = cand
                break
    outcome_types = _load_outcome_types(gold_path)

    scored = [score_record(r, outcome_types) for r in results]
    summary = summarize(scored)

    def pct(x: Optional[float]) -> str:
        return f"{x*100:.1f}%" if x is not None else "n/a"

    print("=" * 66)
    print("PRIMARY-OUTCOME + DIRECTION SCORECARD")
    print(f"  results: {args.results}   gold: {gold_path or '(none)'}")
    print("=" * 66)
    print(f"Studies scored:            {summary['n_studies']}")
    print(f"Top-1 value match:         {summary['selection']['value_match']}"
          f"  ({pct(summary['top1_value_match_rate'])})")
    print(f"  value mismatch:          {summary['selection']['value_mismatch']}")
    print(f"  measure mismatch:        {summary['selection']['measure_mismatch']}  (wrong KIND of effect)")
    print(f"  no extraction:           {summary['selection']['no_extraction']}")
    print(f"  no reference:            {summary['selection']['no_reference']}")
    print("-" * 66)
    print(f"Direction determinable in: {summary['direction_determinable']} studies (same-measure)")
    print(f"  direction agree:         {summary['direction']['agree']}")
    print(f"  SIGN FLIP:               {summary['direction']['sign_flip']}"
          f"  ({pct(summary['sign_flip_rate'])} of determinable)")
    print(f"  null boundary:           {summary['direction']['null_boundary']}")
    print(f"  measure mismatch:        {summary['direction']['measure_mismatch']}")
    print(f"  undetermined:            {summary['direction']['undetermined']}")
    print(f"Direction accuracy:        {pct(summary['direction_accuracy'])}  (same-measure only)")
    print("=" * 66)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps({"summary": summary, "per_study": scored}, indent=2), encoding="utf-8"
        )
        print(f"Wrote {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
