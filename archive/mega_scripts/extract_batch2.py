# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
import json
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Read input
with open(r'C:\Users\user\rct-extractor-v2\gold_data\mega\clean_batch_2.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

results = []

# STUDY 1: Lepore 2012 - Knowledge (continuous)
results.append({
    'study_id': 'Lepore 2012_2012',
    'found': False,
    'effect_type': 'NONE',
    'point_estimate': None, 'ci_lower': None, 'ci_upper': None,
    'intervention_events': None, 'intervention_n': None,
    'control_events': None, 'control_n': None,
    'intervention_mean': None, 'intervention_sd': None, 'intervention_n_cont': None,
    'control_mean': None, 'control_sd': None, 'control_n_cont': None,
    'source_quote': '',
    'reasoning': 'Abstract states "greater knowledge" but no specific numeric values reported in text'
})

# STUDY 2: Krist 2007 - Knowledge (continuous)
results.append({
    'study_id': 'Krist 2007_2007',
    'found': True,
    'effect_type': 'MD',
    'point_estimate': 15.0,
    'ci_lower': None, 'ci_upper': None,
    'intervention_events': None, 'intervention_n': None,
    'control_events': None, 'control_n': None,
    'intervention_mean': 69.0, 'intervention_sd': None, 'intervention_n_cont': 226,
    'control_mean': 54.0, 'control_sd': None, 'control_n_cont': 75,
    'source_quote': '54% control vs 69% Web site, P <.001',
    'reasoning': 'Knowledge score as percentage correct answers: 69% website vs 54% control (MD = 15 percentage points)'
})

# STUDY 3: Manne 2020 - Knowledge (continuous)
results.append({
    'study_id': 'Manne 2020_2020',
    'found': False,
    'effect_type': 'NONE',
    'point_estimate': None, 'ci_lower': None, 'ci_upper': None,
    'intervention_events': None, 'intervention_n': None,
    'control_events': None, 'control_n': None,
    'intervention_mean': None, 'intervention_sd': None, 'intervention_n_cont': None,
    'control_mean': None, 'control_sd': None, 'control_n_cont': None,
    'source_quote': '',
    'reasoning': 'Abstract states "higher knowledge about CPM" but numeric values not in available text'
})

# STUDY 4: Meade 2015 - Knowledge (continuous)
results.append({
    'study_id': 'Meade 2015_2015',
    'found': True,
    'effect_type': 'MD',
    'point_estimate': 12.0,
    'ci_lower': None, 'ci_upper': None,
    'intervention_events': None, 'intervention_n': None,
    'control_events': None, 'control_n': None,
    'intervention_mean': 13.0, 'intervention_sd': None, 'intervention_n_cont': None,
    'control_mean': 1.0, 'control_sd': None, 'control_n_cont': None,
    'source_quote': 'DA had a 13 % increase in relevant knowledge (PiRAQ) scores...compared to the control group (1 %, 2 % respectively)',
    'reasoning': 'Change in knowledge scores: 13% increase in DA group vs 1% in control (MD = 12 percentage points)'
})

# STUDY 5: Montgomery 2007 - Knowledge (continuous)
results.append({
    'study_id': 'Montgomery 2007_2007',
    'found': False,
    'effect_type': 'NONE',
    'point_estimate': None, 'ci_lower': None, 'ci_upper': None,
    'intervention_events': None, 'intervention_n': None,
    'control_events': None, 'control_n': None,
    'intervention_mean': None, 'intervention_sd': None, 'intervention_n_cont': None,
    'control_mean': None, 'control_sd': None, 'control_n_cont': None,
    'source_quote': '',
    'reasoning': 'No numeric knowledge data found in available text'
})

# STUDY 6: Morgan 2000 - Knowledge (continuous)
results.append({
    'study_id': 'Morgan 2000_2000',
    'found': True,
    'effect_type': 'MD',
    'point_estimate': 13.0,
    'ci_lower': 8.0, 'ci_upper': 18.0,
    'intervention_events': None, 'intervention_n': None,
    'control_events': None, 'control_n': None,
    'intervention_mean': 75.0, 'intervention_sd': None, 'intervention_n_cont': None,
    'control_mean': 62.0, 'control_sd': None, 'control_n_cont': None,
    'source_quote': 'intervention group had higher knowledge scores (75% vs 62%; 95% CI for 13% difference, 8% to 18%)',
    'reasoning': 'Knowledge scores: 75% intervention vs 62% control, MD = 13 percentage points (95% CI 8 to 18)'
})

# STUDY 7: Perestelo-Perez 2019 - Knowledge (continuous)
results.append({
    'study_id': 'Perestelo-Perez 2019_2019',
    'found': False,
    'effect_type': 'NONE',
    'point_estimate': None, 'ci_lower': None, 'ci_upper': None,
    'intervention_events': None, 'intervention_n': None,
    'control_events': None, 'control_n': None,
    'intervention_mean': None, 'intervention_sd': None, 'intervention_n_cont': None,
    'control_mean': None, 'control_sd': None, 'control_n_cont': None,
    'source_quote': '',
    'reasoning': 'No numeric knowledge data found in available text'
})

# STUDY 8: Perestelo-Perez 2017 - Knowledge (continuous)
results.append({
    'study_id': 'Perestelo-Perez 2017_2017',
    'found': False,
    'effect_type': 'NONE',
    'point_estimate': None, 'ci_lower': None, 'ci_upper': None,
    'intervention_events': None, 'intervention_n': None,
    'control_events': None, 'control_n': None,
    'intervention_mean': None, 'intervention_sd': None, 'intervention_n_cont': None,
    'control_mean': None, 'control_sd': None, 'control_n_cont': None,
    'source_quote': '',
    'reasoning': 'No numeric knowledge data found in available text'
})

# STUDY 9: Thomson 2007 - Knowledge (continuous)
results.append({
    'study_id': 'Thomson 2007_2007',
    'found': False,
    'effect_type': 'NONE',
    'point_estimate': None, 'ci_lower': None, 'ci_upper': None,
    'intervention_events': None, 'intervention_n': None,
    'control_events': None, 'control_n': None,
    'intervention_mean': None, 'intervention_sd': None, 'intervention_n_cont': None,
    'control_mean': None, 'control_sd': None, 'control_n_cont': None,
    'source_quote': '',
    'reasoning': 'Only decision outcomes (warfarin uptake) reported, no knowledge scores'
})

# STUDY 10: Schapira 2019 - Knowledge (continuous)
results.append({
    'study_id': 'Schapira 2019_2019',
    'found': True,
    'effect_type': 'MD',
    'point_estimate': 0.67,
    'ci_lower': None, 'ci_upper': None,
    'intervention_events': None, 'intervention_n': None,
    'control_events': None, 'control_n': None,
    'intervention_mean': 3.84, 'intervention_sd': None, 'intervention_n_cont': None,
    'control_mean': 3.17, 'control_sd': None, 'control_n_cont': None,
    'source_quote': 'Follow-up knowledge (0-5)...3.84 (3.5-4.2) versus 3.17 (2.8-3.5), P = 0.01',
    'reasoning': 'Knowledge score (0-5 scale): 3.84 intervention vs 3.17 control (MD = 0.67 points)'
})

# STUDY 11-15: All not found
for study_id in ['Tilburt 2022_2022', 'Varelas 2020_2020', 'Oostendorp 2017_2017',
                  'Wallace 2021_2021', 'Williams 2013_2013']:
    results.append({
        'study_id': study_id,
        'found': False,
        'effect_type': 'NONE',
        'point_estimate': None, 'ci_lower': None, 'ci_upper': None,
        'intervention_events': None, 'intervention_n': None,
        'control_events': None, 'control_n': None,
        'intervention_mean': None, 'intervention_sd': None, 'intervention_n_cont': None,
        'control_mean': None, 'control_sd': None, 'control_n_cont': None,
        'source_quote': '',
        'reasoning': 'No numeric outcome data found in available text'
    })

# STUDY 16: Mathers 2012 - Accurate risk perceptions (binary)
results.append({
    'study_id': 'Mathers 2012_2012',
    'found': True,
    'effect_type': 'RR',
    'point_estimate': None, 'ci_lower': None, 'ci_upper': None,
    'intervention_events': None, 'intervention_n': None,
    'control_events': None, 'control_n': None,
    'intervention_mean': 51.6, 'intervention_sd': None, 'intervention_n_cont': None,
    'control_mean': 28.8, 'control_sd': None, 'control_n_cont': None,
    'source_quote': 'better knowledge (51.6% vs 28.8%, p<0.001)',
    'reasoning': 'Binary outcome reported as percentages: 51.6% intervention vs 28.8% control. Need sample sizes to compute event counts.'
})

# STUDY 17: Wolf 2000 - Accurate risk perceptions (binary)
results.append({
    'study_id': 'Wolf 2000_2000',
    'found': True,
    'effect_type': 'RR',
    'point_estimate': None, 'ci_lower': None, 'ci_upper': None,
    'intervention_events': None, 'intervention_n': None,
    'control_events': None, 'control_n': None,
    'intervention_mean': 71.1, 'intervention_sd': None, 'intervention_n_cont': None,
    'control_mean': 8.0, 'control_sd': None, 'control_n_cont': None,
    'source_quote': '8% of control patients responded correctly, compared with 71.1% of patients who received screening information',
    'reasoning': 'Binary outcome (correct response) as percentages: 71.1% intervention vs 8% control. Need sample sizes to compute event counts.'
})

# STUDY 18-20: All not found
for study_id in ['De Achaval 2012_2012', 'Vodermaier 2009_2009', 'Berry 2018_2018']:
    results.append({
        'study_id': study_id,
        'found': False,
        'effect_type': 'NONE',
        'point_estimate': None, 'ci_lower': None, 'ci_upper': None,
        'intervention_events': None, 'intervention_n': None,
        'control_events': None, 'control_n': None,
        'intervention_mean': None, 'intervention_sd': None, 'intervention_n_cont': None,
        'control_mean': None, 'control_sd': None, 'control_n_cont': None,
        'source_quote': '',
        'reasoning': 'No numeric outcome data found in available text'
    })

# Write output
output_path = r'C:\Users\user\rct-extractor-v2\gold_data\mega\clean_results_batch2.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"Wrote {len(results)} results to clean_results_batch2.json")
print(f"\nSummary:")
print(f"  Found data: {sum(1 for r in results if r['found'])}/20")
print(f"\nStudies with extracted data:")
for r in results:
    if r['found']:
        print(f"  - {r['study_id']}: {r['effect_type']}, PE={r['point_estimate']}")
