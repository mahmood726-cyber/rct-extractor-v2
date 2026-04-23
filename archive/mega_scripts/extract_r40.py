# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
"""
Manual extraction script for clean_batch_r40.json
Extracts numerical outcome data from results_text for each study entry.
"""

import json
import re

def extract_outcome_data(entry):
    """
    Extract numerical outcome data for a specific study entry.

    Args:
        entry: dict with study_id, outcome, results_text, abstract

    Returns:
        dict with extraction results
    """
    study_id = entry['study_id']
    outcome = entry['outcome']
    results_text = entry.get('results_text', '')
    abstract = entry.get('abstract', '')

    # Initialize result structure
    result = {
        'study_id': study_id,
        'found': False,
        'effect_type': None,
        'point_estimate': None,
        'ci_lower': None,
        'ci_upper': None,
        'intervention_events': None,
        'intervention_n': None,
        'control_events': None,
        'control_n': None,
        'intervention_mean': None,
        'intervention_sd': None,
        'control_mean': None,
        'control_sd': None,
        'source_quote': None,
        'reasoning': None
    }

    # Study-specific extraction logic

    if study_id == "Gato-Moreno 2021_2021":
        # Outcome: zBMI (Medium Term) - looking at 2nd year (medium term)
        # From Table 2: 2nd year intervention group
        # Baseline: 0.24 ± 1.21, Final: 0.14 ± 1.05, Change: -0.10
        # Control: Baseline: 0.16 ± 0.83, Final: 0.17 ± 1.03, Change: 0.01
        # This is continuous outcome (mean difference)
        result['found'] = True
        result['effect_type'] = 'MD'
        result['intervention_mean'] = 0.14
        result['intervention_sd'] = 1.05
        result['intervention_n'] = 115
        result['control_mean'] = 0.17
        result['control_sd'] = 1.03
        result['control_n'] = 132
        result['source_quote'] = "Table 2. 2nd year: Control: 132, 0.16 ± 0.83, 0.17 ± 1.03, 0.01; Intervention: 115, 0.24 ± 1.21, 0.14 ±1.05, −0.10"
        result['reasoning'] = "Medium term = 2nd year follow-up. Final zBMI values for intervention (0.14±1.05, n=115) and control (0.17±1.03, n=132) groups extracted from Table 2."

    elif study_id == "Ostbye 2012_2012":
        # Outcome: zBMI (Short Term)
        # No zBMI data in the provided results_text - only mentions feeding practices, sugary beverage, fruit/vegetable intake
        result['found'] = False
        result['source_quote'] = None
        result['reasoning'] = "Results text does not contain child zBMI data. Only mentions maternal feeding practices (instrumental feeding, emotional feeding, TV snacks) and maternal dietary outcomes."

    elif study_id == "Morshed 2018_2018":
        # Outcome: zBMI (Medium Term)
        # Abstract states: "HEALTH intervention had no effect on children's BMI or mothers' feeding practices"
        # But no numerical data provided
        result['found'] = False
        result['source_quote'] = "HEALTH intervention had no effect on children's BMI or mothers' feeding practices."
        result['reasoning'] = "Abstract states no effect on children's BMI, but no numerical zBMI values, means, or SDs are provided in the available text."

    elif study_id == "Morgan 2022_2022":
        # Outcome: zBMI (Medium Term)
        # Results mention steps per day, FMS proficiency, parenting constructs
        # "No effects were observed for both fathers' and children's [text cut off]"
        # Likely says no effects on adiposity/BMI
        result['found'] = False
        result['source_quote'] = "No effects were observed for both fathers' and"
        result['reasoning'] = "Results text indicates no effects observed for children (text appears cut off), and no numerical zBMI data is provided. Focus is on steps/day and FMS proficiency."

    elif study_id == "Tomayko 2019_2019":
        # Outcome: zBMI (Medium Term)
        # Abstract states: "No changes were observed in adult body mass index (BMI), child BMI z-score"
        result['found'] = False
        result['source_quote'] = "No changes were observed in adult body mass index (BMI), child BMI z-score"
        result['reasoning'] = "Abstract explicitly states no changes in child BMI z-score. No numerical values provided for comparison."

    elif study_id == "Tomayko 2016_2016":
        # Outcome: BMI (Medium-Term)
        # Abstract mentions "no change in adult BMI was observed" but discusses child outcomes
        # Results mention "Obese child participants showed a reduction in BMI percentile at Year 1 that continued through Year 2 (P < 0.05)"
        # But no raw BMI values given, only percentiles
        result['found'] = False
        result['source_quote'] = "Obese child participants showed a reduction in BMI percentile at Year 1 that continued through Year 2 (P < 0.05); no change in adult BMI was observed."
        result['reasoning'] = "Results discuss BMI percentile changes for obese subgroup, but no absolute BMI values (kg/m²) are provided. Outcome specified is BMI, not BMI percentile."

    elif study_id == "Hawkins 2019_2019":
        # Outcome: zBMI (Short-Term)
        # Abstract: "BMIz, body weight, and % body weight increased in children in the Health Education arm vs. DRIVE at weeks 9 and 19"
        # No numerical zBMI values provided
        result['found'] = False
        result['source_quote'] = "BMIz, body weight, and % body weight increased in children in the Health Education arm vs. DRIVE at weeks 9 and 19."
        result['reasoning'] = "Abstract indicates BMIz increased in control vs intervention, but no numerical zBMI means or SDs are provided for extraction."

    elif study_id == "Stookey 2017_2017":
        # Outcome: zBMI (Medium Term)
        # Results: "Mean (SE) child BMI percentile (−2.6 (0.9), p = 0.003) and z-score (−0.08 (0.03), p = 0.007) decreased more in CCHP + HAP vs CCHP + HAP Delayed centers"
        # This is a DIFFERENCE (intervention minus control), not raw values
        result['found'] = True
        result['effect_type'] = 'MD'
        result['point_estimate'] = -0.08
        result['ci_lower'] = None
        result['ci_upper'] = None
        result['source_quote'] = "Mean (SE) child BMI percentile (−2.6 (0.9), p = 0.003) and z-score (−0.08 (0.03), p = 0.007) decreased more in CCHP + HAP vs CCHP + HAP Delayed centers."
        result['reasoning'] = "Mean difference in z-score change is -0.08 (SE=0.03) favoring intervention. This is the difference between groups, not raw group values. No individual group means provided."

    elif study_id == "Cunha 2013_2013":
        # Outcome: BMI medium-term
        # Results: "changes in BMI were not significantly different between the 2 groups (b = 0.003; p = 0.75)"
        # This is a regression coefficient, essentially MD ≈ 0.003
        result['found'] = True
        result['effect_type'] = 'MD'
        result['point_estimate'] = 0.003
        result['ci_lower'] = None
        result['ci_upper'] = None
        result['source_quote'] = "changes in BMI were not significantly different between the 2 groups (b = 0.003; p = 0.75)"
        result['reasoning'] = "Regression coefficient b=0.003 represents the difference in BMI change between intervention and control. Essentially zero difference."

    elif study_id == "Hammersley 2021_2021":
        # Outcome: BMI percentile (Medium-Term)
        # This is a protocol paper, not results
        result['found'] = False
        result['source_quote'] = None
        result['reasoning'] = "This appears to be a study protocol/registration, not results. Text describes planned methods and outcomes, not actual findings."

    elif study_id == "Nicholl 2021_2021":
        # Outcome: BMI short-term
        # Results: "We found no significant differential changes between dairy groups in any measure of adiposity, body composition, blood pressure..."
        result['found'] = False
        result['source_quote'] = "We found no significant differential changes between dairy groups in any measure of adiposity, body composition, blood pressure, or fasting serum lipids, glucose, HbA1c, and CRP."
        result['reasoning'] = "Results state no differential changes in adiposity measures, but no numerical BMI values are provided."

    elif study_id == "Davis 2021_2021":
        # Outcome: BMI medium-term
        # Results: "There were no effects of the intervention compared to control on fruit intake, sugar sweetened beverages, any of the obesity measures or blood pressure."
        result['found'] = False
        result['source_quote'] = "There were no effects of the intervention compared to control on fruit intake, sugar sweetened beverages, any of the obesity measures or blood pressure."
        result['reasoning'] = "Results explicitly state no effects on any obesity measures including BMI. No numerical BMI data provided."

    elif study_id == "Stettler 2015_2015":
        # Outcome: BMI medium-term
        # Results: "The increase in body mass index z-score (BMIz) for the 139 subjects (11 practices) randomized to any of the two obesity interventions (combined group) was less than that of the 33 subjects (5 practices) randomized to the control intervention (−0.089, 95%CI: −0.170 to −0.008, p=0.03)"
        # This is a DIFFERENCE in BMIz change (intervention vs control)
        result['found'] = True
        result['effect_type'] = 'MD'
        result['point_estimate'] = -0.089
        result['ci_lower'] = -0.170
        result['ci_upper'] = -0.008
        result['source_quote'] = "The increase in body mass index z-score (BMIz) for the 139 subjects (11 practices) randomized to any of the two obesity interventions (combined group) was less than that of the 33 subjects (5 practices) randomized to the control intervention (−0.089, 95%CI: −0.170 to −0.008, p=0.03)"
        result['reasoning'] = "Mean difference in BMIz change between combined intervention (n=139) and control (n=33) is -0.089 with 95% CI [-0.170, -0.008]. Note: outcome is 'BMI medium-term' but data reported is BMIz. Using as reported."

    elif study_id == "Coleman 2012_2012":
        # Outcome: zBMI medium-term
        # Results: "Changes in rates of obesity for intervention school (28% baseline, 27% year 1, 30% year 2) were similar to those seen for control school (22% baseline, 22% year 1, 25% year 2) children."
        # Only obesity rates given, no zBMI values
        result['found'] = False
        result['source_quote'] = "Changes in rates of obesity for intervention school (28% baseline, 27% year 1, 30% year 2) were similar to those seen for control school (22% baseline, 22% year 1, 25% year 2) children."
        result['reasoning'] = "Results report obesity prevalence percentages only. No zBMI means or standard deviations provided."

    elif study_id == "Ickovics 2019_2019":
        # Outcome: Percentile long-term
        # Results: "Students at schools randomized to receive support for nutrition policy implementation had healthier BMI trajectories over time (F=3.20, p=0.02), with a greater magnitude over time and cumulatively significant effects 3 years post-intervention (β= −2.40, p=0.04)"
        # Beta coefficient of -2.40 for BMI percentile at 3 years
        result['found'] = True
        result['effect_type'] = 'MD'
        result['point_estimate'] = -2.40
        result['ci_lower'] = None
        result['ci_upper'] = None
        result['source_quote'] = "Students at schools randomized to receive support for nutrition policy implementation had healthier BMI trajectories over time (F=3.20, p=0.02), with a greater magnitude over time and cumulatively significant effects 3 years post-intervention (β= −2.40, p=0.04)."
        result['reasoning'] = "Regression coefficient β=-2.40 (p=0.04) represents the difference in BMI percentile at 3 years between nutrition intervention and control groups. Text also mentions '<1% increase vs 3-4% increase' but uses the regression estimate."

    # For any entries not explicitly coded above
    else:
        result['found'] = False
        result['source_quote'] = None
        result['reasoning'] = f"Entry {study_id} not recognized in extraction logic."

    return result


def main():
    # Load input file
    input_file = 'C:/Users/user/rct-extractor-v2/gold_data/mega/clean_batch_r40.json'
    output_file = 'C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r40.json'

    with open(input_file, 'r', encoding='utf-8') as f:
        entries = json.load(f)

    print(f"Processing {len(entries)} entries...")

    results = []
    for entry in entries:
        result = extract_outcome_data(entry)
        results.append(result)
        status = "FOUND" if result['found'] else "NOT FOUND"
        print(f"{result['study_id']}: {status}")

    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nExtraction complete. Results written to {output_file}")
    print(f"Found: {sum(1 for r in results if r['found'])}/{len(results)}")


if __name__ == '__main__':
    main()
