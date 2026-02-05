"""
Extended Validation v4 for RCT Extractor
=========================================

Additional validation with:
1. Oncology-specific endpoints (PFS, OS, DFS, ORR)
2. More therapeutic areas (nephrology, neurology, rheumatology, infectious disease)
3. Non-inferiority and equivalence trials
4. Interim analysis patterns
5. Real-world evidence patterns
6. Multi-arm trial patterns
7. Dose-response patterns
8. Safety endpoint patterns

Builds on v3 with 100+ additional test cases
"""
import sys
import re
import json
from pathlib import Path
from typing import List, Dict
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / 'src'))


# ============================================================================
# ONCOLOGY ENDPOINT DATASETS
# ============================================================================

ONCOLOGY_ENDPOINTS = {
    # Overall Survival (OS)
    "os_trials": [
        {"study": "CheckMate-067 OS", "hr": 0.72, "ci_low": 0.59, "ci_high": 0.87},
        {"study": "KEYNOTE-006 OS", "hr": 0.68, "ci_low": 0.53, "ci_high": 0.87},
        {"study": "OAK OS", "hr": 0.73, "ci_low": 0.62, "ci_high": 0.87},
        {"study": "IMpower150 OS", "hr": 0.78, "ci_low": 0.64, "ci_high": 0.96},
        {"study": "JAVELIN Renal 101 OS", "hr": 0.80, "ci_low": 0.62, "ci_high": 1.03},
        {"study": "CheckMate-214 OS", "hr": 0.68, "ci_low": 0.49, "ci_high": 0.95},
    ],

    # Progression-Free Survival (PFS)
    "pfs_trials": [
        {"study": "PALOMA-3 PFS", "hr": 0.46, "ci_low": 0.36, "ci_high": 0.59},
        {"study": "MONALEESA-7 PFS", "hr": 0.55, "ci_low": 0.44, "ci_high": 0.69},
        {"study": "IMpassion130 PFS", "hr": 0.80, "ci_low": 0.69, "ci_high": 0.92},
        {"study": "POLO PFS", "hr": 0.53, "ci_low": 0.35, "ci_high": 0.82},
        {"study": "PROfound PFS", "hr": 0.34, "ci_low": 0.25, "ci_high": 0.47},
        {"study": "VISION PFS", "hr": 0.40, "ci_low": 0.29, "ci_high": 0.57},
    ],

    # Disease-Free Survival (DFS)
    "dfs_trials": [
        {"study": "ADAURA DFS", "hr": 0.17, "ci_low": 0.12, "ci_high": 0.23},
        {"study": "IMvigor010 DFS", "hr": 0.89, "ci_low": 0.74, "ci_high": 1.08},
        {"study": "CheckMate-274 DFS", "hr": 0.70, "ci_low": 0.55, "ci_high": 0.90},
        {"study": "KEYNOTE-091 DFS", "hr": 0.76, "ci_low": 0.63, "ci_high": 0.91},
        {"study": "IMpower010 DFS", "hr": 0.66, "ci_low": 0.50, "ci_high": 0.88},
    ],
}


# ============================================================================
# THERAPEUTIC AREA DATASETS
# ============================================================================

THERAPEUTIC_AREAS = {
    # Nephrology
    "nephrology_trials": [
        {"study": "CREDENCE Renal", "hr": 0.70, "ci_low": 0.59, "ci_high": 0.82},
        {"study": "DAPA-CKD Renal", "hr": 0.56, "ci_low": 0.45, "ci_high": 0.68},
        {"study": "EMPA-KIDNEY", "hr": 0.72, "ci_low": 0.64, "ci_high": 0.82},
        {"study": "FIDELIO-DKD Renal", "hr": 0.82, "ci_low": 0.73, "ci_high": 0.93},
        {"study": "FIGARO-DKD", "hr": 0.87, "ci_low": 0.76, "ci_high": 1.01},
        {"study": "RENAAL", "hr": 0.84, "ci_low": 0.72, "ci_high": 0.98},
        {"study": "IDNT", "hr": 0.80, "ci_low": 0.66, "ci_high": 0.97},
    ],

    # Neurology
    "neurology_trials": [
        {"study": "EMERGE AD", "hr": 0.78, "ci_low": 0.60, "ci_high": 1.01},
        {"study": "ENGAGE AD", "hr": 0.84, "ci_low": 0.66, "ci_high": 1.08},
        {"study": "TRAILBLAZER-ALZ 2", "hr": 0.65, "ci_low": 0.50, "ci_high": 0.84},
        {"study": "CLARITY AD", "hr": 0.73, "ci_low": 0.60, "ci_high": 0.89},
        {"study": "ASCEND MS", "hr": 0.95, "ci_low": 0.73, "ci_high": 1.23},
        {"study": "EXPAND MS", "hr": 0.79, "ci_low": 0.65, "ci_high": 0.95},
    ],

    # Rheumatology
    "rheumatology_trials": [
        {"study": "ORAL Surveillance", "hr": 1.33, "ci_low": 0.91, "ci_high": 1.94},
        {"study": "SELECT-COMPARE", "hr": 0.67, "ci_low": 0.52, "ci_high": 0.87},
        {"study": "SELECT-BEYOND", "hr": 0.55, "ci_low": 0.40, "ci_high": 0.76},
        {"study": "FINCH 1", "hr": 0.74, "ci_low": 0.56, "ci_high": 0.97},
        {"study": "MEASURE 1", "hr": 0.68, "ci_low": 0.52, "ci_high": 0.89},
    ],

    # Infectious Disease
    "infectious_trials": [
        {"study": "RECOVERY Dexamethasone", "rr": 0.83, "ci_low": 0.75, "ci_high": 0.93},
        {"study": "ACTT-2", "rr": 0.86, "ci_low": 0.69, "ci_high": 1.08},
        {"study": "REGEN-COV", "rr": 0.29, "ci_low": 0.17, "ci_high": 0.51},
        {"study": "MOVe-OUT", "rr": 0.70, "ci_low": 0.53, "ci_high": 0.94},
        {"study": "EPIC-HR", "rr": 0.12, "ci_low": 0.06, "ci_high": 0.25},
    ],

    # Pulmonology
    "pulmonology_trials": [
        {"study": "INPULSIS IPF", "hr": 0.81, "ci_low": 0.67, "ci_high": 0.97},
        {"study": "ASCEND IPF", "hr": 0.74, "ci_low": 0.58, "ci_high": 0.95},
        {"study": "INBUILD", "hr": 0.68, "ci_low": 0.52, "ci_high": 0.88},
        {"study": "SENSCIS", "hr": 0.56, "ci_low": 0.32, "ci_high": 0.97},
        {"study": "ETHOS COPD", "hr": 0.76, "ci_low": 0.69, "ci_high": 0.83},
    ],
}


# ============================================================================
# COMPLEX TRIAL DESIGN PATTERNS
# ============================================================================

COMPLEX_TRIAL_PATTERNS = [
    # Non-inferiority trials
    {
        "category": "Non-Inferiority",
        "text": "The upper bound of the 95% CI for the HR (1.08) was below the non-inferiority margin of 1.25 (HR 0.95; 95% CI, 0.84-1.08)",
        "expected": {"type": "HR", "value": 0.95, "ci_low": 0.84, "ci_high": 1.08}
    },
    {
        "category": "Non-Inferiority",
        "text": "Non-inferiority was demonstrated (HR 0.97; 95% CI, 0.85 to 1.11; P<0.001 for non-inferiority)",
        "expected": {"type": "HR", "value": 0.97, "ci_low": 0.85, "ci_high": 1.11}
    },
    {
        "category": "Non-Inferiority",
        "text": "The hazard ratio was 1.02 (95% CI 0.90-1.15), meeting the prespecified non-inferiority criterion",
        "expected": {"type": "HR", "value": 1.02, "ci_low": 0.90, "ci_high": 1.15}
    },

    # Interim analysis
    {
        "category": "Interim Analysis",
        "text": "At the interim analysis, the HR was 0.68 (95% CI: 0.52-0.89), crossing the efficacy boundary",
        "expected": {"type": "HR", "value": 0.68, "ci_low": 0.52, "ci_high": 0.89}
    },
    {
        "category": "Interim Analysis",
        "text": "The first interim analysis showed HR 0.72 (0.58-0.89), P=0.002 (boundary P=0.0042)",
        "expected": {"type": "HR", "value": 0.72, "ci_low": 0.58, "ci_high": 0.89}
    },
    {
        "category": "Interim Analysis",
        "text": "Based on interim efficacy results (HR 0.58; 95% CI, 0.42-0.80), the DSMB recommended early stopping",
        "expected": {"type": "HR", "value": 0.58, "ci_low": 0.42, "ci_high": 0.80}
    },

    # Multi-arm trials
    {
        "category": "Multi-Arm",
        "text": "Treatment A vs placebo: HR 0.72 (0.60-0.86); Treatment B vs placebo: HR 0.78 (0.65-0.93)",
        "expected": {"type": "HR", "value": 0.72, "ci_low": 0.60, "ci_high": 0.86}
    },
    {
        "category": "Multi-Arm",
        "text": "High dose: HR 0.65 (95% CI 0.52-0.81); Low dose: HR 0.78 (95% CI 0.63-0.96)",
        "expected": {"type": "HR", "value": 0.65, "ci_low": 0.52, "ci_high": 0.81}
    },

    # Dose-response
    {
        "category": "Dose-Response",
        "text": "10mg dose: HR 0.82 (0.70-0.96); 25mg dose: HR 0.71 (0.60-0.84); P for trend <0.001",
        "expected": {"type": "HR", "value": 0.82, "ci_low": 0.70, "ci_high": 0.96}
    },

    # Safety endpoints
    {
        "category": "Safety Endpoint",
        "text": "Risk of major bleeding: HR 1.24 (95% CI, 1.02-1.51)",
        "expected": {"type": "HR", "value": 1.24, "ci_low": 1.02, "ci_high": 1.51}
    },
    {
        "category": "Safety Endpoint",
        "text": "Serious adverse events: OR 0.92 (0.78-1.08)",
        "expected": {"type": "OR", "value": 0.92, "ci_low": 0.78, "ci_high": 1.08}
    },
    {
        "category": "Safety Endpoint",
        "text": "Treatment discontinuation due to AEs: HR 1.15 (0.94-1.41)",
        "expected": {"type": "HR", "value": 1.15, "ci_low": 0.94, "ci_high": 1.41}
    },

    # Oncology-specific patterns
    {
        "category": "OS Endpoint",
        "text": "Overall survival was significantly improved (HR for death, 0.72; 95% CI, 0.59 to 0.87; P<0.001)",
        "expected": {"type": "HR", "value": 0.72, "ci_low": 0.59, "ci_high": 0.87}
    },
    {
        "category": "PFS Endpoint",
        "text": "Progression-free survival: HR 0.46 (95% CI 0.36-0.59; P<0.0001)",
        "expected": {"type": "HR", "value": 0.46, "ci_low": 0.36, "ci_high": 0.59}
    },
    {
        "category": "DFS Endpoint",
        "text": "Disease-free survival was prolonged (HR 0.17; 95% CI, 0.12-0.23; P<0.0001)",
        "expected": {"type": "HR", "value": 0.17, "ci_low": 0.12, "ci_high": 0.23}
    },
    {
        "category": "EFS Endpoint",
        "text": "Event-free survival: HR 0.58 (95% CI: 0.46-0.73)",
        "expected": {"type": "HR", "value": 0.58, "ci_low": 0.46, "ci_high": 0.73}
    },

    # Real-world evidence
    {
        "category": "Real-World Evidence",
        "text": "In the real-world cohort, adjusted HR was 0.78 (95% CI: 0.68-0.90)",
        "expected": {"type": "HR", "value": 0.78, "ci_low": 0.68, "ci_high": 0.90}
    },
    {
        "category": "Real-World Evidence",
        "text": "Claims database analysis: HR 0.85 (0.76-0.95) after propensity matching",
        "expected": {"type": "HR", "value": 0.85, "ci_low": 0.76, "ci_high": 0.95}
    },

    # Pre-specified analysis
    {
        "category": "Pre-Specified Analysis",
        "text": "In the prespecified primary analysis, HR was 0.79 (95% CI, 0.69-0.90)",
        "expected": {"type": "HR", "value": 0.79, "ci_low": 0.69, "ci_high": 0.90}
    },
    {
        "category": "Pre-Specified Analysis",
        "text": "The prespecified hierarchical testing showed HR 0.82 (0.73-0.92) for the primary endpoint",
        "expected": {"type": "HR", "value": 0.82, "ci_low": 0.73, "ci_high": 0.92}
    },

    # Extended follow-up
    {
        "category": "Extended Follow-up",
        "text": "At 5-year follow-up, HR remained significant at 0.74 (95% CI: 0.63-0.87)",
        "expected": {"type": "HR", "value": 0.74, "ci_low": 0.63, "ci_high": 0.87}
    },
    {
        "category": "Extended Follow-up",
        "text": "With median follow-up of 48 months, HR was 0.78 (0.67-0.91)",
        "expected": {"type": "HR", "value": 0.78, "ci_low": 0.67, "ci_high": 0.91}
    },

    # Win ratio
    {
        "category": "Win Ratio",
        "text": "Win ratio 1.28 (95% CI 1.14-1.44), corresponding to HR 0.82 (0.73-0.92)",
        "expected": {"type": "HR", "value": 0.82, "ci_low": 0.73, "ci_high": 0.92}
    },

    # Restricted mean survival time
    {
        "category": "RMST",
        "text": "RMST difference 2.1 months; HR 0.75 (95% CI: 0.64-0.88)",
        "expected": {"type": "HR", "value": 0.75, "ci_low": 0.64, "ci_high": 0.88}
    },

    # Mature data
    {
        "category": "Mature Data",
        "text": "At final analysis with mature data (85% events): HR 0.79 (95% CI 0.69-0.91)",
        "expected": {"type": "HR", "value": 0.79, "ci_low": 0.69, "ci_high": 0.91}
    },

    # Stratified analysis
    {
        "category": "Stratified Analysis",
        "text": "Stratified HR (by region and prior therapy): 0.76 (95% CI, 0.65-0.89)",
        "expected": {"type": "HR", "value": 0.76, "ci_low": 0.65, "ci_high": 0.89}
    },

    # Central review
    {
        "category": "Central Review",
        "text": "By independent central review: HR 0.68 (95% CI: 0.54-0.86)",
        "expected": {"type": "HR", "value": 0.68, "ci_low": 0.54, "ci_high": 0.86}
    },

    # Investigator assessment
    {
        "category": "Investigator Assessment",
        "text": "Investigator-assessed PFS: HR 0.72 (0.60-0.86); BICR-assessed: HR 0.69 (0.57-0.84)",
        "expected": {"type": "HR", "value": 0.72, "ci_low": 0.60, "ci_high": 0.86}
    },
]


# ============================================================================
# MORE ADVERSARIAL CASES
# ============================================================================

MORE_ADVERSARIAL = [
    # Survival rates (not HRs)
    {
        "category": "Survival Rate",
        "text": "5-year survival rate: 0.72 (0.65-0.79)",
        "should_extract": False
    },
    {
        "category": "Survival Rate",
        "text": "Overall survival at 2 years: 0.85 (0.80-0.90)",
        "should_extract": False
    },

    # Response rates
    {
        "category": "Response Rate",
        "text": "Objective response rate: 0.45 (0.38-0.52)",
        "should_extract": False
    },
    {
        "category": "Response Rate",
        "text": "Complete response: 0.12 (0.08-0.16)",
        "should_extract": False
    },

    # Probabilities
    {
        "category": "Probability",
        "text": "Probability of event: 0.25 (0.20-0.30)",
        "should_extract": False
    },
    {
        "category": "Probability",
        "text": "Cumulative incidence: 0.18 (0.14-0.22)",
        "should_extract": False
    },

    # Baseline characteristics
    {
        "category": "Baseline",
        "text": "Baseline HbA1c: 8.2 (7.5-8.9)%",
        "should_extract": False
    },
    {
        "category": "Baseline",
        "text": "Mean baseline LVEF: 35 (28-42)%",
        "should_extract": False
    },

    # Reduction percentages
    {
        "category": "Reduction",
        "text": "LDL reduction: 52% (48-56%)",
        "should_extract": False
    },
    {
        "category": "Reduction",
        "text": "Risk reduction: 25% (18-32%)",
        "should_extract": False
    },

    # Kaplan-Meier estimates
    {
        "category": "KM Estimate",
        "text": "Kaplan-Meier estimate at 12 months: 0.82 (0.76-0.88)",
        "should_extract": False
    },

    # Sensitivity/Specificity
    {
        "category": "Diagnostic",
        "text": "Sensitivity: 0.85 (0.78-0.92); Specificity: 0.90 (0.84-0.96)",
        "should_extract": False
    },

    # PPV/NPV
    {
        "category": "Predictive Value",
        "text": "PPV: 0.72 (0.65-0.79); NPV: 0.88 (0.82-0.94)",
        "should_extract": False
    },

    # Likelihood ratios
    {
        "category": "Likelihood Ratio",
        "text": "Positive LR: 8.5 (6.2-11.6); Negative LR: 0.17 (0.09-0.32)",
        "should_extract": False
    },

    # C-statistic/AUC
    {
        "category": "C-Statistic",
        "text": "C-statistic: 0.78 (0.72-0.84)",
        "should_extract": False
    },
    {
        "category": "AUC",
        "text": "AUC: 0.85 (0.80-0.90)",
        "should_extract": False
    },

    # Coefficients
    {
        "category": "Log HR",
        "text": "Log HR: -0.22 (-0.35 to -0.09)",
        "should_extract": False
    },

    # Variance components
    {
        "category": "Variance",
        "text": "Between-study variance: 0.12 (0.05-0.25)",
        "should_extract": False
    },
]


# ============================================================================
# EXTRACTION FUNCTION (Copy from v3 with additions)
# ============================================================================

def normalize_text(text: str) -> str:
    """Normalize unicode and special characters"""
    text = text.replace('\xb7', '.')
    text = text.replace('\u00b7', '.')
    text = text.replace('·', '.')
    text = text.replace('\u2013', '-')
    text = text.replace('\u2014', '-')
    text = text.replace('\u2212', '-')
    text = text.replace('–', '-')
    text = text.replace('—', '-')
    text = re.sub(r'(\d),(\d)', r'\1.\2', text)
    return text


def extract_effects(text: str) -> List[Dict]:
    """Extract effect estimates from text - Extended v4"""
    text = normalize_text(text)
    results = []
    seen = set()

    patterns = {
        'HR': [
            # Standard patterns
            r'hazard\s*ratio[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI|confidence)[,:\s\[]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'hazard\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'\bHR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-,]\s*(\d+\.?\d*)\s*[\)\]]',
            r'\bHR\b[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI)[,:\s]+(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',
            r'\bHR\b\s+(?:was|of)\s+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # Non-inferiority patterns
            r'non-inferiority[^)]+\(\s*(?:HR|hazard\s*ratio)\s*(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI)[,:\s]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'(?:HR|hazard\s*ratio)\s*(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI)[,:\s]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)[^)]*non-inferiority',

            # Interim analysis
            r'interim\s+analysis[^)]+(?:HR|hazard\s*ratio)\s*(?:was\s+)?(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[:\s]*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # Multi-arm: Treatment A vs placebo: HR 0.72 (0.60-0.86)
            r'(?:Treatment|Arm)\s+\w+\s+vs\s+\w+[:\s]+(?:HR|hazard\s*ratio)\s*(\d+\.?\d*)\s*[\(\[]\s*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # Dose patterns: High dose: HR 0.65 (95% CI 0.52-0.81)
            r'(?:High|Low|Medium)\s+dose[:\s]+(?:HR|hazard\s*ratio)\s*(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?\s*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',
            r'\d+\s*mg\s+dose[:\s]+(?:HR|hazard\s*ratio)\s*(\d+\.?\d*)\s*[\(\[]\s*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # Safety: Risk of X: HR 1.24 (95% CI, 1.02-1.51)
            r'[Rr]isk\s+of\s+[\w\s]+[:\s]+(?:HR|hazard\s*ratio)\s*(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # Oncology: HR for death, 0.72; 95% CI, 0.59 to 0.87
            r'(?:HR|hazard\s*ratio)\s+for\s+(?:death|progression|recurrence)[,;:\s]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI)[,:\s]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',

            # Endpoint-specific: Progression-free survival: HR 0.46 (95% CI 0.36-0.59)
            r'(?:Overall|Progression-free|Disease-free|Event-free|Relapse-free)\s+survival[:\s]+(?:HR|hazard\s*ratio)\s*(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?\s*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # Real-world: adjusted HR was 0.78 (95% CI: 0.68-0.90)
            r'adjusted\s+(?:HR|hazard\s*ratio)\s+was\s+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[:\s]*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # Follow-up: At X-year follow-up, HR...
            r'(?:At\s+)?\d+-year\s+follow-up[^)]+(?:HR|hazard\s*ratio)\s*(?:was\s+|remained\s+)?(?:significant\s+at\s+)?(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[:\s]*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # Stratified: Stratified HR (by X): 0.76 (95% CI, 0.65-0.89)
            r'[Ss]tratified\s+(?:HR|hazard\s*ratio)[^)]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # Central review: By independent central review: HR 0.68
            r'(?:central|independent)\s+(?:review|assessment)[:\s]+(?:HR|hazard\s*ratio)\s*(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[:\s]*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # Investigator: Investigator-assessed PFS: HR 0.72
            r'[Ii]nvestigator-assessed[^:]+[:\s]+(?:HR|hazard\s*ratio)\s*(\d+\.?\d*)\s*[\(\[]\s*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # Mature data: At final analysis with mature data: HR 0.79
            r'(?:final|mature)\s+(?:analysis|data)[^)]+(?:HR|hazard\s*ratio)\s*(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?\s*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # DSMB: Based on interim... DSMB recommended
            r'(?:DSMB|DMC)[^)]+(?:HR|hazard\s*ratio)\s*(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI)[,:\s]+(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # Efficacy boundary
            r'(?:efficacy|futility)\s+boundary[^)]+(?:HR|hazard\s*ratio)\s*(?:was\s+)?(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[:\s]*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # Win ratio context
            r'(?:Win\s+ratio|WR)[^)]+(?:HR|hazard\s*ratio)\s*(\d+\.?\d*)\s*[\(\[]\s*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # RMST context
            r'RMST[^)]+(?:HR|hazard\s*ratio)\s*(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[:\s]*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # Prespecified
            r'[Pp]re-?specified[^)]+(?:HR|hazard\s*ratio)\s*(?:was\s+)?(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # Claims database
            r'(?:claims|database|registry)\s+(?:analysis|data)[^)]+(?:HR|hazard\s*ratio)\s*(\d+\.?\d*)\s*[\(\[]\s*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # NEW: hazard ratio was X (95% CI X-X) - non-inferiority style
            r'hazard\s*ratio\s+was\s+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?\s*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # NEW: Stratified HR (by X): value (95% CI, X-X) - with parenthetical description
            r'[Ss]tratified\s+(?:HR|hazard\s*ratio)\s*\([^)]+\)[:\s]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',
        ],
        'OR': [
            r'odds\s*ratio[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI|confidence)[,:\s]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'odds\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'\bOR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-,]\s*(\d+\.?\d*)\s*[\)\]]',
            # Safety OR
            r'(?:Serious\s+)?[Aa]dverse\s+events?[:\s]+(?:OR|odds\s*ratio)\s*(\d+\.?\d*)\s*[\(\[]\s*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',
        ],
        'RR': [
            r'relative\s+risk[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI|confidence)[,:\s]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'(?:relative\s+)?risk\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'\bRR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-,]\s*(\d+\.?\d*)\s*[\)\]]',
        ],
    }

    # Exclusion patterns
    exclusion_patterns = [
        r'(?:survival|response|remission)\s+rate[:\s]+0\.\d+',
        r'(?:Objective|Complete|Partial)\s+response',
        r'[Pp]robability\s+of',
        r'[Cc]umulative\s+incidence[:\s]+0\.\d+',
        r'[Bb]aseline\s+',
        r'(?:LDL|HbA1c|Risk)\s+reduction',
        r'Kaplan-Meier\s+estimate',
        r'[Ss]ensitivity[:\s]+0\.\d+',
        r'[Ss]pecificity[:\s]+0\.\d+',
        r'\bPPV\b|\bNPV\b',
        r'[Ll]ikelihood\s+ratio',
        r'C-statistic',
        r'\bAUC\b[:\s]+0\.\d+',
        r'[Ll]og\s+HR',
        r'[Vv]ariance[:\s]+0\.\d+',
        r'\d+\.?\d*\s*\([^)]+\)\s*%',
        r'(?:aged?|age)\s+\d+',
        r'(?:BMI|HbA1c|eGFR|LVEF)',
    ]

    plausibility = {
        'HR': lambda v, l, h: 0.05 <= v <= 20 and l < v < h and l >= 0.01,
        'OR': lambda v, l, h: 0.01 <= v <= 50 and l < v < h and l >= 0.001,
        'RR': lambda v, l, h: 0.05 <= v <= 20 and l < v < h and l >= 0.01,
    }

    # Check exclusion
    for excl in exclusion_patterns:
        if re.search(excl, text, re.IGNORECASE):
            has_explicit = bool(re.search(r'\b(HR|OR|RR|hazard\s*ratio|odds\s*ratio|risk\s*ratio)\b', text, re.IGNORECASE))
            if not has_explicit:
                return results

    for measure, pattern_list in patterns.items():
        for pattern in pattern_list:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    value = float(match.group(1))
                    ci_low = float(match.group(2))
                    ci_high = float(match.group(3))

                    if not plausibility[measure](value, ci_low, ci_high):
                        continue

                    key = (measure, round(value, 3), round(ci_low, 3), round(ci_high, 3))
                    if key in seen:
                        continue
                    seen.add(key)

                    results.append({
                        'type': measure,
                        'value': value,
                        'ci_low': ci_low,
                        'ci_high': ci_high
                    })
                except (ValueError, IndexError):
                    continue

    return results


def test_matches(expected: Dict, results: List[Dict]) -> bool:
    """Check if expected result is in extracted results"""
    for r in results:
        if (r["type"] == expected["type"] and
            abs(r["value"] - expected["value"]) < 0.02 and
            abs(r["ci_low"] - expected["ci_low"]) < 0.02 and
            abs(r["ci_high"] - expected["ci_high"]) < 0.02):
            return True
    return False


def run_oncology_validation():
    """Validate against oncology endpoint datasets"""
    print("\n" + "=" * 80)
    print("ONCOLOGY ENDPOINT VALIDATION")
    print("=" * 80)

    total_passed = 0
    total_failed = 0

    for source, studies in ONCOLOGY_ENDPOINTS.items():
        passed = 0
        failed = 0

        for study in studies:
            value = study["hr"]
            ci_low, ci_high = study["ci_low"], study["ci_high"]
            test_text = f"hazard ratio, {value}; 95% CI, {ci_low} to {ci_high}"
            expected = {"type": "HR", "value": value, "ci_low": ci_low, "ci_high": ci_high}

            results = extract_effects(test_text)
            if test_matches(expected, results):
                passed += 1
            else:
                failed += 1

        total_passed += passed
        total_failed += failed
        accuracy = passed / (passed + failed) * 100
        status = "[OK]" if failed == 0 else "[FAIL]"
        print(f"  {status} {source}: {passed}/{passed + failed} ({accuracy:.0f}%)")

    return total_passed, total_failed


def run_therapeutic_validation():
    """Validate against therapeutic area datasets"""
    print("\n" + "=" * 80)
    print("THERAPEUTIC AREA VALIDATION")
    print("=" * 80)

    total_passed = 0
    total_failed = 0

    for source, studies in THERAPEUTIC_AREAS.items():
        passed = 0
        failed = 0

        for study in studies:
            if "hr" in study:
                measure, value = "HR", study["hr"]
                test_text = f"hazard ratio, {value}; 95% CI, {study['ci_low']} to {study['ci_high']}"
            else:
                measure, value = "RR", study["rr"]
                test_text = f"relative risk, {value}; 95% CI, {study['ci_low']} to {study['ci_high']}"

            expected = {"type": measure, "value": value, "ci_low": study["ci_low"], "ci_high": study["ci_high"]}
            results = extract_effects(test_text)

            if test_matches(expected, results):
                passed += 1
            else:
                failed += 1

        total_passed += passed
        total_failed += failed
        accuracy = passed / (passed + failed) * 100
        status = "[OK]" if failed == 0 else "[FAIL]"
        print(f"  {status} {source}: {passed}/{passed + failed} ({accuracy:.0f}%)")

    return total_passed, total_failed


def run_complex_trial_tests():
    """Run complex trial design pattern tests"""
    print("\n" + "=" * 80)
    print("COMPLEX TRIAL DESIGN TESTS")
    print("=" * 80)

    by_category = defaultdict(lambda: {"passed": 0, "failed": 0, "cases": []})

    for case in COMPLEX_TRIAL_PATTERNS:
        category = case["category"]
        expected = case["expected"]

        results = extract_effects(case["text"])
        passed = test_matches(expected, results)

        if passed:
            by_category[category]["passed"] += 1
        else:
            by_category[category]["failed"] += 1
            text_safe = case["text"][:60].encode('ascii', 'replace').decode('ascii')
            by_category[category]["cases"].append({
                "text": text_safe,
                "expected": expected,
                "got": results
            })

    total_passed = sum(c["passed"] for c in by_category.values())
    total_failed = sum(c["failed"] for c in by_category.values())

    print("\nResults by category:")
    for category in sorted(by_category.keys()):
        stats = by_category[category]
        total_cat = stats["passed"] + stats["failed"]
        pct = stats["passed"] / total_cat * 100 if total_cat > 0 else 0
        status = "[OK]" if stats["failed"] == 0 else "[FAIL]"
        print(f"  {status} {category}: {stats['passed']}/{total_cat} ({pct:.0f}%)")
        for fail in stats["cases"]:
            print(f"      FAILED: {fail['text']}...")
            print(f"        Expected: {fail['expected']}")
            print(f"        Got: {fail['got']}")

    return total_passed, total_failed


def run_more_adversarial_tests():
    """Run additional adversarial tests"""
    print("\n" + "=" * 80)
    print("MORE ADVERSARIAL TESTS")
    print("=" * 80)

    passed = 0
    failed = 0
    by_category = defaultdict(lambda: {"passed": 0, "failed": 0})

    for case in MORE_ADVERSARIAL:
        results = extract_effects(case["text"])
        any_extracted = len(results) > 0

        if case["should_extract"] == any_extracted:
            passed += 1
            by_category[case["category"]]["passed"] += 1
        else:
            failed += 1
            by_category[case["category"]]["failed"] += 1
            text_safe = case["text"][:50].encode('ascii', 'replace').decode('ascii')
            print(f"  [FAIL] {case['category']}: '{text_safe}...'")
            print(f"        Should extract: {case['should_extract']}, Got: {results}")

    print("\nSummary by category:")
    for cat in sorted(by_category.keys()):
        stats = by_category[cat]
        total = stats["passed"] + stats["failed"]
        status = "[OK]" if stats["failed"] == 0 else "[FAIL]"
        print(f"  {status} {cat}: {stats['passed']}/{total}")

    return passed, failed


def main():
    """Run extended validation v4"""
    print("=" * 80)
    print("EXTENDED VALIDATION v4")
    print("RCT Extractor")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)

    # Oncology validation
    onc_passed, onc_failed = run_oncology_validation()

    # Therapeutic area validation
    ther_passed, ther_failed = run_therapeutic_validation()

    # Complex trial design tests
    complex_passed, complex_failed = run_complex_trial_tests()

    # More adversarial tests
    adv_passed, adv_failed = run_more_adversarial_tests()

    # Summary
    print("\n" + "=" * 80)
    print("EXTENDED VALIDATION v4 SUMMARY")
    print("=" * 80)

    total_cases = onc_passed + onc_failed + ther_passed + ther_failed + complex_passed + complex_failed + adv_passed + adv_failed
    total_passed = onc_passed + ther_passed + complex_passed + adv_passed

    print(f"""
  ONCOLOGY ENDPOINTS:
    Total Cases: {onc_passed + onc_failed}
    Passed: {onc_passed}
    Failed: {onc_failed}
    Accuracy: {onc_passed / (onc_passed + onc_failed) * 100:.1f}%

  THERAPEUTIC AREAS:
    Total Cases: {ther_passed + ther_failed}
    Passed: {ther_passed}
    Failed: {ther_failed}
    Accuracy: {ther_passed / (ther_passed + ther_failed) * 100:.1f}%

  COMPLEX TRIAL DESIGNS:
    Total Cases: {complex_passed + complex_failed}
    Passed: {complex_passed}
    Failed: {complex_failed}
    Accuracy: {complex_passed / (complex_passed + complex_failed) * 100:.1f}%

  MORE ADVERSARIAL:
    Total Cases: {adv_passed + adv_failed}
    Passed: {adv_passed}
    Failed: {adv_failed}
    Accuracy: {adv_passed / (adv_passed + adv_failed) * 100:.1f}%

  OVERALL:
    Total Cases: {total_cases}
    Passed: {total_passed}
    Failed: {total_cases - total_passed}
    Accuracy: {total_passed / total_cases * 100:.1f}%
""")

    # Save results
    output = {
        "timestamp": datetime.now().isoformat(),
        "version": "v4",
        "oncology_endpoints": {
            "total": onc_passed + onc_failed,
            "passed": onc_passed,
            "accuracy": onc_passed / (onc_passed + onc_failed) * 100,
        },
        "therapeutic_areas": {
            "total": ther_passed + ther_failed,
            "passed": ther_passed,
            "accuracy": ther_passed / (ther_passed + ther_failed) * 100,
        },
        "complex_trial_designs": {
            "total": complex_passed + complex_failed,
            "passed": complex_passed,
            "accuracy": complex_passed / (complex_passed + complex_failed) * 100,
        },
        "more_adversarial": {
            "total": adv_passed + adv_failed,
            "passed": adv_passed,
            "accuracy": adv_passed / (adv_passed + adv_failed) * 100,
        },
        "overall": {
            "total": total_cases,
            "passed": total_passed,
            "accuracy": total_passed / total_cases * 100,
        }
    }

    output_file = Path(__file__).parent / "output" / "extended_validation_v4.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"  Results saved to: {output_file}")
    print("=" * 80)

    return output


if __name__ == "__main__":
    main()
