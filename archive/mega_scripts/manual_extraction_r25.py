# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
"""
Manual extraction for clean_batch_r25.json
Each study requires careful reading of the results_text to extract numerical outcome data.
"""

import json

def extract_data():
    results = []

    # Study 1: Anand 2008 - PIPP during endotracheal suctioning
    results.append({
        'study_id': 'Anand 2008_2008',
        'found': False,
        'effect_type': 'NONE',
        'point_estimate': None, 'ci_lower': None, 'ci_upper': None,
        'intervention_events': None, 'intervention_n': None,
        'control_events': None, 'control_n': None,
        'intervention_mean': None, 'intervention_sd': None,
        'control_mean': None, 'control_sd': None,
        'source_quote': '',
        'reasoning': 'Results text states "There was no relationship between morphine concentrations (range 0–440 mg litre−1) and heart rate changes associated with ETT suctioning or with the Premature Infant Pain Profile." No specific PIPP scores during ETT suctioning are reported for morphine vs placebo groups.'
    })

    # Study 2: Daubenmier 2016 - Systolic blood pressure change
    results.append({
        'study_id': 'Daubenmier 2016_2016',
        'found': False,
        'effect_type': 'NONE',
        'point_estimate': None, 'ci_lower': None, 'ci_upper': None,
        'intervention_events': None, 'intervention_n': None,
        'control_events': None, 'control_n': None,
        'intervention_mean': None, 'intervention_sd': None,
        'control_mean': None, 'control_sd': None,
        'source_quote': 'Estimates for other metabolic risk factors were not statistically significant, including waist circumference, blood pressure, and C-reactive protein.',
        'reasoning': 'Results abstract states blood pressure changes were not statistically significant, but does not provide specific values for systolic BP change from baseline in mindfulness vs control groups.'
    })

    # Study 3: Raja-Khan 2017 - Systolic blood pressure change
    results.append({
        'study_id': 'Raja-Khan 2017_2017',
        'found': False,
        'effect_type': 'NONE',
        'point_estimate': None, 'ci_lower': None, 'ci_upper': None,
        'intervention_events': None, 'intervention_n': None,
        'control_events': None, 'control_n': None,
        'intervention_mean': None, 'intervention_sd': None,
        'control_mean': None, 'control_sd': None,
        'source_quote': 'There were no significant changes in blood pressure, weight, or insulin resistance in the MBSR group.',
        'reasoning': 'Results state no significant changes in blood pressure in MBSR group, but no specific values for systolic BP change are provided for either group.'
    })

    # Study 4: Carpenter 2019 - Anxiety change
    results.append({
        'study_id': 'Carpenter 2019_2019',
        'found': False,
        'effect_type': 'NONE',
        'point_estimate': None, 'ci_lower': None, 'ci_upper': None,
        'intervention_events': None, 'intervention_n': None,
        'control_events': None, 'control_n': None,
        'intervention_mean': None, 'intervention_sd': None,
        'control_mean': None, 'control_sd': None,
        'source_quote': '',
        'reasoning': 'Results text mentions GAD-7 scores at baseline (46.6% had scores ≥10) but does not report anxiety change from baseline at 6 months for intervention vs control groups. Focus is on mindful eating, binge eating, and weight outcomes.'
    })

    # Study 5: Miller 2014 - Anxiety change
    results.append({
        'study_id': 'Miller 2014_2014',
        'found': False,
        'effect_type': 'NONE',
        'point_estimate': None, 'ci_lower': None, 'ci_upper': None,
        'intervention_events': None, 'intervention_n': None,
        'control_events': None, 'control_n': None,
        'intervention_mean': None, 'intervention_sd': None,
        'control_mean': None, 'control_sd': None,
        'source_quote': 'Both groups experienced significant reduction in depressive symptoms at study end, and the SC group experienced significant reduction in anxiety postintervention and at study end (all p < .01).',
        'reasoning': 'States SC group had significant reduction in anxiety but does not provide specific mean changes or SD for anxiety in MB-EAT-D vs SC groups. No numeric data for anxiety measure.'
    })

    # Study 6: Gavin 2020 - Venous thromboembolism
    results.append({
        'study_id': 'Gavin 2020_2020',
        'found': False,
        'effect_type': 'NONE',
        'point_estimate': None, 'ci_lower': None, 'ci_upper': None,
        'intervention_events': None, 'intervention_n': None,
        'control_events': None, 'control_n': None,
        'intervention_mean': None, 'intervention_sd': None,
        'control_mean': None, 'control_sd': None,
        'source_quote': '',
        'reasoning': 'Results report PICC failure rates (24% intervention, 22% control) but do not specifically report venous thromboembolism events. Thrombosis mentioned as one type of failure but no separate counts given.'
    })

    # Study 7: Brosnahan 2022 - Change in eGFR
    results.append({
        'study_id': 'Brosnahan 2022_2022',
        'found': False,
        'effect_type': 'NONE',
        'point_estimate': None, 'ci_lower': None, 'ci_upper': None,
        'intervention_events': None, 'intervention_n': None,
        'control_events': None, 'control_n': None,
        'intervention_mean': None, 'intervention_sd': None,
        'control_mean': None, 'control_sd': None,
        'source_quote': 'In exploratory analyses, changes in height-adjusted total kidney volume or eGFR were not significantly different between groups.',
        'reasoning': 'States eGFR changes were not significantly different between metformin and placebo but does not provide specific mean change values or SD for either group.'
    })

    # Study 8: Taraskina 2017 - Mental state (PANSS/BPRS)
    results.append({
        'study_id': 'Taraskina 2017_2017',
        'found': False,
        'effect_type': 'NONE',
        'point_estimate': None, 'ci_lower': None, 'ci_upper': None,
        'intervention_events': None, 'intervention_n': None,
        'control_events': None, 'control_n': None,
        'intervention_mean': None, 'intervention_sd': None,
        'control_mean': None, 'control_sd': None,
        'source_quote': '',
        'reasoning': 'Results discuss correlations between biomarkers (5HTR2A mRNA, dopamine) and PANSS scores but do not report endpoint PANSS total scores for olanzapine vs haloperidol groups.'
    })

    # Study 9: Mousavi 2013 - Weight increase
    results.append({
        'study_id': 'Mousavi 2013_2013',
        'found': False,
        'effect_type': 'NONE',
        'point_estimate': None, 'ci_lower': None, 'ci_upper': None,
        'intervention_events': None, 'intervention_n': None,
        'control_events': None, 'control_n': None,
        'intervention_mean': None, 'intervention_sd': None,
        'control_mean': None, 'control_sd': None,
        'source_quote': 'The most common side‑effects were sedation and drug induced Parkinsonism.',
        'reasoning': 'Results mention sedation and Parkinsonism as most common side effects but do not report weight increase as an adverse event or provide counts by treatment group.'
    })

    # Study 10: Fayad 2017 - Stone-free rate
    results.append({
        'study_id': 'Fayad 2017_2017',
        'found': True,
        'effect_type': 'NONE',
        'point_estimate': None, 'ci_lower': None, 'ci_upper': None,
        'intervention_events': 51, 'intervention_n': 55,
        'control_events': 43, 'control_n': 51,
        'intervention_mean': None, 'intervention_sd': None,
        'control_mean': None, 'control_sd': None,
        'source_quote': 'The SFR for Group A was 92.72% and for Group B it was 84.31%, which was not significantly different (P = 0.060).',
        'reasoning': 'Group A (mini-PCNL) had 92.72% SFR from 55 patients = 51 stone-free. Group B (RIRS) had 84.31% SFR from 51 patients = 43 stone-free. Calculated from percentages: 55*0.9272≈51, 51*0.8431≈43.'
    })

    # Study 11: Mhaske 2018 - Stone-free rate
    results.append({
        'study_id': 'Mhaske 2018_2018',
        'found': True,
        'effect_type': 'NONE',
        'point_estimate': None, 'ci_lower': None, 'ci_upper': None,
        'intervention_events': 40, 'intervention_n': 40,
        'control_events': 38, 'control_n': 40,
        'intervention_mean': None, 'intervention_sd': None,
        'control_mean': None, 'control_sd': None,
        'source_quote': 'The mini‑perc group had complete clearance in all the cases. The success rate in mini‑perc group was 100% as compared to RIRS group which had success rate of 95%',
        'reasoning': 'Mini-perc group: 100% success rate with n=40 → 40/40 stone-free. RIRS group: 95% success rate with n=40 → 38/40 stone-free.'
    })

    # Study 12: Krogshede 2022 - ETDQ-7 change
    results.append({
        'study_id': 'Krogshede 2022_2022',
        'found': False,
        'effect_type': 'NONE',
        'point_estimate': None, 'ci_lower': None, 'ci_upper': None,
        'intervention_events': None, 'intervention_n': None,
        'control_events': None, 'control_n': None,
        'intervention_mean': None, 'intervention_sd': None,
        'control_mean': None, 'control_sd': None,
        'source_quote': 'There was no significant difference in mean Eustachian Tube Dysfunction Questionnaire-7 score between the two groups (P = .35).',
        'reasoning': 'States no significant difference in mean ETDQ-7 score between balloon dilation and control groups but does not provide the actual mean change values or SDs.'
    })

    # Study 13: Resick 2002 - PTSD symptoms post-treatment
    results.append({
        'study_id': 'Resick 2002_2002',
        'found': False,
        'effect_type': 'NONE',
        'point_estimate': None, 'ci_lower': None, 'ci_upper': None,
        'intervention_events': None, 'intervention_n': None,
        'control_events': None, 'control_n': None,
        'intervention_mean': None, 'intervention_sd': None,
        'control_mean': None, 'control_sd': None,
        'source_quote': '',
        'reasoning': 'Abstract states both CPT and PE were superior to MA (minimal attention) but does not provide specific PTSD symptom scores. Results text is truncated and does not contain numerical outcomes for comparison.'
    })

    # Study 14: Littleton 2016 - PTSD symptoms post-treatment
    results.append({
        'study_id': 'Littleton 2016_2016',
        'found': False,
        'effect_type': 'NONE',
        'point_estimate': None, 'ci_lower': None, 'ci_upper': None,
        'intervention_events': None, 'intervention_n': None,
        'control_events': None, 'control_n': None,
        'intervention_mean': None, 'intervention_sd': None,
        'control_mean': None, 'control_sd': None,
        'source_quote': 'Both programs led to large reductions in interview-assessed PTSD at post-treatment (interactive d = 2.22, psycho-educational d = 1.10)',
        'reasoning': 'Abstract reports effect sizes (Cohen d) but not raw mean PTSD scores or SDs at post-treatment. Results text discusses methods and design but numerical outcomes are not in the provided excerpt.'
    })

    # Study 15: Walsh 2017 - PTSD symptoms post-treatment
    results.append({
        'study_id': 'Walsh 2017_2017',
        'found': False,
        'effect_type': 'NONE',
        'point_estimate': None, 'ci_lower': None, 'ci_upper': None,
        'intervention_events': None, 'intervention_n': None,
        'control_events': None, 'control_n': None,
        'intervention_mean': None, 'intervention_sd': None,
        'control_mean': None, 'control_sd': None,
        'source_quote': '',
        'reasoning': 'Study focused on substance use outcomes (alcohol and marijuana) following sexual assault. Results text discusses substance use findings but does not report PTSD symptom scores for PPRS vs TAU or PIRI groups.'
    })

    return results

if __name__ == '__main__':
    results = extract_data()

    with open('C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r25.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Extracted data for {len(results)} studies")
    found_count = sum(1 for r in results if r['found'])
    print(f"Found data in {found_count} studies")
    print(f"No data found in {len(results) - found_count} studies")
