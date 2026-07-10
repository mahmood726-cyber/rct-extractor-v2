#!/usr/bin/env python3
"""Generate a results file that scores the EXTRACTOR'S OWN primary pick.

The Phase-1 scorecard (score_primary_direction.py) was fed
gold_data/baseline_results.json, whose `best_match` is oracle-selected (the
extraction closest to the Cochrane value, from the raw core extractor, with no
`is_primary`). That measures a ceiling, not the extractor's selection.

This generator runs the PUBLIC api.extract on a text corpus and sets
`best_match = the effect with is_primary == True` (i.e. effects[0] after
order_effects) -- so the scorecard finally measures the SELECTION logic
(order_effects / is_primary / direction), not an oracle. It also keeps every
effect under `all_effects` so a downstream oracle-ceiling column can compare
"the pick we made" against "the best pick available".

Corpus format (JSONL, one study per line) -- text is required; the reference
fields are optional and only used by the scorer:
    {"study_id": "...", "text": "<abstract or body text>",
     "specialty": "auto|<name>",           # optional, default "auto"
     "cochrane_effect": 0.74,              # optional reference value
     "cochrane_raw": {...},                # optional per-study 2x2/summary
     "cochrane_outcome_type": "binary"}    # optional

Usage:
    python scripts/gen_api_extract_results.py \
        --corpus data/my_corpus.jsonl \
        --output output/api_extract_results.json
    python scripts/score_primary_direction.py \
        --results output/api_extract_results.json --gold <gold-with-cochrane_raw>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import rct_extractor as rx  # noqa: E402


# A study that yields no comparative effect is not necessarily a recall MISS. On
# real full-text corpora, many "no extraction" studies are diagnostic-accuracy /
# prediction-model papers (AUC / C-statistic / sensitivity+specificity) that report
# no poolable HR/OR/RR/MD by design. Labelling this lets recall be measured honestly
# (genuine misses vs appropriate no-effect) instead of conflating the two.
_DIAGNOSTIC_CUES = re.compile(
    r"\bAUC\b|\bAUROC\b|area under the (?:receiver[-\s]operating[-\s]characteristic\s+|ROC\s+)?curve"
    r"|c[-\s]statistic|c[-\s]index|concordance\s+(?:statistic|index)"
    r"|sensitivity[^.\n]{0,60}specificity|specificity[^.\n]{0,60}sensitivity",
    re.IGNORECASE,
)


def no_effect_reason(text: str) -> str:
    """Why a study produced no comparative effect. Conservative: only the
    diagnostic-accuracy case is positively identified; everything else is left
    generic (could be a genuine recall miss, a table-only effect, or a non-RCT).
    """
    if _DIAGNOSTIC_CUES.search(text or ""):
        return "diagnostic_accuracy"     # AUC / Se-Sp: no poolable comparative effect
    return "no_comparative_effect_found"


def _primary_pick(effects: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """The extractor's own primary pick: the is_primary effect (effects[0] after
    order_effects), falling back to the first effect if the flag is absent."""
    if not effects:
        return None
    for e in effects:
        if e.get("is_primary"):
            return e
    return effects[0]


def result_for_record(rec: Dict[str, Any], default_specialty: str = "auto") -> Dict[str, Any]:
    """Run api.extract on one corpus record and build a scorer-compatible result.
    best_match is the extractor's OWN primary pick (is_primary), NOT an oracle."""
    text = rec.get("text") or ""
    specialty = rec.get("specialty") or default_specialty
    out = rx.extract(text, specialty=specialty)
    effects = out.get("effects") or []
    pick = _primary_pick(effects)
    result = {
        "study_id": rec.get("study_id"),
        "status": "extracted" if pick else "no_extractions",
        "n_extractions": len(effects),
        "specialty": out.get("specialty"),
        # best_match carries is_primary + direction -> the scorer detects this is a
        # REAL selection result (oracle_selected == False) rather than a ceiling.
        "best_match": pick if pick else {},
        "all_effects": effects,
        "cochrane_effect": rec.get("cochrane_effect"),
    }
    if not pick:
        # Distinguish an appropriate no-effect (diagnostic/prediction study) from a
        # potential genuine recall miss, so coverage is not over-counted as failure.
        result["no_effect_reason"] = no_effect_reason(text)
    return result


def generate_results(corpus: List[Dict[str, Any]], default_specialty: str = "auto") -> List[Dict[str, Any]]:
    return [result_for_record(rec, default_specialty) for rec in corpus]


def _load_corpus(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            print(f"WARN: skipping unparseable corpus line: {exc}", file=sys.stderr)
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpus", type=Path, required=True, help="JSONL corpus with a 'text' field per study")
    parser.add_argument("--output", type=Path, default=Path("output/api_extract_results.json"))
    parser.add_argument("--specialty", type=str, default="auto")
    args = parser.parse_args()

    if not args.corpus.exists():
        print(f"ERROR: corpus not found: {args.corpus}", file=sys.stderr)
        return 1
    corpus = _load_corpus(args.corpus)
    if not corpus:
        print(f"ERROR: corpus is empty: {args.corpus}", file=sys.stderr)
        return 1

    results = generate_results(corpus, default_specialty=args.specialty)
    n_extracted = sum(1 for r in results if r["best_match"])
    reasons: Dict[str, int] = {}
    for r in results:
        if not r["best_match"]:
            reasons[r.get("no_effect_reason", "?")] = reasons.get(r.get("no_effect_reason", "?"), 0) + 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Ran api.extract on {len(results)} studies; {n_extracted} produced a primary pick.")
    if reasons:
        print("No-pick breakdown (appropriate vs potential recall miss):")
        for reason, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
            tag = " (appropriate: no poolable effect)" if reason == "diagnostic_accuracy" else ""
            print(f"  {reason:28} {n}{tag}")
    print(f"Wrote {args.output}  (best_match = extractor's own is_primary effect).")
    print("Score it:  python scripts/score_primary_direction.py "
          f"--results {args.output} --gold <gold-with-cochrane_raw>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
