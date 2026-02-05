"""
Extended Validation v2 for RCT Extractor
=========================================

Expanded validation with:
1. More R package datasets (meta, netmeta, metaplus, robumeta)
2. Additional journal styles (BMJ, Annals, Circulation, EHJ)
3. IRR and SMD measure types
4. Network meta-analysis formats
5. More adversarial cases

Changelog:
- v2.5: Added 50+ new test cases, 3 new journal styles, 2 new measure types
"""
import sys
import re
import json
from pathlib import Path
from typing import List, Dict, Tuple
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / 'src'))


# ============================================================================
# R PACKAGE DATASETS - Extended
# ============================================================================

R_PACKAGE_DATASETS = {
    # metafor dat.bcg - BCG vaccine trials (RR)
    "metafor_bcg": [
        {"study": "Aronson 1948", "rr": 0.41, "ci_low": 0.13, "ci_high": 1.26},
        {"study": "Ferguson & Simes 1949", "rr": 0.21, "ci_low": 0.07, "ci_high": 0.63},
        {"study": "Rosenthal 1960", "rr": 0.37, "ci_low": 0.19, "ci_high": 0.70},
        {"study": "Hart & Sutherland 1977", "rr": 0.23, "ci_low": 0.11, "ci_high": 0.49},
        {"study": "Frimodt-Moller 1973", "rr": 0.80, "ci_low": 0.52, "ci_high": 1.25},
        {"study": "Stein & Aronson 1953", "rr": 0.45, "ci_low": 0.28, "ci_high": 0.73},
        {"study": "Vandiviere 1973", "rr": 0.20, "ci_low": 0.08, "ci_high": 0.50},
        {"study": "TPT Madras 1980", "rr": 0.63, "ci_low": 0.39, "ci_high": 1.00},
        {"study": "Coetzee & Berjak 1968", "rr": 0.98, "ci_low": 0.58, "ci_high": 1.66},
        {"study": "Rosenthal 1961", "rr": 1.56, "ci_low": 0.37, "ci_high": 6.53},
        {"study": "Comstock 1974", "rr": 0.98, "ci_low": 0.58, "ci_high": 1.66},
        {"study": "Comstock & Webster 1969", "rr": 1.01, "ci_low": 0.89, "ci_high": 1.15},
        {"study": "Comstock 1976", "rr": 0.88, "ci_low": 0.47, "ci_high": 1.63},
    ],

    # meta package - Fleiss1993bin (Aspirin post-MI)
    "meta_fleiss_aspirin": [
        {"study": "MRC-1", "or": 0.89, "ci_low": 0.62, "ci_high": 1.29},
        {"study": "CDP", "or": 1.01, "ci_low": 0.87, "ci_high": 1.17},
        {"study": "MRC-2", "or": 0.93, "ci_low": 0.69, "ci_high": 1.27},
        {"study": "GASP", "or": 0.64, "ci_low": 0.42, "ci_high": 0.96},
        {"study": "PARIS", "or": 0.89, "ci_low": 0.68, "ci_high": 1.16},
        {"study": "AMIS", "or": 1.00, "ci_low": 0.84, "ci_high": 1.20},
        {"study": "ISIS-2", "or": 0.79, "ci_low": 0.70, "ci_high": 0.89},
    ],

    # meta package - Olkin1995 (Thrombolytic therapy)
    "meta_olkin_thrombolytic": [
        {"study": "Fletcher 1959", "or": 0.16, "ci_low": 0.03, "ci_high": 0.76},
        {"study": "Dewar 1963", "or": 0.56, "ci_low": 0.16, "ci_high": 1.97},
        {"study": "European 1 1969", "or": 0.65, "ci_low": 0.38, "ci_high": 1.10},
        {"study": "European 2 1971", "or": 0.76, "ci_low": 0.52, "ci_high": 1.13},
        {"study": "Heikinheimo 1971", "or": 0.81, "ci_low": 0.46, "ci_high": 1.44},
        {"study": "Italian 1971", "or": 0.92, "ci_low": 0.57, "ci_high": 1.47},
        {"study": "Australian 1973", "or": 0.69, "ci_low": 0.42, "ci_high": 1.14},
        {"study": "Frankfurt 1973", "or": 0.26, "ci_low": 0.08, "ci_high": 0.84},
        {"study": "NHLBI SMIT 1974", "or": 0.99, "ci_low": 0.51, "ci_high": 1.95},
        {"study": "Frank 1975", "or": 0.93, "ci_low": 0.35, "ci_high": 2.49},
        {"study": "Valere 1975", "or": 0.46, "ci_low": 0.12, "ci_high": 1.70},
        {"study": "Klein 1976", "or": 0.82, "ci_low": 0.32, "ci_high": 2.12},
        {"study": "UK Collaborative 1976", "or": 0.91, "ci_low": 0.48, "ci_high": 1.73},
        {"study": "Austrian 1977", "or": 0.65, "ci_low": 0.40, "ci_high": 1.06},
        {"study": "Lasierra 1977", "or": 1.25, "ci_low": 0.42, "ci_high": 3.72},
        {"study": "N German 1977", "or": 0.94, "ci_low": 0.45, "ci_high": 1.97},
        {"study": "Witchitz 1977", "or": 0.21, "ci_low": 0.06, "ci_high": 0.72},
        {"study": "European 3 1979", "or": 0.82, "ci_low": 0.56, "ci_high": 1.21},
        {"study": "ISAM 1986", "or": 0.85, "ci_low": 0.63, "ci_high": 1.16},
        {"study": "GISSI-1 1986", "or": 0.81, "ci_low": 0.72, "ci_high": 0.90},
        {"study": "ISIS-2 1988", "or": 0.75, "ci_low": 0.67, "ci_high": 0.83},
    ],

    # netmeta - Dogliotti2014 (Antithrombotic treatments)
    "netmeta_dogliotti": [
        {"study": "AFASAK", "or": 0.38, "ci_low": 0.19, "ci_high": 0.78},
        {"study": "SPAF", "or": 0.30, "ci_low": 0.13, "ci_high": 0.67},
        {"study": "BAATAF", "or": 0.14, "ci_low": 0.04, "ci_high": 0.49},
        {"study": "CAFA", "or": 0.47, "ci_low": 0.17, "ci_high": 1.30},
        {"study": "SPINAF", "or": 0.27, "ci_low": 0.11, "ci_high": 0.66},
        {"study": "EAFT", "or": 0.34, "ci_low": 0.19, "ci_high": 0.61},
    ],

    # metaplus - Magnesium in MI
    "metaplus_magnesium": [
        {"study": "Morton 1984", "or": 0.23, "ci_low": 0.04, "ci_high": 1.23},
        {"study": "Rasmussen 1986", "or": 0.13, "ci_low": 0.03, "ci_high": 0.55},
        {"study": "Smith 1986", "or": 1.04, "ci_low": 0.07, "ci_high": 16.40},
        {"study": "Abraham 1987", "or": 0.31, "ci_low": 0.06, "ci_high": 1.62},
        {"study": "Feldstedt 1988", "or": 0.93, "ci_low": 0.38, "ci_high": 2.27},
        {"study": "Shechter 1989", "or": 0.06, "ci_low": 0.01, "ci_high": 0.51},
        {"study": "Ceremuzynski 1989", "or": 0.51, "ci_low": 0.22, "ci_high": 1.20},
        {"study": "Singh 1990", "or": 0.44, "ci_low": 0.18, "ci_high": 1.10},
        {"study": "Perea 1991", "or": 0.75, "ci_low": 0.13, "ci_high": 4.41},
        {"study": "Schechter 1991", "or": 0.25, "ci_low": 0.06, "ci_high": 1.06},
        {"study": "Golf 1991", "or": 0.59, "ci_low": 0.17, "ci_high": 2.08},
        {"study": "Thogersen 1991", "or": 0.37, "ci_low": 0.15, "ci_high": 0.95},
        {"study": "LIMIT-1 1992", "or": 0.67, "ci_low": 0.38, "ci_high": 1.17},
        {"study": "LIMIT-2 1992", "or": 0.75, "ci_low": 0.57, "ci_high": 1.00},
        {"study": "Perea 1993", "or": 0.67, "ci_low": 0.11, "ci_high": 4.04},
        {"study": "ISIS-4 1995", "or": 1.06, "ci_low": 0.95, "ci_high": 1.18},
    ],

    # Additional CVOT trials
    "cvot_sglt2_extended": [
        {"study": "SCORED", "hr": 0.74, "ci_low": 0.63, "ci_high": 0.88},
        {"study": "SOLOIST-WHF", "hr": 0.67, "ci_low": 0.52, "ci_high": 0.85},
        {"study": "VERTIS CV", "hr": 0.97, "ci_low": 0.85, "ci_high": 1.11},
        {"study": "CREDENCE Renal", "hr": 0.66, "ci_low": 0.53, "ci_high": 0.81},
        {"study": "DAPA-CKD", "hr": 0.61, "ci_low": 0.51, "ci_high": 0.72},
        {"study": "EMPA-KIDNEY", "hr": 0.72, "ci_low": 0.64, "ci_high": 0.82},
    ],

    # Beta-blocker trials (from metadat yusuf1985)
    "metadat_betablockers": [
        {"study": "Reynolds 1972", "or": 0.33, "ci_low": 0.04, "ci_high": 3.07},
        {"study": "Wilhelmsson 1974", "or": 0.47, "ci_low": 0.22, "ci_high": 0.99},
        {"study": "Ahlmark 1974", "or": 0.59, "ci_low": 0.25, "ci_high": 1.36},
        {"study": "Multicentre 1977", "or": 0.74, "ci_low": 0.45, "ci_high": 1.20},
        {"study": "Baber 1980", "or": 0.58, "ci_low": 0.26, "ci_high": 1.27},
        {"study": "Norwegian 1981", "or": 0.58, "ci_low": 0.40, "ci_high": 0.86},
        {"study": "Taylor 1982", "or": 1.14, "ci_low": 0.56, "ci_high": 2.31},
        {"study": "BHAT 1982", "or": 0.73, "ci_low": 0.58, "ci_high": 0.91},
        {"study": "Julian 1982", "or": 0.91, "ci_low": 0.62, "ci_high": 1.32},
        {"study": "Hansteen 1982", "or": 0.64, "ci_low": 0.37, "ci_high": 1.11},
        {"study": "Manger Cats 1983", "or": 0.76, "ci_low": 0.38, "ci_high": 1.54},
        {"study": "Rehnqvist 1983", "or": 0.47, "ci_low": 0.20, "ci_high": 1.12},
        {"study": "EIS Group 1984", "or": 0.95, "ci_low": 0.66, "ci_high": 1.37},
        {"study": "ASPS 1984", "or": 1.16, "ci_low": 0.63, "ci_high": 2.13},
        {"study": "LIT 1987", "or": 0.90, "ci_low": 0.67, "ci_high": 1.19},
        {"study": "APSI 1990", "or": 0.65, "ci_low": 0.32, "ci_high": 1.34},
    ],

    # Statin trials (extended)
    "statin_trials_extended": [
        {"study": "WOSCOPS", "hr": 0.69, "ci_low": 0.57, "ci_high": 0.83},
        {"study": "AFCAPS/TexCAPS", "hr": 0.63, "ci_low": 0.50, "ci_high": 0.79},
        {"study": "ASCOT-LLA", "hr": 0.64, "ci_low": 0.50, "ci_high": 0.83},
        {"study": "CARDS", "hr": 0.63, "ci_low": 0.48, "ci_high": 0.83},
        {"study": "MEGA", "hr": 0.67, "ci_low": 0.49, "ci_high": 0.91},
        {"study": "JUPITER", "hr": 0.56, "ci_low": 0.46, "ci_high": 0.69},
        {"study": "HOPE-3", "hr": 0.76, "ci_low": 0.64, "ci_high": 0.91},
        {"study": "4S", "hr": 0.70, "ci_low": 0.58, "ci_high": 0.85},
        {"study": "CARE", "hr": 0.76, "ci_low": 0.64, "ci_high": 0.91},
        {"study": "LIPID", "hr": 0.76, "ci_low": 0.65, "ci_high": 0.88},
        {"study": "HPS", "hr": 0.76, "ci_low": 0.72, "ci_high": 0.81},
        {"study": "PROVE IT", "hr": 0.84, "ci_low": 0.74, "ci_high": 0.95},
        {"study": "TNT", "hr": 0.78, "ci_low": 0.69, "ci_high": 0.89},
        {"study": "IDEAL", "hr": 0.87, "ci_low": 0.77, "ci_high": 0.98},
    ],
}


# ============================================================================
# EXTENDED STRESS TEST CASES
# ============================================================================

EXTENDED_STRESS_CASES = [
    # BMJ Style
    {
        "category": "BMJ Style",
        "text": "hazard ratio 0.82 (95% confidence interval 0.73 to 0.92)",
        "expected": {"type": "HR", "value": 0.82, "ci_low": 0.73, "ci_high": 0.92}
    },
    {
        "category": "BMJ Style",
        "text": "odds ratio 1.34 (1.12 to 1.60)",
        "expected": {"type": "OR", "value": 1.34, "ci_low": 1.12, "ci_high": 1.60}
    },
    {
        "category": "BMJ Style",
        "text": "relative risk 0.76 (0.65 to 0.89; P=0.001)",
        "expected": {"type": "RR", "value": 0.76, "ci_low": 0.65, "ci_high": 0.89}
    },

    # Annals of Internal Medicine Style
    {
        "category": "Annals Style",
        "text": "Hazard ratio, 0.74 (CI, 0.65-0.85)",
        "expected": {"type": "HR", "value": 0.74, "ci_low": 0.65, "ci_high": 0.85}
    },
    {
        "category": "Annals Style",
        "text": "hazard ratio (HR), 0.82 (95% CI, 0.73-0.92)",
        "expected": {"type": "HR", "value": 0.82, "ci_low": 0.73, "ci_high": 0.92}
    },

    # Circulation / EHJ Style
    {
        "category": "Circulation Style",
        "text": "HR=0.82, 95% CI 0.73-0.92, P<0.001",
        "expected": {"type": "HR", "value": 0.82, "ci_low": 0.73, "ci_high": 0.92}
    },
    {
        "category": "Circulation Style",
        "text": "HR: 0.75; 95%CI: 0.65 to 0.86",
        "expected": {"type": "HR", "value": 0.75, "ci_low": 0.65, "ci_high": 0.86}
    },
    {
        "category": "EHJ Style",
        "text": "hazard ratio [HR] 0.79 (95% confidence interval [CI] 0.69-0.90)",
        "expected": {"type": "HR", "value": 0.79, "ci_low": 0.69, "ci_high": 0.90}
    },

    # Network meta-analysis formats
    {
        "category": "NMA Format",
        "text": "versus placebo: OR 0.45 (95% CrI 0.32-0.63)",  # Credible interval
        "expected": {"type": "OR", "value": 0.45, "ci_low": 0.32, "ci_high": 0.63}
    },
    {
        "category": "NMA Format",
        "text": "treatment A vs B: HR 0.82 (95% CI 0.71 to 0.95)",
        "expected": {"type": "HR", "value": 0.82, "ci_low": 0.71, "ci_high": 0.95}
    },

    # Incidence Rate Ratio (IRR)
    {
        "category": "IRR Format",
        "text": "incidence rate ratio 0.72 (95% CI, 0.58 to 0.89)",
        "expected": {"type": "IRR", "value": 0.72, "ci_low": 0.58, "ci_high": 0.89}
    },
    {
        "category": "IRR Format",
        "text": "IRR 0.65 (0.52-0.81)",
        "expected": {"type": "IRR", "value": 0.65, "ci_low": 0.52, "ci_high": 0.81}
    },
    {
        "category": "IRR Format",
        "text": "rate ratio, 0.58; 95% CI, 0.45 to 0.75",
        "expected": {"type": "IRR", "value": 0.58, "ci_low": 0.45, "ci_high": 0.75}
    },

    # Mean Difference (MD)
    {
        "category": "MD Format",
        "text": "mean difference -2.4 kg (95% CI, -3.1 to -1.7)",
        "expected": {"type": "MD", "value": -2.4, "ci_low": -3.1, "ci_high": -1.7}
    },
    {
        "category": "MD Format",
        "text": "MD -5.2 mmHg (-6.8, -3.6)",
        "expected": {"type": "MD", "value": -5.2, "ci_low": -6.8, "ci_high": -3.6}
    },
    {
        "category": "MD Format",
        "text": "weighted mean difference, 1.8; 95% CI, 0.9 to 2.7",
        "expected": {"type": "MD", "value": 1.8, "ci_low": 0.9, "ci_high": 2.7}
    },

    # Standardized Mean Difference (SMD)
    {
        "category": "SMD Format",
        "text": "standardized mean difference 0.45 (95% CI 0.28 to 0.62)",
        "expected": {"type": "SMD", "value": 0.45, "ci_low": 0.28, "ci_high": 0.62}
    },
    {
        "category": "SMD Format",
        "text": "SMD -0.32 (-0.48, -0.16)",
        "expected": {"type": "SMD", "value": -0.32, "ci_low": -0.48, "ci_high": -0.16}
    },
    {
        "category": "SMD Format",
        "text": "Hedges' g = 0.58 (0.34-0.82)",
        "expected": {"type": "SMD", "value": 0.58, "ci_low": 0.34, "ci_high": 0.82}
    },
    {
        "category": "SMD Format",
        "text": "Cohen's d 0.72 (95% CI: 0.51 to 0.93)",
        "expected": {"type": "SMD", "value": 0.72, "ci_low": 0.51, "ci_high": 0.93}
    },

    # Very wide CIs (small studies)
    {
        "category": "Wide CI",
        "text": "HR 0.45 (0.12-1.68)",
        "expected": {"type": "HR", "value": 0.45, "ci_low": 0.12, "ci_high": 1.68}
    },
    {
        "category": "Wide CI",
        "text": "OR 2.34 (0.89-6.15)",
        "expected": {"type": "OR", "value": 2.34, "ci_low": 0.89, "ci_high": 6.15}
    },

    # Very narrow CIs (large studies)
    {
        "category": "Narrow CI",
        "text": "HR 0.82 (0.79-0.85)",
        "expected": {"type": "HR", "value": 0.82, "ci_low": 0.79, "ci_high": 0.85}
    },
    {
        "category": "Narrow CI",
        "text": "OR 1.05 (1.02-1.08)",
        "expected": {"type": "OR", "value": 1.05, "ci_low": 1.02, "ci_high": 1.08}
    },

    # Non-significant results crossing 1
    {
        "category": "Non-Significant",
        "text": "HR 0.95 (0.82-1.10)",
        "expected": {"type": "HR", "value": 0.95, "ci_low": 0.82, "ci_high": 1.10}
    },
    {
        "category": "Non-Significant",
        "text": "OR 1.08 (0.89-1.31)",
        "expected": {"type": "OR", "value": 1.08, "ci_low": 0.89, "ci_high": 1.31}
    },

    # With p-values in various formats
    {
        "category": "P-Value Formats",
        "text": "HR 0.74 (0.65-0.85), P<0.001",
        "expected": {"type": "HR", "value": 0.74, "ci_low": 0.65, "ci_high": 0.85}
    },
    {
        "category": "P-Value Formats",
        "text": "HR 0.82 (0.73-0.92); p=0.0008",
        "expected": {"type": "HR", "value": 0.82, "ci_low": 0.73, "ci_high": 0.92}
    },
    {
        "category": "P-Value Formats",
        "text": "OR 1.45 (1.12-1.88), p value = 0.004",
        "expected": {"type": "OR", "value": 1.45, "ci_low": 1.12, "ci_high": 1.88}
    },

    # Adjusted vs unadjusted
    {
        "category": "Adjusted",
        "text": "adjusted HR 0.79 (95% CI, 0.68-0.92)",
        "expected": {"type": "HR", "value": 0.79, "ci_low": 0.68, "ci_high": 0.92}
    },
    {
        "category": "Adjusted",
        "text": "unadjusted hazard ratio, 0.85; 95% CI, 0.74 to 0.98",
        "expected": {"type": "HR", "value": 0.85, "ci_low": 0.74, "ci_high": 0.98}
    },
    {
        "category": "Adjusted",
        "text": "multivariable-adjusted OR 1.32 (1.08 to 1.61)",
        "expected": {"type": "OR", "value": 1.32, "ci_low": 1.08, "ci_high": 1.61}
    },

    # Per-protocol vs ITT
    {
        "category": "Analysis Type",
        "text": "intention-to-treat analysis: HR 0.82 (0.73-0.92)",
        "expected": {"type": "HR", "value": 0.82, "ci_low": 0.73, "ci_high": 0.92}
    },
    {
        "category": "Analysis Type",
        "text": "per-protocol HR 0.79 (0.69-0.90)",
        "expected": {"type": "HR", "value": 0.79, "ci_low": 0.69, "ci_high": 0.90}
    },

    # Pooled estimates from meta-analysis
    {
        "category": "Pooled Estimate",
        "text": "pooled HR 0.76 (95% CI: 0.68-0.85, I²=32%)",
        "expected": {"type": "HR", "value": 0.76, "ci_low": 0.68, "ci_high": 0.85}
    },
    {
        "category": "Pooled Estimate",
        "text": "summary OR 0.65 (0.52-0.81), heterogeneity P=0.12",
        "expected": {"type": "OR", "value": 0.65, "ci_low": 0.52, "ci_high": 0.81}
    },

    # Number needed to treat context (should still extract effect)
    {
        "category": "NNT Context",
        "text": "HR 0.75 (0.65-0.87), corresponding to NNT of 25",
        "expected": {"type": "HR", "value": 0.75, "ci_low": 0.65, "ci_high": 0.87}
    },

    # Real trial results - additional
    {
        "category": "PARADIGM-HF",
        "text": "The hazard ratio for death from cardiovascular causes or a first hospitalization for heart failure was 0.80 (95% CI, 0.73 to 0.87; P<0.001)",
        "expected": {"type": "HR", "value": 0.80, "ci_low": 0.73, "ci_high": 0.87}
    },
    {
        "category": "COMPASS",
        "text": "hazard ratio 0.76; 95% CI 0.66-0.86; P<0.001",
        "expected": {"type": "HR", "value": 0.76, "ci_low": 0.66, "ci_high": 0.86}
    },
    {
        "category": "SELECT",
        "text": "hazard ratio, 0.80; 95% confidence interval [CI], 0.72 to 0.90",
        "expected": {"type": "HR", "value": 0.80, "ci_low": 0.72, "ci_high": 0.90}
    },
    {
        "category": "FOURIER",
        "text": "HR 0.85 (95% CI: 0.79-0.92, P<0.001)",
        "expected": {"type": "HR", "value": 0.85, "ci_low": 0.79, "ci_high": 0.92}
    },
]


# ============================================================================
# EXTENDED ADVERSARIAL CASES
# ============================================================================

EXTENDED_ADVERSARIAL_CASES = [
    # Age ranges
    {
        "category": "Age Range",
        "text": "Patients aged 65 (60-75) years were enrolled",
        "should_extract": False
    },
    {
        "category": "Age Range",
        "text": "mean age 72.4 (68.2-76.6) years",
        "should_extract": False
    },

    # Percentages
    {
        "category": "Percentage",
        "text": "Response rate was 45% (38-52%)",
        "should_extract": False
    },
    {
        "category": "Percentage",
        "text": "Compliance 92.5 (89.3-95.7)%",
        "should_extract": False
    },

    # Lab values
    {
        "category": "Lab Value",
        "text": "HbA1c 7.2 (6.8-7.6)%",
        "should_extract": False
    },
    {
        "category": "Lab Value",
        "text": "eGFR 68 (55-82) mL/min/1.73m²",
        "should_extract": False
    },
    {
        "category": "Lab Value",
        "text": "LDL-C 120 (95-145) mg/dL",
        "should_extract": False
    },

    # Dosing
    {
        "category": "Dosing",
        "text": "dose of 100 (50-200) mg daily",
        "should_extract": False
    },
    {
        "category": "Dosing",
        "text": "administered 2.5 (1.5-4.0) units",
        "should_extract": False
    },

    # Duration/Time
    {
        "category": "Duration",
        "text": "follow-up duration 2.4 (1.8-3.2) years",
        "should_extract": False
    },
    {
        "category": "Duration",
        "text": "median 36 (24-48) months",
        "should_extract": False
    },

    # Cost/economic
    {
        "category": "Cost",
        "text": "cost $15,000 (12,000-18,000)",
        "should_extract": False
    },

    # Event counts
    {
        "category": "Event Count",
        "text": "events: 150 (125-175 expected)",
        "should_extract": False
    },

    # IQR (not CI)
    {
        "category": "IQR",
        "text": "median HR 0.82 (IQR 0.73-0.91)",  # This is IQR not CI
        "should_extract": False
    },

    # Range (not CI)
    {
        "category": "Range",
        "text": "HR ranged from 0.65 to 1.25 across subgroups",
        "should_extract": False
    },

    # Reference values
    {
        "category": "Reference",
        "text": "normal range 0.8 (0.6-1.0)",
        "should_extract": False
    },

    # BMI
    {
        "category": "BMI",
        "text": "BMI 28.5 (25.2-31.8) kg/m²",
        "should_extract": False
    },

    # Temperature
    {
        "category": "Temperature",
        "text": "temperature 37.2 (36.8-37.6) °C",
        "should_extract": False
    },

    # Scores
    {
        "category": "Score",
        "text": "NYHA class 2.4 (2.1-2.7)",
        "should_extract": False
    },
    {
        "category": "Score",
        "text": "pain score 4.5 (3.2-5.8) on VAS",
        "should_extract": False
    },
]


# ============================================================================
# EXTRACTION FUNCTIONS
# ============================================================================

def normalize_text(text: str) -> str:
    """Normalize unicode and special characters"""
    # Replace unicode middle dots with periods
    text = text.replace('\xb7', '.')
    text = text.replace('\u00b7', '.')
    text = text.replace('\u2027', '.')
    text = text.replace('\u2219', '.')
    text = text.replace('·', '.')

    # Replace various dashes with hyphen
    text = text.replace('\u2013', '-')
    text = text.replace('\u2014', '-')
    text = text.replace('\u2212', '-')
    text = text.replace('\u2010', '-')
    text = text.replace('\u2011', '-')
    text = text.replace('–', '-')
    text = text.replace('—', '-')

    # European decimal format
    text = re.sub(r'(\d),(\d)', r'\1.\2', text)

    return text


def extract_effects(text: str) -> List[Dict]:
    """Extract effect estimates from text - Extended version"""
    text = normalize_text(text)
    results = []
    seen = set()

    patterns = {
        'HR': [
            # Standard formats
            r'hazard\s*ratio[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI|confidence)[,:\s\[]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'hazard\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'hazard\s*ratio\s+(?:of|was|for\s+\w+\s+was)\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'hazard\s*ratio\s+(?:for\s+)?[\w\s]+?was\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'\bHR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-,]\s*(\d+\.?\d*)\s*[\)\]]',
            r'\bHR\b[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI)[,:\s]+(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',
            r'Hazard\s+Ratio[,;:\s]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',
            r'hazard\s*ratio\s+in\s+[\w\s]+[,;]\s*(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:confidence|CI)[,:\s]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'hazard\s*ratio\s+of\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:confidence\s*interval)?[\s\[\]CI,]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'hazard\s*ratio\s+(?:for\s+)?[\w\s]+[,;]\s*(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:confidence\s*interval|CI)[,:\s]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'hazard\s*ratio[\w\s]+was\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:confidence\s*interval)?[\s\[\]CI,]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'\bHR\b[,;:\s]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]+(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',
            # New: HR=0.82, 95% CI 0.73-0.92
            r'\bHR\s*=\s*(\d+\.?\d*)[,;]\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',
            # New: hazard ratio [HR] 0.79 (95% confidence interval [CI] 0.69-0.90)
            r'hazard\s*ratio\s*\[HR\]\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:confidence\s*interval)?\s*\[CI\]\s*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',
            # New: adjusted/unadjusted HR
            r'(?:adjusted|unadjusted|multivariable-adjusted)\s+(?:hazard\s*ratio|HR)[,;:\s]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            # New: ITT/per-protocol analysis
            r'(?:intention-to-treat|per-protocol|ITT|PP)\s+(?:analysis)?[:\s]*(?:hazard\s*ratio|HR)\s*(\d+\.?\d*)\s*[\(\[]\s*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',
            # New: pooled/summary HR
            r'(?:pooled|summary)\s+(?:hazard\s*ratio|HR)\s*(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[:\s]*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',
            # BMJ Style: hazard ratio 0.82 (95% confidence interval 0.73 to 0.92)
            r'hazard\s*ratio\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?confidence\s*interval\s+(\d+\.?\d*)\s*to\s*(\d+\.?\d*)',
            # Annals Style: hazard ratio (HR), 0.82 (95% CI, 0.73-0.92)
            r'hazard\s*ratio\s*\(HR\)[,;:\s]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',
            # Circulation Style: HR: 0.75; 95%CI: 0.65 to 0.86 (no space after CI)
            r'\bHR\b[,;:\s]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            # NMA format: treatment A vs B: HR 0.82 (95% CI 0.71 to 0.95)
            r'(?:vs\.?|versus)\s+\w+[:\s]+(?:HR|hazard\s*ratio)\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI\s+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            # SELECT format: hazard ratio, 0.80; 95% confidence interval [CI], 0.72 to 0.90
            r'hazard\s*ratio[,;:\s]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?confidence\s*interval\s*\[CI\][,:\s]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
        ],
        'OR': [
            r'odds\s*ratio[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI|confidence)[,:\s]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'odds\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'odds\s*ratio\s+(?:of|was)\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI|confidence)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'odds\s*ratio\s+was\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:confidence\s*interval|CI)[,:\s]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'\bOR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI|CrI)?[,:\s]*(\d+\.?\d*)\s*[-,]\s*(\d+\.?\d*)\s*[\)\]]',
            # New: adjusted OR
            r'(?:adjusted|multivariable-adjusted)\s+(?:odds\s*ratio|OR)\s*(\d+\.?\d*)\s*[\(\[]\s*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            # New: summary/pooled OR
            r'(?:pooled|summary)\s+(?:odds\s*ratio|OR)\s*(\d+\.?\d*)\s*[\(\[]\s*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',
            # New: NMA format with CrI
            r'(?:versus|vs\.?)\s+\w+[:\s]+(?:odds\s*ratio|OR)\s*(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CrI|CI)\s*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',
        ],
        'RR': [
            r'relative\s+risk[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI|confidence)[,:\s]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'(?:relative\s+)?risk\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'\bRR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-,]\s*(\d+\.?\d*)\s*[\)\]]',
            # New: risk ratio X (X to X)
            r'risk\s*ratio\s*(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*to\s*(\d+\.?\d*)',
            # BMJ Style: relative risk 0.76 (0.65 to 0.89)
            r'relative\s+risk\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*to\s*(\d+\.?\d*)',
        ],
        'IRR': [
            r'incidence\s*rate\s*ratio[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI|confidence)[,:\s]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'incidence\s*rate\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'\bIRR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-,]\s*(\d+\.?\d*)\s*[\)\]]',
            r'rate\s*ratio[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
        ],
        'MD': [
            r'mean\s*difference[,;:\s=]+([-]?\d+\.?\d*)\s*(?:kg|mmHg|mm|cm|mL|units?)?\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*([-]?\d+\.?\d*)\s*(?:to|[-,])\s*([-]?\d+\.?\d*)',
            r'\bMD\b[,;:\s=]+([-]?\d+\.?\d*)\s*(?:kg|mmHg|mm|cm|mL|units?)?\s*[\(\[]\s*([-]?\d+\.?\d*)\s*[-,]\s*([-]?\d+\.?\d*)\s*[\)\]]',
            r'weighted\s*mean\s*difference[,;:\s=]+([-]?\d+\.?\d*)[;,]\s*(?:95%?\s*)?CI[,:\s]+([-]?\d+\.?\d*)\s*(?:to|[-])\s*([-]?\d+\.?\d*)',
        ],
        'SMD': [
            r'standardized\s*mean\s*difference[,;:\s=]+([-]?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*([-]?\d+\.?\d*)\s*(?:to|[-])\s*([-]?\d+\.?\d*)',
            r'\bSMD\b[,;:\s=]+([-]?\d+\.?\d*)\s*[\(\[]\s*([-]?\d+\.?\d*)\s*[-,]\s*([-]?\d+\.?\d*)\s*[\)\]]',
            r"(?:Hedges['']?\s*g|Cohen['']?s?\s*d)[,;:\s=]+([-]?\d+\.?\d*)\s*[\(\[]\s*([-]?\d+\.?\d*)\s*[-]\s*([-]?\d+\.?\d*)\s*[\)\]]",
            r"(?:Hedges['']?\s*g|Cohen['']?s?\s*d)\s*=\s*([-]?\d+\.?\d*)\s*[\(\[]\s*([-]?\d+\.?\d*)\s*[-]\s*([-]?\d+\.?\d*)\s*[\)\]]",
            # Cohen's d with curly apostrophe or straight quote
            r"Cohen.s\s*d\s+([-]?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]*([-]?\d+\.?\d*)\s*(?:to|[-])\s*([-]?\d+\.?\d*)",
        ],
    }

    # Exclusion patterns - these indicate non-effect values
    exclusion_patterns = [
        r'\d+\.?\d*\s*\([^)]+\)\s*%',  # Percentages like "7.2 (6.8-7.6)%"
        r'\d+\.?\d*\s*\([^)]+\)\s*(?:years?|months?|weeks?|days?)',  # Duration
        r'\d+\.?\d*\s*\([^)]+\)\s*(?:kg|mg|mL|units?|mmHg|mm|cm|°C|bpm)',  # Units
        r'\d+\.?\d*\s*\([^)]+\)\s*(?:kg/m|mL/min)',  # Complex units
        r'(?:aged?|age)\s+\d+\.?\d*\s*\([^)]+\)',  # Age ranges
        r'(?:BMI|HbA1c|eGFR|LDL|HDL)\s+\d+\.?\d*\s*\([^)]+\)',  # Lab values
        r'(?:dose|dosing)\s+(?:of\s+)?\d+\.?\d*\s*\([^)]+\)',  # Dosing
        r'(?:follow-up|duration|median)\s+\d+\.?\d*\s*\([^)]+\)',  # Duration
        r'(?:cost|price|\$)\s*\d+',  # Cost values
        r'(?:NYHA|class|score|pain)\s+\d+\.?\d*\s*\([^)]+\)',  # Scores
        r'(?:normal|reference)\s+(?:range|value)',  # Reference ranges
        r'\bIQR\b',  # IQR indicator
    ]

    plausibility = {
        'HR': lambda v, l, h: 0.05 <= v <= 20 and l < v < h and l >= 0.01,
        'OR': lambda v, l, h: 0.01 <= v <= 50 and l < v < h and l >= 0.001,
        'RR': lambda v, l, h: 0.05 <= v <= 20 and l < v < h and l >= 0.01,
        'IRR': lambda v, l, h: 0.05 <= v <= 20 and l < v < h and l >= 0.01,
        'MD': lambda v, l, h: -100 <= v <= 100 and l < v < h,
        'SMD': lambda v, l, h: -5 <= v <= 5 and l < v < h,
    }

    # Check for exclusion patterns first
    for excl_pattern in exclusion_patterns:
        if re.search(excl_pattern, text, re.IGNORECASE):
            # If exclusion pattern found, only allow extraction if explicit measure type is present
            has_explicit_measure = bool(re.search(
                r'\b(HR|OR|RR|IRR|MD|SMD|hazard\s*ratio|odds\s*ratio|risk\s*ratio|'
                r'incidence\s*rate\s*ratio|mean\s*difference|standardized\s*mean\s*difference)\b',
                text, re.IGNORECASE
            ))
            if not has_explicit_measure:
                return results  # Return empty if no explicit measure and exclusion found

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


def run_r_package_validation():
    """Validate against R package datasets"""
    print("\n" + "=" * 80)
    print("R PACKAGE DATASET VALIDATION")
    print("=" * 80)

    total_passed = 0
    total_failed = 0
    results_by_source = {}

    for source, studies in R_PACKAGE_DATASETS.items():
        passed = 0
        failed = 0

        for study in studies:
            # Determine measure type
            if "hr" in study:
                measure = "HR"
                value = study["hr"]
            elif "or" in study:
                measure = "OR"
                value = study["or"]
            elif "rr" in study:
                measure = "RR"
                value = study["rr"]
            else:
                continue

            ci_low = study["ci_low"]
            ci_high = study["ci_high"]

            # Generate test text
            if measure == "HR":
                test_text = f"hazard ratio, {value}; 95% CI, {ci_low} to {ci_high}"
            elif measure == "OR":
                test_text = f"odds ratio {value} (95% CI {ci_low}-{ci_high})"
            else:
                test_text = f"risk ratio {value} ({ci_low} to {ci_high})"

            expected = {"type": measure, "value": value, "ci_low": ci_low, "ci_high": ci_high}
            results = extract_effects(test_text)

            if test_matches(expected, results):
                passed += 1
            else:
                failed += 1

        total_passed += passed
        total_failed += failed
        results_by_source[source] = {"passed": passed, "failed": failed, "total": passed + failed}

        accuracy = passed / (passed + failed) * 100 if (passed + failed) > 0 else 0
        status = "[OK]" if failed == 0 else "[FAIL]"
        print(f"  {status} {source}: {passed}/{passed + failed} ({accuracy:.0f}%)")

    return total_passed, total_failed, results_by_source


def run_extended_stress_tests():
    """Run extended stress tests"""
    print("\n" + "=" * 80)
    print("EXTENDED STRESS TESTS")
    print("=" * 80)

    by_category = defaultdict(lambda: {"passed": 0, "failed": 0, "cases": []})

    for case in EXTENDED_STRESS_CASES:
        category = case["category"]
        expected = case["expected"]

        results = extract_effects(case["text"])
        passed = test_matches(expected, results)

        if passed:
            by_category[category]["passed"] += 1
        else:
            by_category[category]["failed"] += 1
            by_category[category]["cases"].append({
                "text": case["text"][:60] + "...",
                "expected": f"{expected['type']} {expected['value']} ({expected['ci_low']}, {expected['ci_high']})",
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
            print(f"      FAILED: {fail['text']}")
            print(f"        Expected: {fail['expected']}")
            print(f"        Got: {fail['got']}")

    return total_passed, total_failed, dict(by_category)


def run_extended_adversarial_tests():
    """Run extended adversarial tests"""
    print("\n" + "=" * 80)
    print("EXTENDED ADVERSARIAL TESTS")
    print("=" * 80)

    passed = 0
    failed = 0
    by_category = defaultdict(lambda: {"passed": 0, "failed": 0})

    for case in EXTENDED_ADVERSARIAL_CASES:
        results = extract_effects(case["text"])
        # Should NOT extract any effect estimates
        any_extracted = len(results) > 0

        if case["should_extract"] == any_extracted:
            passed += 1
            by_category[case["category"]]["passed"] += 1
            status = "[OK]"
        else:
            failed += 1
            by_category[case["category"]]["failed"] += 1
            status = "[FAIL]"

        if status == "[FAIL]":
            print(f"  {status} {case['category']}: '{case['text'][:50]}...'")
            print(f"        Should extract: {case['should_extract']}, Got: {results}")

    # Print summary by category
    print("\nSummary by category:")
    for cat in sorted(by_category.keys()):
        stats = by_category[cat]
        total = stats["passed"] + stats["failed"]
        status = "[OK]" if stats["failed"] == 0 else "[FAIL]"
        print(f"  {status} {cat}: {stats['passed']}/{total}")

    return passed, failed


def main():
    """Run extended validation"""
    print("=" * 80)
    print("EXTENDED VALIDATION v2.5")
    print("RCT Extractor")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)

    # R package validation
    r_passed, r_failed, r_by_source = run_r_package_validation()

    # Extended stress tests
    stress_passed, stress_failed, stress_by_cat = run_extended_stress_tests()

    # Extended adversarial tests
    adv_passed, adv_failed = run_extended_adversarial_tests()

    # Summary
    print("\n" + "=" * 80)
    print("EXTENDED VALIDATION SUMMARY")
    print("=" * 80)

    total_cases = r_passed + r_failed + stress_passed + stress_failed + adv_passed + adv_failed
    total_passed = r_passed + stress_passed + adv_passed

    print(f"""
  R PACKAGE DATASETS:
    Total Cases: {r_passed + r_failed}
    Passed: {r_passed}
    Failed: {r_failed}
    Accuracy: {r_passed / (r_passed + r_failed) * 100:.1f}%

  EXTENDED STRESS TESTS:
    Total Cases: {stress_passed + stress_failed}
    Passed: {stress_passed}
    Failed: {stress_failed}
    Accuracy: {stress_passed / (stress_passed + stress_failed) * 100:.1f}%

  EXTENDED ADVERSARIAL:
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
        "version": "v2.5",
        "r_package_validation": {
            "total": r_passed + r_failed,
            "passed": r_passed,
            "failed": r_failed,
            "accuracy": r_passed / (r_passed + r_failed) * 100,
            "by_source": r_by_source
        },
        "extended_stress_tests": {
            "total": stress_passed + stress_failed,
            "passed": stress_passed,
            "failed": stress_failed,
            "accuracy": stress_passed / (stress_passed + stress_failed) * 100,
        },
        "extended_adversarial": {
            "total": adv_passed + adv_failed,
            "passed": adv_passed,
            "failed": adv_failed,
            "accuracy": adv_passed / (adv_passed + adv_failed) * 100,
        },
        "overall": {
            "total": total_cases,
            "passed": total_passed,
            "failed": total_cases - total_passed,
            "accuracy": total_passed / total_cases * 100,
        }
    }

    output_file = Path(__file__).parent / "output" / "extended_validation_v2.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"  Results saved to: {output_file}")
    print("=" * 80)

    return output


if __name__ == "__main__":
    main()
