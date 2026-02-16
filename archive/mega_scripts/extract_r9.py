import json

# Read the batch file
with open('C:/Users/user/rct-extractor-v2/gold_data/mega/clean_batch_r9.json', 'r', encoding='utf-8') as f:
    batch = json.load(f)

results = []

# Process each entry
for entry in batch:
    study_id = entry['study_id']
    outcome = entry['outcome']
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

    # Study-specific extraction
    if study_id == 'Carey 2006_2006':
        result['reasoning'] = 'No specific numerical outcome data for "Extent of substance use" found. Results discuss statistical models and effect patterns but do not report raw counts, means/SDs, or direct effect estimates with CIs for the outcome.'

    elif study_id == 'Carey 2011_2011':
        result['found'] = True
        result['effect_type'] = 'MD'
        result['intervention_mean'] = -5.01
        result['control_mean'] = -2.67
        result['point_estimate'] = -2.34
        result['source_quote'] = 'Females in the delayed-control condition reduced their drinking equivalent to −2.67 drinks per heaviest week (95% CI [−4.47, −1.13])... Females receiving interventions also reduced consumption... BMI (M = −5.01, p = .09)'
        result['reasoning'] = 'For females, the text reports mean change from baseline in drinks per heaviest week: control = -2.67 drinks, BMI = -5.01 drinks. This is mean change data for a continuous outcome.'

    elif study_id == 'Mastroleo 2010_2010':
        result['reasoning'] = 'No specific numerical outcome data for "Extent of substance use" extractable. Text mentions "Both treatment groups reduced total drinks per week and heavy drinking behaviors compared to control" but does not provide the actual numerical values, means, SDs, or effect estimates.'

    elif study_id == 'Dermen 2011_2011':
        result['reasoning'] = 'No extractable numerical data for "Extent of substance use". Results mention frequency differences and fewer drinks per drinking day for alcohol intervention vs control, but specific values are not provided in the visible text.'

    elif study_id == 'Schaus 2009_2009':
        result['found'] = True
        result['effect_type'] = 'MD'
        result['control_mean'] = 0.071
        result['intervention_mean'] = 0.057
        result['point_estimate'] = -0.014
        result['source_quote'] = 'compared with the control group (C), the intervention group (I) had signiﬁ cant reductions in typical estimated blood alcohol concentration (BAC) (C = .071 vs I = .057 at 3 months; C = .073 vs I = .057 at 6 months)'
        result['reasoning'] = 'At 3 months, typical BAC: control = 0.071, intervention = 0.057. Difference = -0.014. This is a continuous outcome (BAC level).'

    elif study_id == 'Carroll 2009_2009':
        result['reasoning'] = 'No specific numerical values extractable for "Extent of substance use". Results describe differential effectiveness and odds ratios but do not report raw data, means/SDs, or specific effect estimates in the visible text.'

    elif study_id == 'Stein 2009_2009':
        result['found'] = True
        result['effect_type'] = 'OR'
        result['point_estimate'] = 2.89
        result['ci_lower'] = 1.22
        result['ci_upper'] = 6.84
        result['source_quote'] = 'At the 12 month follow-up, however, 45% of the intervention group were marijuana abstinent as measured by TLFB, compared to 22% of the assessed controls (OR 2.89, 95%CI 1.22, 6.84, p<0.014).'
        result['reasoning'] = 'Direct OR reported for marijuana abstinence at 12 months: OR 2.89 (95% CI 1.22, 6.84). This is an explicitly stated effect estimate with confidence interval.'

    elif study_id == 'Walker 2006_2006':
        result['reasoning'] = 'No extractable numerical data for "Extent of substance use". Text mentions "significant reductions in marijuana use" overall but states "between-groups effect size at follow-up was small (d = 0.08)" without providing means, SDs, or counts.'

    elif study_id == 'Marín-Navarrete 2017_2017':
        result['reasoning'] = 'No extractable numerical data. Results state "both conditions with signiﬁcant changes in substance use over" time but "no differences between conditions in substance use". No specific values provided.'

    elif study_id == 'Mertens 2014_2014':
        result['reasoning'] = 'No numerical outcome data found in visible text. Abstract mentions "significantly reduced scores on ASSIST for alcohol" but specific values not provided in the visible results section.'

    elif study_id == "D'Amico 2018_2018":
        result['reasoning'] = 'No extractable numerical data for substance use extent. Results report p-values and comparative statements about perceived peer use and consequences, but do not provide actual consumption data (means, counts, or direct effect estimates).'

    elif study_id == 'Field 2020_2020':
        result['reasoning'] = 'No extractable numerical data for "Extent of substance use". Results focus on mediation analysis and stages of change, mentioning "reduced likelihood of at-risk drinking, less alcohol use" but without specific numerical values.'

    elif study_id == 'Winhusen 2008_2008':
        result['reasoning'] = 'No extractable numerical data. Results state "Participants attended 62% of scheduled treatment on average and reported decreased substance use during the first month of treatment, with no differences between MET-PS and treatment as usual" but do not provide specific values for substance use outcomes.'

    elif study_id == 'Brown 2015_2015':
        result['found'] = True
        result['effect_type'] = 'MD'
        result['intervention_mean'] = 36
        result['control_mean'] = 11
        result['point_estimate'] = 25
        result['source_quote'] = 'Results indicated that the MI group had a longer latency to first use of any substance following hospital discharge relative to TAU (36 days versus 11 days).'
        result['reasoning'] = 'Latency to first use (days): MI = 36 days, TAU = 11 days. Difference = 25 days. This is a continuous time-to-event outcome measured as mean days.'

    elif study_id == 'Swogger 2016_2016':
        result['reasoning'] = 'No extractable numerical data for "Extent of substance use". Results describe interaction effects and variance accounted for but do not report actual substance use frequency values, means, or direct effect estimates.'

    results.append(result)

# Write results
with open('C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r9.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"Processed {len(results)} entries")
print(f"Found data in: {sum(1 for r in results if r['found'])} studies")
for r in results:
    if r['found']:
        print(f"  - {r['study_id']}: {r['effect_type']}")
