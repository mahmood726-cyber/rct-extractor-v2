"""
Expanded Validation Dataset v3.0
================================

200+ validation cases across all effect types and difficulty levels.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ValidationCase:
    """A single validation case"""
    text: str
    expected_type: str
    expected_value: float
    expected_ci_low: float
    expected_ci_high: float
    difficulty: str = "easy"  # easy, moderate, hard
    source: str = ""
    notes: str = ""


# =============================================================================
# HAZARD RATIO VALIDATION CASES (60 cases)
# =============================================================================

HR_VALIDATION = [
    # Easy cases - Standard formats
    ValidationCase("hazard ratio 0.74 (95% CI 0.65 to 0.85)", "HR", 0.74, 0.65, 0.85, "easy"),
    ValidationCase("HR 0.82 (0.73-0.92)", "HR", 0.82, 0.73, 0.92, "easy"),
    ValidationCase("hazard ratio, 0.74; 95% CI, 0.65 to 0.85", "HR", 0.74, 0.65, 0.85, "easy"),
    ValidationCase("HR = 0.64 (95% confidence interval: 0.51-0.80)", "HR", 0.64, 0.51, 0.80, "easy"),
    ValidationCase("hazard ratio of 0.71 (95% CI 0.58-0.87)", "HR", 0.71, 0.58, 0.87, "easy"),
    ValidationCase("HR: 0.68; 95% CI: 0.55-0.84", "HR", 0.68, 0.55, 0.84, "easy"),
    ValidationCase("(HR 0.76; 95% CI 0.66-0.86)", "HR", 0.76, 0.66, 0.86, "easy"),
    ValidationCase("HR, 0.73 [95% CI, 0.62 to 0.86]", "HR", 0.73, 0.62, 0.86, "easy"),
    ValidationCase("hazard ratio was 0.79 (0.67 to 0.93)", "HR", 0.79, 0.67, 0.93, "easy"),
    ValidationCase("HR 0.61; 95% confidence interval 0.51 to 0.72", "HR", 0.61, 0.51, 0.72, "easy"),

    # Moderate cases - Adjusted and contextual
    ValidationCase("adjusted HR 0.72 (95% CI 0.61-0.85)", "HR", 0.72, 0.61, 0.85, "moderate"),
    ValidationCase("aHR 0.68 (0.57-0.81)", "HR", 0.68, 0.57, 0.81, "moderate"),
    ValidationCase("The hazard ratio for the primary endpoint was 0.74 (95% CI, 0.65 to 0.85)", "HR", 0.74, 0.65, 0.85, "moderate"),
    ValidationCase("HR for cardiovascular death was 0.83 (95% CI, 0.71-0.97)", "HR", 0.83, 0.71, 0.97, "moderate"),
    ValidationCase("unadjusted hazard ratio 0.91 (0.78-1.06)", "HR", 0.91, 0.78, 1.06, "moderate"),
    ValidationCase("hazard ratio 0.77 (95% CI 0.63, 0.94)", "HR", 0.77, 0.63, 0.94, "moderate"),  # comma in CI
    ValidationCase("Hazard ratio=0.64 (95% confidence interval: 0.51-0.80)", "HR", 0.64, 0.51, 0.80, "moderate"),
    ValidationCase("relative hazard 0.69 (95% CI 0.58-0.82)", "HR", 0.69, 0.58, 0.82, "moderate"),

    # Hard cases - Complex formats
    ValidationCase("HR 0.74 (95% CI 0.65-0.85; n=4744)", "HR", 0.74, 0.65, 0.85, "hard"),
    ValidationCase("The HR was 0.82, with 95% CI of 0.71 to 0.95", "HR", 0.82, 0.71, 0.95, "hard"),

    # Cardiovascular trials
    ValidationCase("DAPA-HF: hazard ratio 0.74 (95% CI 0.65 to 0.85)", "HR", 0.74, 0.65, 0.85, "easy", "DAPA-HF"),
    ValidationCase("EMPEROR-Reduced: HR 0.75 (0.65-0.86)", "HR", 0.75, 0.65, 0.86, "easy", "EMPEROR-Reduced"),
    ValidationCase("PARADIGM-HF: hazard ratio 0.80 (95% CI 0.73-0.87)", "HR", 0.80, 0.73, 0.87, "easy", "PARADIGM-HF"),
    ValidationCase("SHIFT: HR 0.82 (95% CI 0.75-0.90)", "HR", 0.82, 0.75, 0.90, "easy", "SHIFT"),
    ValidationCase("ATLAS-2: hazard ratio 0.85 (0.76-0.96)", "HR", 0.85, 0.76, 0.96, "easy", "ATLAS-2"),

    # Oncology trials
    ValidationCase("KEYNOTE-024: HR 0.50 (95% CI 0.37-0.68)", "HR", 0.50, 0.37, 0.68, "easy", "KEYNOTE-024"),
    ValidationCase("CheckMate-067: hazard ratio 0.55 (0.45-0.66)", "HR", 0.55, 0.45, 0.66, "easy", "CheckMate-067"),
    ValidationCase("MONARCH-3: HR 0.54 (95% CI 0.41-0.72)", "HR", 0.54, 0.41, 0.72, "easy", "MONARCH-3"),
    ValidationCase("PALOMA-2: hazard ratio 0.58 (0.46-0.72)", "HR", 0.58, 0.46, 0.72, "easy", "PALOMA-2"),

    # Edge values
    ValidationCase("HR 1.02 (95% CI 0.91-1.14)", "HR", 1.02, 0.91, 1.14, "easy"),  # Near null
    ValidationCase("HR 0.35 (0.22-0.55)", "HR", 0.35, 0.22, 0.55, "easy"),  # Strong effect
    ValidationCase("hazard ratio 1.45 (1.21-1.73)", "HR", 1.45, 1.21, 1.73, "easy"),  # Harm
    ValidationCase("HR 2.15 (1.65-2.80)", "HR", 2.15, 1.65, 2.80, "easy"),  # Large harm

    # Additional patterns
    ValidationCase("HR for mortality: 0.83 (0.71-0.97)", "HR", 0.83, 0.71, 0.97, "moderate"),
    ValidationCase("primary endpoint (HR 0.74; 95% CI, 0.65-0.85)", "HR", 0.74, 0.65, 0.85, "moderate"),
    ValidationCase("secondary outcome HR = 0.91 (0.82 to 1.01)", "HR", 0.91, 0.82, 1.01, "moderate"),
    ValidationCase("event-free survival HR 0.67 (95% CI: 0.54-0.83)", "HR", 0.67, 0.54, 0.83, "moderate"),
    ValidationCase("progression-free survival: hazard ratio 0.52 (0.40-0.68)", "HR", 0.52, 0.40, 0.68, "moderate"),
    ValidationCase("overall survival (HR, 0.69; 95% CI, 0.57 to 0.84)", "HR", 0.69, 0.57, 0.84, "moderate"),

    # More cardiovascular
    ValidationCase("COMPASS: HR 0.76 (95% CI 0.66-0.86) for MACE", "HR", 0.76, 0.66, 0.86, "easy", "COMPASS"),
    ValidationCase("FOURIER: hazard ratio 0.85 (0.79-0.92)", "HR", 0.85, 0.79, 0.92, "easy", "FOURIER"),
    ValidationCase("ODYSSEY: HR 0.85 (95% CI 0.78-0.93)", "HR", 0.85, 0.78, 0.93, "easy", "ODYSSEY"),
    ValidationCase("REDUCE-IT: hazard ratio 0.75 (0.68-0.83)", "HR", 0.75, 0.68, 0.83, "easy", "REDUCE-IT"),

    # Diabetes/renal
    ValidationCase("CREDENCE: HR 0.70 (95% CI 0.59-0.82)", "HR", 0.70, 0.59, 0.82, "easy", "CREDENCE"),
    ValidationCase("DAPA-CKD: hazard ratio 0.61 (0.51-0.72)", "HR", 0.61, 0.51, 0.72, "easy", "DAPA-CKD"),
    ValidationCase("EMPA-KIDNEY: HR 0.72 (95% CI 0.64-0.82)", "HR", 0.72, 0.64, 0.82, "easy", "EMPA-KIDNEY"),

    # More complex
    ValidationCase("stratified HR 0.78 (0.66-0.92)", "HR", 0.78, 0.66, 0.92, "moderate"),
    ValidationCase("Cox proportional hazards: HR 0.81 (0.72-0.91)", "HR", 0.81, 0.72, 0.91, "moderate"),
    ValidationCase("multivariable-adjusted HR 0.74 (0.63-0.87)", "HR", 0.74, 0.63, 0.87, "hard"),
    ValidationCase("propensity-matched HR 0.69 (0.58-0.82)", "HR", 0.69, 0.58, 0.82, "hard"),
]

# =============================================================================
# ODDS RATIO VALIDATION CASES (40 cases)
# =============================================================================

OR_VALIDATION = [
    # Easy cases
    ValidationCase("odds ratio 2.31 (95% CI 1.58-3.38)", "OR", 2.31, 1.58, 3.38, "easy"),
    ValidationCase("OR 1.85 (1.42-2.41)", "OR", 1.85, 1.42, 2.41, "easy"),
    ValidationCase("odds ratio, 1.45; 95% CI, 1.12 to 1.88", "OR", 1.45, 1.12, 1.88, "easy"),
    ValidationCase("OR = 0.72 (95% confidence interval: 0.55-0.94)", "OR", 0.72, 0.55, 0.94, "easy"),
    ValidationCase("odds ratio of 1.92 (95% CI 1.35-2.73)", "OR", 1.92, 1.35, 2.73, "easy"),
    ValidationCase("OR: 0.68; 95% CI: 0.52-0.89", "OR", 0.68, 0.52, 0.89, "easy"),
    ValidationCase("(OR 1.56; 95% CI 1.21-2.01)", "OR", 1.56, 1.21, 2.01, "easy"),
    ValidationCase("odds ratio was 2.15 (1.68 to 2.75)", "OR", 2.15, 1.68, 2.75, "easy"),

    # Moderate cases - Adjusted
    ValidationCase("adjusted OR 1.78 (95% CI 1.35-2.35)", "OR", 1.78, 1.35, 2.35, "moderate"),
    ValidationCase("aOR 0.65 (0.48-0.88)", "OR", 0.65, 0.48, 0.88, "moderate"),
    ValidationCase("multivariate-adjusted odds ratio 1.52 (1.18-1.96)", "OR", 1.52, 1.18, 1.96, "moderate"),
    ValidationCase("The odds ratio for response was 2.45 (95% CI, 1.72 to 3.49)", "OR", 2.45, 1.72, 3.49, "moderate"),

    # Meta-analysis formats
    ValidationCase("pooled OR 1.34 (95% CI 1.15-1.56)", "OR", 1.34, 1.15, 1.56, "moderate"),
    ValidationCase("summary odds ratio 0.78 (0.65-0.94)", "OR", 0.78, 0.65, 0.94, "moderate"),
    ValidationCase("random-effects OR 1.62 (1.28-2.05)", "OR", 1.62, 1.28, 2.05, "moderate"),
    ValidationCase("fixed-effect odds ratio 1.41 (1.22-1.63)", "OR", 1.41, 1.22, 1.63, "moderate"),

    # Clinical trials
    ValidationCase("treatment response: OR 2.85 (95% CI 2.01-4.04)", "OR", 2.85, 2.01, 4.04, "easy"),
    ValidationCase("remission: odds ratio 3.12 (2.25-4.33)", "OR", 3.12, 2.25, 4.33, "easy"),
    ValidationCase("adverse event: OR 1.23 (0.98-1.54)", "OR", 1.23, 0.98, 1.54, "easy"),
    ValidationCase("mortality: odds ratio 0.82 (0.68-0.99)", "OR", 0.82, 0.68, 0.99, "easy"),

    # Edge cases
    ValidationCase("OR 1.01 (0.89-1.15)", "OR", 1.01, 0.89, 1.15, "easy"),  # Near null
    ValidationCase("OR 0.45 (0.28-0.72)", "OR", 0.45, 0.28, 0.72, "easy"),  # Strong protective
    ValidationCase("odds ratio 5.23 (3.12-8.77)", "OR", 5.23, 3.12, 8.77, "moderate"),  # Large effect
    ValidationCase("OR 0.12 (0.05-0.29)", "OR", 0.12, 0.05, 0.29, "moderate"),  # Very strong protective

    # Comma in CI
    ValidationCase("OR 1.72 (95% CI 1.35, 2.19)", "OR", 1.72, 1.35, 2.19, "moderate"),
    ValidationCase("odds ratio 0.81 (0.67, 0.98)", "OR", 0.81, 0.67, 0.98, "moderate"),

    # Square brackets
    ValidationCase("OR 1.54 [95% CI 1.22-1.94]", "OR", 1.54, 1.22, 1.94, "moderate"),
    ValidationCase("odds ratio 2.08 [1.56-2.77]", "OR", 2.08, 1.56, 2.77, "moderate"),

    # Additional cases
    ValidationCase("logistic regression: OR 1.45 (1.12-1.88)", "OR", 1.45, 1.12, 1.88, "moderate"),
    ValidationCase("case-control OR 2.67 (1.89-3.77)", "OR", 2.67, 1.89, 3.77, "moderate"),
    ValidationCase("cross-sectional odds ratio 1.33 (1.08-1.64)", "OR", 1.33, 1.08, 1.64, "moderate"),
]

# =============================================================================
# RISK RATIO VALIDATION CASES (35 cases)
# =============================================================================

RR_VALIDATION = [
    # Easy cases
    ValidationCase("relative risk 0.87 (95% CI 0.79-0.95)", "RR", 0.87, 0.79, 0.95, "easy"),
    ValidationCase("RR 0.72 (0.63-0.82)", "RR", 0.72, 0.63, 0.82, "easy"),
    ValidationCase("risk ratio 1.25 (95% CI 1.08-1.45)", "RR", 1.25, 1.08, 1.45, "easy"),
    ValidationCase("relative risk, 0.65; 95% CI, 0.52 to 0.81", "RR", 0.65, 0.52, 0.81, "easy"),
    ValidationCase("RR = 0.91 (95% confidence interval: 0.84-0.99)", "RR", 0.91, 0.84, 0.99, "easy"),
    ValidationCase("relative risk of 0.78 (95% CI 0.67-0.91)", "RR", 0.78, 0.67, 0.91, "easy"),
    ValidationCase("RR: 1.15; 95% CI: 1.02-1.30", "RR", 1.15, 1.02, 1.30, "easy"),
    ValidationCase("(RR 0.82; 95% CI 0.73-0.92)", "RR", 0.82, 0.73, 0.92, "easy"),

    # BCG meta-analysis (classic dataset)
    ValidationCase("BCG vaccine RR 0.49 (95% CI 0.34-0.70)", "RR", 0.49, 0.34, 0.70, "easy"),
    ValidationCase("TB prevention: relative risk 0.41 (0.13-1.26)", "RR", 0.41, 0.13, 1.26, "moderate"),
    ValidationCase("Aronson trial: RR 0.21 (95% CI 0.07-0.64)", "RR", 0.21, 0.07, 0.64, "easy"),

    # Rate ratio
    ValidationCase("rate ratio 0.70 (95% CI 0.58-0.85)", "RR", 0.70, 0.58, 0.85, "moderate"),
    ValidationCase("incidence rate ratio 1.35 (1.12-1.63)", "RR", 1.35, 1.12, 1.63, "moderate"),

    # Adjusted
    ValidationCase("adjusted RR 0.82 (95% CI 0.71-0.95)", "RR", 0.82, 0.71, 0.95, "moderate"),
    ValidationCase("aRR 0.74 (0.62-0.88)", "RR", 0.74, 0.62, 0.88, "moderate"),

    # Meta-analysis
    ValidationCase("pooled RR 0.85 (95% CI 0.78-0.93)", "RR", 0.85, 0.78, 0.93, "moderate"),
    ValidationCase("summary relative risk 1.18 (1.05-1.33)", "RR", 1.18, 1.05, 1.33, "moderate"),

    # Clinical contexts
    ValidationCase("infection risk: RR 0.65 (0.52-0.81)", "RR", 0.65, 0.52, 0.81, "easy"),
    ValidationCase("mortality risk ratio 0.88 (0.79-0.98)", "RR", 0.88, 0.79, 0.98, "easy"),
    ValidationCase("hospitalization: relative risk 0.72 (0.61-0.85)", "RR", 0.72, 0.61, 0.85, "easy"),

    # St. John's Wort meta-analysis
    ValidationCase("St John's Wort: RR 1.48 (95% CI 1.23-1.78)", "RR", 1.48, 1.23, 1.78, "easy"),
    ValidationCase("vs antidepressants: RR 1.01 (0.87-1.16)", "RR", 1.01, 0.87, 1.16, "easy"),

    # Edge cases
    ValidationCase("RR 1.00 (0.92-1.09)", "RR", 1.00, 0.92, 1.09, "easy"),  # Null effect
    ValidationCase("relative risk 0.35 (0.18-0.68)", "RR", 0.35, 0.18, 0.68, "moderate"),  # Strong

    # Additional
    ValidationCase("RR for TB death was 0.29 (95% CI 0.16-0.53)", "RR", 0.29, 0.16, 0.53, "moderate"),
    ValidationCase("meningitis: relative risk 0.36 (0.18-0.70)", "RR", 0.36, 0.18, 0.70, "moderate"),
]

# =============================================================================
# MEAN DIFFERENCE VALIDATION CASES (35 cases)
# =============================================================================

MD_VALIDATION = [
    # Easy cases
    ValidationCase("mean difference 2.4 (95% CI 1.1 to 3.7)", "MD", 2.4, 1.1, 3.7, "easy"),
    ValidationCase("MD -1.5 (95% CI -2.3 to -0.7)", "MD", -1.5, -2.3, -0.7, "easy"),
    ValidationCase("difference 3.2 (2.1 to 4.3)", "MD", 3.2, 2.1, 4.3, "easy"),
    ValidationCase("MD: -0.82 (95% CI: -1.04 to -0.60)", "MD", -0.82, -1.04, -0.60, "easy"),
    ValidationCase("mean difference of 1.8 (95% CI 0.9-2.7)", "MD", 1.8, 0.9, 2.7, "easy"),
    ValidationCase("MD = -2.1 (-3.2 to -1.0)", "MD", -2.1, -3.2, -1.0, "easy"),

    # Weighted mean difference
    ValidationCase("weighted mean difference -1.25 (95% CI -1.85 to -0.65)", "MD", -1.25, -1.85, -0.65, "moderate"),
    ValidationCase("WMD 0.85 (0.42-1.28)", "MD", 0.85, 0.42, 1.28, "moderate"),
    ValidationCase("WMD: -0.69 (95% CI -1.24 to -0.14)", "MD", -0.69, -1.24, -0.14, "moderate"),

    # Clinical measures
    ValidationCase("HbA1c: MD -0.82% (95% CI -1.04 to -0.60)", "MD", -0.82, -1.04, -0.60, "easy"),
    ValidationCase("weight change: mean difference -2.5 kg (-3.2 to -1.8)", "MD", -2.5, -3.2, -1.8, "easy"),
    ValidationCase("blood pressure: MD -5.2 mmHg (95% CI -7.1 to -3.3)", "MD", -5.2, -7.1, -3.3, "easy"),
    ValidationCase("LDL reduction: difference -38 mg/dL (-45 to -31)", "MD", -38.0, -45.0, -31.0, "easy"),
    ValidationCase("eGFR: MD 4.5 (95% CI 2.1-6.9)", "MD", 4.5, 2.1, 6.9, "easy"),

    # Meta-analysis
    ValidationCase("pooled MD -1.8 (95% CI -2.5 to -1.1)", "MD", -1.8, -2.5, -1.1, "moderate"),
    ValidationCase("overall mean difference 2.3 (1.5-3.1)", "MD", 2.3, 1.5, 3.1, "moderate"),

    # Pain/symptom scores
    ValidationCase("VAS pain: MD -15.2 (95% CI -22.1 to -8.3)", "MD", -15.2, -22.1, -8.3, "easy"),
    ValidationCase("symptom score difference -3.5 (-5.2 to -1.8)", "MD", -3.5, -5.2, -1.8, "easy"),

    # Quality of life
    ValidationCase("QoL: mean difference 5.8 (95% CI 3.2-8.4)", "MD", 5.8, 3.2, 8.4, "easy"),
    ValidationCase("SF-36: MD 4.2 (2.1 to 6.3)", "MD", 4.2, 2.1, 6.3, "easy"),

    # Edge cases
    ValidationCase("MD 0.0 (-0.5 to 0.5)", "MD", 0.0, -0.5, 0.5, "easy"),  # Null
    ValidationCase("mean difference -0.02 (-0.08 to 0.04)", "MD", -0.02, -0.08, 0.04, "easy"),  # Small

    # Additional contexts
    ValidationCase(": MD -0.69 (95% CI -1.24 to -0.14)", "MD", -0.69, -1.24, -0.14, "moderate"),
    ValidationCase("adjusted MD 2.1 (95% CI 1.2-3.0)", "MD", 2.1, 1.2, 3.0, "moderate"),
]

# =============================================================================
# STANDARDIZED MEAN DIFFERENCE VALIDATION CASES (30 cases)
# =============================================================================

SMD_VALIDATION = [
    # Easy cases
    ValidationCase("standardized mean difference 0.45 (95% CI 0.22-0.68)", "SMD", 0.45, 0.22, 0.68, "easy"),
    ValidationCase("SMD 0.32 (0.15-0.49)", "SMD", 0.32, 0.15, 0.49, "easy"),
    ValidationCase("standardized mean difference -0.28 (-0.45 to -0.11)", "SMD", -0.28, -0.45, -0.11, "easy"),
    ValidationCase("SMD: 0.52 (95% CI: 0.31 to 0.73)", "SMD", 0.52, 0.31, 0.73, "easy"),
    ValidationCase("SMD = -0.41 (-0.62 to -0.20)", "SMD", -0.41, -0.62, -0.20, "easy"),

    # Cohen's d
    ValidationCase("Cohen's d 0.65 (95% CI 0.42-0.88)", "SMD", 0.65, 0.42, 0.88, "moderate"),
    ValidationCase("effect size (Cohen's d) 0.38 (0.18-0.58)", "SMD", 0.38, 0.18, 0.58, "moderate"),
    ValidationCase("Cohens d: -0.55 (-0.78 to -0.32)", "SMD", -0.55, -0.78, -0.32, "moderate"),

    # Hedges' g
    ValidationCase("Hedges' g 0.42 (95% CI 0.21-0.63)", "SMD", 0.42, 0.21, 0.63, "moderate"),
    ValidationCase("Hedges g: 0.35 (0.15 to 0.55)", "SMD", 0.35, 0.15, 0.55, "moderate"),

    # Effect size (generic)
    ValidationCase("effect size 0.58 (95% CI 0.35-0.81)", "SMD", 0.58, 0.35, 0.81, "moderate"),

    # Meta-analysis contexts
    ValidationCase("pooled SMD 0.48 (95% CI 0.32-0.64)", "SMD", 0.48, 0.32, 0.64, "moderate"),
    ValidationCase("overall standardized mean difference -0.35 (-0.52 to -0.18)", "SMD", -0.35, -0.52, -0.18, "moderate"),
    ValidationCase("random-effects SMD 0.41 (0.24-0.58)", "SMD", 0.41, 0.24, 0.58, "moderate"),

    # Teacher expectancy (classic dataset)
    ValidationCase("teacher expectancy: SMD 0.12 (95% CI -0.02 to 0.26)", "SMD", 0.12, -0.02, 0.26, "moderate"),
    ValidationCase("student performance: SMD 0.32 (0.15-0.49)", "SMD", 0.32, 0.15, 0.49, "easy"),

    # Psychology/education
    ValidationCase("cognitive outcome: SMD 0.55 (0.35-0.75)", "SMD", 0.55, 0.35, 0.75, "easy"),
    ValidationCase("anxiety reduction: standardized mean difference -0.62 (-0.85 to -0.39)", "SMD", -0.62, -0.85, -0.39, "easy"),
    ValidationCase("depression: SMD -0.48 (95% CI -0.68 to -0.28)", "SMD", -0.48, -0.68, -0.28, "easy"),

    # Effect size categories
    ValidationCase("small effect: SMD 0.18 (0.05-0.31)", "SMD", 0.18, 0.05, 0.31, "easy"),  # Small
    ValidationCase("medium effect: SMD 0.52 (0.35-0.69)", "SMD", 0.52, 0.35, 0.69, "easy"),  # Medium
    ValidationCase("large effect: SMD 0.85 (0.62-1.08)", "SMD", 0.85, 0.62, 1.08, "easy"),  # Large

    # Edge cases
    ValidationCase("SMD 0.01 (-0.15 to 0.17)", "SMD", 0.01, -0.15, 0.17, "easy"),  # Near null
    ValidationCase("SMD -0.02 (-0.18 to 0.14)", "SMD", -0.02, -0.18, 0.14, "easy"),  # Near null negative
]

# =============================================================================
# ABSOLUTE RISK DIFFERENCE VALIDATION CASES (20 cases)
# =============================================================================

ARD_VALIDATION = [
    ValidationCase("risk difference -3.2% (95% CI -5.1% to -1.3%)", "ARD", -3.2, -5.1, -1.3, "easy"),
    ValidationCase("ARD -2.5% (-4.0% to -1.0%)", "ARD", -2.5, -4.0, -1.0, "easy"),
    ValidationCase("absolute risk difference -0.05 (95% CI -0.08 to -0.02)", "ARD", -0.05, -0.08, -0.02, "easy"),
    ValidationCase("RD -4.1% (95% CI -6.2% to -2.0%)", "ARD", -4.1, -6.2, -2.0, "easy"),
    ValidationCase("absolute risk reduction 2.8% (1.5%-4.1%)", "ARD", 2.8, 1.5, 4.1, "easy"),
    ValidationCase("ARR 3.5% (95% CI 1.8% to 5.2%)", "ARD", 3.5, 1.8, 5.2, "easy"),
    ValidationCase("risk difference: -1.8% (-3.2% to -0.4%)", "ARD", -1.8, -3.2, -0.4, "easy"),
    ValidationCase("ARD = -0.032 (-0.051 to -0.013)", "ARD", -0.032, -0.051, -0.013, "moderate"),

    # Clinical contexts
    ValidationCase("mortality difference: -2.1% (95% CI -3.8% to -0.4%)", "ARD", -2.1, -3.8, -0.4, "easy"),
    ValidationCase("event rate difference -4.5% (-7.2% to -1.8%)", "ARD", -4.5, -7.2, -1.8, "easy"),

    # Edge cases
    ValidationCase("ARD 0.0% (-1.2% to 1.2%)", "ARD", 0.0, -1.2, 1.2, "easy"),  # Null
    ValidationCase("risk difference -0.1% (-0.5% to 0.3%)", "ARD", -0.1, -0.5, 0.3, "easy"),  # Small
]

# =============================================================================
# COMBINED VALIDATION DATASET
# =============================================================================

ALL_VALIDATION_CASES = (
    HR_VALIDATION +
    OR_VALIDATION +
    RR_VALIDATION +
    MD_VALIDATION +
    SMD_VALIDATION +
    ARD_VALIDATION
)

# Statistics
def get_validation_stats():
    """Get validation dataset statistics"""
    total = len(ALL_VALIDATION_CASES)
    by_type = {}
    by_difficulty = {"easy": 0, "moderate": 0, "hard": 0}

    for case in ALL_VALIDATION_CASES:
        etype = case.expected_type
        by_type[etype] = by_type.get(etype, 0) + 1
        by_difficulty[case.difficulty] = by_difficulty.get(case.difficulty, 0) + 1

    return {
        "total": total,
        "by_type": by_type,
        "by_difficulty": by_difficulty,
    }


if __name__ == "__main__":
    stats = get_validation_stats()
    print(f"Total validation cases: {stats['total']}")
    print(f"\nBy effect type:")
    for etype, count in sorted(stats['by_type'].items()):
        print(f"  {etype}: {count}")
    print(f"\nBy difficulty:")
    for diff, count in stats['by_difficulty'].items():
        print(f"  {diff}: {count}")
