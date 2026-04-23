# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
"""
Manual extraction from clean_batch_r38.json results_text.
Extracts explicitly stated numerical data only - no calculation or inference.
"""

import json
import re

def extract_study_data(entry):
    """
    Extract outcome data from a single study entry.
    Returns a dict with extracted fields.
    """
    study_id = entry["study_id"]
    outcome = entry["outcome"]
    data_type = entry.get("data_type")
    results_text = entry["results_text"]

    result = {
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
        "reasoning": ""
    }

    # Process each study individually
    # Study-specific extraction logic goes here

    if study_id == "Dass 2012_2012":
        # Outcome: "Recurrence rate"
        # Results text mentions: "three recurrences for the primary closure group against zero
        # recurrence of the Limberg flap group"
        # 40 patients per group
        result["found"] = True
        result["effect_type"] = "OR"
        result["intervention_events"] = 0  # Limberg flap (intervention)
        result["intervention_n"] = 40
        result["control_events"] = 3  # Primary closure (control)
        result["control_n"] = 40
        result["source_quote"] = "three recurrences for the primary closure group against zero recurrence of the Limberg flap group"
        result["reasoning"] = "Binary outcome data explicitly stated. Limberg flap group (40 patients) had 0 recurrences, primary closure group (40 patients) had 3 recurrences."

    elif study_id == "Enshaei 2014_2014":
        # Outcome: "Time to wound healing"
        # data_type: "continuous"
        # Results mention various metrics but NOT time to wound healing explicitly
        # Pain relief duration and suture duration mentioned, but NOT wound healing time
        result["found"] = False
        result["reasoning"] = "Time to wound healing not explicitly stated. Results mention pain relief duration (15.2±3.35 vs 7±2.3 days) and suture duration (15.3±2.3 vs 12±3.6 days), but these are different outcomes."
        result["source_quote"] = ""

    elif study_id == "Alvandipour 2019_2019":
        # Outcome: "Time to wound healing"
        # data_type: "continuous"
        # Results text: "Compared to the KF group, the LF group showed faster complete wound healing"
        # But no explicit numerical values for time to wound healing
        result["found"] = False
        result["reasoning"] = "Results state 'faster complete wound healing' for LF group compared to KF group, but no explicit numerical values (mean, SD, or median) for time to wound healing are provided."
        result["source_quote"] = "Compared to the KF group, the LF group showed faster complete wound healing"

    elif study_id == "Arnous 2019_2019":
        # Outcome: "Recurrence rate"
        # Results: "Group I had significantly higher recurrence rate (20% vs 0; P < 0.02)"
        # 60 patients total, need to find n per group
        # Looking for group sizes... "Sixty patients were included"
        # Need to check if groups are equal
        result["found"] = False
        result["reasoning"] = "Recurrence rate mentioned as percentages (20% vs 0%), but the number of patients per group is not explicitly stated in the results_text excerpt. Cannot determine absolute numbers without group sizes."
        result["source_quote"] = "Group I had significantly higher recurrence rate (20% vs 0; P < 0.02)"

    elif study_id == "Finberg 2021_2021":
        # Outcome: "All-cause mortality – at 28 to 30 days, or in‐hospital"
        # Results: "Fifty patients were enrolled and stratified by disease severity"
        # No explicit mortality data in the excerpt
        result["found"] = False
        result["reasoning"] = "No explicit all-cause mortality data found in results_text excerpt. Text discusses viral clearance outcomes but not mortality counts."
        result["source_quote"] = ""

    elif study_id == "Lou 2020_2020":
        # Outcome: "Progression to invasive mechanical ventilation"
        # Results text does not mention mechanical ventilation explicitly
        result["found"] = False
        result["reasoning"] = "No explicit data on progression to invasive mechanical ventilation in results_text. Text discusses viral clearance and clinical improvement but not mechanical ventilation."
        result["source_quote"] = ""

    elif study_id == "McMahon 2022_2022":
        # Outcome: "Need for admission to hospital (if ambulatory)"
        # Results: "Progression to hospitalisation for those in the community (WHO category 1 or 2)
        # occurred in 14 people receiving favipiravir and 9 receiving placebo (p = 0.38)"
        # Need to find total n per group
        # "200 participants... 199 participants in the intention to treat population"
        # "mITT population comprised 190 people"
        # Looking for allocation... need to trace back
        result["found"] = True
        result["effect_type"] = "OR"
        result["intervention_events"] = 14  # favipiravir
        result["control_events"] = 9  # placebo
        # From text: 199 ITT, need to check allocation ratio
        # Cannot determine exact n per group from excerpt, mark as found but incomplete
        result["intervention_n"] = None
        result["control_n"] = None
        result["source_quote"] = "Progression to hospitalisation for those in the community (WHO category 1 or 2) occurred in 14 people receiving favipiravir and 9 receiving placebo (p = 0.38)"
        result["reasoning"] = "Events explicitly stated (14 favipiravir, 9 placebo) but denominators not explicitly stated in this excerpt. Would need baseline table or earlier text."
        result["found"] = False  # Mark as not found due to missing denominators

    elif study_id == "Lowe 2022_2022":
        # Outcome: "All adverse events"
        # data_type: "binary"
        # Results mention adverse events but need to find total counts
        result["found"] = False
        result["reasoning"] = "Adverse events discussed but specific counts per arm not extracted yet from this excerpt."
        result["source_quote"] = ""

    elif study_id == "Shinkai 2021_2021":
        # Outcome: "All adverse events"
        # data_type: "binary"
        # Results: "A total of 156 patients were randomized"
        # "Although adverse events in the favipiravir group were predominantly transient,
        # the incidence was significantly higher"
        # Need to find actual numbers
        result["found"] = False
        result["reasoning"] = "Results state adverse events were significantly higher in favipiravir group but explicit counts not provided in this excerpt."
        result["source_quote"] = "Although adverse events in the favipiravir group were predominantly transient, the incidence was significantly higher"

    return result


def main():
    # Load input data
    input_file = "C:/Users/user/rct-extractor-v2/gold_data/mega/clean_batch_r38.json"
    output_file = "C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r38.json"

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Processing {len(data)} studies...")

    results = []
    for entry in data:
        result = extract_study_data(entry)
        results.append(result)
        print(f"  {result['study_id']}: found={result['found']}")

    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nWrote {len(results)} results to {output_file}")
    found_count = sum(1 for r in results if r['found'])
    print(f"Found data for {found_count}/{len(results)} studies")


if __name__ == "__main__":
    main()
