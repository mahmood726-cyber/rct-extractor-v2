"""
Mine the published-hypertension-MA misses: effect estimates the reviewers reported
that our extractor did NOT recover, with snippets, to reveal fixable format gaps.

Usage: python scripts/hypertension/analyze_hypertension_ma_misses.py --retmax 200 --email you@org
"""
import argparse
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from rct_extractor._engine.core.enhanced_extractor_v3 import EnhancedExtractor
from rct_extractor._engine.specialties.malaria_effects import extract_malaria_effects
from scripts.malaria.validate_against_ma import (
    MA_DATUM, _f, _EFFECT_LABEL_PHRASE as HINT_PHRASE, _EFFECT_LABEL_ABBR as HINT_ABBR)
from scripts.hypertension.validate_hypertension_ma import HYPERTENSION_MA_TERM

OUT = Path(__file__).resolve().parents[2] / "data" / "field_portability" / "hypertension" / "ma_misses.jsonl"


def close(a, b, tol=0.05):
    if a is None or b is None:
        return False
    if a == 0 or b == 0:
        return abs(a - b) < tol
    return abs(a - b) / max(abs(a), abs(b)) <= tol


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--retmax", type=int, default=200)
    ap.add_argument("--email", default="research@example.org")
    args = ap.parse_args()

    from scripts.malaria.build_malaria_corpus import esearch_pmids, efetch_records, chunks
    e = EnhancedExtractor()
    pmids = esearch_pmids(HYPERTENSION_MA_TERM, args.retmax, args.email)
    print(f"hypertension MA PMIDs: {len(pmids)}")

    misses, phrase_counter = [], Counter()
    n_eff = n_recovered = 0
    for batch in chunks(pmids, 180):
        meta = efetch_records(batch, args.email)
        for pmid in batch:
            m = meta.get(pmid)
            if not m or not m["abstract"]:
                continue
            text = m["abstract"]
            extracted = extract_malaria_effects(e, text)
            for dm in MA_DATUM.finditer(text):
                v, lo, hi = _f(dm["val"]), _f(dm["lo"]), _f(dm["hi"])
                if None in (v, lo, hi):
                    continue
                if not (min(lo, hi) - 0.1 <= v <= max(lo, hi) + 0.1):
                    continue
                window = text[max(0, dm.start() - 45):dm.start()]
                hint = HINT_PHRASE.search(window) or HINT_ABBR.search(window)
                if not hint:
                    continue
                n_eff += 1
                if any(close(x.get("effect_size"), v) and close(x.get("ci_lower"), lo)
                       and close(x.get("ci_upper"), hi) for x in extracted):
                    n_recovered += 1
                    continue
                snip = re.sub(r"\s+", " ", text[max(0, dm.start() - 55):dm.end() + 10]).strip()
                key = re.sub(r"\d+(\.\d+)?", "#", hint.group(0).lower())
                phrase_counter[key] += 1
                misses.append({"pmid": pmid, "snippet": snip[:150]})

    with open(OUT, "w", encoding="utf-8") as f:
        for mm in misses:
            f.write(json.dumps(mm, ensure_ascii=False) + "\n")
    print(f"effect-labelled reviewer estimates: {n_eff}")
    print(f"recovered: {n_recovered} ({n_recovered/max(n_eff,1):.1%})  misses: {len(misses)}")
    print("top missed phrase forms:")
    for k, v in phrase_counter.most_common(15):
        print(f"  {v:4d}  {k}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
