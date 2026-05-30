"""
Build a ClinicalTrials.gov/AACT gold file of malaria trial effect estimates.

Queries a local AACT flat-file snapshot for malaria trials and their reported
outcome_analyses (effect estimates), normalises the AACT param_type free text
to the extractor's effect-type codes, and writes a CTG-format JSON that
scripts/ctg_validator.py consumes directly:

  {"studies": [{"nct_id","title","effect_estimates":[
       {"effect_type","value","ci_lower","ci_upper","p_value","outcome_title"}]}]}

AACT files are pipe-delimited, double-quoted CSV. Don't hardcode the drive;
pass --aact or rely on candidate discovery.

Usage:
  python scripts/malaria/build_aact_malaria_gold.py --aact "F:/AACT-storage/AACT/2026-04-12"
"""
import argparse
import io
import json
import re
import sys
from pathlib import Path

import duckdb

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PROJECT_DIR = Path(__file__).resolve().parents[2]
MAL_DIR = PROJECT_DIR / "data" / "field_portability" / "malaria"
OUT_FILE = MAL_DIR / "aact_malaria_gold.json"

CANDIDATE_AACT = [
    "F:/AACT-storage/AACT/2026-04-12",
    "C:/AACT-storage/AACT/2026-04-12",
    "D:/AACT-storage/AACT/2026-04-12",
]


def normalize_param_type(pt: str) -> str:
    """Map AACT param_type free text -> extractor effect-type code, or '' if unmapped."""
    if not pt:
        return ""
    p = pt.lower()
    if "hazard" in p:
        return "HR"
    if "odds" in p:
        return "OR"
    if "incidence rate" in p or ("rate ratio" in p and "hazard" not in p):
        return "IRR"
    if "risk ratio" in p or "relative risk" in p:
        return "RR"
    if "geometric mean ratio" in p:
        return "GMR"
    if "risk difference" in p:
        return "ARD"
    if "number needed" in p:
        return "NNT"
    # Mean differences: standardized vs plain. Exclude ratios already handled.
    if "standardized mean" in p or "standardised mean" in p:
        return "SMD"
    if "mean difference" in p or "mean diff" in p or re.search(r"\bls\s*mean", p):
        return "MD"
    return ""


def resolve_aact(arg):
    if arg:
        return arg
    for c in CANDIDATE_AACT:
        if Path(c).exists():
            return c
    return None


def rc(path):
    """read_csv() call string with the AACT dialect."""
    return (f"read_csv('{path}', delim='|', quote='\"', escape='\"', "
            f"header=true, ignore_errors=true, all_varchar=true)")


def main():
    ap = argparse.ArgumentParser(description="Build AACT malaria gold file")
    ap.add_argument("--aact", default=None, help="Path to AACT snapshot dir")
    ap.add_argument("--min-analyses", type=int, default=1)
    args = ap.parse_args()

    aact = resolve_aact(args.aact)
    if not aact or not Path(aact).exists():
        print(f"AACT snapshot not found. Tried: {args.aact or CANDIDATE_AACT}")
        sys.exit(1)
    print(f"AACT: {aact}")

    MAL_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()

    studies_f = f"{aact}/studies.txt"
    conditions_f = f"{aact}/conditions.txt"
    browse_f = f"{aact}/browse_conditions.txt"
    outcomes_f = f"{aact}/outcomes.txt"
    oa_f = f"{aact}/outcome_analyses.txt"

    # Malaria NCTs: union of conditions + MeSH browse_conditions matching 'malaria'
    nct_q = f"""
    SELECT DISTINCT nct_id FROM (
        SELECT nct_id FROM {rc(conditions_f)} WHERE downcase_name LIKE '%malaria%'
        UNION
        SELECT nct_id FROM {rc(browse_f)} WHERE downcase_mesh_term LIKE '%malaria%'
    )
    """
    malaria_ncts = [r[0] for r in con.execute(nct_q).fetchall() if r[0]]
    print(f"Malaria NCTs in AACT: {len(malaria_ncts)}")

    con.execute("CREATE TEMP TABLE mal_nct AS SELECT * FROM (VALUES "
                + ",".join(f"('{n}')" for n in malaria_ncts) + ") t(nct_id)")

    # Effect estimates for malaria NCTs with a numeric param_value
    eff_q = f"""
    SELECT oa.nct_id,
           oa.param_type,
           TRY_CAST(oa.param_value AS DOUBLE)        AS value,
           TRY_CAST(oa.ci_lower_limit AS DOUBLE)     AS ci_lower,
           TRY_CAST(oa.ci_upper_limit AS DOUBLE)     AS ci_upper,
           TRY_CAST(oa.p_value AS DOUBLE)            AS p_value,
           o.title                                   AS outcome_title
    FROM {rc(oa_f)} oa
    JOIN mal_nct m ON oa.nct_id = m.nct_id
    LEFT JOIN {rc(outcomes_f)} o ON oa.outcome_id = o.id
    WHERE TRY_CAST(oa.param_value AS DOUBLE) IS NOT NULL
    """
    rows = con.execute(eff_q).fetchall()
    print(f"Numeric outcome_analyses rows for malaria trials: {len(rows)}")

    # Study titles
    title_q = f"SELECT t.nct_id, t.brief_title FROM {rc(studies_f)} t JOIN mal_nct m ON t.nct_id=m.nct_id"
    titles = {r[0]: r[1] for r in con.execute(title_q).fetchall()}

    studies = {}
    n_typed = 0
    for nct, param_type, value, ci_lo, ci_hi, pval, outcome_title in rows:
        etype = normalize_param_type(param_type)
        if etype:
            n_typed += 1
        studies.setdefault(nct, {
            "nct_id": nct,
            "title": titles.get(nct, ""),
            "effect_estimates": [],
        })["effect_estimates"].append({
            "effect_type": etype,            # '' if AACT type unmapped
            "raw_param_type": param_type,
            "value": value,
            "ci_lower": ci_lo,
            "ci_upper": ci_hi,
            "p_value": pval,
            "outcome_title": outcome_title or "",
        })

    studies = {k: v for k, v in studies.items()
               if len(v["effect_estimates"]) >= args.min_analyses}

    out = {
        "source": "AACT",
        "snapshot": Path(aact).name,
        "n_studies": len(studies),
        "n_effects": sum(len(s["effect_estimates"]) for s in studies.values()),
        "n_typed_effects": n_typed,
        "studies": list(studies.values()),
    }
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)

    print("=" * 60)
    print(f"Studies with reported effects: {out['n_studies']}")
    print(f"Total effect estimates: {out['n_effects']}  (typed: {out['n_typed_effects']})")
    print(f"Wrote -> {OUT_FILE}")


if __name__ == "__main__":
    main()
