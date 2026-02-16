#!/usr/bin/env python
"""
Manual extraction script for clean_batch_r49.json
Extracts numerical outcome data from results_text for each study entry.
"""

import json
import re
from typing import Optional, Dict, Any


def extract_kumar_rai_2022(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Kumar Rai 2022_2022 - All-cause mortality"""
    # Results text shows vaccine immunogenicity study, no mortality data
    return {
        "study_id": entry["study_id"],
        "found": False,
        "effect_type": None,
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
        "reasoning": "Text discusses Vi-DT vaccine immunogenicity and safety. No all-cause mortality data reported."
    }


def extract_thuluva_2022(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Thuluva 2022_2022 - All-cause mortality"""
    # Text mentions 1 death due to dengue in Typbar-TCV group (unrelated to vaccine)
    # But no systematic mortality reporting for both groups
    return {
        "study_id": entry["study_id"],
        "found": False,
        "effect_type": None,
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
        "source_quote": "death due to SAE (dengue fever) in 1 subject (from Typbar-TCV group)",
        "reasoning": "Only 1 death mentioned in control group (Typbar-TCV) due to dengue, considered unrelated to vaccine. No systematic mortality reporting for both groups to allow extraction of 2x2 data."
    }


def extract_mantovani_2010(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Mantovani 2010_2010 - Changes in physical function and strength"""
    # Outcome is "Changes in physical function and strength" (continuous)
    # No explicit data for this outcome in results_text
    return {
        "study_id": entry["study_id"],
        "found": False,
        "effect_type": None,
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
        "reasoning": "Results text discusses LBM, REE, fatigue, appetite, IL-6, GPS, ECOG PS. No explicit data for 'Changes in physical function and strength' outcome."
    }


def extract_baldi_2010(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Baldi 2010_2010 - Body composition and weight"""
    # Outcome: "Body composition and weight" (continuous)
    # Results: "a body weight increment occurred in 92% and 15% of patients in
    # the EAAs and C group, respectively, with an average increase of 3.8 ± 2.6 kg (P = 0.0002)
    # and −0.1 ± 1.1 kg (P = 0.81), respectively. A FFM increment occurred in 69% and 15% of EAAs
    # and C patients, respectively, with an average increase of 1.5 ± 2.6 kg (P = 0.05) and −0.1 ± 2.3 kg"

    return {
        "study_id": entry["study_id"],
        "found": True,
        "effect_type": "MD",
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "intervention_mean": 3.8,
        "intervention_sd": 2.6,
        "control_mean": -0.1,
        "control_sd": 1.1,
        "source_quote": "a body weight increment occurred in 92% and 15% of patients in the EAAs and C group, respectively, with an average increase of 3.8 ± 2.6 kg (P = 0.0002) and −0.1 ± 1.1 kg (P = 0.81), respectively",
        "reasoning": "Body weight change data explicitly stated: EAAs group mean increase 3.8 kg (SD 2.6), control group mean -0.1 kg (SD 1.1). Using body weight as primary measure of body composition and weight outcome."
    }


def extract_aleem_2021(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Aleem 2021_2021 - Difference in mean change in adherence"""
    # Outcome: "Difference in mean change in adherence" (continuous)
    # Results mention MGL scale shift from low to high adherence but no numerical mean change data
    return {
        "study_id": entry["study_id"],
        "found": False,
        "effect_type": None,
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
        "source_quote": "a significant shift was found in the interventional group from low to high adherence according to MGL scale evaluation",
        "reasoning": "Results describe shift from low to high adherence but do not report numerical mean change scores with SD for intervention vs control groups."
    }


def extract_fiscella_2018(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Fiscella 2018_2018 - Difference in mean change in adherence"""
    # Outcome: "Difference in mean change in adherence" (continuous)
    # Results: "Mean PDC was 0.54-0.56 across cohorts. At 12 months... mean PDC was 0.53-0.54 across cohorts.
    # No statistically significant between-cohort differences in PDC and adherence were observed."
    # But no explicit mean change with SD reported

    return {
        "study_id": entry["study_id"],
        "found": False,
        "effect_type": None,
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
        "source_quote": "Mean PDC was 0.54-0.56 across cohorts. At 12 months, ≥ 90.5% of physicians and ≥ 75.5% of patients remained in the study; mean PDC was 0.53-0.54 across cohorts. No statistically significant between-cohort differences in PDC and adherence were observed.",
        "reasoning": "PDC values reported at baseline (0.54-0.56) and 12 months (0.53-0.54) across cohorts, but no explicit mean CHANGE scores with SD for difference calculation."
    }


def extract_cook_2017(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Cook 2017_2017 - Difference in final mean adherence"""
    # Outcome: "Difference in final mean adherence" (continuous)
    # Results: "Reminder calls increased adherence compared to usual care based on MEMS, p = .005,
    # and self-report, p = .04. MI had a nonsignificant effect"
    # No explicit numerical means with SD

    return {
        "study_id": entry["study_id"],
        "found": False,
        "effect_type": None,
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
        "source_quote": "Reminder calls increased adherence compared to usual care based on MEMS, p = .005, and self-report, p = .04. MI had a nonsignificant effect but produced higher satisfaction than reminder calls, p = .007.",
        "reasoning": "Results report statistical significance (p-values) but do not provide explicit final mean adherence scores with SD for each group."
    }


def extract_bilger_2019(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Bilger 2019_2019 - Proportion of participants who were adherent"""
    # Outcome: "Proportion of participants who were adherent" (binary)
    # Results: "medication adherence at Month 6 was 12.2 (p = 0.027) percentage points higher
    # in the adherence-contingent rebates group than in the control group"
    # "Month 6 medication adherence in the control group was 61.6%"
    # So intervention ~73.8%, control 61.6%
    # But need n for each group
    # Text says 100 participants randomized 1:1, so 50 each
    # "92% of participants completed the study and the primary outcome was successfully recorded for 83% of the participants at Month 6"
    # So ~83 participants with data, but need exact n per group

    return {
        "study_id": entry["study_id"],
        "found": False,
        "effect_type": None,
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
        "source_quote": "medication adherence at Month 6 was 12.2 (p = 0.027) percentage points higher in the adherence-contingent rebates group than in the control group after adjusting for baseline differences. [...] Month 6 medication adherence in the control group was 61.6%",
        "reasoning": "Percentage point difference (12.2) and control group adherence (61.6%) reported, implying intervention ~73.8%. However, explicit number of adherent participants per group not stated - only percentages. Cannot extract n_events without n_total per group."
    }


def extract_gray_2012(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Gray 2012_2012 - Proportion of participants who were adherent"""
    # Outcome: "Proportion of participants who were adherent" (binary)
    # Results: "Intervention-arm patients collected signiﬁcantly more prescriptions than control-arm patients.
    # Self-report adherence was signiﬁcantly better in the intervention-arm"
    # No explicit n/N data

    return {
        "study_id": entry["study_id"],
        "found": False,
        "effect_type": None,
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
        "source_quote": "Intervention-arm patients collected signiﬁcantly more prescriptions than control-arm patients. Self-report adherence was signiﬁcantly better in the intervention-arm for patients who forgot drops and those who intentionally missed drops.",
        "reasoning": "Results report qualitative comparison (significantly more/better) but do not provide explicit number or proportion of adherent participants per group."
    }


def extract_goldstein_2007(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Goldstein 2007_2007 - QOL subscore: self-efficacy-change score"""
    # Outcome: "QOL subscore: self-efficacy-change score" (continuous)
    # Results: "There was no significant difference in change of self-efficacy score or
    # in emotional affect between the two groups."
    # No numerical data provided

    return {
        "study_id": entry["study_id"],
        "found": False,
        "effect_type": None,
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
        "source_quote": "There was no significant difference in change of self-efficacy score or in emotional affect between the two groups.",
        "reasoning": "Results state no significant difference in self-efficacy change score but do not provide numerical mean change values with SD."
    }


def extract_apsangikar_2021(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Apsangikar 2021_2021 - Proportion of participants who lost fewer than 15 letters in BCVA from baseline at 24 to 48 weeks"""
    # Outcome: "Proportion of participants who lost fewer than 15 letters in BCVA from baseline at 24 to 48 weeks" (binary)
    # Results: "In the biosimilar test arm, 104 (98.11%) and 105 (99.06%) patients lost fewer than
    # 15 letters in visual acuity at week 16 and week 24, respectively, compared with 53 (100%) at
    # both follow-ups in reference arm."
    # Week 24 data: test 105/106, reference 53/53

    return {
        "study_id": entry["study_id"],
        "found": True,
        "effect_type": "RR",
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "intervention_events": 105,
        "intervention_n": 106,
        "control_events": 53,
        "control_n": 53,
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": "In the biosimilar test arm, 104 (98.11%) and 105 (99.06%) patients lost fewer than 15 letters in visual acuity at week 16 and week 24, respectively, compared with 53 (100%) at both follow-ups in reference arm.",
        "reasoning": "Week 24 data extracted (within 24-48 week timeframe): biosimilar test arm 105/106 (99.06%) lost <15 letters, reference arm 53/53 (100%). Total n inferred from percentages."
    }


def extract_yoon_2022(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Yoon 2022_2022 - Change from baseline in best-corrected visual acuity (BCVA) at 8 to 12 weeks"""
    # Outcome: "Change from baseline in best-corrected visual acuity (BCVA) at 8 to 12 weeks" (continuous)
    # Results: "The BCVA improved with a mean improvement of +7.0 (CKD-701) and +6.2 (ranibizumab) letters at 3 months (P = 0.43)"
    # 3 months = 12 weeks, within the 8-12 week range
    # But no SD provided

    return {
        "study_id": entry["study_id"],
        "found": False,
        "effect_type": None,
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
        "source_quote": "The BCVA improved with a mean improvement of +7.0 (CKD-701) and +6.2 (ranibizumab) letters at 3 months (P = 0.43).",
        "reasoning": "Mean change in BCVA reported at 3 months (12 weeks): CKD-701 +7.0 letters, ranibizumab +6.2 letters. However, SD not provided for these mean changes."
    }


def extract_herbison_2016(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Herbison 2016_2016 - Visual acuity (1 week to 3 months)"""
    # Outcome: "Visual acuity (1 week to 3 months)" (continuous)
    # Results: "The visual acuity improved in all three arms by approximately 0.07 logMAR in the amblyopic eye at 6 weeks.
    # There was no difference between I-BiT DVD and non-I-BiT games compared with I-BiT games"
    # No specific mean/SD per group

    return {
        "study_id": entry["study_id"],
        "found": False,
        "effect_type": None,
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
        "source_quote": "The visual acuity improved in all three arms by approximately 0.07 logMAR in the amblyopic eye at 6 weeks. There was no difference between I-BiT DVD and non-I-BiT games compared with I-BiT games (stated primary outcome) in terms of gain in vision.",
        "reasoning": "Results report approximate improvement (0.07 logMAR) across all arms at 6 weeks, but no specific mean/SD per individual treatment arm provided."
    }


def extract_jukes_2019(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Jukes 2019_2019 - Subjective adherence (1 week to 3 months) - 5-point scale"""
    # Outcome: "Subjective adherence (1 week to 3 months) - 5-point scale" (continuous)
    # Results text discusses VA improvement but no adherence scale data
    # "After seven weeks the mean VA of the amblyopic eye in the computer game group improved by 0.147 ± 0.182 logMAR,
    # and in the close work group improved by 0.181 ± 0.124 logMAR"

    return {
        "study_id": entry["study_id"],
        "found": False,
        "effect_type": None,
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
        "source_quote": "Parents were asked to complete a compliance diary recording the duration and activity performed during occlusion.",
        "reasoning": "Outcome is subjective adherence on 5-point scale, but results text only reports VA improvement data. No adherence scale scores reported."
    }


def extract_mohammed_2021(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Mohammed 2021_2021 - Change from baseline in 6-minute walk distance (6MWT) (subgroups with different formulations)"""
    # Outcome: "Change from baseline in 6-minute walk distance (6MWT) (subgroups with different formulations)" (continuous)
    # Results: "There was a signiﬁcant improvement in the 6 MWD and oxygen saturation in the mono-
    # therapy group. Both the parameters had insigniﬁcant improvement in the combination therapy group"
    # "The primary and secondary outcomes in both the groups were similar without any signiﬁcant differences (Table 2)"
    # Tables not shown in results_text

    return {
        "study_id": entry["study_id"],
        "found": False,
        "effect_type": None,
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
        "source_quote": "There was a signiﬁcant improvement in the 6 MWD and oxygen saturation in the monotherapy group. Both the parameters had insigniﬁcant improvement in the combination therapy group (Table 3).",
        "reasoning": "Results mention significant improvement in 6MWD in monotherapy group and refer to Table 3 for detailed data, but table content not included in results_text. Cannot extract specific mean change values with SD."
    }


def main():
    # Load input
    with open('C:/Users/user/rct-extractor-v2/gold_data/mega/clean_batch_r49.json', 'r', encoding='utf-8') as f:
        batch = json.load(f)

    # Define extraction functions
    extractors = {
        "Kumar Rai 2022_2022": extract_kumar_rai_2022,
        "Thuluva 2022_2022": extract_thuluva_2022,
        "Mantovani 2010_2010": extract_mantovani_2010,
        "Baldi 2010_2010": extract_baldi_2010,
        "Aleem 2021_2021": extract_aleem_2021,
        "Fiscella 2018_2018": extract_fiscella_2018,
        "Cook 2017_2017": extract_cook_2017,
        "Bilger 2019_2019": extract_bilger_2019,
        "Gray 2012_2012": extract_gray_2012,
        "Goldstein 2007_2007": extract_goldstein_2007,
        "Apsangikar 2021_2021": extract_apsangikar_2021,
        "Yoon 2022_2022": extract_yoon_2022,
        "Herbison 2016_2016": extract_herbison_2016,
        "Jukes 2019_2019": extract_jukes_2019,
        "Mohammed 2021_2021": extract_mohammed_2021,
    }

    results = []

    for entry in batch:
        study_id = entry["study_id"]

        if study_id in extractors:
            result = extractors[study_id](entry)
            results.append(result)
        else:
            # For entries not yet processed, mark as pending
            results.append({
                "study_id": study_id,
                "found": False,
                "effect_type": None,
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
                "reasoning": "NOT YET PROCESSED"
            })

    # Write output
    with open('C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r49.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Processed {len(results)} entries")
    print(f"Found data: {sum(1 for r in results if r['found'])}")
    print(f"Not found: {sum(1 for r in results if not r['found'])}")


if __name__ == '__main__':
    main()
