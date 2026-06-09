"""
Targeted miss analysis for tuning.

Pre-filters abstracts to those containing a GENUINE comparative-effect phrase
(cheap regex), then runs the extractor only on those to find which produce zero
extractions -- the real tuning list. Prints the matched phrase + a snippet so we
can see exactly what reporting form is being missed.

Usage:
  python scripts/malaria/analyze_misses.py
"""
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from rct_extractor._engine.core.enhanced_extractor_v3 import EnhancedExtractor, to_dict
from rct_extractor._engine.specialties.malaria_effects import augment_malaria_effects

PROJECT_DIR = Path(__file__).resolve().parents[2]
MAL_DIR = PROJECT_DIR / "data" / "field_portability" / "malaria"
MATCHED = MAL_DIR / "malaria_matched.jsonl"
OUT = MAL_DIR / "misses.jsonl"

# Two precise cues for a genuine comparative effect estimate:
#  - full ratio/difference phrases (case-insensitive), or efficacy percentage
#  - abbreviations matched CASE-SENSITIVELY so "OR"/"aOR" != the conjunction "or"
HINT_PHRASE = re.compile(
    r"(hazard ratio|risk ratio|relative risk|odds ratio|rate ratio|"
    r"incidence rate ratio|mean difference|risk difference|"
    r"(?:vaccine|protective)\s+efficacy|efficacy (?:of|was|=)\s*\d{1,3}\s*%)",
    re.IGNORECASE,
)
HINT_ABBR = re.compile(
    r"\b(?:aOR|aHR|aRR|aIRR|OR|HR|RR|IRR|RD)\s*(?:=|:|of)?\s*\d(?:\.\d+)?")


def find_hint(text):
    """Return the first genuine effect-phrase match, or None."""
    m = HINT_PHRASE.search(text)
    if m:
        return m
    return HINT_ABBR.search(text)  # case-sensitive (no IGNORECASE)


def snippet(text, m, pad=70):
    lo, hi = max(0, m.start() - pad), min(len(text), m.end() + pad)
    return re.sub(r"\s+", " ", text[lo:hi]).strip()


def main():
    extractor = EnhancedExtractor()
    rows = [json.loads(l) for l in open(MATCHED, encoding="utf-8")]
    rows = [r for r in rows if r.get("abstract")]

    candidates = []
    for r in rows:
        m = find_hint(r["abstract"])
        if m:
            candidates.append((r, m))
    print(f"Abstracts with a genuine effect phrase: {len(candidates)} / {len(rows)}")

    misses = []
    phrase_counter = Counter()
    core_only_misses = 0
    for r, m in candidates:
        try:
            core = [to_dict(x) for x in extractor.extract(r["abstract"])]
        except Exception:
            core = []
        if not core:
            core_only_misses += 1
        extra = augment_malaria_effects(r["abstract"], core)
        n = len(core) + len(extra)
        if n == 0:
            phrase = m.group(0).lower()
            phrase_key = re.sub(r"\d+(\.\d+)?", "#", phrase)
            phrase_counter[phrase_key] += 1
            misses.append({
                "study_id": r["study_id"], "pmid": r.get("pmid"),
                "phrase": m.group(0), "snippet": snippet(r["abstract"], m),
                "title": r.get("title", "")[:100],
            })

    with open(OUT, "w", encoding="utf-8") as f:
        for mm in misses:
            f.write(json.dumps(mm, ensure_ascii=False) + "\n")

    n_cand = len(candidates)
    print(f"Core-only misses:        {core_only_misses} "
          f"(recall {1 - core_only_misses/n_cand:.1%})")
    print(f"Core+malaria-augment misses: {len(misses)} "
          f"(recall {1 - len(misses)/n_cand:.1%})")
    print(f"Recovered by augmenter:  {core_only_misses - len(misses)}")
    print("\nTop missed phrase forms:")
    for k, v in phrase_counter.most_common(15):
        print(f"  {v:4d}  {k}")
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
