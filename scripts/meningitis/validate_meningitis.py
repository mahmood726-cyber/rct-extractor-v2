"""
Meningitis extractor validation on the corpus: extraction yield, 2x2 / continuous
yield, and internal-consistency rate over abstracts (and PDFs with --pdfs).

Usage:
  python scripts/meningitis/validate_meningitis.py --limit 4000
  python scripts/meningitis/validate_meningitis.py --pdfs        # use downloaded full-text PDFs
"""
import argparse
import io
import json
import sys
import glob
import os
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from src.core.enhanced_extractor_v3 import EnhancedExtractor
from src.specialties.malaria_effects import extract_malaria_effects
from src.specialties.meningitis_arm_data import extract_arm_level
from src.specialties.registry import detect_specialty

MENINGITIS = Path(__file__).resolve().parents[2] / "data" / "field_portability" / "meningitis"
MATCHED = MENINGITIS / "meningitis_matched.jsonl"
PDF_DIR = MENINGITIS / "rct_trial_pdfs"
OUT = MENINGITIS / "validation.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--pdfs", action="store_true")
    args = ap.parse_args()

    extractor = EnhancedExtractor()
    rows = [json.loads(l) for l in open(MATCHED, encoding="utf-8")]
    rows = [r for r in rows if r.get("abstract")]
    if args.limit:
        rows = rows[:args.limit]

    parser = None
    pdfmap = {}
    if args.pdfs:
        from src.pdf.pdf_parser import PDFParser
        parser = PDFParser()
        pdfmap = {os.path.basename(p).split("_PMC")[0]: p
                  for p in glob.glob(str(PDF_DIR / "*.pdf"))}

    n = n_eff = n_with_eff = 0
    eff_consistent = 0
    types = Counter(); meningitis_subspec = Counter()
    n_props = props_consistent = n_2x2 = n_2x2_poolable = n_cont = 0
    trials_with_2x2 = 0
    src_used = Counter()

    for r in rows:
        text = r["abstract"]
        if args.pdfs and r["study_id"] in pdfmap:
            try:
                c = parser.parse(pdfmap[r["study_id"]])
                text = "\n".join(p.full_text for p in c.pages); src_used["pdf"] += 1
            except Exception:
                src_used["abstract"] += 1
        else:
            src_used["abstract"] += 1
        n += 1
        spec, sub, _ = detect_specialty(text)
        if spec == "meningitis":
            meningitis_subspec[sub] += 1
        effs = extract_malaria_effects(extractor, text)
        if effs:
            n_with_eff += 1
        n_eff += len(effs)
        for e in effs:
            types[e["type"]] += 1
            if not e.get("needs_review"):
                eff_consistent += 1
        arm = extract_arm_level(text)
        n_props += len(arm["proportions"])
        props_consistent += sum(1 for p in arm["proportions"] if p["pct_consistent"])
        n_2x2 += len(arm["tables_2x2"]); n_2x2_poolable += len(arm["poolable_2x2"])
        n_cont += len(arm["continuous"])
        if arm["tables_2x2"]:
            trials_with_2x2 += 1

    res = {
        "n_docs": n, "source": dict(src_used),
        "effects": {
            "total": n_eff, "docs_with_effect": n_with_eff,
            "coverage": round(n_with_eff / n, 4) if n else 0,
            "internally_consistent": round(eff_consistent / n_eff, 4) if n_eff else 0,
            "type_distribution": dict(types.most_common()),
        },
        "meningitis_subspecialty": dict(meningitis_subspec.most_common()),
        "arm_level": {
            "proportions": n_props,
            "proportion_consistency": round(props_consistent / n_props, 4) if n_props else 0,
            "trials_with_2x2": trials_with_2x2, "total_2x2": n_2x2,
            "poolable_2x2": n_2x2_poolable, "continuous_rows": n_cont,
        },
    }
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
