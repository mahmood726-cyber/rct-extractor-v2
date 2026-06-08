"""
Validate the malnutrition extractor against PUBLISHED malnutrition / child-nutrition
meta-analyses (silver standard).

Reuses the malaria MA-validation machinery: for each published nutrition RCT
meta-analysis, treat every reported `value (95% CI lo-hi)` as a reviewer datum and
measure how many our extractor recovers (point AND CI agree). Separates comparative
effect estimates (HR/OR/RR/IRR/MD) from prevalences/proportions.

Usage:
  python scripts/malnutrition/validate_malnutrition_ma.py --retmax 150 --email you@org
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.enhanced_extractor_v3 import EnhancedExtractor
from src.specialties.malaria_effects import extract_malaria_effects
from scripts.malaria.validate_against_ma import reviewer_data, recover

OUT = Path(__file__).resolve().parents[2] / "data" / "field_portability" / "malnutrition" / "ma_validation.json"

MALNUTRITION_MA_TERM = (
    '(malnutrition OR undernutrition OR "ready-to-use therapeutic food" OR '
    'stunting OR wasting OR micronutrient OR "supplementary feeding") AND '
    '(meta-analysis[Publication Type] OR systematic review[Publication Type]) '
    'AND (children OR child OR nutritional OR randomized OR randomised OR efficacy OR trial)'
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--retmax", type=int, default=150)
    ap.add_argument("--email", default="research@example.org")
    args = ap.parse_args()

    from scripts.malaria.build_malaria_corpus import esearch_pmids, efetch_records, chunks

    extractor = EnhancedExtractor()
    pmids = esearch_pmids(MALNUTRITION_MA_TERM, args.retmax, args.email)
    print(f"malnutrition MA PMIDs: {len(pmids)}")

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
