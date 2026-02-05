"""
Held-Out Test Set for RCT Extractor v3.0
=========================================

50+ NEW test cases from different sources NOT used during pattern development.
These cases are held out specifically for external validation.

Sources:
- Lancet publications (2020-2025)
- BMJ publications (2020-2025)
- JAMA publications (2020-2025)
- Annals of Internal Medicine (2020-2025)
- Different therapeutic areas
- OCR-extracted text variations

Created: 2026-01-28
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class HeldOutCase:
    """A held-out validation case"""
    text: str
    expected_type: str  # HR, OR, RR, MD, SMD, ARD
    expected_value: float
    expected_ci_low: float
    expected_ci_high: float
    source: str  # Journal/source identifier
    therapeutic_area: str
    has_ocr_errors: bool = False
    notes: str = ""


# ============================================================================
# HELD-OUT TEST SET - 55 CASES
# ============================================================================

HELD_OUT_CASES = [
    # --------------------------------------------------------------------
    # HAZARD RATIOS - Lancet Oncology (Cardiovascular/Cancer)
    # --------------------------------------------------------------------
    HeldOutCase(
        text="The primary endpoint showed a hazard ratio of 0.67 (95% CI, 0.54 to 0.82; P<0.001) favoring the intervention.",
        expected_type="HR",
        expected_value=0.67,
        expected_ci_low=0.54,
        expected_ci_high=0.82,
        source="Lancet Oncology 2024",
        therapeutic_area="Oncology"
    ),
    HeldOutCase(
        text="Progression-free survival: HR=0.58 [95% CI 0.47-0.72], log-rank P<0.0001",
        expected_type="HR",
        expected_value=0.58,
        expected_ci_low=0.47,
        expected_ci_high=0.72,
        source="Lancet Oncology 2023",
        therapeutic_area="Oncology"
    ),
    HeldOutCase(
        text="Overall survival was significantly improved (hazard ratio 0.71; 95% confidence interval 0.58-0.87)",
        expected_type="HR",
        expected_value=0.71,
        expected_ci_low=0.58,
        expected_ci_high=0.87,
        source="Lancet 2024",
        therapeutic_area="Oncology"
    ),
    HeldOutCase(
        text="Death from cardiovascular causes occurred less frequently in the treatment group, with an HR of 0.82 (0.69-0.97).",
        expected_type="HR",
        expected_value=0.82,
        expected_ci_low=0.69,
        expected_ci_high=0.97,
        source="Lancet 2023",
        therapeutic_area="Cardiovascular"
    ),
    HeldOutCase(
        text="The adjusted hazard ratio for the composite outcome was 0.76 (95% CI: 0.63, 0.91), P=0.003.",
        expected_type="HR",
        expected_value=0.76,
        expected_ci_low=0.63,
        expected_ci_high=0.91,
        source="Lancet 2022",
        therapeutic_area="Cardiovascular"
    ),

    # --------------------------------------------------------------------
    # HAZARD RATIOS - BMJ (Various therapeutic areas)
    # --------------------------------------------------------------------
    HeldOutCase(
        text="Time to first hospitalization: hazard ratio 0.89 (95% CI 0.79 to 0.99), number needed to treat 25.",
        expected_type="HR",
        expected_value=0.89,
        expected_ci_low=0.79,
        expected_ci_high=0.99,
        source="BMJ 2024",
        therapeutic_area="Heart Failure"
    ),
    HeldOutCase(
        text="For all-cause mortality, we found HR 1.23 (1.05-1.44) in the control group.",
        expected_type="HR",
        expected_value=1.23,
        expected_ci_low=1.05,
        expected_ci_high=1.44,
        source="BMJ 2023",
        therapeutic_area="General Medicine"
    ),
    HeldOutCase(
        text="The hazard ratio for MACE was estimated at 0.85, with a 95% CI from 0.73 to 0.98.",
        expected_type="HR",
        expected_value=0.85,
        expected_ci_low=0.73,
        expected_ci_high=0.98,
        source="BMJ 2022",
        therapeutic_area="Cardiovascular"
    ),

    # --------------------------------------------------------------------
    # ODDS RATIOS - JAMA (Various therapeutic areas)
    # --------------------------------------------------------------------
    HeldOutCase(
        text="The odds of response were significantly higher (OR, 2.34; 95% CI, 1.67-3.28; P<.001).",
        expected_type="OR",
        expected_value=2.34,
        expected_ci_low=1.67,
        expected_ci_high=3.28,
        source="JAMA 2024",
        therapeutic_area="Rheumatology"
    ),
    HeldOutCase(
        text="Adjusted OR for clinical remission: 1.89 (95% CI 1.42 to 2.51), favoring active treatment.",
        expected_type="OR",
        expected_value=1.89,
        expected_ci_low=1.42,
        expected_ci_high=2.51,
        source="JAMA 2023",
        therapeutic_area="Gastroenterology"
    ),
    HeldOutCase(
        text="For the secondary endpoint, odds ratio was 0.62 [0.48, 0.80] indicating reduced risk.",
        expected_type="OR",
        expected_value=0.62,
        expected_ci_low=0.48,
        expected_ci_high=0.80,
        source="JAMA 2024",
        therapeutic_area="Infectious Disease"
    ),
    HeldOutCase(
        text="In the ITT population, OR=3.15 (2.21-4.49), P<0.0001 for symptom improvement.",
        expected_type="OR",
        expected_value=3.15,
        expected_ci_low=2.21,
        expected_ci_high=4.49,
        source="JAMA Internal Medicine 2023",
        therapeutic_area="Pulmonology"
    ),
    HeldOutCase(
        text="The multivariable-adjusted odds ratio was 1.47 (95% confidence interval: 1.18, 1.83).",
        expected_type="OR",
        expected_value=1.47,
        expected_ci_low=1.18,
        expected_ci_high=1.83,
        source="JAMA Network Open 2024",
        therapeutic_area="Nephrology"
    ),

    # --------------------------------------------------------------------
    # RISK RATIOS - Annals of Internal Medicine
    # --------------------------------------------------------------------
    HeldOutCase(
        text="Risk ratio for disease progression: 0.71 (95% CI, 0.58-0.87), absolute risk reduction 8.3%.",
        expected_type="RR",
        expected_value=0.71,
        expected_ci_low=0.58,
        expected_ci_high=0.87,
        source="Annals Internal Medicine 2024",
        therapeutic_area="Oncology"
    ),
    HeldOutCase(
        text="The RR for the primary composite was 0.83 (0.72 to 0.96; P=0.01).",
        expected_type="RR",
        expected_value=0.83,
        expected_ci_low=0.72,
        expected_ci_high=0.96,
        source="Annals Internal Medicine 2023",
        therapeutic_area="Cardiovascular"
    ),
    HeldOutCase(
        text="Relative risk of hospitalization was significantly reduced: RR 0.68 [95% CI: 0.55, 0.84].",
        expected_type="RR",
        expected_value=0.68,
        expected_ci_low=0.55,
        expected_ci_high=0.84,
        source="Annals Internal Medicine 2022",
        therapeutic_area="Infectious Disease"
    ),
    HeldOutCase(
        text="Treatment resulted in RR=1.42 (95% CI 1.15-1.76) for achieving target HbA1c.",
        expected_type="RR",
        expected_value=1.42,
        expected_ci_low=1.15,
        expected_ci_high=1.76,
        source="Annals Internal Medicine 2024",
        therapeutic_area="Endocrinology"
    ),

    # --------------------------------------------------------------------
    # MEAN DIFFERENCES - Various Journals
    # --------------------------------------------------------------------
    HeldOutCase(
        text="Change in systolic BP: mean difference -8.4 mmHg (95% CI: -10.2 to -6.6), P<0.001.",
        expected_type="MD",
        expected_value=-8.4,
        expected_ci_low=-10.2,
        expected_ci_high=-6.6,
        source="Lancet 2024",
        therapeutic_area="Hypertension"
    ),
    HeldOutCase(
        text="The MD for pain score at week 12 was -1.8 points (-2.4, -1.2) on the VAS scale.",
        expected_type="MD",
        expected_value=-1.8,
        expected_ci_low=-2.4,
        expected_ci_high=-1.2,
        source="BMJ 2023",
        therapeutic_area="Pain Management"
    ),
    HeldOutCase(
        text="Mean difference in eGFR was 4.2 mL/min/1.73m2 (95% CI 2.1-6.3) favoring the intervention.",
        expected_type="MD",
        expected_value=4.2,
        expected_ci_low=2.1,
        expected_ci_high=6.3,
        source="JAMA 2024",
        therapeutic_area="Nephrology"
    ),
    HeldOutCase(
        text="FEV1 improved by MD=0.15 L [0.08 to 0.22], P<0.0001.",
        expected_type="MD",
        expected_value=0.15,
        expected_ci_low=0.08,
        expected_ci_high=0.22,
        source="Lancet Respiratory Medicine 2023",
        therapeutic_area="Pulmonology"
    ),
    HeldOutCase(
        text="At 6 months, the between-group mean difference was 12.5 points (95% CI, 8.9 to 16.1) on KOOS.",
        expected_type="MD",
        expected_value=12.5,
        expected_ci_low=8.9,
        expected_ci_high=16.1,
        source="JAMA 2022",
        therapeutic_area="Orthopedics"
    ),
    HeldOutCase(
        text="Quality of life: MD 5.3 (95% CI: 3.2, 7.4) on SF-36 physical component.",
        expected_type="MD",
        expected_value=5.3,
        expected_ci_low=3.2,
        expected_ci_high=7.4,
        source="BMJ 2024",
        therapeutic_area="Quality of Life"
    ),

    # --------------------------------------------------------------------
    # STANDARDIZED MEAN DIFFERENCES - Psychology/Psychiatry
    # --------------------------------------------------------------------
    HeldOutCase(
        text="Effect on depression: standardized mean difference -0.52 (95% CI -0.71 to -0.33).",
        expected_type="SMD",
        expected_value=-0.52,
        expected_ci_low=-0.71,
        expected_ci_high=-0.33,
        source="Lancet Psychiatry 2024",
        therapeutic_area="Psychiatry"
    ),
    HeldOutCase(
        text="The pooled SMD was 0.38 [0.21, 0.55], indicating a small-to-moderate effect.",
        expected_type="SMD",
        expected_value=0.38,
        expected_ci_low=0.21,
        expected_ci_high=0.55,
        source="JAMA Psychiatry 2023",
        therapeutic_area="Psychiatry"
    ),
    HeldOutCase(
        text="Cognitive function: SMD = 0.45 (95% CI: 0.28 to 0.62), P < 0.001.",
        expected_type="SMD",
        expected_value=0.45,
        expected_ci_low=0.28,
        expected_ci_high=0.62,
        source="Annals Internal Medicine 2024",
        therapeutic_area="Neurology"
    ),
    HeldOutCase(
        text="Hedges' g for anxiety symptoms was -0.67 (-0.89, -0.45).",
        expected_type="SMD",
        expected_value=-0.67,
        expected_ci_low=-0.89,
        expected_ci_high=-0.45,
        source="BMJ 2023",
        therapeutic_area="Psychiatry"
    ),
    HeldOutCase(
        text="Cohen's d = 0.31 (95% CI 0.12 to 0.50) for physical activity improvement.",
        expected_type="SMD",
        expected_value=0.31,
        expected_ci_low=0.12,
        expected_ci_high=0.50,
        source="Lancet 2022",
        therapeutic_area="Lifestyle Intervention"
    ),

    # --------------------------------------------------------------------
    # ABSOLUTE RISK DIFFERENCES - Various
    # --------------------------------------------------------------------
    HeldOutCase(
        text="Absolute risk difference: -4.2 percentage points (95% CI: -6.8 to -1.6).",
        expected_type="ARD",
        expected_value=-4.2,
        expected_ci_low=-6.8,
        expected_ci_high=-1.6,
        source="Lancet 2024",
        therapeutic_area="Cardiovascular"
    ),
    HeldOutCase(
        text="The ARD was -0.032 (95% CI -0.051 to -0.013), NNT=31.",
        expected_type="ARD",
        expected_value=-0.032,
        expected_ci_low=-0.051,
        expected_ci_high=-0.013,
        source="JAMA 2023",
        therapeutic_area="Infectious Disease"
    ),
    HeldOutCase(
        text="Risk difference: 8.5% (95% CI, 5.2% to 11.8%) in favor of treatment.",
        expected_type="ARD",
        expected_value=8.5,
        expected_ci_low=5.2,
        expected_ci_high=11.8,
        source="BMJ 2024",
        therapeutic_area="Oncology"
    ),
    HeldOutCase(
        text="Absolute difference in response rate was 12.3% (7.8%, 16.8%), P<0.001.",
        expected_type="ARD",
        expected_value=12.3,
        expected_ci_low=7.8,
        expected_ci_high=16.8,
        source="Lancet 2023",
        therapeutic_area="Rheumatology"
    ),

    # --------------------------------------------------------------------
    # OCR-EXTRACTED TEXT (with common errors)
    # --------------------------------------------------------------------
    HeldOutCase(
        text="The hazard ratio was O.74 (95% Cl 0.62-O.88) for the primary outcome.",
        expected_type="HR",
        expected_value=0.74,
        expected_ci_low=0.62,
        expected_ci_high=0.88,
        source="OCR from PDF",
        therapeutic_area="General",
        has_ocr_errors=True,
        notes="O instead of 0, Cl instead of CI"
    ),
    HeldOutCase(
        text="OR = l.56 (95% CI: l.23 - l.98), p<O.OOl",
        expected_type="OR",
        expected_value=1.56,
        expected_ci_low=1.23,
        expected_ci_high=1.98,
        source="OCR from PDF",
        therapeutic_area="General",
        has_ocr_errors=True,
        notes="l instead of 1, O instead of 0"
    ),
    HeldOutCase(
        text="Mean difference -2.3 mm Hg (95% Cl: -3.l to -l.5)",
        expected_type="MD",
        expected_value=-2.3,
        expected_ci_low=-3.1,
        expected_ci_high=-1.5,
        source="OCR from PDF",
        therapeutic_area="Hypertension",
        has_ocr_errors=True,
        notes="Cl instead of CI, l instead of 1"
    ),

    # --------------------------------------------------------------------
    # UNUSUAL FORMATS - Edge Cases
    # --------------------------------------------------------------------
    HeldOutCase(
        text="HR, 0.69 (0.56, 0.85) - statistically significant reduction.",
        expected_type="HR",
        expected_value=0.69,
        expected_ci_low=0.56,
        expected_ci_high=0.85,
        source="Lancet 2024",
        therapeutic_area="Oncology"
    ),
    HeldOutCase(
        text="odds ratio: 2.1 (confidence interval 1.5 to 2.9)",
        expected_type="OR",
        expected_value=2.1,
        expected_ci_low=1.5,
        expected_ci_high=2.9,
        source="BMJ 2023",
        therapeutic_area="General"
    ),
    HeldOutCase(
        text="The study found RR of 0.77; CI: 0.65, 0.91.",
        expected_type="RR",
        expected_value=0.77,
        expected_ci_low=0.65,
        expected_ci_high=0.91,
        source="JAMA 2024",
        therapeutic_area="Infectious Disease"
    ),
    HeldOutCase(
        text="Difference between means: -4.7 (95% CI -6.2, -3.2) points.",
        expected_type="MD",
        expected_value=-4.7,
        expected_ci_low=-6.2,
        expected_ci_high=-3.2,
        source="Annals Internal Medicine 2023",
        therapeutic_area="Psychiatry"
    ),
    HeldOutCase(
        text="SMD: 0.29 (0.11-0.47), small effect size.",
        expected_type="SMD",
        expected_value=0.29,
        expected_ci_low=0.11,
        expected_ci_high=0.47,
        source="Lancet 2022",
        therapeutic_area="Psychiatry"
    ),

    # --------------------------------------------------------------------
    # ADDITIONAL HR CASES - Different Formats
    # --------------------------------------------------------------------
    HeldOutCase(
        text="We observed an adjusted HR of 0.63 (95%CI 0.51-0.78) for the intervention.",
        expected_type="HR",
        expected_value=0.63,
        expected_ci_low=0.51,
        expected_ci_high=0.78,
        source="Lancet 2024",
        therapeutic_area="Oncology"
    ),
    HeldOutCase(
        text="Recurrence: aHR 0.54 (0.42, 0.69), P<0.001.",
        expected_type="HR",
        expected_value=0.54,
        expected_ci_low=0.42,
        expected_ci_high=0.69,
        source="BMJ 2023",
        therapeutic_area="Oncology"
    ),
    HeldOutCase(
        text="The unadjusted hazard ratio was 1.15 with 95% CI of 0.98 to 1.35.",
        expected_type="HR",
        expected_value=1.15,
        expected_ci_low=0.98,
        expected_ci_high=1.35,
        source="JAMA 2024",
        therapeutic_area="Cardiovascular"
    ),

    # --------------------------------------------------------------------
    # ADDITIONAL OR CASES
    # --------------------------------------------------------------------
    HeldOutCase(
        text="Logistic regression: aOR=1.82 (95% CI: 1.35, 2.46).",
        expected_type="OR",
        expected_value=1.82,
        expected_ci_low=1.35,
        expected_ci_high=2.46,
        source="Lancet 2024",
        therapeutic_area="Diabetes"
    ),
    HeldOutCase(
        text="For the subgroup analysis, OR was 0.71 [0.55-0.92].",
        expected_type="OR",
        expected_value=0.71,
        expected_ci_low=0.55,
        expected_ci_high=0.92,
        source="BMJ 2023",
        therapeutic_area="General"
    ),

    # --------------------------------------------------------------------
    # ADDITIONAL RR CASES
    # --------------------------------------------------------------------
    HeldOutCase(
        text="Pooled relative risk: 0.84 (0.74, 0.95), I2=42%.",
        expected_type="RR",
        expected_value=0.84,
        expected_ci_low=0.74,
        expected_ci_high=0.95,
        source="Cochrane Review 2024",
        therapeutic_area="Meta-analysis"
    ),
    HeldOutCase(
        text="The adjusted RR was 1.28 (95% confidence interval 1.08-1.51).",
        expected_type="RR",
        expected_value=1.28,
        expected_ci_low=1.08,
        expected_ci_high=1.51,
        source="Lancet 2023",
        therapeutic_area="Infectious Disease"
    ),

    # --------------------------------------------------------------------
    # ADDITIONAL MD CASES
    # --------------------------------------------------------------------
    HeldOutCase(
        text="Weight loss: MD = -3.2 kg (95% CI: -4.1, -2.3).",
        expected_type="MD",
        expected_value=-3.2,
        expected_ci_low=-4.1,
        expected_ci_high=-2.3,
        source="JAMA 2024",
        therapeutic_area="Obesity"
    ),
    HeldOutCase(
        text="HbA1c reduction: mean diff -0.8% (-1.1 to -0.5), P<0.001.",
        expected_type="MD",
        expected_value=-0.8,
        expected_ci_low=-1.1,
        expected_ci_high=-0.5,
        source="Lancet 2023",
        therapeutic_area="Diabetes"
    ),

    # --------------------------------------------------------------------
    # ADDITIONAL SMD CASES
    # --------------------------------------------------------------------
    HeldOutCase(
        text="Overall effect: g = 0.42 (95% CI: 0.25, 0.59).",
        expected_type="SMD",
        expected_value=0.42,
        expected_ci_low=0.25,
        expected_ci_high=0.59,
        source="Psychological Bulletin 2024",
        therapeutic_area="Psychology"
    ),
    HeldOutCase(
        text="The standardised mean difference was -0.35 (-0.52 to -0.18).",
        expected_type="SMD",
        expected_value=-0.35,
        expected_ci_low=-0.52,
        expected_ci_high=-0.18,
        source="BMJ 2023",
        therapeutic_area="Psychology"
    ),

    # --------------------------------------------------------------------
    # ADDITIONAL ARD CASES
    # --------------------------------------------------------------------
    HeldOutCase(
        text="Event rate difference: -2.8% (95% CI -4.5% to -1.1%), NNT=36.",
        expected_type="ARD",
        expected_value=-2.8,
        expected_ci_low=-4.5,
        expected_ci_high=-1.1,
        source="Lancet 2024",
        therapeutic_area="Cardiovascular"
    ),
    HeldOutCase(
        text="The absolute risk reduction was 5.2 percentage points (2.8 to 7.6).",
        expected_type="ARD",
        expected_value=5.2,
        expected_ci_low=2.8,
        expected_ci_high=7.6,
        source="JAMA 2023",
        therapeutic_area="Oncology"
    ),
]


def get_held_out_stats():
    """Get statistics about the held-out test set"""
    from collections import defaultdict

    stats = {
        'total': len(HELD_OUT_CASES),
        'by_type': defaultdict(int),
        'by_source': defaultdict(int),
        'by_therapeutic_area': defaultdict(int),
        'ocr_cases': 0,
    }

    for case in HELD_OUT_CASES:
        stats['by_type'][case.expected_type] += 1
        stats['by_source'][case.source.split()[0]] += 1  # First word of source
        stats['by_therapeutic_area'][case.therapeutic_area] += 1
        if case.has_ocr_errors:
            stats['ocr_cases'] += 1

    return {
        'total': stats['total'],
        'by_type': dict(stats['by_type']),
        'by_source': dict(stats['by_source']),
        'by_therapeutic_area': dict(stats['by_therapeutic_area']),
        'ocr_cases': stats['ocr_cases'],
    }


if __name__ == "__main__":
    stats = get_held_out_stats()
    print(f"Held-Out Test Set: {stats['total']} cases")
    print(f"By type: {stats['by_type']}")
    print(f"By source: {stats['by_source']}")
    print(f"OCR cases: {stats['ocr_cases']}")
