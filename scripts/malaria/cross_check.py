"""
Unified automatic cross-check for malaria trials.

For every downloaded malaria PDF, automatically reconciles three sources:
  1. PDF        — effect estimates extracted from the full-text OA PDF
  2. ABSTRACT   — effect estimates extracted from the PubMed abstract
  3. AACT       — ClinicalTrials.gov posted results (only when the trial has an NCT)

It matches effects across sources by (effect_type, value within tolerance) and
reports, per trial:
  - pdf_vs_abstract agreement (recall of abstract-reported effects in the PDF)
  - pdf_vs_aact / abstract_vs_aact agreement (independent external check)
  - discrepancies for human review

This is the "automatic cross-check with PubMed abstracts and ct.gov/AACT" layer.
AACT only covers the NCT subset; abstract cross-check covers every trial.

Outputs:
  data/field_portability/malaria/cross_check.jsonl   (one record per trial)
  data/field_portability/malaria/cross_check_report.md

Usage:
  python scripts/malaria/cross_check.py --limit 0     # all downloaded PDFs
  python scripts/malaria/cross_check.py --value-tol 0.02
"""
import argparse
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from src.core.enhanced_extractor_v3 import EnhancedExtractor, to_dict
from src.pdf.pdf_parser import PDFParser
from src.specialties.malaria import get_malaria_endpoint_patterns
from src.specialties.malaria_effects import augment_malaria_effects, extract_malaria_effects

import re

PROJECT_DIR = Path(__file__).resolve().parents[2]
MAL_DIR = PROJECT_DIR / "data" / "field_portability" / "malaria"
MATCHED = MAL_DIR / "malaria_matched.jsonl"
AACT_GOLD = MAL_DIR / "aact_malaria_gold.json"
PDF_DIR = MAL_DIR / "rct_trial_pdfs"
OUT_JSONL = MAL_DIR / "cross_check.jsonl"
OUT_MD = MAL_DIR / "cross_check_report.md"

ALL_PATTERNS = []
for _s in ("treatment", "prevention", "severe", "transmission"):
    ALL_PATTERNS.extend(get_malaria_endpoint_patterns(_s))


def tag_endpoint(text, start, end, window=140):
    lo, hi = max(0, start - window), min(len(text), end + window)
    ctx = text[lo:hi].lower()
    for pat, ep in ALL_PATTERNS:
        if re.search(pat, ctx):
            return ep
    return None


def extract_effects(extractor, text):
    out = []
    if not text:
        return out
    try:
        merged = extract_malaria_effects(extractor, text)  # core + augment + consistency
    except Exception:
        return out
    for d in merged:
        out.append({
            "type": d["type"],
            "value": d["effect_size"],
            "ci_lower": d.get("ci_lower"),
            "ci_upper": d.get("ci_upper"),
            "endpoint": tag_endpoint(text, d.get("char_start", 0), d.get("char_end", 0)),
            "origin": d.get("origin", "core"),
            "needs_review": d.get("needs_review", False),
            "source_text": d.get("source_text", "")[:160],
        })
    return out


def values_match(a, b, tol):
    if a is None or b is None:
        return False
    if a == 0 and b == 0:
        return True
    if a == 0 or b == 0:
        return False
    return abs(a - b) / max(abs(a), abs(b)) <= tol


def reconcile(primary, reference, tol):
    """How many `reference` effects are matched by some `primary` effect."""
    matched = 0
    details = []
    for r in reference:
        hit = next((p for p in primary
                    if p["type"] == r["type"] and values_match(p["value"], r["value"], tol)), None)
        matched += 1 if hit else 0
        details.append({
            "type": r["type"], "ref_value": r["value"],
            "matched": bool(hit),
            "primary_value": hit["value"] if hit else None,
        })
    return matched, details


def load_matched():
    rows = []
    with open(MATCHED, encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    return rows


def main():
    ap = argparse.ArgumentParser(description="Unified malaria cross-check")
    ap.add_argument("--limit", type=int, default=0, help="Max PDFs (0=all)")
    ap.add_argument("--value-tol", type=float, default=0.02)
    args = ap.parse_args()

    extractor = EnhancedExtractor()
    parser = PDFParser()
    matched = {r["study_id"]: r for r in load_matched()}
    aact = {}
    if AACT_GOLD.exists():
        for s in json.loads(AACT_GOLD.read_text(encoding="utf-8"))["studies"]:
            typed = [{"type": e["effect_type"], "value": e["value"],
                      "ci_lower": e.get("ci_lower"), "ci_upper": e.get("ci_upper")}
                     for e in s["effect_estimates"] if e.get("effect_type")]
            if typed:
                aact[s["nct_id"]] = typed

    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    if args.limit:
        pdfs = pdfs[:args.limit]
    print(f"Cross-checking {len(pdfs)} PDFs...")

    records = []
    agg = {"pdf_eff": 0, "abs_eff": 0,
           "abs_in_pdf_matched": 0, "abs_in_pdf_total": 0,
           "aact_in_pdf_matched": 0, "aact_in_pdf_total": 0,
           "n_with_nct": 0}

    for i, pdf_path in enumerate(pdfs):
        # study_id is the filename prefix before _PMC...
        stem = pdf_path.stem
        study_id = stem.split("_PMC")[0]
        rec = matched.get(study_id)
        if not rec:
            continue
        try:
            content = parser.parse(str(pdf_path))
            pdf_text = "\n".join(p.full_text for p in content.pages)
        except Exception as e:
            pdf_text = ""
        pdf_eff = extract_effects(extractor, pdf_text)
        abs_eff = extract_effects(extractor, rec.get("abstract", ""))

        abs_matched, abs_details = reconcile(pdf_eff, abs_eff, args.value_tol)
        nct = rec.get("nct_id")
        aact_eff = aact.get(nct, []) if nct else []
        aact_matched, aact_details = reconcile(pdf_eff, aact_eff, args.value_tol)

        agg["pdf_eff"] += len(pdf_eff)
        agg["abs_eff"] += len(abs_eff)
        agg["abs_in_pdf_matched"] += abs_matched
        agg["abs_in_pdf_total"] += len(abs_eff)
        if nct:
            agg["n_with_nct"] += 1
            agg["aact_in_pdf_matched"] += aact_matched
            agg["aact_in_pdf_total"] += len(aact_eff)

        records.append({
            "study_id": study_id, "pmid": rec.get("pmid"), "pmcid": rec.get("pmcid"),
            "nct_id": nct, "other_registry_ids": rec.get("other_registry_ids", []),
            "title": rec.get("title", "")[:140],
            "n_pdf_effects": len(pdf_eff), "n_abstract_effects": len(abs_eff),
            "abstract_recovered_in_pdf": f"{abs_matched}/{len(abs_eff)}",
            "aact_effects": len(aact_eff),
            "aact_recovered_in_pdf": f"{aact_matched}/{len(aact_eff)}" if nct else None,
            "pdf_effects": pdf_eff,
            "abstract_vs_pdf": abs_details,
            "aact_vs_pdf": aact_details,
        })
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(pdfs)} processed")

    with open(OUT_JSONL, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    def pct(a, b):
        return f"{a/b:.1%}" if b else "n/a"

    lines = [
        "# Malaria Unified Cross-Check Report", "",
        f"- PDFs cross-checked: **{len(records)}**",
        f"- Effects extracted from PDFs: **{agg['pdf_eff']}**",
        f"- Effects extracted from abstracts: **{agg['abs_eff']}**", "",
        "## Abstract -> PDF consistency (every trial)",
        f"- Abstract-reported effects recovered in the PDF: "
        f"**{agg['abs_in_pdf_matched']}/{agg['abs_in_pdf_total']}** "
        f"({pct(agg['abs_in_pdf_matched'], agg['abs_in_pdf_total'])})", "",
        "## AACT -> PDF agreement (NCT subset, independent gold)",
        f"- Trials with NCT: **{agg['n_with_nct']}**",
        f"- AACT effects recovered in the PDF: "
        f"**{agg['aact_in_pdf_matched']}/{agg['aact_in_pdf_total']}** "
        f"({pct(agg['aact_in_pdf_matched'], agg['aact_in_pdf_total'])})", "",
        f"Per-trial detail: `{OUT_JSONL.name}`",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print("=" * 60)
    print(f"abstract->pdf recall: {pct(agg['abs_in_pdf_matched'], agg['abs_in_pdf_total'])}")
    print(f"aact->pdf recall:     {pct(agg['aact_in_pdf_matched'], agg['aact_in_pdf_total'])}")
    print(f"Wrote {OUT_JSONL} and {OUT_MD}")


if __name__ == "__main__":
    main()
