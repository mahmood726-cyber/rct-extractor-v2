"""
Malaria extractor validation + tuning harness.

Two cross-validation arms:

  ABSTRACT arm (primary gold for malaria):
    Run the malaria-aware extractor over every corpus abstract. Reports
    extraction yield, effect-type distribution, and how many extractions get
    tagged to a malaria endpoint (treatment/prevention/severe/transmission).
    Surfaces abstracts where a clear effect phrase ("efficacy 77%", "HR 0.55")
    was reported but nothing was extracted -> tuning signal.

  AACT arm (independent external gold):
    For malaria trials with posted ClinicalTrials.gov results, compare
    extracted effects (from the matched PDF if downloaded, else the abstract)
    against AACT-reported param_value/CI using the existing CTGValidator.

Outputs:
  data/field_portability/malaria/validation_report.md
  data/field_portability/malaria/validation_results.json

Usage:
  python scripts/malaria/validate_malaria.py --arm abstract --limit 1500
  python scripts/malaria/validate_malaria.py --arm aact
  python scripts/malaria/validate_malaria.py --arm both
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
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from src.core.enhanced_extractor_v3 import EnhancedExtractor, to_dict
from src.specialties.registry import detect_specialty
from src.specialties.malaria import get_malaria_endpoint_patterns, MALARIA_ENDPOINTS

PROJECT_DIR = Path(__file__).resolve().parents[2]
MAL_DIR = PROJECT_DIR / "data" / "field_portability" / "malaria"
MATCHED = MAL_DIR / "malaria_matched.jsonl"
AACT_GOLD = MAL_DIR / "aact_malaria_gold.json"
PDF_DIR = MAL_DIR / "rct_trial_pdfs"
REPORT_MD = MAL_DIR / "validation_report.md"
RESULTS_JSON = MAL_DIR / "validation_results.json"

# Effect phrases that SHOULD yield an extraction; used to flag GENUINE misses.
# Must denote a comparative effect estimate -- NOT the bare word "or", and not a
# lone "95% CI" (single-arm proportions also carry CIs). Either a full ratio
# phrase, or a ratio abbreviation glued to a number, or an efficacy percentage.
EFFECT_HINT = re.compile(
    r"(?:hazard ratio|risk ratio|relative risk|odds ratio|rate ratio|"
    r"incidence rate ratio|mean difference|risk difference|"
    r"\b(?:a?OR|a?HR|a?RR|IRR|RD)\s*(?:=|:|of|was|,)?\s*\d|"
    r"(?:vaccine|protective)\s+efficacy|efficacy (?:of|was|=)\s*\d{1,3}\s*%)",
    re.IGNORECASE,
)

ALL_MALARIA_PATTERNS = []
for _sub in ("treatment", "prevention", "severe", "transmission"):
    ALL_MALARIA_PATTERNS.extend(get_malaria_endpoint_patterns(_sub))


def tag_endpoint(text, start, end, window=140):
    """Tag an extraction with the nearest malaria endpoint by context window."""
    lo = max(0, start - window)
    hi = min(len(text), end + window)
    ctx = text[lo:hi].lower()
    for pat, endpoint in ALL_MALARIA_PATTERNS:
        if re.search(pat, ctx):
            return endpoint
    return None


def load_matched(limit=None):
    rows = []
    with open(MATCHED, encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    return rows[:limit] if limit else rows


def run_abstract_arm(limit):
    extractor = EnhancedExtractor()
    rows = load_matched(limit)
    rows = [r for r in rows if r.get("abstract")]

    n_with_ext = 0
    total_ext = 0
    type_counts = Counter()
    endpoint_counts = Counter()
    subspec_counts = Counter()
    misses = []  # effect phrase present but 0 extractions

    for r in rows:
        text = r["abstract"]
        spec, subspec, _ = detect_specialty(text)
        if spec == "malaria":
            subspec_counts[subspec] += 1
        try:
            exts = extractor.extract(text)
        except Exception:
            exts = []
        if exts:
            n_with_ext += 1
        total_ext += len(exts)
        for x in exts:
            d = to_dict(x)
            type_counts[d["type"]] += 1
            ep = tag_endpoint(text, d.get("char_start", 0), d.get("char_end", 0))
            endpoint_counts[ep or "(untagged)"] += 1
        if not exts and EFFECT_HINT.search(text):
            misses.append({
                "study_id": r["study_id"], "pmid": r.get("pmid"),
                "title": r.get("title", "")[:120],
                "hint": EFFECT_HINT.search(text).group(0),
            })

    return {
        "n_abstracts": len(rows),
        "n_with_extraction": n_with_ext,
        "coverage_rate": round(n_with_ext / len(rows), 4) if rows else 0,
        "total_extractions": total_ext,
        "mean_extractions_per_abstract": round(total_ext / len(rows), 3) if rows else 0,
        "effect_type_distribution": dict(type_counts.most_common()),
        "endpoint_distribution": dict(endpoint_counts.most_common()),
        "malaria_subspecialty_distribution": dict(subspec_counts.most_common()),
        "n_flagged_misses": len(misses),
        "sample_misses": misses[:25],
    }


def run_aact_arm():
    from scripts.ctg_validator import CTGValidator  # reuse existing validator

    gold = json.loads(AACT_GOLD.read_text(encoding="utf-8"))
    matched = {r.get("nct_id"): r for r in load_matched() if r.get("nct_id")}

    # Map NCT -> downloaded PDF path (via matched pmcid) if present
    def pdf_for(nct):
        m = matched.get(nct)
        if not m or not m.get("pmcid"):
            return None, m
        safe = m["study_id"].replace(" ", "_").replace("/", "_")
        p = PDF_DIR / f"{safe}_{m['pmcid']}.pdf"
        return (str(p) if p.exists() else None), m

    validator = CTGValidator()
    per_study = []
    n_pdf = n_abs = n_none = 0
    tot_eff = tot_match = tot_type = tot_val = 0

    for s in gold["studies"]:
        nct = s["nct_id"]
        # Only score effects that have a comparable mapped type
        typed = [e for e in s["effect_estimates"] if e.get("effect_type")]
        if not typed:
            continue
        s_typed = {**s, "effect_estimates": typed}
        pdf_path, m = pdf_for(nct)
        if pdf_path:
            n_pdf += 1
            v = validator.validate_study(s_typed, pdf_path=pdf_path)
            src = "pdf"
        elif m and m.get("abstract"):
            n_abs += 1
            v = validator.validate_study(s_typed, pdf_text=m["abstract"])
            src = "abstract"
        else:
            n_none += 1
            continue
        per_study.append({
            "nct_id": nct, "source": src, "gold_effects": v.ctg_effects,
            "extracted": v.pdf_effects, "matched": v.matched,
            "value_acc": round(v.value_accuracy, 3),
            "type_acc": round(v.type_accuracy, 3),
        })
        tot_eff += v.ctg_effects
        tot_match += v.matched
        tot_val += v.value_accuracy * v.ctg_effects
        tot_type += v.type_accuracy * v.ctg_effects

    return {
        "studies_scored": len(per_study),
        "sources": {"pdf": n_pdf, "abstract": n_abs, "skipped_no_text": n_none},
        "total_gold_effects": tot_eff,
        "total_matched": tot_match,
        "overall_match_rate": round(tot_match / tot_eff, 4) if tot_eff else 0,
        "value_accuracy": round(tot_val / tot_eff, 4) if tot_eff else 0,
        "type_accuracy": round(tot_type / tot_eff, 4) if tot_eff else 0,
        "per_study": per_study,
    }


def write_report(results):
    lines = ["# Malaria Extractor Validation Report", ""]
    ab = results.get("abstract")
    if ab:
        lines += [
            "## Abstract arm (primary gold)", "",
            f"- Abstracts evaluated: **{ab['n_abstracts']}**",
            f"- With >=1 extraction: **{ab['n_with_extraction']}** "
            f"({ab['coverage_rate']:.1%})",
            f"- Total effect estimates extracted: **{ab['total_extractions']}** "
            f"(mean {ab['mean_extractions_per_abstract']}/abstract)",
            f"- Abstracts with an effect phrase but 0 extractions (tuning misses): "
            f"**{ab['n_flagged_misses']}**", "",
            "### Effect-type distribution",
            "| type | n |", "|---|---|",
        ]
        lines += [f"| {k} | {v} |" for k, v in ab["effect_type_distribution"].items()]
        lines += ["", "### Malaria endpoint distribution (context-tagged)",
                  "| endpoint | n |", "|---|---|"]
        lines += [f"| {k} | {v} |" for k, v in ab["endpoint_distribution"].items()]
        lines += ["", "### Subspecialty mix", "| subspecialty | n |", "|---|---|"]
        lines += [f"| {k} | {v} |" for k, v in ab["malaria_subspecialty_distribution"].items()]
        lines += [""]
    aa = results.get("aact")
    if aa:
        lines += [
            "## AACT arm (independent external gold)", "",
            f"- Studies scored: **{aa['studies_scored']}** "
            f"(pdf={aa['sources']['pdf']}, abstract={aa['sources']['abstract']})",
            f"- Gold effects compared: **{aa['total_gold_effects']}**",
            f"- Value accuracy (within 2%): **{aa['value_accuracy']:.1%}**",
            f"- Type accuracy: **{aa['type_accuracy']:.1%}**",
            f"- Overall match (value+type): **{aa['overall_match_rate']:.1%}**", "",
        ]
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Validate malaria extractor")
    ap.add_argument("--arm", choices=["abstract", "aact", "both"], default="both")
    ap.add_argument("--limit", type=int, default=None, help="Max abstracts")
    args = ap.parse_args()

    results = {}
    if args.arm in ("abstract", "both"):
        print("Running abstract arm...")
        results["abstract"] = run_abstract_arm(args.limit)
        a = results["abstract"]
        print(f"  coverage {a['coverage_rate']:.1%}  "
              f"extractions={a['total_extractions']}  misses={a['n_flagged_misses']}")
    if args.arm in ("aact", "both"):
        if AACT_GOLD.exists():
            print("Running AACT arm...")
            results["aact"] = run_aact_arm()
            a = results["aact"]
            print(f"  studies={a['studies_scored']}  value_acc={a['value_accuracy']:.1%}  "
                  f"type_acc={a['type_accuracy']:.1%}")
        else:
            print("  (AACT gold not found; run build_aact_malaria_gold.py first)")

    RESULTS_JSON.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    write_report(results)
    print(f"Wrote {REPORT_MD} and {RESULTS_JSON}")


if __name__ == "__main__":
    main()
