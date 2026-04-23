# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
"""
Extract numerical outcome data from clean_batch_r15.json
Manual extraction for all 15 studies based on careful reading of results_text
"""
import json

def create_results():
    """Create extraction results for all 15 studies"""

    results = []

    # 1. Roset-Salla 2016
    results.append({
        'study_id': 'Roset-Salla 2016_2016',
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
        'source_quote': 'Mediterranean diet adherence had improved in the IG by 5.8 points in the Gerber index (P = 0.01) and 0.6 points in the Kidmed test (P = 0.02) compared with the CG',
        'reasoning': 'Results report change scores (improvement in IG by 5.8 points Gerber, 0.6 points Kidmed vs CG) but these are relative change scores, not raw means or SDs for the outcome "Fruit and vegetable intake" that would allow extraction'
    })

    # 2. Tabak 2012
    results.append({
        'study_id': 'Tabak 2012_2012',
        'found': True,
        'effect_type': 'MD',
        'point_estimate': None,
        'ci_lower': None,
        'ci_upper': None,
        'intervention_events': None,
        'intervention_n': None,
        'control_events': None,
        'control_n': None,
        'intervention_mean': 1.5,
        'intervention_sd': 2.5,
        'control_mean': -0.3,
        'control_sd': 2.7,
        'source_quote': 'Intervention increased availability of vegetables (+1.5± 2.5 vegetable types vs. −0.3 ± 2.7, P=0.02)',
        'reasoning': 'Extracted change in vegetable availability (change score): intervention +1.5±2.5 vegetable types vs control -0.3±2.7. These are mean±SD for change from baseline.'
    })

    # 3. Verbestel 2014
    results.append({
        'study_id': 'Verbestel 2014_2014',
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
        'source_quote': 'No intervention effects were found for activity- and dietary-related behaviours targeted by the intervention. In both intervention and control groups, daily consumption of fruit and vegetables decreased over 1 year.',
        'reasoning': 'Results state no intervention effects on dietary behaviors and that fruit/vegetable consumption decreased in both groups, but no specific numerical data (means, SDs, counts) are provided in the results_text'
    })

    # 4. Wyse 2012
    results.append({
        'study_id': 'Wyse 2012_2012',
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
        'source_quote': 'children\'s fruit and vegetable scores were significantly higher in the intervention group than in the control group at 2 mo (P < 0.001) and at 6 mo (P = 0.021)',
        'reasoning': 'Results report that fruit/vegetable scores were significantly higher in intervention vs control (P<0.001 at 2mo, P=0.021 at 6mo), but no actual means, SDs, or raw counts are provided in the results_text'
    })

    # 5. Kamath 2021
    results.append({
        'study_id': 'Kamath 2021_2021',
        'found': True,
        'effect_type': 'MD',
        'point_estimate': None,
        'ci_lower': None,
        'ci_upper': None,
        'intervention_events': None,
        'intervention_n': None,
        'control_events': None,
        'control_n': None,
        'intervention_mean': 78.783,
        'intervention_sd': None,
        'control_mean': 71.211,
        'control_sd': None,
        'source_quote': 'remaining 5 cases showed fair results (Mean MRS: 74.783, VAS: 3.348, AOFAS: 78.783). Thirty one cases treated with cast also showed fair results (Mean MRS: 57.368, VAS: 4.944, AOFAS: 71.211)',
        'reasoning': 'Extracted AOFAS scores (function outcome): operative group mean AOFAS=78.783 vs non-operative (cast) mean=71.211. SDs not reported. Note these are described as "fair results" groups, possibly not full cohorts.'
    })

    # 6. Kulkarni 2015
    results.append({
        'study_id': 'Kulkarni 2015_2015',
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
        'source_quote': 'When we consider the clinical evaluation under the C–N score, the results of operatively managed calcaneal fractures are slightly better than those of the conservative group. But this did not have any statistical signiﬁcance.',
        'reasoning': 'Results state operative outcomes were "slightly better" than conservative but not significant. Outcome is "number of people with scores of excellent, good, or satisfactory/fair" (binary) but no counts (events/n) are provided in results_text'
    })

    # 7. Gunerhan 2009
    results.append({
        'study_id': 'Gunerhan 2009_2009',
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
        'source_quote': 'groups did not differ in terms of postoperative complications and postoperative durations of hospital stay',
        'reasoning': 'Outcome is "Infectious complications" (binary). Results state groups did not differ in postoperative complications, but no specific counts (events/n) for infectious complications are provided in results_text'
    })

    # 8. Harvey 2012
    results.append({
        'study_id': 'Harvey 2012_2012',
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
        'reasoning': 'Outcome is "Maternal adverse events" (binary). The results_text is truncated and contains only methods section describing study procedures. No results data for maternal adverse events is present in the provided text.'
    })

    # 9. Roth 2013_2018
    results.append({
        'study_id': 'Roth 2013_2018',
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
        'source_quote': 'Groups were similar with respect to other anthropometric measures, birth outcomes, and morbidity.',
        'reasoning': 'Outcome is "Gestational diabetes (ALL)" (binary). Results state groups were similar with respect to birth outcomes and morbidity, but no specific counts for gestational diabetes are provided in the results_text'
    })

    # 10. Levin 2011
    results.append({
        'study_id': 'Levin 2011_2011',
        'found': True,
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
        'source_quote': 'There was no significant difference between treatment groups in the proportion of participants who achieved 2 weeks of abstinence at the end of the maintenance phase (dronabinol: 17.7%; placebo: 15.6%)',
        'reasoning': 'Outcome is "Participants abstinent at end of treatment" (binary). Percentages given: dronabinol 17.7%, placebo 15.6%. However, denominators (n per group) not provided in results_text, so cannot extract events/n. NOTE: Abstract says 156 enrolled, randomized to 2 groups, but exact n per group not in results_text.'
    })

    # 11. Moriya 2015
    results.append({
        'study_id': 'Moriya 2015_2015',
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
        'reasoning': 'Outcome is "Non-infectious complications" (binary). However, the results_text appears to be from a completely different paper about materials engineering and porous composites - NOT a clinical trial. This is a data quality issue in the batch file.'
    })

    # 12. Levin 2016
    results.append({
        'study_id': 'Levin 2016_2016',
        'found': True,
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
        'source_quote': 'There was no significant difference between treatment groups in the proportion of participants who achieved 3 weeks of abstinence during the maintenance phase of the trial (27.9 % for the medication group and 29.5% for the placebo group)',
        'reasoning': 'Outcome is "Participants abstinent at end of treatment" (binary). Percentages given: medication 27.9%, placebo 29.5%. However, denominators (n per group) not provided in results_text, so cannot extract events/n.'
    })

    # 13. Palefsky 2022
    results.append({
        'study_id': 'Palefsky 2022_2022',
        'found': True,
        'effect_type': 'NONE',
        'point_estimate': None,
        'ci_lower': None,
        'ci_upper': None,
        'intervention_events': 9,
        'intervention_n': None,
        'control_events': 21,
        'control_n': None,
        'intervention_mean': None,
        'intervention_sd': None,
        'control_mean': None,
        'control_sd': None,
        'source_quote': 'With a median follow-up of 25.8 months, 9 cases were diagnosed in the treatment group (173 per 100,000 person-years; 95% confidence interval [CI], 90 to 332) and 21 cases in the active-monitoring group (402 per 100,000 person-years; 95% CI, 262 to 616)',
        'reasoning': 'Outcome is "Development of anal cancer" (binary). Events extracted: treatment=9, active-monitoring (control)=21. Denominators not stated in results_text (abstract says 4446 analyzed, randomized 1:1, but exact n per group not in this excerpt).'
    })

    # 14. Verhaeghe 2021
    results.append({
        'study_id': 'Verhaeghe 2021_2021',
        'found': True,
        'effect_type': 'NONE',
        'point_estimate': None,
        'ci_lower': None,
        'ci_upper': None,
        'intervention_events': 35,
        'intervention_n': 117,
        'control_events': 40,
        'control_n': 119,
        'intervention_mean': None,
        'intervention_sd': None,
        'control_mean': None,
        'control_sd': None,
        'source_quote': '236 patients were randomized to either manual rotation (n=117) or expectant management (n=119). Manual rotation did not decrease the rate of operative vaginal delivery (29.9% in manual rotation group vs 33.6% in expectant management group',
        'reasoning': 'Outcome is "Operative delivery" (binary). N per group stated: manual rotation n=117, expectant management n=119. Percentages given: 29.9% vs 33.6%. Events calculated: 117*0.299=35 (rounded), 119*0.336=40 (rounded).'
    })

    # 15. Beeckman 2021
    results.append({
        'study_id': 'Beeckman 2021_2021',
        'found': True,
        'effect_type': 'RR',
        'point_estimate': 0.64,
        'ci_lower': 0.41,
        'ci_upper': 0.99,
        'intervention_events': None,
        'intervention_n': None,
        'control_events': None,
        'control_n': None,
        'intervention_mean': None,
        'intervention_sd': None,
        'control_mean': None,
        'control_sd': None,
        'source_quote': 'In the intention-to-treat population (n = 1605), PUs of category 2 or worse occurred in 4·0% of patients in the treatment group and 6·3% in the control group [relative risk (RR) 0·64, 95% conﬁdence interval (CI) 0·41–0·99, P = 0·04]',
        'reasoning': 'Outcome is "Pressure ulcer" (binary). RR and CI directly reported: RR=0.64 (95% CI 0.41-0.99). Percentages 4.0% treatment vs 6.3% control with total n=1605, but n per group not stated so cannot calculate exact events/n.'
    })

    return results


def main():
    results = create_results()

    # Write to output file
    with open('C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r15.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Processed {len(results)} entries")
    print(f"Found data in {sum(1 for r in results if r['found'])} entries")
    print("\nSummary:")
    for r in results:
        status = "FOUND" if r['found'] else "NOT FOUND"
        print(f"  {r['study_id']}: {status}")


if __name__ == '__main__':
    main()
