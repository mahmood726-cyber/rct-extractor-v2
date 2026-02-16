#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Manual extraction of outcome data from clean_batch_r26.json
Only extract data that is EXPLICITLY stated in results_text.
Never calculate or infer values.
"""

import json
import re

def extract_entry(entry):
    """Extract outcome data from a single study entry."""
    study_id = entry['study_id']
    outcome = entry['outcome']
    data_type = entry['data_type']
    results_text = entry['results_text']

    result = {
        'study_id': study_id,
        'found': False,
        'effect_type': 'NONE',
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
        'source_quote': '',
        'reasoning': ''
    }

    # Study-specific extraction logic

    if study_id == 'Sikkema 2018_2018':
        # Outcome: PTSD symptoms, post-treatment (continuous)
        # No explicit numerical data for PTSD symptoms in results_text
        result['found'] = False
        result['reasoning'] = 'Results mention "greater reductions in avoidance and arousal symptoms of PTSD" and "Clinically significant decreases in overall PTSD symptoms" but no explicit numerical values (means, SDs) are reported in the results_text for the PTSD outcome measure.'
        result['source_quote'] = 'ImpACT participants, compared to SoC, reported greater reductions in avoidance and arousal symptoms of PTSD...'

    elif study_id == 'Covers 2021_2021':
        # Outcome: PTSD symptoms, post-treatment (continuous)
        # Effect sizes mentioned but not raw means/SDs
        result['found'] = False
        result['reasoning'] = 'Results report within-group effect sizes (EMDR d=0.89-1.57, control d=0.79-1.54) but do not provide raw means and standard deviations for PTSD symptoms. Effect sizes alone are not sufficient without the underlying statistics.'
        result['source_quote'] = 'Within-group effect sizes of the EMDR condition (d = 0.89 to 1.57) and control condition (d = 0.79 to 1.54) were large, indicating that both conditions were effective.'

    elif study_id == 'Mohammadi 2018_2018':
        # Outcome: Change in burn-related pruritus (continuous)
        result['found'] = False
        result['reasoning'] = 'Results state "enalapril treated scars had significantly lower itching scores compared to the placebo group" but do not provide explicit numerical values for itching scores (mean ± SD) in either group.'
        result['source_quote'] = 'enalapril treated scars had significantly lower itching scores compared to the placebo group.'

    elif study_id == 'Thibaut 2019_2019':
        # Outcome: Change in burn-related pruritus (continuous)
        result['found'] = False
        result['reasoning'] = 'Results mention "itch levels were reduced at 2-week follow-up after the sham tDCS session" and use VAS itch scale, but no explicit numerical values (means ± SD) for itch scores are reported in the results section.'
        result['source_quote'] = 'We identified that itch levels were reduced at 2-week follow-up after the sham tDCS session, while no placebo effect was found for the active group.'

    elif study_id == 'Agren 2012_2012':
        # Outcome: Depression (continuous)
        result['found'] = False
        result['reasoning'] = 'Results state "No group differences were observed over time in dyads\' health-related quality of life and depressive symptoms" but do not report explicit numerical values for depression measures.'
        result['source_quote'] = 'No group differences were observed over time in dyads\' health-related quality of life and depressive symptoms, patients\' self-care behaviors, and partners\' experiences of caregiver burden.'

    elif study_id == 'Byrd 2018_2018':
        # Outcome: Overall survival (time to event)
        # Results_text is truncated and contains only references section
        result['found'] = False
        result['reasoning'] = 'The results_text provided is a references section only, with no outcome data. Cannot extract survival data from bibliography.'
        result['source_quote'] = 'N/A - results_text contains only references'

    elif study_id == 'Freedland 2009_2009':
        # Outcome: Depression (continuous)
        # Hamilton scores reported!
        result['found'] = True
        result['effect_type'] = 'MD'
        result['control_mean'] = 10.7
        result['control_sd'] = 1.0  # standard error reported
        result['intervention_mean'] = 5.5  # CBT group
        result['intervention_sd'] = 1.0
        result['source_quote'] = 'Covariate-adjusted Hamilton scores were lower in the cognitive behavior therapy (mean [standard error], 5.5 [1.0]) and the supportive stress-management (7.8 [1.0]) arms than in the usual care arm (10.7 [1.0]) at 3 months.'
        result['reasoning'] = 'Hamilton Depression Rating Scale scores at 3 months explicitly reported with mean and standard error. CBT vs usual care comparison. Note: SE reported, not SD.'

    elif study_id == 'Kumar 2020_2020':
        # Outcome: Caregiver burden (≤ 1 month postintervention) (continuous)
        result['found'] = False
        result['reasoning'] = 'Results section describes the BPI intervention methods and group therapy sessions but does not present numerical outcome data for caregiver burden measures.'
        result['source_quote'] = 'N/A - methods description only in results_text'

    elif study_id == 'Nijjar 2019_2019':
        # Outcome: Depression (continuous)
        # PHQ-9 change reported!
        result['found'] = True
        result['effect_type'] = 'MD'
        result['intervention_mean'] = -2.3  # Change score
        # SD not explicitly stated for the change, need to extract from table if available
        # Looking at p=0.01, this is significant
        result['source_quote'] = 'The change was statistically significant for depression (P = 0.01)... While the average 3-month change in PHQ9 scores in the MBSR group was −2.3 points'
        result['reasoning'] = 'Change in PHQ-9 scores explicitly reported for MBSR group (-2.3 points). However, SD for change not reported, and control group change value not explicitly stated in results narrative. Incomplete data.'
        result['found'] = False  # Change to false - incomplete
        result['intervention_mean'] = None

    elif study_id == 'Song 2006_2006':
        # Outcome: Participant-reported cure or improvement (binary)
        # Satisfaction/improvement rates reported as percentages only
        result['found'] = False
        result['source_quote'] = 'Satisfaction scores at 12 weeks did not differ among the three groups, being 1.5 in the BT group, with improvement in 53.9%; 1.4 in the To group, with improvement in 63.0%; and 1.3 in the Co group, with improvement in 71.0%.'
        result['reasoning'] = 'Binary outcome (cure/improvement) reported as percentages (BT: 53.9%, To: 63.0%, Co: 71.0%) with sample sizes known (BT n=26, To n=32, Co n=31). However, the actual number of events (people who improved) is not explicitly stated - it would require calculation from percentages. Per extraction rules, only explicitly stated values are extracted.'

    elif study_id == 'Sharif 2012_2012':
        # Outcome: Caregiver burden (≤ 1 month postintervention) (continuous)
        result['found'] = False
        result['reasoning'] = 'Results state "significantly reduced symptom severity and caregiver burden both immediately after intervention and one month later" but do not provide explicit numerical values (means ± SD) for caregiver burden scores.'
        result['source_quote'] = 'Compared with the control group, the case group showed significantly reduced symptom severity and caregiver burden both immediately after intervention and one month later.'

    elif study_id == 'Eleuterio 2019_2019':
        # Outcome: Frequency of crisis
        result['found'] = False
        result['reasoning'] = 'Results discuss nitrite/nitrate levels and "reduction in pain frequency using a pain frequency scale" but do not provide explicit numerical values for crisis frequency in intervention vs control groups.'
        result['source_quote'] = 'there was also a reduction in pain frequency using a pain frequency scale by day, week, and month'

    elif study_id == 'Scoffone 2013_2013':
        # Outcome: Haemoglobin status (continuous)
        # Hemoglobin S mentioned but not clear hemoglobin levels
        result['found'] = False
        result['reasoning'] = 'Text mentions "difference in hemoglobin S level" and transfusion rates but does not report explicit numerical values for hemoglobin levels (g/dL) with means and SDs for both groups.'
        result['source_quote'] = 'The difference in hemoglobin S level is likely caused by differences in clinically indicated blood transfusion.'

    elif study_id == 'Nur 2012_2012':
        # Outcome: Haemoglobin status (g/dL) (continuous)
        result['found'] = False
        result['reasoning'] = 'Results section discusses oxidative stress, glutathione, and various markers but does not present explicit numerical hemoglobin values with means and SDs for treatment groups in the provided results_text.'
        result['source_quote'] = 'N/A - hemoglobin values not explicitly stated in provided text'

    elif study_id == 'Nakata 2022_2022':
        # Outcome: Physical activity (moderate to vigorous physical activity) (continuous)
        # Weight change is primary, but looking for physical activity
        result['found'] = False
        result['reasoning'] = 'Results present detailed weight change data and biochemistry measures (Table 2), but do not report physical activity levels or MVPA data explicitly in the results_text provided.'
        result['source_quote'] = 'N/A - physical activity data not in provided results section'

    return result

def main():
    # Load input
    with open(r'C:\Users\user\rct-extractor-v2\gold_data\mega\clean_batch_r26.json', 'r', encoding='utf-8') as f:
        entries = json.load(f)

    print(f"Processing {len(entries)} entries...")

    # Extract data from each entry
    results = []
    for i, entry in enumerate(entries, 1):
        print(f"  [{i}/{len(entries)}] {entry['study_id']}")
        result = extract_entry(entry)
        results.append(result)

    # Write output
    with open(r'C:\Users\user\rct-extractor-v2\gold_data\mega\clean_results_r26.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Summary
    found_count = sum(1 for r in results if r['found'])
    print(f"\nComplete: {found_count}/{len(results)} entries have extractable data")

    # Show found entries
    if found_count > 0:
        print("\nEntries with data found:")
        for r in results:
            if r['found']:
                print(f"  - {r['study_id']}: {r['effect_type']}")

if __name__ == '__main__':
    main()
