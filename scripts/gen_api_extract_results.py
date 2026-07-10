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
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import rct_extractor as rx  # noqa: E402


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
    return {
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
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Ran api.extract on {len(results)} studies; {n_extracted} produced a primary pick.")
    print(f"Wrote {args.output}  (best_match = extractor's own is_primary effect).")
    print("Score it:  python scripts/score_primary_direction.py "
          f"--results {args.output} --gold <gold-with-cochrane_raw>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
