#!/usr/bin/env python3
"""
Manual extraction for clean_batch_r47.json
Carefully read each results_text and extract ONLY explicitly stated data.
"""

import json
import re
import sys
import io
import unicodedata

# Set UTF-8 encoding for output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def extract_data():
    """Extract outcome data from all 15 entries."""

    with open('gold_data/mega/clean_batch_r47.json', 'r', encoding='utf-8') as f:
        batch = json.load(f)

    results = []

    for entry in batch:
        study_id = entry["study_id"]
        outcome = entry["outcome"]
        data_type = entry["data_type"]
        results_text = entry.get("results_text", "")

        # Normalize Unicode (ligatures, special chars)
        results_text = unicodedata.normalize('NFKD', results_text)

        print(f"\n{'='*80}")
        print(f"Study: {study_id}")
        print(f"Outcome: {outcome}")
        print(f"Data type: {data_type}")
        print(f"Results text length: {len(results_text)} chars")
        print(f"{'='*80}")

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

        # Extract based on study_id and outcome

        # Study 1: Thomas 2022 - COVID-19 incidence
        if study_id == "Thomas 2022_2022":
            # Look for: "Four BNT162b2 and 71 placebo recipients developed COVID-19"
            # VE: 94.4% (95% CI: 85.2, 98.5)
            match1 = re.search(r'Four BNT162b2 and 71 placebo recipients\s+developed COVID-19', results_text, re.IGNORECASE)
            match2 = re.search(r'vaccine\s+efficacy\s+was\s+94\.4%\s*\(95%\s*CI:\s*85\.2,\s*98\.5\)', results_text, re.IGNORECASE)

            if match1:
                result["found"] = True
                result["effect_type"] = "VE"
                result["intervention_events"] = 4
                result["control_events"] = 71
                # Total N per arm not explicitly stated, so leave as null
                result["source_quote"] = "Four BNT162b2 and 71 placebo recipients developed COVID-19 from 7 days post-dose 2"
                result["reasoning"] = "Events clearly stated: 4 in BNT162b2, 71 in placebo. Total N per arm not explicitly stated in results_text."

                if match2:
                    result["point_estimate"] = 94.4
                    result["ci_lower"] = 85.2
                    result["ci_upper"] = 98.5
                    result["source_quote"] += "; vaccine efficacy was 94.4% (95% CI: 85.2, 98.5)"

        # Study 2: Chandran 2021 - 28-day mortality
        elif study_id == "Chandran 2021_2021":
            # "62.74% (32 of 51) tracheostomies were done early"
            # "The 30-day mortality rate was 66.66% (34 of 51)"
            # "Of these, 23 (67.64%) tracheostomies were performed early and 11 (32.36%) late"
            match1 = re.search(r'62\.74%\s*\(32\s+of\s+51\)', results_text)
            match2 = re.search(r'Of these,\s+23\s+\(67\.64%\)\s+tracheostomies were performed early and\s+11\s+\(32\.36%\)\s+late', results_text)

            if match1 and match2:
                result["found"] = True
                result["effect_type"] = "RR"
                result["intervention_events"] = 23  # Early deaths
                result["intervention_n"] = 32
                result["control_events"] = 11  # Late deaths
                result["control_n"] = 19  # 51 total - 32 early
                result["source_quote"] = "62.74% (32 of 51) tracheostomies were done early; 30-day mortality was 66.66% (34 of 51) with 23 deaths in early group and 11 in late group"
                result["reasoning"] = "Early tracheostomy: 23/32 died. Late tracheostomy: 11/19 died (51 total - 32 early = 19 late)."

        # Study 3: Volo 2021 - Overall mortality
        elif study_id == "Volo 2021_2021":
            # Only percentages given, no absolute counts
            result["found"] = False
            result["source_quote"] = "The mortality rate of COVID-19 patients admitted to ICU that underwent tracheostomy was 18%"
            result["reasoning"] = "Only percentages provided (18% mortality in tracheostomy group, 53% overall ICU). No absolute event counts or denominators explicitly stated."

        # Study 4: Polok 2021 - 90-day mortality
        elif study_id == "Polok 2021_2021":
            # "hazard ratio [HR]¼0.96; 95% confidence interval [CI], 0.70e1.33"
            # Note: special chars ¼ (equals) and e (dash)
            match = re.search(r'hazard\s+ratio.*?HR.*?0\.96.*?confidence\s+interval.*?CI.*?0\.70.*?1\.33', results_text, re.IGNORECASE | re.DOTALL)

            if match:
                result["found"] = True
                result["effect_type"] = "HR"
                result["point_estimate"] = 0.96
                result["ci_lower"] = 0.70
                result["ci_upper"] = 1.33
                result["source_quote"] = "hazard ratio [HR]=0.96; 95% confidence interval [CI], 0.70-1.33 (in primary analysis)"
                result["reasoning"] = "HR with 95% CI explicitly stated for 3-month mortality comparison between early and late tracheostomy."

        # Study 5: Kuno 2021 - In-hospital mortality
        elif study_id == "Kuno 2021_2021":
            # No numerical data in results_text provided
            result["found"] = False
            result["reasoning"] = "Results text is discussion/conclusion only. No numerical outcome data presented."

        # Study 6: Arnold 2022 - In-hospital mortality
        elif study_id == "Arnold 2022_2022":
            # No mortality data explicitly stated in results excerpt
            result["found"] = False
            result["reasoning"] = "Results text discusses timing, decannulation, ICU stay. No mortality counts explicitly stated."

        # Study 7: Evrard 2021 - Tracheal stenosis
        elif study_id == "Evrard 2021_2021":
            # data_type is null, outcome is tracheal stenosis
            # Looking for complication rates
            # "17 (57%) had complications with unilateral laryngeal palsy (n = 5)"
            # But this is out of 30 examined, not the full 48
            result["found"] = False
            result["reasoning"] = "Outcome is tracheal stenosis (data_type=null). Complications mentioned but no direct comparison for tracheal stenosis between early vs late groups."

        # Study 8: Mahmood 2021 - In-hospital mortality
        elif study_id == "Mahmood 2021_2021":
            # "Eighteen (15.3%) patients died in the hospital"
            # "100 patients (84.7%) were discharged from the hospital"
            # Total: 118 patients
            # But no breakdown by early vs late timing
            result["found"] = False
            result["source_quote"] = "Eighteen (15.3%) patients died in the hospital"
            result["reasoning"] = "Overall mortality stated (18/118) but no breakdown by intervention (early vs late tracheostomy) provided in results_text."

        # Study 9: Battaglini 2021 - 28-day mortality
        elif study_id == "Battaglini 2021_2021":
            # "There was no significant difference in survival between early and late"
            # No specific numbers given in the excerpt
            result["found"] = False
            result["reasoning"] = "Results text states no difference in survival between early vs late tracheostomy but provides no specific mortality counts."

        # Study 10: Livneh 2021 - Overall mortality and in-hospital mortality
        elif study_id == "Livneh 2021_2021":
            # "Decannulation rates were significantly higher while mortality rates were non-significantly lower in the early tracheostomy group compared with the late tracheostomy group (58% vs 21% p < 0.05; 42% vs 74% p = 0.1, respectively)"
            # 58% vs 21% = decannulation
            # 42% vs 74% = mortality
            # But no absolute counts or totals given
            result["found"] = False
            result["source_quote"] = "mortality rates were non-significantly lower in the early tracheostomy group compared with the late tracheostomy group (42% vs 74% p = 0.1)"
            result["reasoning"] = "Percentages provided (42% mortality in early vs 74% in late) but no absolute counts or group sizes."

        # Study 11: Glibbery 2020 - Duration to liberation from mechanical ventilation
        elif study_id == "Glibbery 2020_2020":
            # Continuous outcome
            # "Mean time to decannulation was 15.8 days (standard deviation = 9.4)"
            # But this is overall, not early vs late comparison
            result["found"] = False
            result["reasoning"] = "Outcome is duration to liberation (continuous). Results provide overall means but no intervention vs control comparison."

        # Study 12: Hansson 2022 - 28-day mortality
        elif study_id == "Hansson 2022_2022":
            # "Early tracheostomy (<7 days, n = 56) was associated with a shorter median duration..."
            # But no mortality data in results excerpt
            result["found"] = False
            result["reasoning"] = "Results text discusses ventilation duration and ICU stay. No mortality outcome data explicitly stated."

        # Study 13: Yao 2007 - Serious adverse events
        elif study_id == "Yao 2007_2007":
            # Hepatitis B drug trial, not COVID/tracheostomy
            # "68% vs. 6%, respectively) achieved ALT normalization"
            # "The safety profile of entecavir was similar to that of placebo"
            # Need to look for serious adverse events specifically
            result["found"] = False
            result["reasoning"] = "Outcome is serious adverse events. Results text discusses efficacy (ALT normalization, HBV DNA) and states 'safety profile similar' but no specific SAE counts given."

        # Study 14: Luetkemeyer 2011 - Detectable HBV-DNA
        elif study_id == "Luetkemeyer 2011_2011":
            # "All 10 enrollees..."
            # "The 5 participants randomized to ETV intensification all had HBV <1.6 log10 IU/mL by 48 weeks"
            # "In the 5 patients randomized to no ETV intensification, 3 participants (#1, 4, 5)...had HBV DNA <1.6 log10 IU/mL by week 12"
            # So ETV: 5/5 suppressed. No ETV: 3/5 suppressed at 12 weeks
            match1 = re.search(r'The 5 participants randomized to ETV intensification all had\s+HBV <1\.6 log10 IU/mL by 48 weeks', results_text)
            match2 = re.search(r'In the 5 patients randomized to no ETV\s+intensification, 3 participants.*?had\s+HBV DNA <1\.6 log10 IU/mL by week 12', results_text, re.DOTALL)

            if match1 and match2:
                result["found"] = True
                result["effect_type"] = "RR"
                # Detectable HBV-DNA means NOT suppressed
                # ETV: 0/5 detectable (5/5 suppressed)
                # No ETV: 2/5 detectable (3/5 suppressed at week 12, but 2/5 still detectable at week 24)
                result["intervention_events"] = 0  # ETV group with detectable HBV
                result["intervention_n"] = 5
                result["control_events"] = 2  # No ETV with detectable HBV at 24 weeks
                result["control_n"] = 5
                result["source_quote"] = "The 5 participants randomized to ETV intensification all had HBV <1.6 log10 IU/mL by 48 weeks. In the 5 patients randomized to no ETV intensification, 3 had HBV DNA <1.6 by week 12; 2 had detectable HBV at 24 weeks."
                result["reasoning"] = "Outcome is detectable HBV-DNA. ETV: 0/5 detectable (all suppressed). Control: 2/5 detectable at 24 weeks (#2, #3 per text)."

        # Study 15: Tetaj 2021 - 28-day mortality
        elif study_id == "Tetaj 2021_2021":
            # "The early group included 61 patients and the late group included 59 patients"
            # "No difference in the case fatality ratio between the two groups was observed"
            # No specific counts
            result["found"] = False
            result["source_quote"] = "No difference in the case fatality ratio between the two groups was observed"
            result["reasoning"] = "Results state no difference in case fatality between early (n=61) and late (n=59) groups but provide no specific death counts."

        results.append(result)

    return results

def main():
    results = extract_data()

    # Write output
    with open('gold_data/mega/clean_results_r47.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Summary
    found_count = sum(1 for r in results if r["found"])
    print(f"\n{'='*80}")
    print(f"[OK] Extraction complete: {found_count}/{len(results)} found")
    print(f"Output: gold_data/mega/clean_results_r47.json")
    print(f"{'='*80}")

    # List found studies
    print("\nFOUND:")
    for r in results:
        if r["found"]:
            print(f"  - {r['study_id']}: {r['effect_type']}")

    print("\nNOT FOUND:")
    for r in results:
        if not r["found"]:
            reason = r["reasoning"][:80] + "..." if len(r["reasoning"]) > 80 else r["reasoning"]
            print(f"  - {r['study_id']}: {reason}")

if __name__ == "__main__":
    main()
