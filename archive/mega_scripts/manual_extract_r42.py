#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Manual extraction for clean_batch_r42.json
Each study manually reviewed and extracted based on results_text
"""

import json
import sys

# Fix Windows cp1252 encoding issues
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def create_result(study_id, found=False, **kwargs):
    """Helper to create result dict with all fields"""
    result = {
        "study_id": study_id,
        "found": found,
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
    result.update(kwargs)
    return result

def extract_all_studies():
    """
    Manual extraction for all 15 studies in clean_batch_r42.json
    Based on careful reading of results_text for each entry.
    """
    results = []

    # 1. Rosario 2012 - BMI short-term
    # Results text: "BMI z-score increased 0.176 units more in the control group than in the intervention group [95% CI = (0.044;0.308), p = 0.009]"
    # Outcome: BMI short-term
    results.append(create_result(
        "Rosario 2012_2012",
        found=True,
        effect_type="MD",
        point_estimate=-0.176,  # Intervention effect (intervention minus control)
        ci_lower=-0.308,
        ci_upper=-0.044,
        source_quote="BMI z-score increased 0.176 units more in the control group than in the intervention group [95% CI = (0.044;0.308), p = 0.009]",
        reasoning="Mean difference in BMI z-score change. Text states control increased 0.176 more than intervention, so intervention effect is -0.176. CI needs sign flip: original (0.044, 0.308) is for control-intervention, so intervention-control is (-0.308, -0.044)"
    ))

    # 2. Rosenkranz 2010 - BMI short-term
    # Results text: "Most effects of the intervention on individual-level variables of girls and parents were not significantly different from the control condition, including the primary outcome of child BMI z-score (F1, 5 = 0.42, p = .544)"
    # No explicit numerical outcome data
    results.append(create_result(
        "Rosenkranz 2010_2010",
        found=False,
        reasoning="Results state no significant difference in BMI z-score (p=.544) but do not provide explicit mean values, confidence intervals, or effect estimates for BMI outcome"
    ))

    # 3. Kain 2014 - BMI medium-term
    # Results text: "In boys, BMI Z declined (1.33–1.24) and increased (1.22–1.35) in intervention and control schools, respectively. In girls, BMI Z remained unchanged in intervention schools, while increasing significantly in control schools (0.91–1.06, P= 0.024). Interaction group ∗time was significant for boys (P< 0.0001) and girls (P= 0.004)."
    # Outcome: BMI medium-term - looking for overall effect or gender-specific
    # Boys: intervention change = -0.09, control change = +0.13
    # Girls: intervention change ≈ 0, control change = +0.15
    results.append(create_result(
        "Kain 2014_2014",
        found=True,
        effect_type="MD",
        intervention_mean=1.24,  # Boys post-intervention BMI Z
        control_mean=1.35,  # Boys post-intervention control BMI Z (worse outcome, higher)
        source_quote="In boys, BMI Z declined (1.33–1.24) and increased (1.22–1.35) in intervention and control schools, respectively.",
        reasoning="Boys showed BMI Z decline in intervention (1.33→1.24) vs increase in control (1.22→1.35). Extracted final BMI Z values. Point estimate would be 1.24-1.35=-0.11 but not explicitly stated. Interaction significant (P<0.0001)"
    ))

    # 4. Elder 2014 - BMI medium-term
    # Results text: "No significant intervention effects were observed for the primary outcomes of child or parent BMI and child waist circumference."
    # BUT also states: "Moderator analyses however showed girls (but not boys) in the intervention condition reduced their BMI."
    # No explicit numerical BMI data for overall or subgroup
    results.append(create_result(
        "Elder 2014_2014",
        found=False,
        reasoning="Results state no significant intervention effects on child BMI in primary analysis. Moderator analysis showed effect in girls but no explicit BMI values, CIs, or effect estimates provided in results text"
    ))

    # 5. Klesges 2010 - BMI medium-term
    # Results text: "BMI increased in all girls with no treatment effect (obesity prevention minus alternative) at 2 years (0.09, 95% CI: −0.40, 0.58) kg/m2"
    # Clear MD with CI
    results.append(create_result(
        "Klesges 2010_2010",
        found=True,
        effect_type="MD",
        point_estimate=0.09,
        ci_lower=-0.40,
        ci_upper=0.58,
        source_quote="BMI increased in all girls with no treatment effect (obesity prevention minus alternative) at 2 years (0.09, 95% CI: −0.40, 0.58) kg/m2",
        reasoning="Explicit mean difference in BMI at 2 years with 95% CI. Treatment effect (intervention minus control) = 0.09 kg/m2, not significant as CI crosses zero"
    ))

    # 6. Kobel 2017 - BMI medium-term
    # Results text mentions FVI, PA, SDC but for BMI: "Although the effects are small, the intervention seems to reach children with MB. An intervention lasting longer than one year might result in more changes."
    # Uses logistic regression for OR outcomes but no explicit BMI data
    results.append(create_result(
        "Kobel 2017_2017",
        found=False,
        reasoning="Results discuss intervention effects on FVI, PA, SDC with odds ratios but do not provide explicit BMI values, changes, or effect estimates for the BMI outcome"
    ))

    # 7. Kubik 2021 - BMI medium-term
    # Results text: "In an intent-to-treat analysis, there were no significant between-group differences in child BMIz at 12 [0.04; 95% confidence interval (CI) -0.07 to 0.16] or 24 months (0.06; 95% CI -0.08 to 0.20)"
    # Clear MD with CI for BMIz
    results.append(create_result(
        "Kubik 2021_2021",
        found=True,
        effect_type="MD",
        point_estimate=0.06,  # 24 months is more relevant for "medium-term"
        ci_lower=-0.08,
        ci_upper=0.20,
        source_quote="there were no significant between-group differences in child BMIz at 12 [0.04; 95% confidence interval (CI) -0.07 to 0.16] or 24 months (0.06; 95% CI -0.08 to 0.20)",
        reasoning="Explicit mean difference in BMI z-score at 24 months (medium-term endpoint) with 95% CI. Effect = 0.06, not significant"
    ))

    # 8. Grydeland 2014 - BMI long-term
    # Results text: "Beneficial effects were found for BMI (p=0.02) and BMIz (p=0.003) in girls, but not in boys."
    # P-values given but no explicit effect sizes or CIs in the abstract
    results.append(create_result(
        "Grydeland 2014_2014",
        found=False,
        reasoning="Results report significant effects on BMI (p=0.02) and BMIz (p=0.003) in girls, but no explicit effect estimates, mean differences, or confidence intervals provided in results text"
    ))

    # 9. Caballero 2003 - BMI long-term
    # Results text: "The intervention resulted in no significant reduction in percentage body fat. However, a significant reduction in the percentage of energy from fat was observed in the intervention schools."
    # Focus is on % body fat, not BMI. No BMI data provided
    results.append(create_result(
        "Caballero 2003_2003",
        found=False,
        reasoning="Results focus on percentage body fat (no significant reduction) and dietary fat intake. No explicit BMI values or effect estimates provided for BMI outcome"
    ))

    # 10. Story 2012 - BMI long-term
    # Results text mentions: "While the intervention was not associated with statistically significant change in mean levels of BMI, BMI-Z, skinfolds or percentage body fat, the intervention was associated with a statistically significant net decrease of 10% in the prevalence of overweight."
    # Also: "Intervention children experienced a 13.4% incidence of overweight, while the control children experienced a corresponding incidence of 24.8%; a difference of −11.4% (p=0.033)."
    # This is about overweight prevalence/incidence, not BMI values
    results.append(create_result(
        "Story 2012_2012",
        found=False,
        reasoning="Results state no significant change in mean BMI or BMI-Z. Only overweight prevalence/incidence data provided (13.4% vs 24.8%, p=0.033), which is categorical not continuous BMI outcome"
    ))

    # 11. Baranowski 2011 - zBMI short-term
    # Results text: "Children playing these video games increased fruit and vegetable consumption by about .67 servings per day (p<0.018), but not water, moderate-to-vigorous physical activity, or body composition."
    # States no effect on body composition, which would include zBMI
    results.append(create_result(
        "Baranowski 2011_2011",
        found=False,
        reasoning="Results explicitly state intervention had no effect on body composition (which includes BMI/zBMI). Only significant finding was increased FV consumption. No BMI/zBMI values provided"
    ))

    # 12. Choo 2020 - zBMI short-term
    # Results text: "Compared to the control group, the intervention group showed significant improvements in total composite scores of healthy-lifestyle behaviors—including 60-min of moderate physical activity—but not in obesity status among children."
    # No obesity status change = no zBMI effect
    results.append(create_result(
        "Choo 2020_2020",
        found=False,
        reasoning="Results state significant improvements in healthy lifestyle behaviors but NOT in obesity status (BMI ≥85th percentile). No explicit zBMI values or effect estimates provided"
    ))

    # 13. Griffin 2019 - zBMI short-term
    # Results text: "Weight loss at 6 months in the intervention group (n=17) was 2.9 kg (95% CI −5.1 to −0.6)."
    # This is weight loss in fathers (not children). The study is about fathers and children but weight loss reported is for fathers
    # No child zBMI data in results text
    results.append(create_result(
        "Griffin 2019_2019",
        found=False,
        reasoning="Results report weight loss in fathers (2.9 kg, 95% CI -5.1 to -0.6) but the outcome is child zBMI. No explicit child BMI or zBMI data provided in results text"
    ))

    # 14. Haire-Joshu 2010 - zBMI short-term
    # Results text focuses on behavioral outcomes: knowledge, challenges, calorie intake, activity time
    # "There were no significant differences in percent time being active."
    # No BMI/zBMI data mentioned
    results.append(create_result(
        "Haire-Joshu 2010_2010",
        found=False,
        reasoning="Results report behavioral outcomes (knowledge, dietary intake, activity) but do not provide any BMI or zBMI values, changes, or effect estimates for the zBMI outcome"
    ))

    # 15. Kocken 2016 - zBMI short-term
    # Results text: "No positive effects of EF! were found with regard to behavior and anthropometric measures when follow-up measurements were compared to the baseline."
    # "limited intervention effects were found for the intervention on knowledge and inactivity"
    # No explicit zBMI data
    results.append(create_result(
        "Kocken 2016_2016",
        found=False,
        reasoning="Results state no positive effects on anthropometric measures (which includes BMI/zBMI). Only significant effects were on knowledge and inactivity. No explicit zBMI values provided"
    ))

    return results

def main():
    print("Manual extraction for clean_batch_r42.json")
    print("=" * 60)

    results = extract_all_studies()

    # Display summary
    print(f"\nProcessed {len(results)} studies:")
    for i, r in enumerate(results, 1):
        status = "[OK]" if r["found"] else "[--]"
        effect_info = f" ({r['effect_type']})" if r["effect_type"] else ""
        print(f"{i:2d}. {status} {r['study_id']}{effect_info}")
        if r["found"] and r["point_estimate"] is not None:
            print(f"     Point estimate: {r['point_estimate']}, CI: [{r['ci_lower']}, {r['ci_upper']}]")

    found_count = sum(1 for r in results if r["found"])
    print(f"\nSummary: {found_count}/{len(results)} studies with extractable data")

    # Write output
    output_path = 'C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r42.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Wrote results to {output_path}")

if __name__ == "__main__":
    main()
