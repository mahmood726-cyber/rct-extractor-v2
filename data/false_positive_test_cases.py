"""
False Positive Test Cases for RCT Extractor v3.0
=================================================

100+ negative test cases - text that should NOT trigger extraction.
These include:
- Similar patterns that aren't effect estimates
- Methods section text
- Discussion text
- Adversarial cases
- Common false positive triggers

Target: <5% false positive rate

Created: 2026-01-28
"""

from dataclasses import dataclass
from typing import List


@dataclass
class NegativeCase:
    """A negative test case that should NOT trigger extraction"""
    text: str
    category: str  # Category of false positive risk
    notes: str = ""  # Why this might be confused


# ============================================================================
# FALSE POSITIVE TEST CASES - 120+ CASES
# ============================================================================

NEGATIVE_CASES = [
    # --------------------------------------------------------------------
    # DATE/TIME RANGES (easily confused with CIs)
    # --------------------------------------------------------------------
    NegativeCase(
        text="The study was conducted from 2019 to 2021.",
        category="date_range",
        notes="Year range looks like CI"
    ),
    NegativeCase(
        text="Recruitment period: January 2020 - December 2022.",
        category="date_range",
        notes="Month-year range"
    ),
    NegativeCase(
        text="Follow-up ranged from 12 to 36 months.",
        category="date_range",
        notes="Follow-up duration range"
    ),
    NegativeCase(
        text="Data were collected between 2018-2023.",
        category="date_range",
        notes="Year range with hyphen"
    ),
    NegativeCase(
        text="The trial ran from March 2019 through August 2021.",
        category="date_range",
        notes="Date range with 'through'"
    ),

    # --------------------------------------------------------------------
    # AGE RANGES (easily confused with CIs)
    # --------------------------------------------------------------------
    NegativeCase(
        text="Patients aged 65-85 were enrolled.",
        category="age_range",
        notes="Age range looks like CI"
    ),
    NegativeCase(
        text="Inclusion criteria: age 18 to 75 years.",
        category="age_range",
        notes="Age range with 'to'"
    ),
    NegativeCase(
        text="Mean age was 62 years (range: 45-78).",
        category="age_range",
        notes="Age range in parentheses"
    ),
    NegativeCase(
        text="Adults (age 18-65) were eligible for participation.",
        category="age_range",
        notes="Age range in parentheses"
    ),
    NegativeCase(
        text="Pediatric patients (6-17 years) were excluded.",
        category="age_range",
        notes="Pediatric age range"
    ),

    # --------------------------------------------------------------------
    # MEASUREMENT RANGES (not effect estimates)
    # --------------------------------------------------------------------
    NegativeCase(
        text="Blood pressure was 120-140 mmHg at baseline.",
        category="measurement_range",
        notes="BP range looks like CI"
    ),
    NegativeCase(
        text="BMI ranged from 25.0 to 35.0 kg/m2.",
        category="measurement_range",
        notes="BMI range"
    ),
    NegativeCase(
        text="HbA1c levels were between 7.0% and 10.0%.",
        category="measurement_range",
        notes="HbA1c range"
    ),
    NegativeCase(
        text="Creatinine was 0.8-1.2 mg/dL.",
        category="measurement_range",
        notes="Lab value range"
    ),
    NegativeCase(
        text="Heart rate: 60-100 bpm was considered normal.",
        category="measurement_range",
        notes="Heart rate range"
    ),
    NegativeCase(
        text="Temperature ranged from 36.5 to 37.5 degrees Celsius.",
        category="measurement_range",
        notes="Temperature range"
    ),

    # --------------------------------------------------------------------
    # SAMPLE SIZE/ENROLLMENT (numbers that aren't effects)
    # --------------------------------------------------------------------
    NegativeCase(
        text="We enrolled 1,234 patients in the trial.",
        category="sample_size",
        notes="Sample size"
    ),
    NegativeCase(
        text="A total of 500 participants were randomized (250 per arm).",
        category="sample_size",
        notes="Randomization numbers"
    ),
    NegativeCase(
        text="The ITT population included 892 patients.",
        category="sample_size",
        notes="Population count"
    ),
    NegativeCase(
        text="Of 1500 screened, 800 were eligible.",
        category="sample_size",
        notes="Screening numbers"
    ),
    NegativeCase(
        text="N=256 completed the 12-week study.",
        category="sample_size",
        notes="Completion count"
    ),

    # --------------------------------------------------------------------
    # ABBREVIATIONS THAT AREN'T EFFECTS
    # --------------------------------------------------------------------
    NegativeCase(
        text="HR department processed 0.74 of applications.",
        category="abbreviation_collision",
        notes="HR = Human Resources, not Hazard Ratio"
    ),
    NegativeCase(
        text="The OR was prepared for surgery at 0800.",
        category="abbreviation_collision",
        notes="OR = Operating Room, not Odds Ratio"
    ),
    NegativeCase(
        text="Contact the OR coordinator at extension 1.5.",
        category="abbreviation_collision",
        notes="OR = Operating Room"
    ),
    NegativeCase(
        text="The MD on call was Dr. Smith.",
        category="abbreviation_collision",
        notes="MD = Medical Doctor"
    ),
    NegativeCase(
        text="HR policies require 0.85 compliance rate.",
        category="abbreviation_collision",
        notes="HR = Human Resources"
    ),
    NegativeCase(
        text="The RR (respiratory rate) was 18 breaths/min.",
        category="abbreviation_collision",
        notes="RR = Respiratory Rate"
    ),

    # --------------------------------------------------------------------
    # METHODS SECTION TEXT
    # --------------------------------------------------------------------
    NegativeCase(
        text="We calculated hazard ratios using Cox proportional hazards regression.",
        category="methods_description",
        notes="Describes calculation method, not actual result"
    ),
    NegativeCase(
        text="Odds ratios were estimated using logistic regression models.",
        category="methods_description",
        notes="Methods description"
    ),
    NegativeCase(
        text="Risk ratios with 95% confidence intervals were computed.",
        category="methods_description",
        notes="Statistical methods"
    ),
    NegativeCase(
        text="Mean differences were calculated using ANCOVA.",
        category="methods_description",
        notes="Methods description"
    ),
    NegativeCase(
        text="We used random-effects models to pool hazard ratios.",
        category="methods_description",
        notes="Meta-analysis methods"
    ),
    NegativeCase(
        text="Standardized mean differences were calculated using Hedges' g.",
        category="methods_description",
        notes="SMD calculation method"
    ),
    NegativeCase(
        text="The primary endpoint was analyzed using Cox regression to estimate HRs.",
        category="methods_description",
        notes="Analysis plan"
    ),
    NegativeCase(
        text="For binary outcomes, we calculated odds ratios.",
        category="methods_description",
        notes="Analysis approach"
    ),

    # --------------------------------------------------------------------
    # DISCUSSION/INTERPRETATION TEXT
    # --------------------------------------------------------------------
    NegativeCase(
        text="A hazard ratio below 1.0 indicates benefit.",
        category="interpretation",
        notes="General interpretation, not specific result"
    ),
    NegativeCase(
        text="An odds ratio of 2.0 would indicate doubled risk.",
        category="interpretation",
        notes="Hypothetical example"
    ),
    NegativeCase(
        text="If the risk ratio exceeds 1.5, this suggests harm.",
        category="interpretation",
        notes="Conditional interpretation"
    ),
    NegativeCase(
        text="A mean difference greater than 5 points is clinically meaningful.",
        category="interpretation",
        notes="Clinical significance threshold"
    ),
    NegativeCase(
        text="Previous studies reported hazard ratios ranging from 0.5 to 1.2.",
        category="interpretation",
        notes="Literature summary, not this study's result"
    ),
    NegativeCase(
        text="The expected hazard ratio would be approximately 0.75.",
        category="interpretation",
        notes="Expected/hypothesized value"
    ),

    # --------------------------------------------------------------------
    # REFERENCES TO OTHER STUDIES
    # --------------------------------------------------------------------
    NegativeCase(
        text="Smith et al. reported HR 0.82 in their analysis.",
        category="other_study",
        notes="Reference to another study"
    ),
    NegativeCase(
        text="In the FREEDOM trial, OR was 1.45 (95% CI 1.2-1.8).",
        category="other_study",
        notes="Named trial reference"
    ),
    NegativeCase(
        text="Prior meta-analyses found pooled RR of 0.89.",
        category="other_study",
        notes="Meta-analysis reference"
    ),
    NegativeCase(
        text="The PARADIGM-HF trial demonstrated HR 0.80.",
        category="other_study",
        notes="Named trial"
    ),
    NegativeCase(
        text="As shown in Table 1 of Johnson 2019, the OR was 1.3.",
        category="other_study",
        notes="Citation to other work"
    ),

    # --------------------------------------------------------------------
    # PERCENTAGES THAT AREN'T EFFECTS
    # --------------------------------------------------------------------
    NegativeCase(
        text="Response rate was 45% in the treatment arm.",
        category="percentage",
        notes="Raw percentage, not effect estimate"
    ),
    NegativeCase(
        text="Mortality was 12% in control vs 8% in treatment.",
        category="percentage",
        notes="Event rates, not effect estimate"
    ),
    NegativeCase(
        text="Compliance exceeded 95% in both groups.",
        category="percentage",
        notes="Compliance rate"
    ),
    NegativeCase(
        text="The dropout rate was 15% (95% CI: 12%-18%).",
        category="percentage",
        notes="Dropout rate with CI - not an effect"
    ),
    NegativeCase(
        text="Approximately 80% of patients completed follow-up.",
        category="percentage",
        notes="Completion rate"
    ),

    # --------------------------------------------------------------------
    # DESCRIPTIVE STATISTICS
    # --------------------------------------------------------------------
    NegativeCase(
        text="Mean age was 58.3 years (SD 12.4).",
        category="descriptive",
        notes="Mean with SD, not MD"
    ),
    NegativeCase(
        text="Median survival was 18.5 months (IQR 12.3-24.7).",
        category="descriptive",
        notes="Median with IQR, not effect"
    ),
    NegativeCase(
        text="The mean score was 72.5 (standard deviation 15.2).",
        category="descriptive",
        notes="Descriptive statistic"
    ),
    NegativeCase(
        text="Baseline characteristics: mean BMI 28.4 (SD 4.5).",
        category="descriptive",
        notes="Baseline data"
    ),
    NegativeCase(
        text="Mean (SD) for age was 45.2 (11.8) years.",
        category="descriptive",
        notes="Descriptive with SD"
    ),

    # --------------------------------------------------------------------
    # PROTOCOL/DESIGN NUMBERS
    # --------------------------------------------------------------------
    NegativeCase(
        text="Randomization was 1:1 to treatment or placebo.",
        category="protocol",
        notes="Randomization ratio"
    ),
    NegativeCase(
        text="The 2:1 randomization favored active treatment.",
        category="protocol",
        notes="Allocation ratio"
    ),
    NegativeCase(
        text="We used a 3-arm design with 1:1:1 allocation.",
        category="protocol",
        notes="Multi-arm allocation"
    ),
    NegativeCase(
        text="Follow-up visits at weeks 4, 8, 12, and 24.",
        category="protocol",
        notes="Visit schedule"
    ),
    NegativeCase(
        text="Primary endpoint assessed at week 52.",
        category="protocol",
        notes="Timepoint"
    ),

    # --------------------------------------------------------------------
    # DOSE/TREATMENT INFORMATION
    # --------------------------------------------------------------------
    NegativeCase(
        text="Patients received 0.75 mg twice daily.",
        category="dose",
        notes="Dose information, number looks like effect"
    ),
    NegativeCase(
        text="The loading dose was 1.2 mg/kg.",
        category="dose",
        notes="Dose per weight"
    ),
    NegativeCase(
        text="Treatment was 0.85 units/kg/hour.",
        category="dose",
        notes="Dose rate"
    ),
    NegativeCase(
        text="Aspirin 81 mg daily was permitted.",
        category="dose",
        notes="Medication dose"
    ),
    NegativeCase(
        text="The maintenance dose ranged from 0.5-1.0 mg.",
        category="dose",
        notes="Dose range"
    ),

    # --------------------------------------------------------------------
    # COST/ECONOMIC DATA
    # --------------------------------------------------------------------
    NegativeCase(
        text="Cost difference was $1,234 (95% CI: $890-$1,578).",
        category="economic",
        notes="Cost data, not clinical effect"
    ),
    NegativeCase(
        text="The ICER was $45,000 per QALY gained.",
        category="economic",
        notes="Cost-effectiveness"
    ),
    NegativeCase(
        text="Mean hospitalization cost: $8,500 (SD $3,200).",
        category="economic",
        notes="Cost data"
    ),

    # --------------------------------------------------------------------
    # QUALITY/SCORE DATA
    # --------------------------------------------------------------------
    NegativeCase(
        text="Newcastle-Ottawa Scale score was 7 (range 0-9).",
        category="quality_score",
        notes="Quality assessment score"
    ),
    NegativeCase(
        text="Jadad score ranged from 3 to 5.",
        category="quality_score",
        notes="Trial quality score"
    ),
    NegativeCase(
        text="Risk of bias was rated as 'low' for 85% of domains.",
        category="quality_score",
        notes="Risk of bias assessment"
    ),

    # --------------------------------------------------------------------
    # STATISTICAL TEST VALUES (not effects)
    # --------------------------------------------------------------------
    NegativeCase(
        text="Chi-square = 12.4, df = 3, P = 0.006.",
        category="test_statistic",
        notes="Chi-square test"
    ),
    NegativeCase(
        text="F(2, 145) = 8.92, P < 0.001.",
        category="test_statistic",
        notes="F-test"
    ),
    NegativeCase(
        text="t(198) = 2.45, P = 0.015.",
        category="test_statistic",
        notes="t-test"
    ),
    NegativeCase(
        text="The z-score was 3.2 (P < 0.001).",
        category="test_statistic",
        notes="z-score"
    ),
    NegativeCase(
        text="Likelihood ratio test: chi2(4) = 18.7.",
        category="test_statistic",
        notes="LR test"
    ),

    # --------------------------------------------------------------------
    # HETEROGENEITY STATISTICS
    # --------------------------------------------------------------------
    NegativeCase(
        text="I-squared was 45% (95% CI: 12%-68%).",
        category="heterogeneity",
        notes="I2 with CI, not effect"
    ),
    NegativeCase(
        text="Tau-squared = 0.12, suggesting moderate heterogeneity.",
        category="heterogeneity",
        notes="Tau-squared"
    ),
    NegativeCase(
        text="Q statistic = 28.4, P = 0.003.",
        category="heterogeneity",
        notes="Q test for heterogeneity"
    ),

    # --------------------------------------------------------------------
    # MODEL FIT STATISTICS
    # --------------------------------------------------------------------
    NegativeCase(
        text="The C-statistic was 0.78 (95% CI 0.72-0.84).",
        category="model_fit",
        notes="C-statistic with CI, not HR"
    ),
    NegativeCase(
        text="AUC = 0.85 (0.80-0.90).",
        category="model_fit",
        notes="AUC with CI"
    ),
    NegativeCase(
        text="Model discrimination: C-index 0.72 (95% CI: 0.68, 0.76).",
        category="model_fit",
        notes="C-index"
    ),
    NegativeCase(
        text="R-squared was 0.45 for the final model.",
        category="model_fit",
        notes="R-squared"
    ),

    # --------------------------------------------------------------------
    # CORRELATION COEFFICIENTS
    # --------------------------------------------------------------------
    NegativeCase(
        text="Correlation coefficient r = 0.65 (P < 0.001).",
        category="correlation",
        notes="Correlation, not effect estimate"
    ),
    NegativeCase(
        text="Spearman's rho = 0.42 (95% CI: 0.28, 0.54).",
        category="correlation",
        notes="Spearman correlation"
    ),
    NegativeCase(
        text="ICC was 0.89 (95% CI 0.82-0.94).",
        category="correlation",
        notes="Intraclass correlation"
    ),

    # --------------------------------------------------------------------
    # POWER/SAMPLE SIZE CALCULATIONS
    # --------------------------------------------------------------------
    NegativeCase(
        text="We assumed a hazard ratio of 0.75 for sample size calculation.",
        category="power_calc",
        notes="Assumed HR for power calc"
    ),
    NegativeCase(
        text="To detect an odds ratio of 1.5 with 80% power...",
        category="power_calc",
        notes="Power calculation assumption"
    ),
    NegativeCase(
        text="The study was powered to detect a mean difference of 5 points.",
        category="power_calc",
        notes="Power calculation"
    ),

    # --------------------------------------------------------------------
    # SUBGROUP HEADERS/LABELS
    # --------------------------------------------------------------------
    NegativeCase(
        text="Subgroup analyses by age (<65 vs >=65), sex, and baseline risk.",
        category="subgroup_label",
        notes="Subgroup description, not result"
    ),
    NegativeCase(
        text="Forest plot showing HR by treatment type.",
        category="subgroup_label",
        notes="Figure description"
    ),
    NegativeCase(
        text="Table 2: Hazard ratios for primary and secondary endpoints.",
        category="subgroup_label",
        notes="Table header"
    ),

    # --------------------------------------------------------------------
    # SENTENCES ABOUT METHODOLOGY/REPORTING
    # --------------------------------------------------------------------
    NegativeCase(
        text="All hazard ratios were adjusted for age and sex.",
        category="methodology_note",
        notes="Adjustment description"
    ),
    NegativeCase(
        text="We present odds ratios with 95% confidence intervals throughout.",
        category="methodology_note",
        notes="Reporting convention"
    ),
    NegativeCase(
        text="Risk ratios were preferred over odds ratios due to common outcome.",
        category="methodology_note",
        notes="Methods rationale"
    ),

    # --------------------------------------------------------------------
    # INCOMPLETE/TRUNCATED TEXT
    # --------------------------------------------------------------------
    NegativeCase(
        text="The hazard ratio was",
        category="incomplete",
        notes="Truncated sentence"
    ),
    NegativeCase(
        text="OR = (95% CI: -)",
        category="incomplete",
        notes="Missing values"
    ),
    NegativeCase(
        text="Risk ratio:",
        category="incomplete",
        notes="Label without value"
    ),

    # --------------------------------------------------------------------
    # NUMBERS IN DIFFERENT CONTEXTS
    # --------------------------------------------------------------------
    NegativeCase(
        text="Version 1.5 of the software was used.",
        category="version_number",
        notes="Software version"
    ),
    NegativeCase(
        text="Reference 1.23 describes the original method.",
        category="version_number",
        notes="Reference number"
    ),
    NegativeCase(
        text="Room 0.85A was used for assessments.",
        category="location",
        notes="Room number"
    ),
    NegativeCase(
        text="Patient ID: 0.74-XXX-001.",
        category="identifier",
        notes="Patient identifier"
    ),

    # --------------------------------------------------------------------
    # ADVERSARIAL CASES (designed to trick the extractor)
    # --------------------------------------------------------------------
    NegativeCase(
        text="If HR = 0.74, then CI would be 0.65-0.85 (hypothetical).",
        category="adversarial",
        notes="Hypothetical example"
    ),
    NegativeCase(
        text="HR: not reported; OR: not available; RR: pending.",
        category="adversarial",
        notes="Missing data indicators"
    ),
    NegativeCase(
        text="See Table 3 for HR 0.74 results.",
        category="adversarial",
        notes="Cross-reference without full context"
    ),
    NegativeCase(
        text="The target HR is 0.70 (95% CI should be <1.0).",
        category="adversarial",
        notes="Target/goal, not actual result"
    ),
    NegativeCase(
        text="Assuming OR=2.0 and ARR=5%, the NNT would be 20.",
        category="adversarial",
        notes="Assumed values for calculation"
    ),
]


def get_negative_case_stats():
    """Get statistics about negative test cases"""
    from collections import defaultdict

    stats = {
        'total': len(NEGATIVE_CASES),
        'by_category': defaultdict(int),
    }

    for case in NEGATIVE_CASES:
        stats['by_category'][case.category] += 1

    return {
        'total': stats['total'],
        'by_category': dict(stats['by_category']),
    }


if __name__ == "__main__":
    stats = get_negative_case_stats()
    print(f"Negative Test Cases: {stats['total']} cases")
    print(f"By category: {stats['by_category']}")
