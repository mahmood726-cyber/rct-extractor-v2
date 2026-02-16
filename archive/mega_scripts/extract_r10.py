#!/usr/bin/env python3
"""
Manual extraction from clean_batch_r10.json
Extract ONLY numbers that actually appear in abstract + results_text
NEVER fabricate or guess numbers
"""

import json
import re
import sys
import io
from typing import Dict, Any, Optional

# Fix UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def extract_outcome_data(entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract outcome data from a single study entry.
    CRITICAL: Only extract numbers that ACTUALLY appear in text.
    """
    study_id = entry.get("study_id", "UNKNOWN")
    abstract = entry.get("abstract", "")
    results_text = entry.get("results_text", "")
    full_text = abstract + "\n" + results_text

    result = {
        "study_id": study_id,
        "found": False,
        "effect_type": "NONE",
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        # Binary outcome fields
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        # Continuous outcome fields
        "intervention_mean": None,
        "intervention_sd": None,
        "intervention_n_cont": None,
        "control_mean": None,
        "control_sd": None,
        "control_n_cont": None,
        "source_quote": "",
        "reasoning": ""
    }

    # Study 1: Bernstein 2009
    if "Bernstein 2009" in study_id:
        # OR 2.89, 95%CI 1.22, 6.84 for abstinence at 12 months
        result["found"] = True
        result["effect_type"] = "OR"
        result["point_estimate"] = 2.89
        result["ci_lower"] = 1.22
        result["ci_upper"] = 6.84
        result["source_quote"] = "45% of the intervention group were marijuana abstinent...compared to 22% of the assessed controls (OR 2.89, 95%CI 1.22, 6.84, p<0.014)"
        result["reasoning"] = "Direct OR with CI extracted from results text for marijuana abstinence at 12 months"

    # Study 2: McDevitt-Murphy 2014
    elif "McDevitt-Murphy 2014" in study_id:
        result["found"] = False
        result["reasoning"] = "Only effect sizes (Cohen's d = .34 to .55) reported, no raw outcome data or ORs/RRs/MDs with CIs in provided text"

    # Study 3: Stein 2010
    elif "Stein 2010" in study_id:
        # OR = 1.96, 95% CI 1.17, 3.30 for abstinent days at 3 months
        result["found"] = True
        result["effect_type"] = "OR"
        result["point_estimate"] = 1.96
        result["ci_lower"] = 1.17
        result["ci_upper"] = 3.30
        result["source_quote"] = "Intervention effects on abstinent days were statistically significant at 3-months (OR = 1.96, 95% CI 1.17, 3.30); the percent of days abstinent was 68% for those randomized to intervention and 57% for controls."
        result["reasoning"] = "Direct OR with CI from abstract and results text for abstinent days at 3 months"

    # Study 4: Morgenstern 2012
    elif "Morgenstern 2012" in study_id:
        result["found"] = False
        result["reasoning"] = "Abstract states 'Drinking was significantly reduced...but the reduction was equivalent across conditions'. No specific ORs, RRs, MDs with CIs or raw counts/means in provided text"

    # Study 5: Walters 2009
    elif "Walters 2009" in study_id:
        result["found"] = False
        result["reasoning"] = "Abstract mentions effect sizes (.54, .63, .48) but these are standardized effects, not raw outcome data. Results text describes composite drinking measures and effect sizes but no extractable ORs, RRs, MDs with CIs or raw data"

    # Study 6: Aharonovich 2017
    elif "Aharonovich 2017" in study_id:
        result["found"] = False
        result["reasoning"] = "Abstract states 'significantly greater reductions in the MI-Only group' but no specific ORs, RRs, MDs with CIs provided in available text. Results text cut off before presenting numerical outcomes"

    # Study 7: Barnett 2007
    elif "Barnett 2007" in study_id:
        result["found"] = False
        result["reasoning"] = "Results report effect sizes (Cohen's d) and time effects, but no ORs, RRs, or MDs with CIs. Main finding is Time × Group interaction for RAPI (p=.0191) but no specific estimate with CI"

    # Study 8: Mackiewicz Seghete 2022
    elif "Mackiewicz Seghete 2022" in study_id:
        result["found"] = False
        result["reasoning"] = "Neuroimaging study. Results describe brain activation differences and 'significantly better treatment outcomes...at 12 months' but no specific ORs, RRs, MDs with CIs or raw outcome data in provided text"

    # Study 9: UKATT 2005
    elif "UKATT 2005" in study_id:
        result["found"] = False
        result["reasoning"] = "Cost-effectiveness analysis. States 'Neither net savings nor cost effectiveness differed significantly between therapies' but no clinical outcome ORs, RRs, or MDs with CIs provided in available text"

    # Study 10: Slesnick 2013
    elif "Slesnick 2013" in study_id:
        result["found"] = False
        result["reasoning"] = "Abstract and results describe 'statistically significant improvement in frequency of substance use' and trajectory classes, but no specific ORs, RRs, MDs with CIs or raw outcome data in provided text"

    # Study 11: Borsari 2005
    elif "Borsari 2005" in study_id:
        result["found"] = False
        result["reasoning"] = "Results show significant Time × Group interaction for RAPI (F(2,123)=4.09, p=.0191) and effect sizes reported, but no ORs, RRs, or MDs with CIs. Main findings are within-group and between-group effect sizes"

    # Study 12: Colby 2018
    elif "Colby 2018" in study_id:
        result["found"] = False
        result["reasoning"] = "Abstract states 'significantly fewer average drinks per week, percent drinking days...all ps < .05' but no specific ORs, RRs, or MDs with CIs provided in available text"

    # Study 13: Murphy 2018
    elif "Murphy 2018" in study_id:
        result["found"] = False
        result["reasoning"] = "Abstract reports partial η² effect sizes and states 'No significant condition differences...were found' for primary outcomes. No ORs, RRs, or MDs with CIs in provided text"

    # Study 14: Stein 2017
    elif "Stein 2017" in study_id:
        result["found"] = False
        result["reasoning"] = "Abstract states baseline rates (binge drinking: 5.23±4.31 days/30, marijuana: 19.4±10.0 days/30) and 'statistically significant reductions' but results text cut before presenting between-group comparisons with ORs/MDs/CIs"

    # Study 15: Hu 2017
    elif "Hu 2017" in study_id:
        # Vaccination study - binary outcomes with ORs and CIs
        # OR = 3.4, 95%CI: 2.1–4.8 for full vaccination completion
        # OR = 2.3, 95%CI: 1.6–3.5 for timely vaccination
        result["found"] = True
        result["effect_type"] = "OR"
        result["point_estimate"] = 3.4
        result["ci_lower"] = 2.1
        result["ci_upper"] = 4.8
        result["source_quote"] = "In the intervention group...children were more likely to complete the full series of vaccination (OR D 3.4, 95%CI: 2.1–4.8), and children were more likely to complete the full series of vaccination in a timely manner (OR D 2.3, 95%CI: 1.6–3.5)"
        result["reasoning"] = "Direct OR with CI from results text for full vaccination completion. Also found 90.0% vs 82.9% coverage rates in abstract"
        # Additional data: coverage 90.0% intervention vs 82.9% control
        # From abstract: "The coverage of fully vaccination was signiﬁcantly higher in the intervention group (90.0% vs. 82.9%, P<0.01)"

    return result


def main():
    input_file = "C:/Users/user/rct-extractor-v2/gold_data/mega/clean_batch_r10.json"
    output_file = "C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r10.json"

    print(f"Reading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        entries = json.load(f)

    print(f"\nProcessing {len(entries)} entries...\n")
    print("="*80)
    results = []

    for i, entry in enumerate(entries, 1):
        result = extract_outcome_data(entry)
        results.append(result)

        status = "✓ FOUND" if result["found"] else "✗ NOT FOUND"
        effect = f"[{result['effect_type']:3s}]" if result['found'] else "[---]"

        study_name = result['study_id'][:40].ljust(40)
        print(f"{i:2d}. {study_name} {status:12s} {effect}")

        if result["found"]:
            if result["point_estimate"] is not None:
                ci_str = ""
                if result["ci_lower"] is not None and result["ci_upper"] is not None:
                    ci_str = f" (95% CI: {result['ci_lower']}, {result['ci_upper']})"
                print(f"    → {result['effect_type']} = {result['point_estimate']}{ci_str}")
        else:
            print(f"    → {result['reasoning'][:75]}...")

    print("="*80)
    print(f"\nWriting results to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Summary
    found_count = sum(1 for r in results if r["found"])
    with_ci = sum(1 for r in results if r["found"] and r["ci_lower"] is not None)

    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Total entries:              {len(results)}")
    print(f"Extractable data found:     {found_count}/{len(results)} ({100*found_count/len(results):.1f}%)")
    print(f"With confidence intervals:  {with_ci}/{found_count}")
    print(f"{'='*80}\n")

    print("✓ Extraction complete!")
    print(f"Output: {output_file}")


if __name__ == "__main__":
    main()
