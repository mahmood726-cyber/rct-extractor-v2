import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Read batch file
with open('C:/Users/user/rct-extractor-v2/gold_data/mega/clean_batch_r5.json', 'r', encoding='utf-8') as f:
    batch_data = json.load(f)

results = []

# Process each entry
for entry in batch_data:
    study_id = entry['study_id']
    outcome = entry['outcome']
    data_type = entry.get('data_type')
    results_text = entry.get('results_text', '')
    abstract = entry.get('abstract', '')

    # Initialize result
    result = {
        "study_id": study_id,
        "found": False,
        "effect_type": "NONE",
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": "",
        "reasoning": ""
    }

    # Study-specific extraction logic

    if study_id == "Lee 2022_2022":
        # Walking velocity - no raw data provided, only significance statements
        result["found"] = False
        result["reasoning"] = "Results only report significance (P < .05) without actual velocity values. Text states 'pelvic on and CIMT groups showed significant improvement in 10MWT' but no mean±SD values provided for walking velocity in m/s."
        result["source_quote"] = "The pelvic on and CIMT groups showed significant improvement in 10MWT, BBS, TUG, and MI-Lower (P < .05)."

    elif study_id == "Meng 2022_2022":
        # Walking velocity - found it
        result["found"] = True
        result["effect_type"] = "MD"
        result["intervention_mean"] = 0.66
        result["intervention_sd"] = 0.22
        result["control_mean"] = 0.55
        result["control_sd"] = 0.23
        result["source_quote"] = "velocity (0.66 ± 0.22 versus 0.55 ± 0.23 versus 0.51 ± 0.20, p = 0.008)"
        result["reasoning"] = "Extracted walking velocity for RAGT group (intervention: 0.66±0.22 m/s) vs ELLT group (control: 0.55±0.23 m/s). Three-arm trial; used RAGT vs ELLT comparison."

    elif study_id == "Miyagawa 2023_2023":
        # Walking velocity - no significant difference
        result["found"] = False
        result["reasoning"] = "Results state 'no significant difference in the main outcomes between both groups' for 10mWT and 6MWD. No mean±SD values for walking velocity provided in the results text."
        result["source_quote"] = "There was no significant difference in the main outcomes between both groups at the end of gait training."

    elif study_id == "Taveggia 2016_2016":
        # Walking velocity - mentions gait speed but no raw values
        result["found"] = False
        result["reasoning"] = "Results mention 'significant increase in gait speed (10 m walk test)' in experimental group but do not provide mean±SD values for walking velocity in m/s."
        result["source_quote"] = "The experimental group showed a significant increase in functional independence and gait speed (10 m walk test) at the end of the treatment and follow-up, higher than the minimal detectable change."

    elif study_id == "Nam 2022_2022":
        # Walking velocity - only FAC scores provided
        result["found"] = False
        result["reasoning"] = "Results provide FAC scores and mentions 'clinical walking functions showed improvement' but no mean±SD values for walking velocity in m/s are provided."
        result["source_quote"] = "The mean FAC in the experimental group was 3.15 ± 1.39 before intervention (pre-intervention) and 4.22 ± 1.37 after the intervention (post-intervention)"

    elif study_id == "Sczesny-Kaiser 2019_2019":
        # Walking velocity - no significant difference
        result["found"] = False
        result["reasoning"] = "Results state 'neither a significant difference in walking parameters' between groups. No mean±SD values for walking velocity provided."
        result["source_quote"] = "Our study demonstrate neither a significant difference in walking parameters nor in functional and balance parameters."

    elif study_id == "Yu 2021_2021":
        # Walking velocity - mentioned but no values
        result["found"] = False
        result["reasoning"] = "Results mention 'RT group exhibited a significant effect on changes in space parameters (stride length, walk velocity, and toe out angle, P < 0.05)' but do not provide the actual mean±SD values for walking velocity in m/s."
        result["source_quote"] = "the RT group exhibited a significant effect on changes in space parameters (stride length, walk velocity, and toe out angle, P < 0:05)."

    elif study_id == "Kitamura 2020_2020":
        # Withdrawn: any cause
        result["found"] = False
        result["reasoning"] = "This is a telmisartan dose comparison study (40mg vs 80mg). Results mention 'no severe adverse events' and 'occurrence of adverse events did not significantly differ (p = 0.56)' but do not provide specific withdrawal counts for each group."
        result["source_quote"] = "No severe adverse events occurred in either group, and the occurrence of adverse events did not significantly differ between them (p = 0.56)."

    elif study_id == "Weil 2012_2012":
        # Death: any cause - NOT an RCT
        result["found"] = False
        result["reasoning"] = "This is NOT a randomized controlled trial. It is an observational study examining podocyte detachment and endothelial cell fenestration in kidney biopsies from patients with type 2 diabetes. No intervention/control groups or death outcomes reported."
        result["source_quote"] = "Here we studied these relationships in 37 Pima Indians with type 2 diabetes of whom 11 had normal albuminuria, 16 had microalbuminuria, and 10 had macroalbuminuria."

    elif study_id == "Kayentao 2012_2012":
        # Total failure: day 28 (PCR-adjusted) - malaria trial
        result["found"] = True
        result["effect_type"] = "RR"
        result["intervention_events"] = 10  # 339 - 329
        result["intervention_n"] = 339
        result["control_events"] = 2  # 167 - 165
        result["control_n"] = 167
        result["source_quote"] = "Day-28 adequate clinical and parasitological response (ACPR), corrected for re-infection using polymerase chain reaction (PCR) genotyping (per-protocol population) was 97.1% (329/339; 95% CI 94.6, 98.6) for pyronaridine-artesunate; 98.8% (165/167; 95% CI 95.7, 99.9) for artemether-lumefantrine."
        result["reasoning"] = "ACPR success rates given. Calculated failures: pyronaridine-artesunate (intervention) had 10 failures (339-329=10) out of 339; artemether-lumefantrine (control) had 2 failures (167-165=2) out of 167."

    elif study_id == "Nelwan 2015_2015":
        # Serious adverse events
        result["found"] = False
        result["reasoning"] = "Results state 'Subjects in all treatment groups tolerated the therapies well without untoward events' suggesting zero serious adverse events, but specific counts per group are not provided in the results text."
        result["source_quote"] = "Subjects in all treatment groups tolerated the therapies well without untoward events and cleared parasitemia within three days."

    elif study_id == "Falade 2023_2023":
        # Total failure: day 28 (PCR-adjusted)
        result["found"] = True
        result["effect_type"] = "RR"
        result["intervention_events"] = 2  # 78 - 76
        result["intervention_n"] = 78
        result["control_events"] = 8  # 67 - 59
        result["control_n"] = 67
        result["source_quote"] = "PCR-corrected Day-28 cure rates for PA were 97.4% (76/78) and 88.1% (59/67) for AL (= 0.04) in the per-protocol population after new infections were censored."
        result["reasoning"] = "PCR-corrected cure rates given. Calculated failures: PA (intervention) had 2 failures (78-76=2) out of 78; AL (control) had 8 failures (67-59=8) out of 67."

    elif study_id == "Zheng 2022_2022":
        # Live birth - this IS an RCT comparing IVM vs IVF in PCOS
        # "22.3% vs. 50.6%; rate difference −28.3%"
        # But outcome asks for "odds ratio" - no OR reported, only rate difference
        result["found"] = True
        result["effect_type"] = "ARD"  # Absolute Risk Difference
        result["point_estimate"] = -28.3  # rate difference in percentage points
        result["ci_lower"] = -37.9
        result["ci_upper"] = -18.7
        result["source_quote"] = "The IVM procedure without additional gonadotropin resulted in a lower ongoing pregnancy (leading to live birth) within 6 months after randomization compared to standard IVF treatment (22.3% vs. 50.6%; rate difference −28.3%; 95% confidence interval [CI]: −37.9% to −18.7%)."
        result["reasoning"] = "Found absolute rate difference for live birth: IVM 22.3% vs IVF 50.6%, ARD = -28.3 percentage points (95% CI: -37.9 to -18.7). Raw event counts not provided in results text. Outcome requested OR but only ARD reported."

    elif study_id == "Keefer 2012_2012":
        # Quality of life - IBDQ scores reported as F-statistics, not means
        # "IBDQ-Total Score [F(1) = 15.2, p = .001]"
        # Effect sizes given: d = 0.45 for total score
        result["found"] = False
        result["reasoning"] = "Results report ANOVA F-statistics and effect sizes (Cohen's d) but not mean±SD values for IBDQ quality of life scores in each group. Text states 'significant group X time effects favoring PM on IBDQ-Total Score [F(1) = 15.2, p = .001]' with effect size d = 0.45, but raw scores not provided."
        result["source_quote"] = "There were significant group X time effects favoring PM on IBDQ-Total Score [F(1) = 15.2, p = .001]... Moderate effect sizes (d > .30) were observed for IBDQ total score (d =.45)"

    elif study_id == "Bernabeu 2021_2021":
        # Quality of life - found it! "quality of life (164.2 ± 34.3 vs. 176.2 ± 28.0, p = 0.001)"
        result["found"] = True
        result["effect_type"] = "MD"
        result["intervention_mean"] = 176.2  # Post-intervention group (higher is better)
        result["intervention_sd"] = 28.0
        result["control_mean"] = 164.2  # Control group
        result["control_sd"] = 34.3
        result["source_quote"] = "The psychological intervention... improved quality of life (164.2 ± 34.3 vs. 176.2 ± 28.0, p = 0.001)."
        result["reasoning"] = "Extracted quality of life scores (appears to be IBDQ or similar - higher is better). Control group: 164.2±34.3, Intervention (MCBT) group: 176.2±28.0. Intervention showed improvement."

    results.append(result)

# Save results
output_path = 'C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r5.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"Extracted data for {len(results)} studies")
print(f"Found data for: {sum(1 for r in results if r['found'])} studies")
print(f"Results saved to: {output_path}")
