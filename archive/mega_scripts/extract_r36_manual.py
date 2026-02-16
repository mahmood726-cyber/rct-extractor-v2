"""
Manual extraction of numerical outcome data from clean_batch_r36.json
Based on careful reading of results_text for each study.
"""
import json

def create_extractions():
    """Manually extracted data for each study in the batch."""

    extractions = []

    # 1. Okai 2013_2013 - Change in frequency of ICBs
    # Outcome: "Change in frequency of ICBs&nbsp;"
    # Results text mentions CGI (Clinical Global Impression) scores and statistical tests
    # but does NOT provide raw binary counts for ICB frequency change
    # Only provides: "x2 = 16.46, p < 0.001" and mean scores (4.0→2.5 CBT, 3.7→3.5 SMC)
    extractions.append({
        "study_id": "Okai 2013_2013",
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
        "source_quote": "baseline to 6-month follow-up, reduction in symptom severity CBT group, 4.0–2.5; SMC alone group, 3.7–3.5",
        "reasoning": "Study reports CGI severity scores (continuous outcome) not binary event counts for ICB frequency change. No raw events/n provided for the specified binary outcome."
    })

    # 2. Bishop 2017_2017 - Referral for or receipt of any lumbar spine imaging
    # Results: "intervention group n=425, control arm n=553"
    # Text mentions "No evidence of selection bias" but does NOT report imaging referral counts
    # Only exploratory SF-36 PCS: "−0.28 (95% CI −1.35 to 0.79)" at 6m, "0.12 (95% CI −1.27 to 1.51)" at 12m
    extractions.append({
        "study_id": "Bishop 2017_2017",
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
        "source_quote": "intervention group n=425, control arm n=553. Exploratory estimates of between group effect (using 36-item Short Form Health Survey (SF-36) Physical Component Summary (PCS)) at 6 months was −0.28 (95% CI −1.35 to 0.79)",
        "reasoning": "Study does not report imaging referral data in the provided results_text excerpt. Only reports total n and SF-36 PCS outcome, not the specified imaging outcome."
    })

    # 3. DeBar 2022_2022 - Referral for or receipt of any lumbar spine imaging
    # Results: "850 patients participated... 816 (96.0%) completed follow-up"
    # Reports pain outcomes: "change in PEGS score was −0.434 point (95% CI, −0.690 to −0.178 point)"
    # and "change in pain-related disability was −0.060 point (CI, −0.084 to −0.035 point)"
    # Does NOT report imaging referral data in the excerpt
    extractions.append({
        "study_id": "DeBar 2022_2022",
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
        "source_quote": "850 patients participated... change in PEGS score was −0.434 point (95% CI, −0.690 to −0.178 point) for pain impact, and the change in pain-related disability was −0.060 point (CI, −0.084 to −0.035 point)",
        "reasoning": "Study reports pain outcomes (PEGS, disability) but does not report imaging referral data in the provided results_text."
    })

    # 4. Mas 2019_2019 - Pain at last follow-up within 12 months
    # Results: "421 (84%) provided data at 3 months, and 387 (77.2%) at 12 months. Mean age was 46.8 years (SD: 11.5)"
    # "In the adjusted analysis of the RMDQ outcome, only the intervention group showed significant changes at 3 months (−1.33 points, p = 0.005) and at 12 months (−1.11 points, p = 0.027)"
    # "The intervention group presented significant differences in the MGPQ scales of current pain intensity and VAS scores at 3 months"
    # Does NOT provide raw mean pain scores for intervention vs control at 12 months - only reports differences
    extractions.append({
        "study_id": "Mas 2019_2019",
        "found": False,
        "effect_type": "MD",
        "point_estimate": -1.11,
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
        "source_quote": "In the adjusted analysis of the RMDQ outcome, only the intervention group showed significant changes at 3 months (−1.33 points, p = 0.005) and at 12 months (−1.11 points, p = 0.027)",
        "reasoning": "Study reports between-group difference in RMDQ at 12 months (-1.11 points, p=0.027) but does not provide raw mean pain scores or SDs for each group. Only the difference is extractable."
    })

    # 5. Schmidt 2020_2020 - Pain at last follow-up within 12 months
    # Results: "165 (mean age: 50 years (SD 13) and mean Oswestry Disability Index score 42 (SD 11)) were randomized (83 to existing rehabilitation... and 82 to integrated rehabilitation programme)"
    # "139 patients provided the 26-week follow-up data"
    # "The between-group difference in the Oswestry Disability Index score when adjusting for the corresponding baseline score was −0.28 (95% confidence interval (CI): −4.02, 3.45)"
    # Does NOT provide raw pain scores at 12m - only disability index difference
    extractions.append({
        "study_id": "Schmidt 2020_2020",
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
        "source_quote": "The between-group difference in the Oswestry Disability Index score when adjusting for the corresponding baseline score was −0.28 (95% confidence interval (CI): −4.02, 3.45) which was neither statistically nor clinically significant. No significant differences were found in the secondary outcomes.",
        "reasoning": "Study reports Oswestry Disability Index (ODI) at 26 weeks, not pain intensity. Results text does not contain pain outcome data at 12 months."
    })

    # 6. Priebe 2020_2020 - Pain at last follow-up within 12 months
    # Results: "1245 patients (IG: 933; CG: 312) with NLBP were included"
    # "The Rise-uP group showed a significantly stronger pain reduction compared to the control group after 3 months (IG: M=−33.3% vs CG: M=−14.3%)"
    # "Furthermore, high-risk patients who received a teleconsultation showed a larger decrease in pain intensity (−43.5%) than CG patients (−14.3%)"
    # Reports % reduction, not absolute pain scores. No 12-month data in excerpt.
    extractions.append({
        "study_id": "Priebe 2020_2020",
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
        "source_quote": "The Rise-uP group showed a significantly stronger pain reduction compared to the control group after 3 months (IG: M=−33.3% vs CG: M=−14.3%)",
        "reasoning": "Study reports % pain reduction at 3 months only, not absolute pain scores. No 12-month data in provided results_text excerpt."
    })

    # 7. Sanders 2018_2018 - Pain at last follow-up within 12 months
    # Results: "intervention and the control groups, 66 and 62%, respectively, completed the follow-up"
    # "Most patients (77%) recovered to no functional restrictions due to back pain within 26 weeks"
    # "No significant differences in the mean scores for any outcome were observed between intervention patients and controls during the follow-up"
    # Does NOT provide raw pain scores
    extractions.append({
        "study_id": "Sanders 2018_2018",
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
        "source_quote": "Most patients (77%) recovered to no functional restrictions due to back pain within 26 weeks. No significant differences in the mean scores for any outcome were observed between intervention patients and controls during the follow-up",
        "reasoning": "Study states no significant differences in outcomes but does not provide specific pain scores or statistics for pain at 12 months."
    })

    # 8. Mason 2017_2017 - All symptoms (continuous)
    # Results text discusses study methods and objectives but the excerpt provided does NOT contain actual results
    # Only describes the Boston Carpal Tunnel Assessment Questionnaire and study design
    extractions.append({
        "study_id": "Mason 2017_2017",
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
        "source_quote": "Symptoms and function will be measured using Boston Carpal Tunnel Assessment Questionnaire",
        "reasoning": "The results_text excerpt contains only methods/design information, not actual results data. This is a pilot feasibility study and the excerpt does not include outcome data."
    })

    # 9. McKee 2020_2020 - Prescription or use of opioid medication at last follow-up
    # Results: "37.5% of individual arm and 30.3% in group had > 30% improvement in pain interference (d = 7.2%, 95% CI −0.6%, 15.1%)"
    # "63.1% of individual participants and 59.5% of group had clinically important improvement at 12 weeks (d = 3.6%, 95% CI −4.2%, 11.4%)"
    # Does NOT report opioid medication use data in the excerpt
    extractions.append({
        "study_id": "McKee 2020_2020",
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
        "source_quote": "37.5% of individual arm and 30.3% in group had > 30% improvement in pain interference (d = 7.2%, 95% CI −0.6%, 15.1%)",
        "reasoning": "Study compares individual vs group acupuncture on pain outcomes. The provided results_text excerpt does not contain opioid medication use data."
    })

    # Need to load the full data to see remaining entries 10-15
    return extractions

def main():
    # Get partial extractions
    partial_extractions = create_extractions()

    # Load full batch to process remaining entries
    with open('C:/Users/user/rct-extractor-v2/gold_data/mega/clean_batch_r36.json', 'r', encoding='utf-8') as f:
        batch_data = json.load(f)

    print(f"Created {len(partial_extractions)} manual extractions")
    print(f"Total entries in batch: {len(batch_data)}")
    print(f"Need to process entries {len(partial_extractions)+1} to {len(batch_data)}")

    # Write partial results
    output_path = 'C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r36_partial.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(partial_extractions, f, indent=2, ensure_ascii=False)

    print(f"Wrote partial extractions to {output_path}")

if __name__ == "__main__":
    main()
