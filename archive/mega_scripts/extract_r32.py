#!/usr/bin/env python
# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
# -*- coding: utf-8 -*-
"""Manual extraction for clean_batch_r32.json"""

import json
import sys
import io

# Set UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Load batch
with open('C:/Users/user/rct-extractor-v2/gold_data/mega/clean_batch_r32.json', encoding='utf-8') as f:
    batch = json.load(f)

print(f"Processing {len(batch)} studies...")

results = []

# Study 1: Van der Heijde 2006_2006 - All-cause mortality
results.append({
    "study_id": "Van der Heijde 2006_2006",
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
    "reasoning": "The outcome is 'All-cause mortality' but the results text only reports ASAS response rates, disease activity measures, and adverse events. No mortality data is reported. The text states 'Incidence of treatment-emergent adverse events, including infections, was similar among all three groups' but does not provide mortality counts."
})

# Study 2: Baek 2019_2019 - Adverse events
results.append({
    "study_id": "Baek 2019_2019",
    "found": True,
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
    "source_quote": "The patients who experienced any adverse event (AE) were more frequent in the TCZ group compared to the placebo group.",
    "reasoning": "The text indicates AEs were more frequent in TCZ (intervention) vs placebo (control), but does not provide actual counts of patients with AEs or the denominators. The statement is qualitative only ('more frequent') without numerical data."
})

# Study 3: Butchart 2015_2015 - Adverse events
results.append({
    "study_id": "Butchart 2015_2015",
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
    "source_quote": "Although infections were more common in the etanercept group, there were no serious adverse events or new safety concerns.",
    "reasoning": "The outcome is 'Adverse events'. The text states 'infections were more common in the etanercept group' and 'no serious adverse events' but does not provide numerical counts of patients experiencing adverse events in each group. Sample sizes are given (n=20 etanercept, n=21 placebo) but not event counts."
})

# Study 4: Bernstein 2006_2006 - Adverse events
results.append({
    "study_id": "Bernstein 2006_2006",
    "found": True,
    "effect_type": "NONE",
    "point_estimate": None,
    "ci_lower": None,
    "ci_upper": None,
    "intervention_events": 2,
    "intervention_n": 28,
    "control_events": 2,
    "control_n": 28,
    "intervention_mean": None,
    "intervention_sd": None,
    "control_mean": None,
    "control_sd": None,
    "source_quote": "Fifty-six subjects with the metabolic syndrome were randomized... Two subjects dropped out of each group",
    "reasoning": "The outcome is 'Adverse events'. The text reports dropouts (which can indicate adverse events): 2 subjects dropped out of etanercept group and 2 from placebo group. With 56 total randomized, this implies 28 per group (56/2=28). Using dropouts as a proxy for adverse events: intervention_events=2, intervention_n=28, control_events=2, control_n=28."
})

# Study 5: Reich 2017_2017 - Adverse events (serious infections)
results.append({
    "study_id": "Reich 2017_2017",
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
    "source_quote": "Most common adverse events (≥5%) with apremilast, including nausea, diarrhoea, upper respiratory tract infection, nasopharyngitis, tension headache and headache, were mild or moderate in severity",
    "reasoning": "The outcome is 'Adverse events (serious infections)'. The text mentions common AEs (≥5%) like nausea, diarrhea, infections but does not provide specific counts for serious infections. The text describes AE rates qualitatively but no numerical data for serious infections is provided. Sample sizes are n=84 placebo, n=83 apremilast, n=83 etanercept but no event counts for serious infections."
})

# Study 6: Abbate 2020_2020 - All-cause mortality
results.append({
    "study_id": "Abbate 2020_2020",
    "found": True,
    "effect_type": "NONE",
    "point_estimate": None,
    "ci_lower": None,
    "ci_upper": None,
    "intervention_events": None,
    "intervention_n": 64,
    "control_events": None,
    "control_n": 35,
    "intervention_mean": None,
    "intervention_sd": None,
    "control_mean": None,
    "control_sd": None,
    "source_quote": "We conducted a randomized, placebo-controlled, double-blind, clinical trial in 99 patients with ST-segment–elevation myocardial infarction in which patients were assigned to 2 weeks treatment with anakinra once daily (N=33), anakinra twice daily (N=31), or placebo (N=35). [...] The incidence of death or new-onset heart failure or of death and hospitalization for heart failure was significantly lower with anakinra versus placebo (9.4% versus 25.7% [P=0.046] and 0% versus 11.4% [P=0.011], respectively)",
    "reasoning": "The outcome is 'All-cause mortality'. The text reports composite outcomes including death: 'death or new-onset heart failure' was 9.4% in anakinra vs 25.7% in placebo. However, this is a composite outcome, not pure mortality. The text also mentions 0% vs 11.4% for 'death and hospitalization for heart failure'. The anakinra groups are N=33 and N=31 (total 64), placebo N=35. But pure mortality counts are not separately reported. Cannot extract pure all-cause mortality counts."
})

# Study 7: Emsley 2005_2005 - All-cause mortality
results.append({
    "study_id": "Emsley 2005_2005",
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
    "source_quote": "Among patients with cortical infarcts, clinical outcomes at 3 months in the rhIL-1ra treated group were better than in placebo treated.",
    "reasoning": "The outcome is 'All-cause mortality' (binary). The results text reports 34 patients randomized, describes biological markers and states 'clinical outcomes at 3 months in the rhIL-1ra treated group were better than in placebo' but does not provide mortality counts or numbers."
})

# Study 8: Morton 2015_2015 - All-cause mortality
results.append({
    "study_id": "Morton 2015_2015",
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
    "reasoning": "The outcome is 'All-cause mortality'. The results_text is truncated and only shows references, acknowledgements, and a note about data verification. No actual mortality data is present in the provided excerpt."
})

# Study 9: Choudhury 2016_2016 - All-cause mortality
results.append({
    "study_id": "Choudhury 2016_2016",
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
    "source_quote": "There were no statistically significant differences between canakinumab compared with placebo in the primary efficacy and safety endpoints.",
    "reasoning": "The outcome is 'All-cause mortality'. The results report outcomes for carotid wall area, C-reactive protein, lipoprotein levels, etc., but do not mention mortality. The primary endpoints were vascular structure/function measures, not clinical events. Sample sizes are n=94 placebo, n=95 canakinumab, but no mortality data is reported."
})

print("Extraction complete. Now need to read remaining studies...")

