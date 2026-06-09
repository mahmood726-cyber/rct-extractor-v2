"""
Validate the typhoid extractor against PUBLISHED typhoid meta-analyses (silver
standard).

Reuses the malaria MA-validation machinery: for each published typhoid RCT
meta-analysis, treat every reported `value (95% CI lo-hi)` as a reviewer datum
and measure how many our extractor recovers (point AND CI agree). Separates
comparative effect estimates (HR/OR/RR/IRR/MD) from prevalences/proportions.

Usage:
  python scripts/typhoid/validate_typhoid_ma.py --retmax 150 --email you@org
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rct_extractor._engine.core.enhanced_extractor_v3 import EnhancedExtractor
from rct_extractor._engine.specialties.malaria_effects import extract_malaria_effects
from scripts.malaria.validate_against_ma import reviewer_data, recover

OUT = Path(__file__).resolve().parents[2] / "data" / "field_portability" / "typhoid" / "ma_validation.json"

TYPHOID_MA_TERM = (
    '(typhoid OR "enteric fever") AND '
    '(meta-analysis[Publication Type] OR systematic review[Publication Type]) '
    'AND (antibiotic OR vaccine OR randomized OR randomised OR efficacy OR trial)'
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--retmax", type=int, default=150)
    ap.add_argument("--email", default="research@example.org")
    args = ap.parse_args()

    from scripts.malaria.build_malaria_corpus import esearch_pmids, efetch_records, chunks

    extractor = EnhancedExtractor()
    pmids = esearch_pmids(TYPHOID_MA_TERM, args.retmax, args.email)
    print(f"typhoid MA PMIDs: {len(pmids)}")

    n_ma = tot_eff = tot_eff_match = tot_all = tot_all_match = 0
    for batch in chunks(pmids, 180):
        meta = efetch_records(batch, args.email)
        for pmid in batch:
            m = meta.get(pmid)
            if not m or not m["abstract"]:
                continue
            rev = reviewer_data(m["abstract"])
            if not rev:
                continue
            n_ma += 1
            extracted = extract_malaria_effects(extractor, m["abstract"])
            all_match, _ = recover(rev, extracted)
            rev_eff = [r for r in rev if r["is_effect"]]
            eff_match, _ = recover(rev_eff, extracted)
            tot_all += len(rev); tot_all_match += all_match
            tot_eff += len(rev_eff); tot_eff_match += eff_match

    res = {
        "mas_with_data": n_ma,
        "effect_estimates": tot_eff, "effect_recovered": tot_eff_match,
        "effect_agreement": round(tot_eff_match / tot_eff, 4) if tot_eff else 0,
        "all_ci_numbers": tot_all, "all_recovered": tot_all_match,
        "all_agreement": round(tot_all_match / tot_all, 4) if tot_all else 0,
    }
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print("=" * 60)
    print(f"MAs: {n_ma} | EFFECT estimates {tot_eff} recovered {tot_eff_match} "
          f"({res['effect_agreement']:.1%}) | all-CI {tot_all} ({res['all_agreement']:.1%})")


if __name__ == "__main__":
    main()
