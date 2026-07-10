#!/usr/bin/env python3
"""Real (non-oracle) primary-selection eval on the gold_50 studies.

For every gold record with a pmcid, fetch the PMC full text from the NCBI
E-utilities efetch API (JATS XML, cached locally), run the PUBLIC api.extract,
take the extractor's OWN primary pick (effects[0] / is_primary), and score it
against the authoritative per-study Cochrane reference (cochrane_effect /
cochrane_raw) with scripts/score_primary_direction.py.

Unlike gold_data/baseline_results.json (oracle-selected closest-to-truth match),
THIS measures the extractor's real selection. Full text is retrieved as JATS XML
because the PMC/EuropePMC PDF endpoints are blocked in some environments; the
extractor takes text, and JATS body text is cleaner than PDF-parsed text.

    python scripts/eval_gold_real.py            # all pmcid studies
    python scripts/eval_gold_real.py --limit 5  # quick check
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import rct_extractor as rx  # noqa: E402
import score_primary_direction as spd  # noqa: E402
import gen_api_extract_results as gen  # noqa: E402

EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id={num}"
UA = "rct-extractor-gold-eval/1.0 (mailto:research@example.org)"
CACHE = ROOT / "data" / "gold_fulltext_cache"


def _efetch_xml(pmcid: str, timeout: int = 60) -> Optional[str]:
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = CACHE / f"{pmcid}.xml"
    if cached.exists() and cached.stat().st_size > 500:
        return cached.read_text(encoding="utf-8", errors="replace")
    num = pmcid.replace("PMC", "")
    req = urllib.request.Request(EFETCH.format(num=num), headers={"User-Agent": UA})
    try:
        raw = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")
    except Exception as exc:
        print(f"  {pmcid}: efetch failed ({exc})", file=sys.stderr)
        return None
    cached.write_text(raw, encoding="utf-8")
    return raw


def _text_from_jats(xml: str) -> str:
    """Concatenated abstract + body text from a PMC JATS XML document."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        # last resort: strip tags
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", xml))
    parts: List[str] = []
    for tag in ("abstract", "body"):
        for node in root.iter(tag):
            parts.append(" ".join(node.itertext()))
    text = " ".join(parts)
    return re.sub(r"\s+", " ", text).strip()


def _load_gold(gold_path: Path) -> List[Dict[str, Any]]:
    out = []
    for line in gold_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gold", type=Path, default=Path("gold_data/gold_50.jsonl"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=0.4)
    ap.add_argument("--output", type=Path, default=Path("output/real_selection_scorecard.json"))
    args = ap.parse_args()

    gold = [g for g in _load_gold(args.gold) if g.get("pmcid")]
    if args.limit:
        gold = gold[: args.limit]
    print(f"{len(gold)} gold studies with a pmcid")

    gold_meta = {g["study_id"]: {"outcome_type": (g.get("cochrane_outcome_type") or "binary"),
                                 "raw": g.get("cochrane_raw") or {}} for g in gold}

    results: List[Dict[str, Any]] = []
    fetched = extracted = 0
    for i, g in enumerate(gold, 1):
        pmcid, sid = g["pmcid"], g["study_id"]
        xml = _efetch_xml(pmcid)
        newly = not (CACHE / f"{pmcid}.xml").exists() if xml is None else True
        text = _text_from_jats(xml) if xml else ""
        if text:
            fetched += 1
        out = rx.extract(text, specialty="auto") if len(text) > 200 else {"effects": []}
        pick = gen._primary_pick(out.get("effects") or [])
        if pick:
            extracted += 1
        results.append({
            "study_id": sid,
            "best_match": pick if pick else {},
            "n_extractions": len(out.get("effects") or []),
            "n_diagnostic": len(out.get("diagnostic") or []),
            "text_chars": len(text),
            "cochrane_effect": g.get("cochrane_effect"),
        })
        print(f"  [{i:>2}/{len(gold)}] {sid:20} text={len(text):>6}c  eff={len(out.get('effects') or [])}"
              f"  pick={pick['type']+' '+str(pick.get('effect_size')) if pick else '-':<12}"
              f"  dta={len(out.get('diagnostic') or [])}")
        if xml is not None and newly:
            time.sleep(args.delay)

    scored = [spd.score_record(r, gold_meta) for r in results]
    summary = spd.summarize(scored)
    print("=" * 68)
    print(f"REAL selection eval (efetch full text -> api.extract effects[0])")
    print(f"  full text fetched: {fetched}/{len(gold)}   produced a primary pick: {extracted}/{len(gold)}")
    def pct(x): return f"{x*100:.1f}%" if x is not None else "n/a"
    print(f"  top-1 value match:   {summary['selection']['value_match']}  ({pct(summary['top1_value_match_rate'])})")
    print(f"  value mismatch:      {summary['selection']['value_mismatch']}")
    print(f"  measure mismatch:    {summary['selection']['measure_mismatch']}")
    print(f"  no extraction:       {summary['selection']['no_extraction']}")
    print(f"  direction agree:     {summary['direction']['agree']}   SIGN FLIP: {summary['direction']['sign_flip']}")
    print(f"  direction accuracy:  {pct(summary['direction_accuracy'])}  (same-measure determinable={summary['direction_determinable']})")
    print("=" * 68)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"real_selection": True, "summary": summary,
                                       "per_study": scored, "results": results}, indent=2), encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
