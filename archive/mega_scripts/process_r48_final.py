#!/usr/bin/env python3
# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
"""
Manual extraction for clean_batch_r48.json
Processing all 15 studies with careful manual review.
"""

import json

def create_result_entry(study_id, found=False, **kwargs):
    """Create a standardized result entry."""
    return {
        "study_id": study_id,
        "found": found,
        "effect_type": kwargs.get("effect_type"),
        "point_estimate": kwargs.get("point_estimate"),
        "ci_lower": kwargs.get("ci_lower"),
        "ci_upper": kwargs.get("ci_upper"),
        "intervention_events": kwargs.get("intervention_events"),
        "intervention_n": kwargs.get("intervention_n"),
        "control_events": kwargs.get("control_events"),
        "control_n": kwargs.get("control_n"),
        "intervention_mean": kwargs.get("intervention_mean"),
        "intervention_sd": kwargs.get("intervention_sd"),
        "control_mean": kwargs.get("control_mean"),
        "control_sd": kwargs.get("control_sd"),
        "source_quote": kwargs.get("source_quote"),
        "reasoning": kwargs.get("reasoning", "")
    }

def main():
    # Load input
    with open('C:/Users/user/rct-extractor-v2/gold_data/mega/clean_batch_r48.json', 'r', encoding='utf-8') as f:
        studies = json.load(f)

    results = []

    # Study 1: Zhao 2024_2024 - Incidence of COVID-19 (binary)
    # Results text mentions: "One hundred and forty-one patients with (n = 107) or without COVID-19 vaccination (n = 34)"
    # "hazard ratio (HR) HR = 0.47" - this is for infection-free survival, which is time-to-event, not the binary incidence directly
    # The outcome is "Incidence of COVID-19" but only HR is given for infection-free survival
    # Looking for actual events: results don't explicitly state number of COVID-19 cases in each group
    results.append(create_result_entry(
        "Zhao 2024_2024",
        found=True,
        effect_type="HR",
        point_estimate=0.47,
        source_quote="COVID-19 vaccination (hazard ratio (HR) HR = 0.47)",
        reasoning="HR for infection-free survival (time-to-event) found, but CI not stated. Binary incidence counts not explicitly reported."
    ))

    # Study 2: Kohan 2014_2014 - All-cause death (binary)
    # Results text shows completion/discontinuation flow but doesn't give explicit death counts by arm
    # Shows "2 Death" in various arms in flowchart but not clearly separated by intervention vs control
    results.append(create_result_entry(
        "Kohan 2014_2014",
        found=False,
        reasoning="Results text shows patient flow with some deaths listed (e.g., '2 Death' in flow diagram), but death events are not explicitly separated by treatment arm (placebo vs dapagliflozin 5mg vs 10mg) for the all-cause death outcome."
    ))

    # Study 3: Nandula 2021_2021 - eGFR (continuous)
    # Outcome is eGFR, data_type is continuous
    # Results mentions various biomarkers but doesn't provide eGFR mean±SD for intervention vs control
    results.append(create_result_entry(
        "Nandula 2021_2021",
        found=False,
        reasoning="Results text discusses CD34+ cells, glucose, HbA1c, blood pressure, adiponectin, but does not provide explicit eGFR mean and SD values for intervention vs control groups."
    ))

    # Study 4: Allegretti 2019_2019 - 3P-MACE (data_type=None)
    # "3P-MACE" typically means 3-point major adverse cardiovascular events
    # Results show HbA1c reduction: "Bexagliflozin lowered hemoglobin A1c by 0.37% [95% CI 0.20, 0.54]; p <0.001"
    # This is mean difference with CI, but outcome is "3P-MACE" not HbA1c
    # No explicit 3P-MACE events reported in the excerpt
    results.append(create_result_entry(
        "Allegretti 2019_2019",
        found=False,
        reasoning="The specified outcome is 3P-MACE (major adverse cardiovascular events). Results text discusses HbA1c reduction, body weight, blood pressure, and albuminuria, but does not report 3P-MACE event counts or rates."
    ))

    # Study 5: Brown 2009_2009 - Number of heavy-drinking participants (binary)
    # Results: "Naltrexone showed trends (p < .10) toward a greater decrease in drinking days (binary outcome)"
    # "heavy drinking days" mentioned as secondary outcome but no explicit counts
    results.append(create_result_entry(
        "Brown 2009_2009",
        found=False,
        reasoning="Results mention trends toward decrease in drinking days and heavy drinking days with naltrexone, but do not provide explicit counts of heavy-drinking participants (events/n) for intervention vs control."
    ))

    # Study 6: Schmitz 2009_2009 - % Abstinent days (continuous)
    # Results mentions "percentage of days drinking" and "daily use of cocaine"
    # "men receiving the higher naltrexone dose reported less cocaine use, lower drug severity, and greater abstinence from alcohol"
    # No explicit mean±SD for % abstinent days by group
    results.append(create_result_entry(
        "Schmitz 2009_2009",
        found=False,
        reasoning="Results discuss cocaine use, drinks per day, and heavy drinking days, mentioning naltrexone reduced frequency of heavy drinking days. However, explicit mean and SD for '% Abstinent days' outcome is not stated for intervention vs control groups."
    ))

    # Study 7: Fan 2025_2025 - Overall survival (Subgroup analysis: IPC Types) (data_type=None)
    # Results: "The 5-year OS rate in the experimental group was lower than that in the control group, at 75.8% and 88.2%, respectively"
    # Also states: "risk ratio (RR)=7.079, P=0.018" for pT stage (not the intervention)
    # This gives OS rates but not HR with CI for the intervention
    results.append(create_result_entry(
        "Fan 2025_2025",
        found=False,
        reasoning="Results report 5-year OS rates (experimental 75.8% vs control 88.2%) with no statistical significance. An RR=7.079 is mentioned but this is for pT stage, not the intervention effect. No HR or RR with CI given for the intervention on overall survival."
    ))

    # Study 8: Yu 2023_2023 - Disease-free survival (data_type=None)
    # Results: "The 3-year DFS rate was 73.8% in the HIPEC group, which was significantly higher than that in the non-HIPEC group (61.2%, P = 0.031)"
    # These are survival rates, not HR/RR with CI
    # "PM occurrence rate in the HIPEC group was statistically lower than that in the non-HIPEC group (20.9% vs. 40.3%, P = 0.015)"
    # This is for PM, not DFS directly
    results.append(create_result_entry(
        "Yu 2023_2023",
        found=False,
        reasoning="Results report 3-year DFS rates (HIPEC 73.8% vs non-HIPEC 61.2%, P=0.031), but do not provide hazard ratio or risk ratio with confidence interval for disease-free survival."
    ))

    # Study 9: Oslin 2008_2008 - Dropouts (binary)
    # Results focus on alcohol use outcomes, medication adherence
    # "there was no overall efficacy of naltrexone and no medication by psychosocial intervention interaction"
    # No explicit dropout counts by arm
    results.append(create_result_entry(
        "Oslin 2008_2008",
        found=False,
        reasoning="Results discuss psychosocial treatment effects and medication adherence (50% adhered) but do not explicitly report dropout counts (events/n) for intervention vs control groups."
    ))

    # Study 10: Yang 2011_2011 - Overall survival (data_type=None)
    # Results: "death occurred in 33 of 34 (97.1%) cases in the CRS group and 29 of 34 (85.3%) cases of the CRS+HIPEC group"
    # "The median survival was 6.5 months (95% confidence interval 4.8–8.2 months) in CRS and 11.0 months (95% confidence interval 10.0–11.9 months) in the CRS+HIPEC groups (P = 0.046)"
    # Death events: CRS 33/34, CRS+HIPEC 29/34 - this is binary data on death
    # Median survival times with CI are also given
    results.append(create_result_entry(
        "Yang 2011_2011",
        found=True,
        intervention_events=29,  # deaths in CRS+HIPEC
        intervention_n=34,
        control_events=33,  # deaths in CRS alone
        control_n=34,
        source_quote="death occurred in 33 of 34 (97.1%) cases in the CRS group and 29 of 34 (85.3%) cases of the CRS + HIPEC group. The median survival was 6.5 months (95% confidence interval 4.8–8.2 months) in CRS and 11.0 months (95% confidence interval 10.0–11.9 months) in the CRS + HIPEC groups (P = 0.046).",
        reasoning="Explicit death counts provided for both groups. Outcome is overall survival; death is the event. Median survival times with 95% CI also provided."
    ))

    # Study 11: Mitra 2016_2016 - Acute typhoid fever (data_type=None)
    # Results: "11 (1.27%) subjects from the control arm had BACTEC positive typhoid fever... and none from the test arm"
    # Control: 11 cases out of 860 enrolled
    # Test: 0 cases out of 905 enrolled
    # "vaccine efficacy in the study was 100% (95%CI: 97.65%, 100%)"
    results.append(create_result_entry(
        "Mitra 2016_2016",
        found=True,
        intervention_events=0,  # vaccinated group
        intervention_n=905,
        control_events=11,  # unvaccinated group
        control_n=860,
        source_quote="11 (1.27%) subjects from the control arm had BACTEC positive typhoid fever with an estimate relative risk of 0.0128 and none from the test arm had similar positivity among the febrile episodes subjects.",
        reasoning="Explicit case counts: 0/905 in vaccinated (test) group, 11/860 in unvaccinated (control) group. Vaccine efficacy 100% (95% CI: 97.65%, 100%)."
    ))

    # Study 12: Patel 2024_2024 - Acute typhoid fever (binary)
    # Results text is introduction only, no actual results data
    # Existing extractions show RRR values (78.3, 91.5, 80.7) but no CI, and outcome is binary case counts not RRR
    results.append(create_result_entry(
        "Patel 2024_2024",
        found=False,
        reasoning="Results text provided contains only introduction material discussing typhoid burden and vaccine types. No explicit case counts (intervention events/n vs control events/n) for acute typhoid fever are reported in the provided excerpt."
    ))

    # Study 13: Qadri 2021_2021 - Acute typhoid fever (binary)
    # Results text discusses trial design and protection rates
    # Mentions "91.5% (95% CI 77.1–96.6%; p<0.001) protection" for Vi-rEPA vaccine in Vietnamese children
    # Also mentions "81.6% (95% CI 58.8–91.8; p<0.001) protection" for Vi-TT vaccine in Nepal trial
    # And states "incidence of typhoid of 635 cases per 100 000 person-years in children who received the control vaccine"
    # But does not provide explicit case counts (events/n) for intervention vs control in THIS trial
    results.append(create_result_entry(
        "Qadri 2021_2021",
        found=False,
        reasoning="Results text discusses vaccine efficacy percentages from other trials (91.5% for Vi-rEPA, 81.6% for Vi-TT) and mentions incidence rate in control vaccine recipients (635 per 100,000 person-years), but does not explicitly state case counts (events/n) for the intervention vs control groups in this specific trial."
    ))

    # Study 14: Capeding 2020_2020 - Adverse events (binary)
    # Results text describes study design, enrollment (285 participants: 114 single dose, 114 two-dose, 57 comparator)
    # Discusses safety and immunogenicity but the results excerpt focuses on methods section
    # No explicit adverse event counts by group visible in provided text
    results.append(create_result_entry(
        "Capeding 2020_2020",
        found=False,
        reasoning="Results text provided focuses on study design and methods (285 participants enrolled: 114 single dose, 114 two-dose, 57 comparator). Safety section is mentioned but explicit adverse event counts (events/n) by treatment group are not visible in the provided excerpt."
    ))

    # Study 15: Carlos 2022_2022 - Adverse events (binary)
    # Results describe immune equivalence study
    # Safety section mentions: "A total of 992 solicited AEs were reported in 370 participants within the seven days post-vaccination:
    # 151(20.13%) in MD Vi-DT group, 144 (19.20%) in SD Vi-DT group and 75 (25.00%) of control group (p=0.103)"
    # Total participants: 750 MD Vi-DT, 750 SD Vi-DT, 300 control
    # This gives us AE counts: MD 151/750, SD 144/750, Control 75/300
    # But the outcome might be asking for a specific comparison (MD vs control or SD vs control)
    # Let's extract MD vs control as the primary comparison
    results.append(create_result_entry(
        "Carlos 2022_2022",
        found=True,
        intervention_events=151,  # MD Vi-DT group
        intervention_n=750,
        control_events=75,  # Control (MCV-A)
        control_n=300,
        source_quote="A total of 992 solicited AEs were reported in 370 participants within the seven days post-vaccination: 151(20.13%) in MD Vi-DT group, 144 (19.20%) in SD Vi-DT group and 75 (25.00%) of control group (p=0.103).",
        reasoning="Explicit counts of solicited adverse events within 7 days post-vaccination provided for all three groups. Using MD Vi-DT vs control comparison. Total enrolled: 750 MD Vi-DT, 750 SD Vi-DT, 300 control."
    ))

    # Write output
    with open('C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r48.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Summary
    found_count = sum(1 for r in results if r["found"])
    print(f"Extraction complete!")
    print(f"Total studies: {len(results)}")
    print(f"Found data: {found_count}/{len(results)} ({100*found_count/len(results):.1f}%)")
    print(f"\nOutput written to: C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r48.json")

if __name__ == "__main__":
    main()
