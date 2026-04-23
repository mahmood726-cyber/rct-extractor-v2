# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
import json

# Read the batch file
with open('C:/Users/user/rct-extractor-v2/gold_data/mega/clean_batch_r39.json', 'r', encoding='utf-8') as f:
    batch_data = json.load(f)

results = []

# Process all 15 entries
# I'll need to manually review each results_text to extract explicit data

# Entry 1: Ebbert 2007_2007 - Tobacco cessation
result = {
    'study_id': 'Ebbert 2007_2007',
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
    'source_quote': 'Results text discusses nicotine replacement percentages and serum concentrations.',
    'reasoning': 'Results text does not provide explicit tobacco cessation outcome data for longest follow-up.'
}
results.append(result)

# Entry 2: Noonan 2020_2020 - Tobacco cessation
result = {
    'study_id': 'Noonan 2020_2020',
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
    'source_quote': 'The quit rate at 6-months was 21% (p=0.9703) for both groups.',
    'reasoning': 'Percentages given (21% both groups at 6 months) but explicit event counts not stated. Would require calculation.'
}
results.append(result)

# Entry 3: Ebbert 2010_2010 - Tobacco cessation
result = {
    'study_id': 'Ebbert 2010_2010',
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
    'source_quote': 'At 6 months, self-reported point prevalence all tobacco abstinence rate was 30% in nicotine lozenge group and 47% in placebo.',
    'reasoning': 'Percentages given but explicit event counts not stated. Would need to calculate from 30% of 30 and 47% of 30.'
}
results.append(result)

# Entry 4: Dale 2007_2007 - Tobacco cessation
result = {
    'study_id': 'Dale 2007_2007',
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
    'source_quote': 'The 7-day point prevalence abstinence did not differ at weeks 24 and 52.',
    'reasoning': 'Mentions 52-week outcome but provides no numerical data for this timepoint.'
}
results.append(result)

# Entry 5: Reilly 2006_2006 - zBMI Short-term
result = {
    'study_id': 'Reilly 2006_2006',
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
    'source_quote': 'Group allocation had no significant effect on the primary outcome measure at six and 12 months',
    'reasoning': 'No explicit numerical BMI z-score data provided.'
}
results.append(result)

# Entry 6: Fisher 2019_2019 - zBMI Short-term
result = {
    'study_id': 'Fisher 2019_2019',
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
    'source_quote': 'Neither child total daily energy intake nor BMI z-scores differed between groups post-intervention.',
    'reasoning': 'BMI z-scores mentioned but no explicit numerical values provided.'
}
results.append(result)

# Entry 7: Yoong 2020_2020 - zBMI Medium-term
result = {
    'study_id': 'Yoong 2020_2020',
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
    'source_quote': 'No significant differences were observed in diet quality, BMI z scores, or HRQoL.',
    'reasoning': 'BMI z-scores mentioned but no explicit numerical values provided.'
}
results.append(result)

# Entry 8: Bonvin 2013_2013 - BMI Medium-term
result = {
    'study_id': 'Bonvin 2013_2013',
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
    'source_quote': 'No significant increase in motor skills or in any of the secondary outcomes.',
    'reasoning': 'Secondary outcomes include BMI but no explicit values provided.'
}
results.append(result)

# Entry 9: Barber 2016_2016 - zBMI Medium-term
result = {
    'study_id': 'Barber 2016_2016',
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
    'source_quote': 'The mean difference in daily MVPA between trial arms at 52 weeks was 0.4, 95% CI 16.3 to 17.0',
    'reasoning': 'MVPA data provided but no explicit BMI z-score data for the requested outcome.'
}
results.append(result)

# Entry 10: Heerman 2019_2019 - BMI Short-term
result = {
    'study_id': 'Heerman 2019_2019',
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
    'source_quote': 'Prospective cohort analysis of parent-child pairs...',
    'reasoning': 'This is a cohort study examining predictors of obesity, not an RCT with intervention vs control for BMI outcome.'
}
results.append(result)

# Entry 11: Vaughn 2021_2021 - BMI Short-term
result = {
    'study_id': 'Vaughn 2021_2021',
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
    'source_quote': 'No significant changes were noted in any of the outcome measures',
    'reasoning': 'No explicit numerical BMI data provided.'
}
results.append(result)

# Entry 12: Alkon 2014_2014 - zBMI Short Term
result = {
    'study_id': 'Alkon 2014_2014',
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
    'source_quote': 'Results showed significant increases in providers and parents knowledge...and child-level changes in childrens zBMI based on 209 children',
    'reasoning': 'Results mention child-level changes in zBMI but do not provide explicit numerical values (means, SDs, or effect size with CI).'
}
results.append(result)

# Entry 13: Derwig 2021_2021 - BMI Medium Term
result = {
    'study_id': 'Derwig 2021_2021',
    'found': True,
    'effect_type': 'MD',
    'point_estimate': -0.11,
    'ci_lower': -0.24,
    'ci_upper': 0.01,
    'intervention_events': None,
    'intervention_n': None,
    'control_events': None,
    'control_n': None,
    'intervention_mean': None,
    'intervention_sd': None,
    'control_mean': None,
    'control_sd': None,
    'source_quote': 'The intervention effect on zBMI-change for children with overweight was -0.11, with a 95% confidence interval of -0.24 to 0.01 (p = 0.07).',
    'reasoning': 'Explicit mean difference and 95% CI provided for zBMI change in children with overweight at follow-up (mean age 5.1 years, approximately 1 year follow-up from baseline age 4.1 years).'
}
results.append(result)

# Entry 14: Davis 2016_2016 - zBMI Short Term
result = {
    'study_id': 'Davis 2016_2016',
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
    'source_quote': 'At the end of the intervention, there was no significant difference between the two groups in BMI z-scores.',
    'reasoning': 'Results state no significant difference but do not provide explicit numerical values for BMI z-scores.'
}
results.append(result)

# Entry 15: Malden 2019_2019 - zBMI Short Term
result = {
    'study_id': 'Malden 2019_2019',
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
    'source_quote': 'Both intervention and control groups showed small increases in BMI z-scores at follow-up of 0.02 and 0.06, respectively.',
    'reasoning': 'Within-group changes provided (intervention +0.02, control +0.06) but no between-group effect estimate or CI explicitly stated. Would need to calculate difference.'
}
results.append(result)

# Write output
with open('C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r39.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"Extraction complete: {len(results)} entries processed")
print("Output written to: C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r39.json")
