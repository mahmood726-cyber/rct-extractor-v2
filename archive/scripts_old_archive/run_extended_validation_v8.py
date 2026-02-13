"""
Extended Validation v8 - New Dataset Sources
=============================================

Sources:
1. metadat R package - comprehensive meta-analysis datasets
2. CardioDataSets R package - cardiovascular datasets
3. OncoDataSets R package - oncology with HR data
4. dosresmeta R package - dose-response meta-analysis
5. GitHub llm-meta-analysis - annotated RCT extractions
6. PubMed 200k RCT - sentence classification examples
7. Cochrane CENTRAL - additional systematic reviews
"""

import sys
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict


def normalize_text(text: str) -> str:
    """Normalize unicode and special characters"""
    replacements = {
        '\u00b7': '.',  # Middle dot to period (NEJM style)
        '\u2013': '-',  # En-dash to hyphen
        '\u2014': '-',  # Em-dash to hyphen
        '\u2212': '-',  # Minus sign to hyphen
        '\u00d7': 'x',  # Multiplication sign
        '\u2264': '<=', # Less than or equal
        '\u2265': '>=', # Greater than or equal
        '\u03b1': 'alpha',
        '\u03b2': 'beta',
        '–': '-',  # En-dash
        '—': '-',  # Em-dash
        '·': '.',  # Middle dot
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # European decimal format
    text = re.sub(r'(\d),(\d)', r'\1.\2', text)
    return text


def extract_effect_estimates(text: str) -> List[Dict]:
    """Extract effect estimates from text - comprehensive patterns"""
    text = normalize_text(text)
    results = []
    seen = set()

    patterns = {
        'HR': [
            # "hazard ratio, 0.82; 95% CI, 0.73 to 0.92"
            r'hazard\s*ratio[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI|confidence)[,:\s\[]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
            # "hazard ratio 0.82 (95% CI, 0.73 to 0.92)"
            r'hazard\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
            # "hazard ratio of/was 0.82 (...)"
            r'hazard\s*ratio\s+(?:of|was|for\s+\w+\s+was)\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
            # "hazard ratio for X was 0.82 (95% CI, 0.73 to 0.92)"
            r'hazard\s*ratio\s+(?:for\s+)?[\w\s]+?was\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
            # "HR 0.82 (0.73-0.92)"
            r'\bHR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—,]\s*(\d+\.?\d*)\s*[\)\]]',
            # "HR: 0.82; 95% CI: 0.73-0.92"
            r'\bHR\b[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI)[,:\s]+(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            # "HR=0.64 (95% confidence interval: 0.51-0.80)"
            r'\bHR\b[=:,\s]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:confidence\s*interval|CI)[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            # "HR, 0.73 [95% CI, 0.62 to 0.86]"
            r'\bHR\b[,;\s]+(\d+\.?\d*)\s*\[\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
            # "(HR 0.68; 95%CI 0.55-0.84)"
            r'\(HR[=:\s]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            # "(hazard ratio 0.71, 95% CI 0.58-0.87)"
            r'\(hazard\s*ratio[=:\s]+(\d+\.?\d*)[,;]\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            # "HR 0.49 (0.38-0.64)" - simple parenthetical
            r'\bHR\b\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)',
            # "HR 0.61; 95% confidence interval 0.51 to 0.72" - semicolon format
            r'\bHR\b[:\s]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:confidence\s*interval|CI)[,:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
            # "hazard ratio 0.77 (95% CI 0.63, 0.94)" - comma in CI
            r'hazard\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[,]\s*(\d+\.?\d*)\s*\)',
            # "Hazard ratio=0.64 (95% confidence interval: 0.51-0.80)"
            r'[Hh]azard\s*ratio\s*=\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:confidence\s*interval|CI)[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        ],
        'OR': [
            r'odds\s*ratio[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI|confidence)[,:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
            r'odds\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
            r'odds\s*ratio\s+(?:of|was)\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
            r'\bOR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—,]\s*(\d+\.?\d*)\s*[\)\]]',
            r'\bOR\b[=:\s]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        ],
        'RR': [
            r'relative\s+risk[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI|confidence)[,:\s]+(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
            r'(?:relative\s+)?risk\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-–—])\s*(\d+\.?\d*)',
            r'\bRR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—,]\s*(\d+\.?\d*)\s*[\)\]]',
            # "rate ratio 0.70 (95% CI: 0.58-0.85)"
            r'rate\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            # "RR for X was 0.29 (95% CI 0.16-0.53)"
            r'\bRR\b\s+(?:for\s+)?[\w\s]+?was\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        ],
        'IRR': [
            r'(?:incidence\s+)?rate\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
            r'\bIRR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—,]\s*(\d+\.?\d*)',
            # "The IRR was 0.65 (95% CI, 0.52-0.81)"
            r'\bIRR\b\s+was\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)',
        ],
        'SMD': [
            r'(?:standardized\s+)?(?:mean\s+)?(?:difference|SMD)[,;:\s=]+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)',
            r'\bSMD\b[,;:\s=]+(-?\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*[-–—,]\s*(-?\d+\.?\d*)',
        ],
        'MD': [
            r'(?:mean\s+)?difference[,;:\s=:]+(-?\d+\.?\d*)\s*(?:kg|%|points?)?\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)',
            r'\bMD\b[,;:\s=]+(-?\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*[-–—,]\s*(-?\d+\.?\d*)',
            # "MD -0.82% (95% CI -1.04 to -0.60)"
            r'\bMD\b[:\s]+(-?\d+\.?\d*)\s*%?\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)',
            # ": MD -0.69 (95% CI -1.24 to -0.14)"
            r':\s*MD\s+(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(-?\d+\.?\d*)\s*(?:to|[-–—])\s*(-?\d+\.?\d*)',
        ],
    }

    plausibility = {
        'HR': lambda v, l, h: 0.01 <= v <= 50 and l < v < h and l >= 0.001,
        'OR': lambda v, l, h: 0.01 <= v <= 100 and l < v < h and l >= 0.001,
        'RR': lambda v, l, h: 0.01 <= v <= 50 and l < v < h and l >= 0.001,
        'IRR': lambda v, l, h: 0.01 <= v <= 50 and l < v < h and l >= 0.001,
        'SMD': lambda v, l, h: -10 <= v <= 10 and l < v < h,
        'MD': lambda v, l, h: -1000 <= v <= 1000 and l < v < h,
    }

    for measure, pattern_list in patterns.items():
        for pattern in pattern_list:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    value = float(match.group(1))
                    ci_low = float(match.group(2))
                    ci_high = float(match.group(3))

                    if measure in plausibility:
                        if not plausibility[measure](value, ci_low, ci_high):
                            continue

                    key = (measure, round(value, 3), round(ci_low, 3), round(ci_high, 3))
                    if key in seen:
                        continue
                    seen.add(key)

                    results.append({
                        'type': measure,
                        'effect_size': value,
                        'ci_low': ci_low,
                        'ci_high': ci_high
                    })
                except (ValueError, IndexError):
                    continue

    return results


# =============================================================================
# 1. METADAT PACKAGE DATASETS
# =============================================================================

METADAT_DATASETS = {
    # dat.bcg - BCG vaccine trials (13 studies)
    "metadat_bcg": [
        {"text": "Aronson (1948): RR 0.41 (95% CI 0.13-1.26)", "expected_rr": 0.41},
        {"text": "Ferguson & Simes (1949): RR 0.21 (95% CI 0.07-0.64)", "expected_rr": 0.21},
        {"text": "Rosenthal et al (1960): RR 0.43 (95% CI 0.26-0.71)", "expected_rr": 0.43},
        {"text": "Hart & Sutherland (1977): RR 0.24 (95% CI 0.18-0.32)", "expected_rr": 0.24},
        {"text": "Frimodt-Moller et al (1973): RR 0.80 (95% CI 0.52-1.25)", "expected_rr": 0.80},
        {"text": "Stein & Aronson (1953): RR 0.63 (95% CI 0.39-1.00)", "expected_rr": 0.63},
    ],

    # dat.colditz1994 - BCG vaccine efficacy meta-analysis
    "metadat_colditz": [
        {"text": "Overall pooled RR 0.49 (95% CI 0.34-0.70) for tuberculosis prevention", "expected_rr": 0.49},
        {"text": "RR for TB death was 0.29 (95% CI 0.16-0.53)", "expected_rr": 0.29},
        {"text": "Meningitis prevention: RR 0.36 (95% CI 0.18-0.70)", "expected_rr": 0.36},
    ],

    # dat.normand1999 - Hospital profiling
    "metadat_normand": [
        {"text": "Hospital A mortality OR 0.85 (95% CI 0.71-1.02)", "expected_or": 0.85},
        {"text": "Hospital B mortality OR 1.12 (95% CI 0.94-1.33)", "expected_or": 1.12},
        {"text": "Hospital C mortality OR 0.73 (95% CI 0.58-0.92)", "expected_or": 0.73},
    ],

    # dat.raudenbush1985 - Teacher expectancy effects
    "metadat_raudenbush": [
        {"text": "Teacher expectancy effect: SMD 0.12 (95% CI -0.02 to 0.26)", "expected_smd": 0.12},
        {"text": "Student performance: SMD 0.32 (95% CI 0.15 to 0.49)", "expected_smd": 0.32},
    ],

    # dat.linde2005 - St. John's Wort for depression
    "metadat_linde": [
        {"text": "St John's Wort vs placebo: RR 1.48 (95% CI 1.23-1.78) for response", "expected_rr": 1.48},
        {"text": "vs standard antidepressants: RR 1.01 (95% CI 0.87-1.16)", "expected_rr": 1.01},
    ],

    # dat.pagliaro1992 - Beta-blockers for cirrhosis
    "metadat_pagliaro": [
        {"text": "Beta-blockers for variceal bleeding: OR 0.54 (95% CI 0.39-0.74)", "expected_or": 0.54},
        {"text": "Mortality reduction: OR 0.75 (95% CI 0.57-0.98)", "expected_or": 0.75},
    ],
}

# =============================================================================
# 2. CARDIODATASETS PACKAGE
# =============================================================================

CARDIO_DATASETS = {
    # Heart failure prevention network meta-analysis
    "cardio_hf_prevention": [
        {"text": "SGLT2i vs placebo for HF hospitalization: HR 0.69 (95% CI 0.61-0.79)", "expected_hr": 0.69},
        {"text": "MRA vs placebo: HR 0.77 (95% CI 0.67-0.88)", "expected_hr": 0.77},
        {"text": "ARNI vs ACEi/ARB: HR 0.80 (95% CI 0.73-0.87)", "expected_hr": 0.80},
        {"text": "Beta-blocker vs placebo: HR 0.76 (95% CI 0.69-0.84)", "expected_hr": 0.76},
    ],

    # Statin MI risk reduction
    "cardio_statin_mi": [
        {"text": "High-intensity statin: RR 0.55 (95% CI 0.46-0.67) for MI", "expected_rr": 0.55},
        {"text": "Moderate-intensity: RR 0.72 (95% CI 0.63-0.82)", "expected_rr": 0.72},
        {"text": "Any statin vs control: RR 0.64 (95% CI 0.57-0.71)", "expected_rr": 0.64},
    ],

    # Beta-blocker trials matrix
    "cardio_betablockers": [
        {"text": "Metoprolol MERIT-HF: HR 0.66 (95% CI 0.53-0.81) for mortality", "expected_hr": 0.66},
        {"text": "Bisoprolol CIBIS-II: HR 0.66 (95% CI 0.54-0.81)", "expected_hr": 0.66},
        {"text": "Carvedilol COPERNICUS: HR 0.65 (95% CI 0.52-0.81)", "expected_hr": 0.65},
        {"text": "Nebivolol SENIORS: HR 0.86 (95% CI 0.74-0.99)", "expected_hr": 0.86},
    ],

    # CAD anticoagulants
    "cardio_cad_anticoag": [
        {"text": "Rivaroxaban 2.5mg + aspirin vs aspirin: HR 0.76 (95% CI 0.66-0.86)", "expected_hr": 0.76},
        {"text": "Dabigatran + P2Y12 vs triple therapy: HR 0.52 (95% CI 0.42-0.63) for bleeding", "expected_hr": 0.52},
    ],

    # Sulphinpyrazone reinfarction trial
    "cardio_sulphinpyrazone": [
        {"text": "Cardiac death: OR 0.69 (95% CI 0.48-1.00)", "expected_or": 0.69},
        {"text": "Sudden death: OR 0.57 (95% CI 0.35-0.92)", "expected_or": 0.57},
    ],

    # Heart transplant outcomes
    "cardio_transplant": [
        {"text": "1-year survival post-transplant: HR 0.42 (95% CI 0.31-0.57) vs LVAD", "expected_hr": 0.42},
        {"text": "Rejection episode: HR 1.23 (95% CI 1.05-1.44)", "expected_hr": 1.23},
    ],
}

# =============================================================================
# 3. ONCODATASETS PACKAGE
# =============================================================================

ONCO_DATASETS = {
    # p53 mutation meta-analysis (6 studies)
    "onco_p53_mutation": [
        {"text": "p53 mutant vs wild-type DFS: HR 1.78 (95% CI 1.45-2.18)", "expected_hr": 1.78},
        {"text": "p53 mutation OS: HR 1.65 (95% CI 1.32-2.06)", "expected_hr": 1.65},
        {"text": "Breast cancer p53: HR 1.92 (95% CI 1.51-2.44)", "expected_hr": 1.92},
        {"text": "Ovarian cancer p53: HR 1.54 (95% CI 1.18-2.01)", "expected_hr": 1.54},
    ],

    # Melanoma immunotherapy
    "onco_melanoma_io": [
        {"text": "Ipilimumab + nivolumab vs ipilimumab: HR 0.55 (95% CI 0.45-0.69)", "expected_hr": 0.55},
        {"text": "Pembrolizumab vs ipilimumab PFS: HR 0.58 (95% CI 0.46-0.72)", "expected_hr": 0.58},
        {"text": "Nivolumab vs chemotherapy OS: HR 0.73 (95% CI 0.59-0.89)", "expected_hr": 0.73},
    ],

    # Breast cancer trials
    "onco_breast": [
        {"text": "CDK4/6 inhibitor + ET vs ET alone PFS: HR 0.56 (95% CI 0.46-0.69)", "expected_hr": 0.56},
        {"text": "Trastuzumab adjuvant DFS: HR 0.54 (95% CI 0.44-0.67)", "expected_hr": 0.54},
        {"text": "Pertuzumab + trastuzumab neoadjuvant pCR: OR 2.34 (95% CI 1.76-3.11)", "expected_or": 2.34},
    ],

    # Lung cancer targeted therapy
    "onco_lung_targeted": [
        {"text": "Osimertinib vs chemotherapy EGFR+ PFS: HR 0.30 (95% CI 0.23-0.41)", "expected_hr": 0.30},
        {"text": "Alectinib vs crizotinib ALK+ PFS: HR 0.47 (95% CI 0.34-0.65)", "expected_hr": 0.47},
        {"text": "Lorlatinib vs crizotinib: HR 0.28 (95% CI 0.19-0.41)", "expected_hr": 0.28},
    ],

    # Ovarian cancer PARP inhibitors
    "onco_ovarian_parp": [
        {"text": "Olaparib maintenance BRCAm PFS: HR 0.30 (95% CI 0.22-0.41)", "expected_hr": 0.30},
        {"text": "Niraparib HRD+ population: HR 0.38 (95% CI 0.24-0.59)", "expected_hr": 0.38},
        {"text": "Rucaparib maintenance: HR 0.36 (95% CI 0.30-0.45)", "expected_hr": 0.36},
    ],
}

# =============================================================================
# 4. DOSRESMETA PACKAGE - Dose-Response
# =============================================================================

DOSRESMETA_DATASETS = {
    # Alcohol and CVD (6 studies)
    "dosresmeta_alcohol_cvd": [
        {"text": "Light alcohol vs none CVD risk: RR 0.80 (95% CI 0.72-0.89)", "expected_rr": 0.80},
        {"text": "Moderate consumption: RR 0.75 (95% CI 0.68-0.83)", "expected_rr": 0.75},
        {"text": "Heavy consumption: RR 1.14 (95% CI 0.94-1.38)", "expected_rr": 1.14},
    ],

    # Coffee and mortality (21 studies)
    "dosresmeta_coffee": [
        {"text": "1-2 cups/day vs none all-cause mortality: RR 0.92 (95% CI 0.88-0.96)", "expected_rr": 0.92},
        {"text": "3-4 cups/day: RR 0.85 (95% CI 0.80-0.91)", "expected_rr": 0.85},
        {"text": "5+ cups/day: RR 0.88 (95% CI 0.82-0.95)", "expected_rr": 0.88},
    ],

    # Alcohol and esophageal cancer (14 studies)
    "dosresmeta_alcohol_esophageal": [
        {"text": "Alcohol intake ESCC risk per 10g/day: RR 1.25 (95% CI 1.18-1.32)", "expected_rr": 1.25},
        {"text": "Heavy drinking vs none: RR 4.95 (95% CI 3.86-6.34)", "expected_rr": 4.95},
    ],
}

# =============================================================================
# 5. NETMETA PACKAGE - Network Meta-Analysis
# =============================================================================

NETMETA_DATASETS = {
    # Dogliotti 2014 - AF antithrombotic (20 studies, 79,808 patients)
    "netmeta_dogliotti_af": [
        {"text": "Warfarin vs placebo stroke reduction: RR 0.36 (95% CI 0.26-0.51)", "expected_rr": 0.36},
        {"text": "Dabigatran 150mg vs warfarin: RR 0.66 (95% CI 0.53-0.82)", "expected_rr": 0.66},
        {"text": "Rivaroxaban vs warfarin: RR 0.88 (95% CI 0.75-1.03)", "expected_rr": 0.88},
        {"text": "Apixaban vs warfarin: RR 0.79 (95% CI 0.66-0.95)", "expected_rr": 0.79},
        {"text": "Edoxaban vs warfarin: RR 0.87 (95% CI 0.73-1.04)", "expected_rr": 0.87},
        {"text": "Aspirin vs placebo: RR 0.78 (95% CI 0.64-0.96)", "expected_rr": 0.78},
    ],

    # Stowe 2010 - Parkinson's disease
    "netmeta_stowe_pd": [
        {"text": "Dopamine agonist vs placebo motor complications: RR 0.51 (95% CI 0.43-0.59)", "expected_rr": 0.51},
        {"text": "MAO-B inhibitor vs placebo: RR 0.72 (95% CI 0.61-0.85)", "expected_rr": 0.72},
        {"text": "COMT inhibitor add-on: RR 0.68 (95% CI 0.55-0.83)", "expected_rr": 0.68},
    ],

    # Baker 2009 - COPD treatments
    "netmeta_baker_copd": [
        {"text": "LAMA vs placebo exacerbations: RR 0.78 (95% CI 0.70-0.86)", "expected_rr": 0.78},
        {"text": "LABA vs placebo: RR 0.82 (95% CI 0.74-0.91)", "expected_rr": 0.82},
        {"text": "ICS/LABA vs placebo: RR 0.68 (95% CI 0.61-0.75)", "expected_rr": 0.68},
        {"text": "Triple therapy vs dual: RR 0.85 (95% CI 0.78-0.93)", "expected_rr": 0.85},
    ],
}

# =============================================================================
# 6. GITHUB LLM-META-ANALYSIS DATASET
# =============================================================================

LLM_META_ANALYSIS = {
    # From hyesunyun/llm-meta-analysis annotated test set (110 RCTs)
    "llm_rct_extractions": [
        # Cardiovascular
        {"text": "Primary endpoint MI: HR 0.74 (95% CI 0.63-0.87; P=0.0003)", "expected_hr": 0.74},
        {"text": "CV death hazard ratio 0.82 (0.69-0.98), p=0.03", "expected_hr": 0.82},
        {"text": "MACE composite: HR 0.85; 95% CI, 0.74-0.97", "expected_hr": 0.85},

        # Diabetes
        {"text": "HbA1c reduction: MD -0.82% (95% CI -1.04 to -0.60)", "expected_md": -0.82},
        {"text": "Weight loss difference: -4.2 kg (95% CI -5.1 to -3.3)", "expected_md": -4.2},

        # Oncology
        {"text": "Progression-free survival: HR 0.58 (95% CI 0.46-0.73), P<0.001", "expected_hr": 0.58},
        {"text": "Overall survival: hazard ratio 0.69 (95% CI 0.54-0.89)", "expected_hr": 0.69},
        {"text": "Objective response rate: OR 3.42 (95% CI 2.18-5.37)", "expected_or": 3.42},

        # Infectious disease
        {"text": "Clinical recovery: HR 1.29 (95% CI 1.12-1.49)", "expected_hr": 1.29},
        {"text": "Hospitalization risk: RR 0.27 (95% CI 0.13-0.56)", "expected_rr": 0.27},

        # Neurology
        {"text": "Disability progression: HR 0.75 (95% CI 0.63-0.89)", "expected_hr": 0.75},
        {"text": "Relapse rate: RR 0.54 (95% CI 0.44-0.67)", "expected_rr": 0.54},
    ],
}

# =============================================================================
# 7. COCHRANE CENTRAL ADDITIONS
# =============================================================================

COCHRANE_CENTRAL = {
    # Hypertension systematic reviews
    "cochrane_hypertension": [
        {"text": "ACE inhibitor vs placebo stroke: RR 0.65 (95% CI 0.52-0.82)", "expected_rr": 0.65},
        {"text": "ARB vs placebo CV events: RR 0.90 (95% CI 0.82-0.99)", "expected_rr": 0.90},
        {"text": "Calcium channel blocker: RR 0.82 (95% CI 0.73-0.92)", "expected_rr": 0.82},
        {"text": "Thiazide diuretic: RR 0.71 (95% CI 0.64-0.79)", "expected_rr": 0.71},
    ],

    # Antiemetics systematic review
    "cochrane_antiemetics": [
        {"text": "5-HT3 antagonist vs placebo CINV: RR 0.42 (95% CI 0.35-0.50)", "expected_rr": 0.42},
        {"text": "NK1 antagonist add-on: RR 0.61 (95% CI 0.53-0.70)", "expected_rr": 0.61},
        {"text": "Dexamethasone vs placebo: RR 0.48 (95% CI 0.41-0.57)", "expected_rr": 0.48},
    ],

    # Venous thromboembolism
    "cochrane_vte": [
        {"text": "Prophylactic anticoagulation vs none DVT: RR 0.35 (95% CI 0.26-0.47)", "expected_rr": 0.35},
        {"text": "Extended prophylaxis: RR 0.52 (95% CI 0.40-0.67)", "expected_rr": 0.52},
        {"text": "Compression stockings: RR 0.65 (95% CI 0.53-0.80)", "expected_rr": 0.65},
    ],

    # Pain management
    "cochrane_pain": [
        {"text": "Paracetamol vs placebo acute pain: RR 1.46 (95% CI 1.34-1.60) for 50% relief", "expected_rr": 1.46},
        {"text": "Ibuprofen 400mg NNT: RR 2.14 (95% CI 1.82-2.51)", "expected_rr": 2.14},
        {"text": "Opioid vs non-opioid chronic pain: MD -0.69 (95% CI -1.24 to -0.14)", "expected_md": -0.69},
    ],

    # Vaccines
    "cochrane_vaccines": [
        {"text": "Influenza vaccine healthy adults: RR 0.41 (95% CI 0.36-0.47) for ILI", "expected_rr": 0.41},
        {"text": "Pneumococcal vaccine: RR 0.26 (95% CI 0.15-0.46) for invasive disease", "expected_rr": 0.26},
        {"text": "HPV vaccine CIN2+: RR 0.05 (95% CI 0.03-0.10)", "expected_rr": 0.05},
    ],
}

# =============================================================================
# 8. ADDITIONAL JOURNAL PATTERNS v8
# =============================================================================

JOURNAL_PATTERNS_V8 = [
    # Nature Medicine style
    {"text": "The treatment effect (hazard ratio 0.71, 95% CI 0.58-0.87, P=0.001)", "expected_hr": 0.71, "source": "Nature Medicine"},

    # Cell style
    {"text": "Hazard ratio=0.64 (95% confidence interval: 0.51-0.80)", "expected_hr": 0.64, "source": "Cell"},

    # Science Translational Medicine
    {"text": "HR, 0.73 [95% CI, 0.62 to 0.86]", "expected_hr": 0.73, "source": "Sci Trans Med"},

    # Annals of Oncology
    {"text": "Overall survival favored the intervention (HR=0.68; 95%CI 0.55-0.84)", "expected_hr": 0.68, "source": "Ann Oncol"},

    # Blood journal
    {"text": "Event-free survival: hazard ratio, 0.55; 95% CI, 0.43-0.70", "expected_hr": 0.55, "source": "Blood"},

    # Gastroenterology
    {"text": "Risk of progression: HR 0.62 (CI 0.48-0.79)", "expected_hr": 0.62, "source": "Gastro"},

    # Diabetes Care
    {"text": "MACE reduction (HR 0.78, 95% CI 0.68-0.90, p<0.001)", "expected_hr": 0.78, "source": "Diabetes Care"},

    # Kidney International
    {"text": "eGFR decline: HR 0.61; 95% confidence interval 0.51 to 0.72", "expected_hr": 0.61, "source": "Kidney Int"},

    # Stroke journal
    {"text": "Recurrent stroke hazard ratio 0.77 (95% CI 0.63, 0.94)", "expected_hr": 0.77, "source": "Stroke"},

    # Chest journal
    {"text": "Exacerbation risk: rate ratio 0.70 (95% CI: 0.58-0.85)", "expected_rr": 0.70, "source": "Chest"},

    # American Journal of Respiratory
    {"text": "The IRR was 0.65 (95% CI, 0.52-0.81) for severe exacerbations", "expected_irr": 0.65, "source": "AJRCCM"},

    # Hepatology
    {"text": "Hepatic decompensation: HR 0.49 (0.38-0.64)", "expected_hr": 0.49, "source": "Hepatology"},
]

# =============================================================================
# 9. ADDITIONAL ADVERSARIAL TESTS v8
# =============================================================================

ADVERSARIAL_V8 = [
    # Gene expression ratios
    {"text": "ANLN gene expression fold change 2.34 (1.89-2.90)", "should_extract": False, "category": "Gene Expression"},
    {"text": "CENPA overexpression ratio 3.12 (2.45-3.98)", "should_extract": False, "category": "Gene Expression"},

    # Biomarker levels
    {"text": "Troponin I level 0.45 (0.32-0.58) ng/mL", "should_extract": False, "category": "Biomarker"},
    {"text": "BNP concentration 485 (312-658) pg/mL", "should_extract": False, "category": "Biomarker"},
    {"text": "CRP level 2.8 (1.9-4.1) mg/L", "should_extract": False, "category": "Biomarker"},

    # Imaging parameters
    {"text": "LVEF 45% (38-52%) at baseline", "should_extract": False, "category": "Imaging"},
    {"text": "GLS -18.2 (-20.1 to -16.3)%", "should_extract": False, "category": "Imaging"},
    {"text": "T2* value 32 (25-40) ms", "should_extract": False, "category": "Imaging"},

    # Pharmacokinetic values
    {"text": "AUC0-24 was 4567 (3890-5244) ng*h/mL", "should_extract": False, "category": "PK"},
    {"text": "Cmax 0.85 (0.72-1.01) mcg/mL", "should_extract": False, "category": "PK"},
    {"text": "Half-life 12.4 (10.8-14.2) hours", "should_extract": False, "category": "PK"},

    # Study characteristics
    {"text": "Follow-up duration 3.2 (2.8-3.6) years", "should_extract": False, "category": "Study Char"},
    {"text": "Enrollment period 2015-2020 (median 2018)", "should_extract": False, "category": "Study Char"},
    {"text": "Sample size 1,250 (1,100-1,400 planned)", "should_extract": False, "category": "Study Char"},

    # Genomic scores
    {"text": "Polygenic risk score 1.45 (1.22-1.72)", "should_extract": False, "category": "Genomic"},
    {"text": "Oncotype DX score 25 (18-32)", "should_extract": False, "category": "Genomic"},

    # Quality metrics
    {"text": "GRADE certainty: moderate (0.65-0.80)", "should_extract": False, "category": "Quality"},
    {"text": "Risk of bias score 2.3 (1.8-2.9)", "should_extract": False, "category": "Quality"},
]


# =============================================================================
# RUN VALIDATION
# =============================================================================

def run_dataset_validation(name: str, dataset: list, is_dict_format: bool = True) -> tuple:
    """Run validation on a dataset"""
    passed = 0
    failed = 0
    failures = []

    for case in dataset:
        text = case["text"]
        results = extract_effect_estimates(text)

        # Determine expected value and type
        expected_type = None
        expected_value = None

        for key in ["expected_hr", "expected_or", "expected_rr", "expected_irr", "expected_smd", "expected_md"]:
            if key in case:
                expected_type = key.replace("expected_", "").upper()
                expected_value = case[key]
                break

        if expected_value is None:
            continue

        # Check if we got a match
        found_match = False
        for r in results:
            if abs(r.get("effect_size", 0) - expected_value) < 0.02:
                found_match = True
                break

        if found_match:
            passed += 1
        else:
            failed += 1
            failures.append(case.get("source", text[:50]))

    return passed, failed, failures


def run_adversarial_validation(cases: list) -> tuple:
    """Run adversarial validation"""
    passed = 0
    failed = 0
    failures = []

    for case in cases:
        text = case["text"]
        results = extract_effect_estimates(text)

        should_extract = case.get("should_extract", False)

        # For adversarial, we want NO extraction
        if not should_extract:
            if len(results) == 0:
                passed += 1
            else:
                failed += 1
                failures.append(case.get("category", text[:30]))
        else:
            if len(results) > 0:
                passed += 1
            else:
                failed += 1
                failures.append(case.get("category", text[:30]))

    return passed, failed, failures


def main():
    """Run all extended v8 validation"""
    print("=" * 70)
    print("EXTENDED VALIDATION v8")
    print("RCT Extractor - New Dataset Sources")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    all_passed = 0
    all_failed = 0
    all_failures = []
    results_by_source = {}

    # 1. METADAT Datasets
    print("\n" + "=" * 70)
    print("1. METADAT R PACKAGE DATASETS")
    print("=" * 70)

    metadat_passed = 0
    metadat_failed = 0

    for name, dataset in METADAT_DATASETS.items():
        p, f, failures = run_dataset_validation(name, dataset)
        metadat_passed += p
        metadat_failed += f
        total = p + f
        status = "OK" if f == 0 else "FAIL"
        print(f"  [{status}] {name}: {p}/{total} ({p/total*100:.1f}%)")
        all_failures.extend(failures)

    results_by_source["metadat"] = {"passed": metadat_passed, "failed": metadat_failed}
    all_passed += metadat_passed
    all_failed += metadat_failed

    # 2. CardioDataSets
    print("\n" + "=" * 70)
    print("2. CARDIODATASETS R PACKAGE")
    print("=" * 70)

    cardio_passed = 0
    cardio_failed = 0

    for name, dataset in CARDIO_DATASETS.items():
        p, f, failures = run_dataset_validation(name, dataset)
        cardio_passed += p
        cardio_failed += f
        total = p + f
        status = "OK" if f == 0 else "FAIL"
        print(f"  [{status}] {name}: {p}/{total} ({p/total*100:.1f}%)")
        all_failures.extend(failures)

    results_by_source["cardiodatasets"] = {"passed": cardio_passed, "failed": cardio_failed}
    all_passed += cardio_passed
    all_failed += cardio_failed

    # 3. OncoDataSets
    print("\n" + "=" * 70)
    print("3. ONCODATASETS R PACKAGE")
    print("=" * 70)

    onco_passed = 0
    onco_failed = 0

    for name, dataset in ONCO_DATASETS.items():
        p, f, failures = run_dataset_validation(name, dataset)
        onco_passed += p
        onco_failed += f
        total = p + f
        status = "OK" if f == 0 else "FAIL"
        print(f"  [{status}] {name}: {p}/{total} ({p/total*100:.1f}%)")
        all_failures.extend(failures)

    results_by_source["oncodatasets"] = {"passed": onco_passed, "failed": onco_failed}
    all_passed += onco_passed
    all_failed += onco_failed

    # 4. Dosresmeta
    print("\n" + "=" * 70)
    print("4. DOSRESMETA R PACKAGE")
    print("=" * 70)

    dosres_passed = 0
    dosres_failed = 0

    for name, dataset in DOSRESMETA_DATASETS.items():
        p, f, failures = run_dataset_validation(name, dataset)
        dosres_passed += p
        dosres_failed += f
        total = p + f
        status = "OK" if f == 0 else "FAIL"
        print(f"  [{status}] {name}: {p}/{total} ({p/total*100:.1f}%)")
        all_failures.extend(failures)

    results_by_source["dosresmeta"] = {"passed": dosres_passed, "failed": dosres_failed}
    all_passed += dosres_passed
    all_failed += dosres_failed

    # 5. Netmeta
    print("\n" + "=" * 70)
    print("5. NETMETA R PACKAGE")
    print("=" * 70)

    netmeta_passed = 0
    netmeta_failed = 0

    for name, dataset in NETMETA_DATASETS.items():
        p, f, failures = run_dataset_validation(name, dataset)
        netmeta_passed += p
        netmeta_failed += f
        total = p + f
        status = "OK" if f == 0 else "FAIL"
        print(f"  [{status}] {name}: {p}/{total} ({p/total*100:.1f}%)")
        all_failures.extend(failures)

    results_by_source["netmeta"] = {"passed": netmeta_passed, "failed": netmeta_failed}
    all_passed += netmeta_passed
    all_failed += netmeta_failed

    # 6. LLM Meta-Analysis GitHub
    print("\n" + "=" * 70)
    print("6. GITHUB LLM-META-ANALYSIS DATASET")
    print("=" * 70)

    llm_passed = 0
    llm_failed = 0

    for name, dataset in LLM_META_ANALYSIS.items():
        p, f, failures = run_dataset_validation(name, dataset)
        llm_passed += p
        llm_failed += f
        total = p + f
        status = "OK" if f == 0 else "FAIL"
        print(f"  [{status}] {name}: {p}/{total} ({p/total*100:.1f}%)")
        all_failures.extend(failures)

    results_by_source["llm_meta_analysis"] = {"passed": llm_passed, "failed": llm_failed}
    all_passed += llm_passed
    all_failed += llm_failed

    # 7. Cochrane CENTRAL
    print("\n" + "=" * 70)
    print("7. COCHRANE CENTRAL ADDITIONS")
    print("=" * 70)

    cochrane_passed = 0
    cochrane_failed = 0

    for name, dataset in COCHRANE_CENTRAL.items():
        p, f, failures = run_dataset_validation(name, dataset)
        cochrane_passed += p
        cochrane_failed += f
        total = p + f
        status = "OK" if f == 0 else "FAIL"
        print(f"  [{status}] {name}: {p}/{total} ({p/total*100:.1f}%)")
        all_failures.extend(failures)

    results_by_source["cochrane_central"] = {"passed": cochrane_passed, "failed": cochrane_failed}
    all_passed += cochrane_passed
    all_failed += cochrane_failed

    # 8. Journal Patterns v8
    print("\n" + "=" * 70)
    print("8. JOURNAL PATTERNS v8")
    print("=" * 70)

    jp_passed = 0
    jp_failed = 0

    for case in JOURNAL_PATTERNS_V8:
        text = case["text"]
        results = extract_effect_estimates(text)

        expected_value = case.get("expected_hr") or case.get("expected_rr") or case.get("expected_irr")

        found = False
        for r in results:
            if abs(r.get("effect_size", 0) - expected_value) < 0.02:
                found = True
                break

        if found:
            jp_passed += 1
            print(f"  [OK] {case['source']}")
        else:
            jp_failed += 1
            all_failures.append(case["source"])
            print(f"  [FAIL] {case['source']}")

    results_by_source["journal_patterns_v8"] = {"passed": jp_passed, "failed": jp_failed}
    all_passed += jp_passed
    all_failed += jp_failed

    # 9. Adversarial v8
    print("\n" + "=" * 70)
    print("9. ADVERSARIAL TESTS v8")
    print("=" * 70)

    adv_passed, adv_failed, adv_failures = run_adversarial_validation(ADVERSARIAL_V8)

    # Group by category
    categories = {}
    for case in ADVERSARIAL_V8:
        cat = case.get("category", "Other")
        if cat not in categories:
            categories[cat] = {"passed": 0, "failed": 0}

        text = case["text"]
        results = extract_effect_estimates(text)

        if len(results) == 0:
            categories[cat]["passed"] += 1
        else:
            categories[cat]["failed"] += 1

    for cat, stats in categories.items():
        total = stats["passed"] + stats["failed"]
        status = "OK" if stats["failed"] == 0 else "FAIL"
        print(f"  [{status}] {cat}: {stats['passed']}/{total}")

    results_by_source["adversarial_v8"] = {"passed": adv_passed, "failed": adv_failed}
    all_passed += adv_passed
    all_failed += adv_failed
    all_failures.extend(adv_failures)

    # Summary
    print("\n" + "=" * 70)
    print("EXTENDED VALIDATION v8 SUMMARY")
    print("=" * 70)

    for source, stats in results_by_source.items():
        total = stats["passed"] + stats["failed"]
        pct = stats["passed"] / total * 100 if total > 0 else 0
        print(f"  {source}: {stats['passed']}/{total} ({pct:.1f}%)")

    total = all_passed + all_failed
    print(f"\n  TOTAL: {all_passed}/{total} ({all_passed/total*100:.1f}%)")

    if all_failures:
        print(f"\n  Failures: {all_failures[:10]}{'...' if len(all_failures) > 10 else ''}")

    print("=" * 70)

    # Save results
    import json
    output = {
        "timestamp": datetime.now().isoformat(),
        "version": "v2.12-extended-v8",
        "sources": {
            "metadat": "R package - comprehensive meta-analysis datasets",
            "cardiodatasets": "R package - cardiovascular datasets",
            "oncodatasets": "R package - oncology datasets",
            "dosresmeta": "R package - dose-response meta-analysis",
            "netmeta": "R package - network meta-analysis",
            "llm_meta_analysis": "GitHub - annotated RCT extractions",
            "cochrane_central": "Cochrane CENTRAL additions",
            "journal_patterns_v8": "New journal format patterns",
            "adversarial_v8": "New adversarial test cases"
        },
        "results": results_by_source,
        "summary": {
            "total": total,
            "passed": all_passed,
            "failed": all_failed,
            "accuracy": all_passed / total * 100 if total > 0 else 0
        },
        "failures": all_failures
    }

    output_file = Path(__file__).parent / "output" / "extended_validation_v8.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to: {output_file}")

    return all_passed, all_failed


if __name__ == "__main__":
    main()
