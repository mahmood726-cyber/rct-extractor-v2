"""
Diabetes unified cross-check: per trial reconcile PDF extractions vs PubMed
abstract vs AACT (when NCT). Abstract->PDF recall is the at-scale signal;
AACT->PDF is the independent numeric gold (dense for diabetes CVOTs).

Outputs: data/field_portability/diabetes/cross_check.json
Usage: python scripts/diabetes/cross_check.py --limit 0
"""
import argparse
import io
import json
import sys
import glob
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from rct_extractor._engine.core.enhanced_extractor_v3 import EnhancedExtractor, to_dict
from rct_extractor._engine.pdf.pdf_parser import PDFParser
from rct_extractor._engine.specialties.malaria_effects import extract_malaria_effects

DIABETES = Path(__file__).resolve().parents[2] / "data" / "field_portability" / "diabetes"
MATCHED = DIABETES / "diabetes_matched.jsonl"
AACT_GOLD = DIABETES / "aact_diabetes_gold.json"
PDF_DIR = DIABETES / "rct_trial_pdfs"
OUT = DIABETES / "cross_check.json"


def effects(extractor, text):
    if not text:
        return []
    try:
        return [{"type": e["type"], "value": e["effect_size"],
                 "ci_lower": e.get("ci_lower"), "ci_upper": e.get("ci_upper")}
                for e in extract_malaria_effects(extractor, text)]
    except Exception:
        return []


def close(a, b, tol=0.05):
    if a is None or b is None:
        return False
    if a == 0 or b == 0:
        return abs(a - b) < tol
    return abs(a - b) / max(abs(a), abs(b)) <= tol


def recover(primary, reference):
    m = 0
    for r in reference:
        if any(p["type"] == r["type"] and close(p["value"], r["value"]) for p in primary):
            m += 1
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    extractor = EnhancedExtractor()
    parser = PDFParser()
    matched = {r["study_id"]: r for r in (json.loads(l) for l in open(MATCHED, encoding="utf-8"))}
    aact = {}
    if AACT_GOLD.exists():
        for s in json.loads(AACT_GOLD.read_text(encoding="utf-8"))["studies"]:
            typed = [{"type": e["effect_type"], "value": e["value"]}
                     for e in s["effect_estimates"] if e.get("effect_type")]
            if typed:
                aact[s["nct_id"]] = typed

    pdfs = sorted(glob.glob(str(PDF_DIR / "*.pdf")))
    if args.limit:
        pdfs = pdfs[:args.limit]

    abs_tot = abs_match = aact_tot = aact_match = n_nct = 0
    n = 0
    for pdf in pdfs:
        sid = os.path.basename(pdf).split("_PMC")[0]
        rec = matched.get(sid)
        if not rec:
            continue
        try:
            content = parser.parse(pdf)
            ptext = "\n".join(p.full_text for p in content.pages)
        except Exception:
            ptext = ""
        pe = effects(extractor, ptext)
        ae = effects(extractor, rec.get("abstract", ""))
        abs_tot += len(ae); abs_match += recover(pe, ae)
        nct = rec.get("nct_id")
        if nct and nct in aact:
            n_nct += 1
            aact_tot += len(aact[nct]); aact_match += recover(pe, aact[nct])
        n += 1
        if n % 50 == 0:
            print(f"  {n}/{len(pdfs)}", flush=True)

    res = {
        "pdfs": n,
        "abstract_to_pdf": {"total": abs_tot, "recovered": abs_match,
                            "recall": round(abs_match / abs_tot, 4) if abs_tot else 0},
        "aact_to_pdf": {"trials_with_aact": n_nct, "total": aact_tot, "recovered": aact_match,
                        "recall": round(aact_match / aact_tot, 4) if aact_tot else 0},
    }
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
