"""
Build an AACT gold file of meningitis trial effect estimates (reuses the malaria
AACT dialect + param_type normalization). Many epidemic-belt meningitis trials
register on ISRCTN / PACTR rather than ClinicalTrials.gov, so this gold may be
sparser than HIV's; meningococcal/pneumococcal vaccine trials do register on
CT.gov and contribute most of the typed effects.

Usage:
  python scripts/meningitis/build_aact_meningitis_gold.py --aact "F:/AACT-storage/AACT/2026-04-12"
"""
import argparse
import io
import json
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from scripts.malaria.build_aact_malaria_gold import normalize_param_type, rc, CANDIDATE_AACT

OUT = Path(__file__).resolve().parents[2] / "data" / "field_portability" / "meningitis" / "aact_meningitis_gold.json"


def resolve(arg):
    if arg:
        return arg
    for c in CANDIDATE_AACT:
        if Path(c).exists():
            return c
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aact", default=None)
    args = ap.parse_args()
    aact = resolve(args.aact)
    if not aact:
        sys.exit("AACT snapshot not found")
    print(f"AACT: {aact}")
    con = duckdb.connect()

    nct_q = f"""
    SELECT DISTINCT nct_id FROM (
        SELECT nct_id FROM {rc(aact + '/conditions.txt')}
          WHERE downcase_name LIKE '%meningitis%' OR downcase_name LIKE '%meningococc%'
             OR downcase_name LIKE '%neisseria meningitidis%'
        UNION
        SELECT nct_id FROM {rc(aact + '/browse_conditions.txt')}
          WHERE downcase_mesh_term LIKE '%meningitis%' OR downcase_mesh_term LIKE '%meningococc%'
    )
    """
    ncts = [r[0] for r in con.execute(nct_q).fetchall() if r[0]]
    print(f"meningitis NCTs in AACT: {len(ncts)}")
    if not ncts:
        OUT.write_text(json.dumps({"source": "AACT", "n_studies": 0, "n_effects": 0,
                                   "n_typed_effects": 0, "studies": []}, indent=2),
                       encoding="utf-8")
        sys.exit("no meningitis NCTs in AACT")
    con.execute("CREATE TEMP TABLE tn AS SELECT * FROM (VALUES "
                + ",".join(f"('{n}')" for n in ncts) + ") t(nct_id)")

    eff_q = f"""
    SELECT oa.nct_id, oa.param_type,
           TRY_CAST(oa.param_value AS DOUBLE) AS value,
           TRY_CAST(oa.ci_lower_limit AS DOUBLE) AS ci_lower,
           TRY_CAST(oa.ci_upper_limit AS DOUBLE) AS ci_upper,
           TRY_CAST(oa.p_value AS DOUBLE) AS p_value, o.title AS outcome_title
    FROM {rc(aact + '/outcome_analyses.txt')} oa
    JOIN tn m ON oa.nct_id = m.nct_id
    LEFT JOIN {rc(aact + '/outcomes.txt')} o ON oa.outcome_id = o.id
    WHERE TRY_CAST(oa.param_value AS DOUBLE) IS NOT NULL
    """
    rows = con.execute(eff_q).fetchall()
    titles = {r[0]: r[1] for r in con.execute(
        f"SELECT t.nct_id, t.brief_title FROM {rc(aact + '/studies.txt')} t JOIN tn m ON t.nct_id=m.nct_id"
    ).fetchall()}

    studies, n_typed = {}, 0
    for nct, pt, value, lo, hi, pval, otitle in rows:
        et = normalize_param_type(pt)
        if et:
            n_typed += 1
        studies.setdefault(nct, {"nct_id": nct, "title": titles.get(nct, ""),
                                 "effect_estimates": []})["effect_estimates"].append({
            "effect_type": et, "raw_param_type": pt, "value": value,
            "ci_lower": lo, "ci_upper": hi, "p_value": pval, "outcome_title": otitle or ""})

    out = {"source": "AACT", "n_studies": len(studies),
           "n_effects": sum(len(s["effect_estimates"]) for s in studies.values()),
           "n_typed_effects": n_typed, "studies": list(studies.values())}
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"Studies with effects: {out['n_studies']}  effects: {out['n_effects']} "
          f"(typed {n_typed}) -> {OUT}")


if __name__ == "__main__":
    main()
