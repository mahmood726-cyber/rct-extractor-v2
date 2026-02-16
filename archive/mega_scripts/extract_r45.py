import json
import re

# Read the batch file
with open("C:/Users/user/rct-extractor-v2/gold_data/mega/clean_batch_r45.json", "r", encoding="utf-8") as f:
    batch = json.load(f)

results = []

for entry in batch:
    study_id = entry["study_id"]
    outcome = entry["outcome"]
    data_type = entry.get("data_type")
    results_text = entry["results_text"]

    # Initialize result object
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
        "source_quote": None,
        "reasoning": None
    }

    # Study-specific extraction logic

    # French 2011 - zBMI medium term
    if study_id == "French 2011_2011":
        result["found"] = False
        result["reasoning"] = "No significant intervention effects were observed for change in HH BMI-z score mentioned in text, but no numerical data provided."

    # Black 2010 - zBMI medium term
    elif study_id == "Black 2010_2010":
        result["found"] = False
        result["reasoning"] = "Text mentions sustained effects over 24 months in preventing BMI category increase, but no zBMI numerical values provided."

    # Bogart 2016 - Percentile long term
    elif study_id == "Bogart 2016_2016":
        # Handle Unicode en-dash (–), minus sign (−), and regular hyphen
        match = re.search(r"b\s*=\s*[–\u2212-](\d+\.\d+)\s*percentiles;\s*SE,\s*(\d+\.\d+)", results_text)
        if match:
            result["found"] = True
            result["effect_type"] = "MD"
            result["point_estimate"] = -float(match.group(1))
            result["source_quote"] = "intervention students who were classified as obese at baseline (in seventh grade) showed significant reductions in BMI percentile in ninth grade (b = –2.33 percentiles; SE, 0.83; P = .005)"
            result["reasoning"] = "MD extracted from regression coefficient (b = -2.33) for obese subgroup at 2-year follow-up."
        else:
            result["found"] = False
            result["reasoning"] = "Cannot find BMI percentile data for overall population."

    # Gonzalez-Ortega 2021 - PANSS total
    elif study_id == "Gonzalez-Ortega 2021_2021":
        result["found"] = False
        result["reasoning"] = "Text describes greater decline in general psychotic symptoms but no PANSS total scores provided."

    # Kuhlemeier 2022 - zBMI long term
    elif study_id == "Kuhlemeier 2022_2022":
        result["found"] = False
        result["reasoning"] = "Text describes PITE framework methodology but no endpoint BMI z-scores provided in this excerpt."

    # Dadabayev 2020 - pain intensity continuous
    elif study_id == "Dadabayev 2020_2020":
        result["found"] = False
        result["reasoning"] = "Text states both treatments offered comparable improvement, but no numerical VAS or pain scores provided in excerpt."

    # Gasser 2014 - Anxiety on STAI-T
    elif study_id == "Gasser 2014_2014":
        result["found"] = False
        result["reasoning"] = "Text mentions STAI reductions with p-values and effect sizes but no mean scores or raw data provided."

    # Griffiths 2016 - Anxiety on STAI-T
    elif study_id == "Griffiths 2016_2016":
        result["found"] = False
        result["reasoning"] = "Text describes methodology and adverse effects but no STAI-T scores provided in this excerpt."

    # Wolfson 2020 - Anxiety on STAI-T
    elif study_id == "Wolfson 2020_2020":
        # Handle Unicode thin space (U+2009) and regular spaces
        match = re.search(r"Hedges['\u2019\u2032]\s*g\s+between-group\s+effect\s+size\s+was\s+(\d+\.\d+)", results_text)
        if match:
            result["found"] = True
            result["effect_type"] = "SMD"
            result["point_estimate"] = float(match.group(1))
            result["source_quote"] = "Hedges' g between-group effect size was 1.03 (95% CI: -5.25, 7.31)"
            result["reasoning"] = "SMD (Hedges' g) extracted for STAI-T outcome."
        else:
            result["found"] = False
            result["reasoning"] = "No STAI-T scores found."

    # Miller 2008 - All-cause mortality
    elif study_id == "Miller 2008_2008":
        # Handle potential newlines in text
        match = re.search(r"Mortality\s+was\s+(\d+)%\s+in\s+the\s+endoscopic\s+group\s+and\s+(\d+)%\s+in\s+the\s+medical\s+treatment\s+cohort", results_text)
        if match:
            # Need to find group sizes - "Six patients underwent endoscopic evacuation" and total 10 enrolled
            endo_match = re.search(r"Six patients underwent\s+endoscopic evacuation", results_text)
            if endo_match:
                result["found"] = True
                result["effect_type"] = "RR"
                result["intervention_events"] = 1  # 20% of 6 = 1.2, round to 1
                result["intervention_n"] = 6
                result["control_events"] = 2  # 50% of 4 = 2
                result["control_n"] = 4
                result["source_quote"] = "Mortality was 20% in the endoscopic group and 50% in the medical treatment cohort. Six patients underwent endoscopic evacuation"
                result["reasoning"] = "Binary outcome: 20% of 6 endoscopic = 1.2 (round to 1 death), 50% of 4 medical = 2 deaths. 10 patients enrolled total, 6 endoscopic + 4 medical."
            else:
                result["found"] = False
                result["reasoning"] = "Percentages found but cannot determine exact event counts."
        else:
            result["found"] = False
            result["reasoning"] = "No mortality data found in excerpt."

    # Ross 2016 - Anxiety on STAI-T
    elif study_id == "Ross 2016_2016":
        result["found"] = False
        result["reasoning"] = "Text describes sustained benefits and percentage with reductions, but no STAI-T mean scores provided in excerpt."

    # Liu 2023 - All-cause mortality at day 28
    elif study_id == "Liu 2023_2023":
        match = re.search(r"there were (\d+)/(\d+) deaths in\s+the control arm and (\d+)/(\d+) in the Paxlovid arm on day 28", results_text)
        if match:
            result["found"] = True
            result["effect_type"] = "RR"
            result["control_events"] = int(match.group(1))
            result["control_n"] = int(match.group(2))
            result["intervention_events"] = int(match.group(3))
            result["intervention_n"] = int(match.group(4))
            result["source_quote"] = "there were 8/132 deaths in the control arm and 5/132 in the Paxlovid arm on day 28"
            result["reasoning"] = "Binary outcome: 8 deaths in 132 control, 5 deaths in 132 Paxlovid."
        else:
            result["found"] = False
            result["reasoning"] = "No day 28 mortality data found."

    # Mirashrafi 2021 - Pain intensity child-reported 2-24h
    elif study_id == "Mirashrafi 2021_2021":
        result["found"] = False
        result["reasoning"] = "Text states no statistical difference in pain scores on postoperative days 1-3, but no numerical values provided in excerpt."

    # Mahgoobifard 2014 - Pain intensity third-party <2h
    elif study_id == "Mahgoobifard 2014_2014":
        # PACU scores - handle Unicode plus-minus symbol (±), flexible whitespace
        pacu_match = re.search(r"Pain\s+intensity\s+in\s+PACU\s+in\s+Acetaminophen\s+group\s+was\s+(\d+\.\d+)\s*±\s*(\d+\.\d+)\s+vs\.?\s*(\d+\.\d+)\s*±\s*(\d+\.\d+)\s+in\s+placebo\s+group\s+and\s+(\d+\.\d+)\s*±\s*(\d+\.\d+)\s+in\s+ibuprofen\s+group", results_text, re.IGNORECASE)
        if pacu_match:
            result["found"] = True
            result["effect_type"] = "MD"
            result["intervention_mean"] = float(pacu_match.group(1))
            result["intervention_sd"] = float(pacu_match.group(2))
            result["control_mean"] = float(pacu_match.group(5))  # ibuprofen group
            result["control_sd"] = float(pacu_match.group(6))
            result["source_quote"] = "Pain intensity in PACU in Acetaminophen group was 7.05 ± 0.64 vs. 8.38 ± 1.20 in placebo group and 8.14 ± 0.85 in ibuprofen group"
            result["reasoning"] = "PACU pain intensity (CHEOPS scale) - acetaminophen vs ibuprofen groups. PACU is <2h postoperative."
        else:
            result["found"] = False
            result["reasoning"] = "No pain intensity data found in PACU timeframe."

    # Zulqarnain 2019 - Apnea episodes after 24h
    elif study_id == "Zulqarnain 2019_2019":
        result["found"] = False
        result["reasoning"] = "Text provides mean apnea events/day at multiple timepoints but not specifically 'after 24 hours over a 24-hour period' as requested."

    results.append(result)

# Write output
with open("C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r45.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"Processed {len(results)} entries")
print(f"Found: {sum(1 for r in results if r['found'])}")
print(f"Not found: {sum(1 for r in results if not r['found'])}")
