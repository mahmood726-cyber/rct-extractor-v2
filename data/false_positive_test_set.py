"""
False Positive Test Set for RCT Extractor v4.0.6
=================================================

Systematic negative test cases to validate specificity.
Target: 0% false positive rate on 100+ cases.

Categories:
1. Numbers that look like effect estimates
2. Ranges that aren't confidence intervals
3. References and citations
4. Baseline characteristics
5. Descriptive statistics (not effects)
6. Non-clinical contexts
7. Ambiguous formats
8. Near-miss patterns
"""

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class FalsePositiveCategory(Enum):
    """Categories of false positive test cases"""
    NUMERIC_LOOKALIKE = "Numbers resembling effect estimates"
    RANGE_NOT_CI = "Ranges that aren't CIs"
    REFERENCES = "References and citations"
    BASELINE = "Baseline characteristics"
    DESCRIPTIVE = "Descriptive statistics"
    NON_CLINICAL = "Non-clinical context"
    AMBIGUOUS = "Ambiguous formats"
    NEAR_MISS = "Near-miss patterns"


@dataclass
class FalsePositiveCase:
    """A case that should NOT trigger extraction"""
    text: str
    category: FalsePositiveCategory
    reason: str
    should_extract: bool = False  # Always False for this set


# =============================================================================
# FALSE POSITIVE TEST CASES (100+)
# =============================================================================

FALSE_POSITIVE_CASES: List[FalsePositiveCase] = [
    # =========================================================================
    # CATEGORY 1: Numbers that look like effect estimates
    # =========================================================================
    FalsePositiveCase(
        text="The study enrolled 0.75 million patients across 40 countries.",
        category=FalsePositiveCategory.NUMERIC_LOOKALIKE,
        reason="0.75 is a sample size, not an effect estimate"
    ),
    FalsePositiveCase(
        text="Dosing was 0.85 mg/kg administered twice daily.",
        category=FalsePositiveCategory.NUMERIC_LOOKALIKE,
        reason="Drug dosing, not effect estimate"
    ),
    FalsePositiveCase(
        text="The probability threshold was set at 0.95 for significance.",
        category=FalsePositiveCategory.NUMERIC_LOOKALIKE,
        reason="Statistical threshold, not effect"
    ),
    FalsePositiveCase(
        text="Response rate was 95% CI was considered excellent.",
        category=FalsePositiveCategory.NUMERIC_LOOKALIKE,
        reason="CI mentioned but no actual CI values"
    ),
    FalsePositiveCase(
        text="The coefficient was 1.23 in the regression model.",
        category=FalsePositiveCategory.NUMERIC_LOOKALIKE,
        reason="Regression coefficient, not clinical effect"
    ),
    FalsePositiveCase(
        text="Creatinine clearance was 0.82 mL/min/1.73m2.",
        category=FalsePositiveCategory.NUMERIC_LOOKALIKE,
        reason="Lab value, not effect estimate"
    ),
    FalsePositiveCase(
        text="The loading dose was 0.5 mg followed by 0.25 mg daily.",
        category=FalsePositiveCategory.NUMERIC_LOOKALIKE,
        reason="Drug dosing information"
    ),
    FalsePositiveCase(
        text="Intraclass correlation was 0.89 indicating good reliability.",
        category=FalsePositiveCategory.NUMERIC_LOOKALIKE,
        reason="Reliability statistic, not treatment effect"
    ),
    FalsePositiveCase(
        text="The R-squared value was 0.76 for the prediction model.",
        category=FalsePositiveCategory.NUMERIC_LOOKALIKE,
        reason="Model fit statistic"
    ),
    FalsePositiveCase(
        text="Kappa agreement was 0.92 between raters.",
        category=FalsePositiveCategory.NUMERIC_LOOKALIKE,
        reason="Inter-rater reliability, not effect"
    ),

    # =========================================================================
    # CATEGORY 2: Ranges that aren't CIs
    # =========================================================================
    FalsePositiveCase(
        text="Age range was 0.5-0.9 years in the pediatric cohort.",
        category=FalsePositiveCategory.RANGE_NOT_CI,
        reason="Age range, not confidence interval"
    ),
    FalsePositiveCase(
        text="Dose: 1.5 (1.2-1.8) mg/kg based on weight.",
        category=FalsePositiveCategory.RANGE_NOT_CI,
        reason="Dose range, not CI"
    ),
    FalsePositiveCase(
        text="Temperature range 0.8-1.2 degrees above normal.",
        category=FalsePositiveCategory.RANGE_NOT_CI,
        reason="Temperature range"
    ),
    FalsePositiveCase(
        text="BMI ranged from 0.65 to 0.95 in standardized units.",
        category=FalsePositiveCategory.RANGE_NOT_CI,
        reason="Anthropometric range"
    ),
    FalsePositiveCase(
        text="The normal range is 0.7-1.3 mmol/L.",
        category=FalsePositiveCategory.RANGE_NOT_CI,
        reason="Laboratory reference range"
    ),
    FalsePositiveCase(
        text="Score: 0.82 (range 0.75-0.89) on the assessment.",
        category=FalsePositiveCategory.RANGE_NOT_CI,
        reason="Score range, not CI"
    ),
    FalsePositiveCase(
        text="IQR 0.6-0.9 for the biomarker levels.",
        category=FalsePositiveCategory.RANGE_NOT_CI,
        reason="Interquartile range, not CI"
    ),
    FalsePositiveCase(
        text="The therapeutic window is 0.8-1.2 ng/mL.",
        category=FalsePositiveCategory.RANGE_NOT_CI,
        reason="Therapeutic drug range"
    ),
    FalsePositiveCase(
        text="pH range 0.7-0.9 was maintained throughout.",
        category=FalsePositiveCategory.RANGE_NOT_CI,
        reason="pH range"
    ),
    FalsePositiveCase(
        text="Osmolality 0.85-0.95 mOsm/kg was observed.",
        category=FalsePositiveCategory.RANGE_NOT_CI,
        reason="Lab measurement range"
    ),

    # =========================================================================
    # CATEGORY 3: References and citations
    # =========================================================================
    FalsePositiveCase(
        text="See ref 0.85 (95% CI 0.75-0.95) for previous findings.",
        category=FalsePositiveCategory.REFERENCES,
        reason="Reference to another study"
    ),
    FalsePositiveCase(
        text="As reported previously (HR 0.72, 95% CI 0.60-0.86) [12].",
        category=FalsePositiveCategory.REFERENCES,
        reason="Citation of prior result"
    ),
    FalsePositiveCase(
        text="Smith et al. found OR 2.3 (1.8-2.9) in their analysis.",
        category=FalsePositiveCategory.REFERENCES,
        reason="Reference to other study findings"
    ),
    FalsePositiveCase(
        text="The HOPE trial reported RR 0.78 (0.70-0.86) [15].",
        category=FalsePositiveCategory.REFERENCES,
        reason="Citation of another trial"
    ),
    FalsePositiveCase(
        text="Previous meta-analysis: pooled OR 1.45 (1.20-1.75).",
        category=FalsePositiveCategory.REFERENCES,
        reason="Reference to prior meta-analysis"
    ),
    FalsePositiveCase(
        text="Literature suggests HR ranges from 0.6-0.9 across studies.",
        category=FalsePositiveCategory.REFERENCES,
        reason="Summary of literature"
    ),
    FalsePositiveCase(
        text="Based on [23] where RR was 0.82 (0.71-0.95).",
        category=FalsePositiveCategory.REFERENCES,
        reason="Citation-based statement"
    ),
    FalsePositiveCase(
        text="The landmark study showed HR 0.58 (see Discussion).",
        category=FalsePositiveCategory.REFERENCES,
        reason="Internal reference to discussion"
    ),
    FalsePositiveCase(
        text="Consistent with prior OR 1.8 (1.4-2.3) from registry data.",
        category=FalsePositiveCategory.REFERENCES,
        reason="Comparison to registry"
    ),
    FalsePositiveCase(
        text="Table 3 in the appendix shows HR 0.65 (0.55-0.77).",
        category=FalsePositiveCategory.REFERENCES,
        reason="Reference to table/appendix"
    ),

    # =========================================================================
    # CATEGORY 4: Baseline characteristics
    # =========================================================================
    FalsePositiveCase(
        text="Baseline HR 0.85 (SD 0.12) beats per second.",
        category=FalsePositiveCategory.BASELINE,
        reason="Heart rate at baseline, not hazard ratio"
    ),
    FalsePositiveCase(
        text="Mean baseline ratio 0.92 (0.88-0.96) for albumin/creatinine.",
        category=FalsePositiveCategory.BASELINE,
        reason="Baseline lab ratio"
    ),
    FalsePositiveCase(
        text="Screening OR was normal at 0.75 (0.65-0.85).",
        category=FalsePositiveCategory.BASELINE,
        reason="Ocular refraction, not odds ratio"
    ),
    FalsePositiveCase(
        text="Baseline MD -2.5 dB on visual field testing.",
        category=FalsePositiveCategory.BASELINE,
        reason="Mean deviation in ophthalmology"
    ),
    FalsePositiveCase(
        text="Pre-treatment RR 18 (16-20) breaths per minute.",
        category=FalsePositiveCategory.BASELINE,
        reason="Respiratory rate, not risk ratio"
    ),
    FalsePositiveCase(
        text="Initial HR was 72 (95% CI 68-76) bpm at rest.",
        category=FalsePositiveCategory.BASELINE,
        reason="Heart rate measurement"
    ),
    FalsePositiveCase(
        text="Baseline characteristics showed mean age 0.75 (SD 0.12) years.",
        category=FalsePositiveCategory.BASELINE,
        reason="Age in years for infants"
    ),
    FalsePositiveCase(
        text="Enrollment eGFR 0.85 (0.78-0.92) mL/s/1.73m2.",
        category=FalsePositiveCategory.BASELINE,
        reason="Renal function at enrollment"
    ),
    FalsePositiveCase(
        text="Pre-operative EF 0.55 (0.45-0.65) by echocardiography.",
        category=FalsePositiveCategory.BASELINE,
        reason="Ejection fraction at baseline"
    ),
    FalsePositiveCase(
        text="Screening visit showed mean ratio 1.2 (1.0-1.4).",
        category=FalsePositiveCategory.BASELINE,
        reason="Screening measurement"
    ),

    # =========================================================================
    # CATEGORY 5: Descriptive statistics
    # =========================================================================
    FalsePositiveCase(
        text="Mean (SD) was 0.73 (0.15) in the treatment group.",
        category=FalsePositiveCategory.DESCRIPTIVE,
        reason="Mean with SD, not effect with CI"
    ),
    FalsePositiveCase(
        text="Median 0.82, IQR 0.75-0.89 for the biomarker.",
        category=FalsePositiveCategory.DESCRIPTIVE,
        reason="Median with IQR"
    ),
    FalsePositiveCase(
        text="The proportion was 0.65 (SE 0.05) in controls.",
        category=FalsePositiveCategory.DESCRIPTIVE,
        reason="Proportion with SE"
    ),
    FalsePositiveCase(
        text="Variance was 0.82 (95% percentile range 0.70-0.94).",
        category=FalsePositiveCategory.DESCRIPTIVE,
        reason="Variance statistic"
    ),
    FalsePositiveCase(
        text="Coefficient of variation 0.78 (0.65-0.91) across sites.",
        category=FalsePositiveCategory.DESCRIPTIVE,
        reason="CV statistic"
    ),
    FalsePositiveCase(
        text="Skewness 0.85 and kurtosis 1.2 for the distribution.",
        category=FalsePositiveCategory.DESCRIPTIVE,
        reason="Distribution parameters"
    ),
    FalsePositiveCase(
        text="Standard error was 0.12 (range 0.08-0.16) for estimates.",
        category=FalsePositiveCategory.DESCRIPTIVE,
        reason="SE description"
    ),
    FalsePositiveCase(
        text="Geometric mean 0.92 (95% CI 0.88-0.96) of ratios.",
        category=FalsePositiveCategory.DESCRIPTIVE,
        reason="Geometric mean, not effect"
    ),
    FalsePositiveCase(
        text="Percentile 0.75 (0.70-0.80) for the score distribution.",
        category=FalsePositiveCategory.DESCRIPTIVE,
        reason="Percentile value"
    ),
    FalsePositiveCase(
        text="Mode was 0.85 with range 0.65-1.05 in the sample.",
        category=FalsePositiveCategory.DESCRIPTIVE,
        reason="Mode statistic"
    ),

    # =========================================================================
    # CATEGORY 6: Non-clinical contexts
    # =========================================================================
    FalsePositiveCase(
        text="Economic analysis showed cost ratio 0.85 (0.78-0.92).",
        category=FalsePositiveCategory.NON_CLINICAL,
        reason="Economic ratio, not clinical effect"
    ),
    FalsePositiveCase(
        text="The price index was 1.23 (95% CI 1.15-1.31) for drugs.",
        category=FalsePositiveCategory.NON_CLINICAL,
        reason="Economic index"
    ),
    FalsePositiveCase(
        text="Compliance ratio 0.92 (0.88-0.96) in the study arm.",
        category=FalsePositiveCategory.NON_CLINICAL,
        reason="Compliance measure"
    ),
    FalsePositiveCase(
        text="Participation rate 0.75 (0.70-0.80) across centers.",
        category=FalsePositiveCategory.NON_CLINICAL,
        reason="Participation rate"
    ),
    FalsePositiveCase(
        text="Quality score 0.88 (95% CI 0.82-0.94) for data.",
        category=FalsePositiveCategory.NON_CLINICAL,
        reason="Data quality score"
    ),
    FalsePositiveCase(
        text="Retention 0.93 (0.90-0.96) at 12-month follow-up.",
        category=FalsePositiveCategory.NON_CLINICAL,
        reason="Study retention"
    ),
    FalsePositiveCase(
        text="Adherence index 0.82 (0.75-0.89) by pill count.",
        category=FalsePositiveCategory.NON_CLINICAL,
        reason="Adherence measure"
    ),
    FalsePositiveCase(
        text="Protocol deviation rate 0.15 (0.12-0.18) per patient-year.",
        category=FalsePositiveCategory.NON_CLINICAL,
        reason="Protocol compliance"
    ),
    FalsePositiveCase(
        text="Site performance index 0.95 (0.92-0.98) overall.",
        category=FalsePositiveCategory.NON_CLINICAL,
        reason="Operational metric"
    ),
    FalsePositiveCase(
        text="Enrollment velocity 0.85 (0.78-0.92) patients/month.",
        category=FalsePositiveCategory.NON_CLINICAL,
        reason="Enrollment metric"
    ),

    # =========================================================================
    # CATEGORY 7: Ambiguous formats
    # =========================================================================
    FalsePositiveCase(
        text="The result was HR=0.75 without confidence interval.",
        category=FalsePositiveCategory.AMBIGUOUS,
        reason="No CI provided - incomplete"
    ),
    FalsePositiveCase(
        text="OR was approximately 1.5 to 2.0 based on estimates.",
        category=FalsePositiveCategory.AMBIGUOUS,
        reason="Approximate range, not precise CI"
    ),
    FalsePositiveCase(
        text="RR varied from 0.5-1.5 depending on subgroup.",
        category=FalsePositiveCategory.AMBIGUOUS,
        reason="Subgroup variation range"
    ),
    FalsePositiveCase(
        text="Effect size: small (0.2-0.5) by Cohen's criteria.",
        category=FalsePositiveCategory.AMBIGUOUS,
        reason="Cohen's d range description"
    ),
    FalsePositiveCase(
        text="Benefit: HR somewhere between 0.6 and 0.9.",
        category=FalsePositiveCategory.AMBIGUOUS,
        reason="Vague range statement"
    ),
    FalsePositiveCase(
        text="The ratio 0.85 was below the threshold of 1.0.",
        category=FalsePositiveCategory.AMBIGUOUS,
        reason="Threshold comparison, no CI"
    ),
    FalsePositiveCase(
        text="Expected HR 0.75 based on power calculation.",
        category=FalsePositiveCategory.AMBIGUOUS,
        reason="Expected/hypothesized value"
    ),
    FalsePositiveCase(
        text="Sample size assumed HR 0.80 for 80% power.",
        category=FalsePositiveCategory.AMBIGUOUS,
        reason="Sample size assumption"
    ),
    FalsePositiveCase(
        text="Target OR was 1.5 (predetermined threshold).",
        category=FalsePositiveCategory.AMBIGUOUS,
        reason="Target/threshold value"
    ),
    FalsePositiveCase(
        text="Futility boundary crossed at HR 0.95.",
        category=FalsePositiveCategory.AMBIGUOUS,
        reason="Stopping boundary"
    ),

    # =========================================================================
    # CATEGORY 8: Near-miss patterns
    # =========================================================================
    FalsePositiveCase(
        text="HR 0.75 (p<0.001) was highly significant.",
        category=FalsePositiveCategory.NEAR_MISS,
        reason="P-value only, no CI"
    ),
    FalsePositiveCase(
        text="The 90% CI was 0.65-0.85 for the hazard ratio.",
        category=FalsePositiveCategory.NEAR_MISS,
        reason="90% CI, not 95% CI"
    ),
    FalsePositiveCase(
        text="One-sided 97.5% CI: HR 0.75 (upper bound 0.92).",
        category=FalsePositiveCategory.NEAR_MISS,
        reason="One-sided CI only"
    ),
    FalsePositiveCase(
        text="Credible interval 0.65-0.85 from Bayesian analysis.",
        category=FalsePositiveCategory.NEAR_MISS,
        reason="Bayesian credible interval"
    ),
    FalsePositiveCase(
        text="Bootstrap 95% CI: 0.70-0.90 for OR estimate.",
        category=FalsePositiveCategory.NEAR_MISS,
        reason="Bootstrap CI - different method"
    ),
    FalsePositiveCase(
        text="Sensitivity analysis HR 0.75 (0.65-0.85) excluding outliers.",
        category=FalsePositiveCategory.NEAR_MISS,
        reason="Sensitivity analysis result"
    ),
    FalsePositiveCase(
        text="Per-protocol HR 0.72 (0.60-0.86) differed from ITT.",
        category=FalsePositiveCategory.NEAR_MISS,
        reason="Per-protocol, not primary ITT"
    ),
    FalsePositiveCase(
        text="Unadjusted RR 0.80 (0.70-0.91) before covariate adjustment.",
        category=FalsePositiveCategory.NEAR_MISS,
        reason="Unadjusted/crude estimate"
    ),
    FalsePositiveCase(
        text="Exploratory endpoint: MD -2.5 (95% CI -4.0 to -1.0).",
        category=FalsePositiveCategory.NEAR_MISS,
        reason="Exploratory/secondary endpoint"
    ),
    FalsePositiveCase(
        text="Imputed data showed HR 0.78 (0.68-0.89) with MICE.",
        category=FalsePositiveCategory.NEAR_MISS,
        reason="Imputed data result"
    ),

    # =========================================================================
    # ADDITIONAL EDGE CASES
    # =========================================================================
    FalsePositiveCase(
        text="Figure 2 shows hazard ratio over time.",
        category=FalsePositiveCategory.AMBIGUOUS,
        reason="Reference to figure, no values"
    ),
    FalsePositiveCase(
        text="The hazard was proportional (test p=0.42).",
        category=FalsePositiveCategory.AMBIGUOUS,
        reason="Proportionality test, not effect"
    ),
    FalsePositiveCase(
        text="Risk was increased OR but not significantly.",
        category=FalsePositiveCategory.AMBIGUOUS,
        reason="No actual value provided"
    ),
    FalsePositiveCase(
        text="CI width 0.20 was deemed acceptable precision.",
        category=FalsePositiveCategory.DESCRIPTIVE,
        reason="CI width, not the CI itself"
    ),
    FalsePositiveCase(
        text="The funnel plot showed OR symmetry around 1.0.",
        category=FalsePositiveCategory.REFERENCES,
        reason="Funnel plot description"
    ),
    FalsePositiveCase(
        text="I-squared 75% (95% CI 50-90%) indicated heterogeneity.",
        category=FalsePositiveCategory.DESCRIPTIVE,
        reason="Heterogeneity statistic"
    ),
    FalsePositiveCase(
        text="Egger's test intercept 0.85 (p=0.12) suggested no bias.",
        category=FalsePositiveCategory.DESCRIPTIVE,
        reason="Publication bias test"
    ),
    FalsePositiveCase(
        text="NNT would be 20 (95% CI 15-30) if significant.",
        category=FalsePositiveCategory.AMBIGUOUS,
        reason="Conditional NNT"
    ),
    FalsePositiveCase(
        text="Treatment effect 0.75 was consistent across analyses.",
        category=FalsePositiveCategory.AMBIGUOUS,
        reason="No CI provided"
    ),
    FalsePositiveCase(
        text="The ratio of ratios was 0.92 (0.85-0.99) for interaction.",
        category=FalsePositiveCategory.DESCRIPTIVE,
        reason="Interaction term"
    ),
]


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def get_cases_by_category(category: FalsePositiveCategory) -> List[FalsePositiveCase]:
    """Get all test cases for a specific category"""
    return [c for c in FALSE_POSITIVE_CASES if c.category == category]


def get_summary() -> dict:
    """Get summary statistics of the false positive test set"""
    from collections import Counter

    return {
        "total_cases": len(FALSE_POSITIVE_CASES),
        "by_category": Counter(c.category.value for c in FALSE_POSITIVE_CASES),
    }


def validate_extractor_specificity(extractor) -> dict:
    """
    Validate that an extractor does not produce false positives.

    Args:
        extractor: An extractor with extract(text) method

    Returns:
        dict with false positive analysis
    """
    false_positives = []

    for case in FALSE_POSITIVE_CASES:
        results = extractor.extract(case.text)

        if results:
            false_positives.append({
                "text": case.text,
                "category": case.category.value,
                "reason": case.reason,
                "extracted": [str(r) for r in results],
            })

    return {
        "total_cases": len(FALSE_POSITIVE_CASES),
        "false_positives": len(false_positives),
        "specificity": 1 - (len(false_positives) / len(FALSE_POSITIVE_CASES)),
        "details": false_positives,
    }


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    summary = get_summary()
    print("=" * 60)
    print("FALSE POSITIVE TEST SET SUMMARY")
    print("=" * 60)
    print(f"\nTotal cases: {summary['total_cases']}")

    print("\nBy Category:")
    for category, count in sorted(summary['by_category'].items(), key=lambda x: -x[1]):
        print(f"  {category}: {count}")

    print("\n" + "=" * 60)
