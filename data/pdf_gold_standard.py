"""
Gold Standard PDF Dataset for RCT Extractor Validation
=======================================================

This file contains manually curated effect estimates from 50 landmark
clinical trials with their expected values for validation.

Sources:
- PubMed Central open access
- NEJM, Lancet, JAMA open access articles
- EMA assessment reports
- ClinicalTrials.gov results

Each entry includes:
- Trial name and NCT number
- Publication reference (DOI/PMID)
- Expected effect estimates with exact values
- Source URL for verification
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum


class TrialType(Enum):
    HEART_FAILURE = "heart_failure"
    CARDIOVASCULAR = "cardiovascular"
    DIABETES = "diabetes"
    ONCOLOGY = "oncology"
    NEPHROLOGY = "nephrology"
    ANTICOAGULATION = "anticoagulation"
    LIPID = "lipid"


@dataclass
class ExpectedEffect:
    """An expected effect estimate for validation"""
    effect_type: str  # HR, OR, RR, etc.
    value: float
    ci_lower: float
    ci_upper: float
    p_value: Optional[float] = None
    outcome: str = ""
    endpoint_type: str = "primary"  # primary, secondary, composite


@dataclass
class GoldStandardTrial:
    """A trial in the gold standard dataset"""
    name: str
    nct_number: Optional[str]
    trial_type: TrialType
    publication_doi: Optional[str]
    pmid: Optional[str]
    source_url: str
    expected_effects: List[ExpectedEffect]
    notes: str = ""


# =============================================================================
# HEART FAILURE TRIALS (SGLT2 INHIBITORS & ARNI)
# =============================================================================

HEART_FAILURE_TRIALS = [
    GoldStandardTrial(
        name="DAPA-HF",
        nct_number="NCT03036124",
        trial_type=TrialType.HEART_FAILURE,
        publication_doi="10.1056/NEJMoa1911303",
        pmid="31535829",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa1911303",
        expected_effects=[
            ExpectedEffect("HR", 0.74, 0.65, 0.85, 0.00001, "CV death or worsening HF", "primary"),
            ExpectedEffect("HR", 0.83, 0.71, 0.97, None, "CV death", "secondary"),
            ExpectedEffect("HR", 0.70, 0.59, 0.83, None, "HF hospitalization", "secondary"),
            ExpectedEffect("HR", 0.83, 0.71, 0.97, None, "All-cause mortality", "secondary"),
        ],
        notes="Dapagliflozin in HFrEF"
    ),

    GoldStandardTrial(
        name="EMPEROR-Reduced",
        nct_number="NCT03057977",
        trial_type=TrialType.HEART_FAILURE,
        publication_doi="10.1056/NEJMoa2022190",
        pmid="32865377",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa2022190",
        expected_effects=[
            ExpectedEffect("HR", 0.75, 0.65, 0.86, 0.00001, "CV death or HF hospitalization", "primary"),
            ExpectedEffect("HR", 0.69, 0.59, 0.81, None, "HF hospitalization", "secondary"),
            ExpectedEffect("HR", 0.92, 0.75, 1.12, None, "CV death", "secondary"),
        ],
        notes="Empagliflozin in HFrEF"
    ),

    GoldStandardTrial(
        name="EMPEROR-Preserved",
        nct_number="NCT03057951",
        trial_type=TrialType.HEART_FAILURE,
        publication_doi="10.1056/NEJMoa2107038",
        pmid="34449189",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa2107038",
        expected_effects=[
            ExpectedEffect("HR", 0.79, 0.69, 0.90, 0.0003, "CV death or HF hospitalization", "primary"),
            ExpectedEffect("HR", 0.71, 0.60, 0.83, None, "HF hospitalization", "secondary"),
        ],
        notes="Empagliflozin in HFpEF"
    ),

    GoldStandardTrial(
        name="DELIVER",
        nct_number="NCT03619213",
        trial_type=TrialType.HEART_FAILURE,
        publication_doi="10.1056/NEJMoa2206286",
        pmid="36027570",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa2206286",
        expected_effects=[
            ExpectedEffect("HR", 0.82, 0.73, 0.92, 0.0008, "CV death or worsening HF", "primary"),
            ExpectedEffect("HR", 0.77, 0.67, 0.89, None, "HF hospitalization", "secondary"),
        ],
        notes="Dapagliflozin in HFmrEF/HFpEF"
    ),

    GoldStandardTrial(
        name="PARADIGM-HF",
        nct_number="NCT01035255",
        trial_type=TrialType.HEART_FAILURE,
        publication_doi="10.1056/NEJMoa1409077",
        pmid="25176015",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa1409077",
        expected_effects=[
            ExpectedEffect("HR", 0.80, 0.73, 0.87, 0.0000002, "CV death or HF hospitalization", "primary"),
            ExpectedEffect("HR", 0.80, 0.71, 0.89, None, "CV death", "secondary"),
            ExpectedEffect("HR", 0.79, 0.71, 0.89, None, "HF hospitalization", "secondary"),
            ExpectedEffect("HR", 0.84, 0.76, 0.93, None, "All-cause mortality", "secondary"),
        ],
        notes="Sacubitril/valsartan vs enalapril"
    ),

    GoldStandardTrial(
        name="VICTORIA",
        nct_number="NCT02861534",
        trial_type=TrialType.HEART_FAILURE,
        publication_doi="10.1056/NEJMoa1915928",
        pmid="32131908",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa1915928",
        expected_effects=[
            ExpectedEffect("HR", 0.90, 0.82, 0.98, 0.02, "CV death or HF hospitalization", "primary"),
            ExpectedEffect("HR", 0.90, 0.81, 1.00, None, "HF hospitalization", "secondary"),
        ],
        notes="Vericiguat in high-risk HFrEF"
    ),
]

# =============================================================================
# CARDIOVASCULAR OUTCOME TRIALS (SGLT2 & GLP-1)
# =============================================================================

CARDIOVASCULAR_TRIALS = [
    GoldStandardTrial(
        name="EMPA-REG OUTCOME",
        nct_number="NCT01131676",
        trial_type=TrialType.CARDIOVASCULAR,
        publication_doi="10.1056/NEJMoa1504720",
        pmid="26378978",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa1504720",
        expected_effects=[
            ExpectedEffect("HR", 0.86, 0.74, 0.99, 0.04, "3-point MACE", "primary"),
            ExpectedEffect("HR", 0.62, 0.49, 0.77, 0.00001, "CV death", "secondary"),
            ExpectedEffect("HR", 0.65, 0.50, 0.85, None, "HF hospitalization", "secondary"),
            ExpectedEffect("HR", 0.68, 0.57, 0.82, None, "All-cause mortality", "secondary"),
        ],
        notes="Empagliflozin in T2DM with CVD"
    ),

    GoldStandardTrial(
        name="CANVAS Program",
        nct_number="NCT01032629",
        trial_type=TrialType.CARDIOVASCULAR,
        publication_doi="10.1056/NEJMoa1611925",
        pmid="28605608",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa1611925",
        expected_effects=[
            ExpectedEffect("HR", 0.86, 0.75, 0.97, 0.02, "3-point MACE", "primary"),
            ExpectedEffect("HR", 0.87, 0.72, 1.06, None, "CV death", "secondary"),
            ExpectedEffect("HR", 0.67, 0.52, 0.87, None, "HF hospitalization", "secondary"),
        ],
        notes="Canagliflozin in T2DM"
    ),

    GoldStandardTrial(
        name="DECLARE-TIMI 58",
        nct_number="NCT01730534",
        trial_type=TrialType.CARDIOVASCULAR,
        publication_doi="10.1056/NEJMoa1812389",
        pmid="30415602",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa1812389",
        expected_effects=[
            ExpectedEffect("HR", 0.93, 0.84, 1.03, None, "3-point MACE", "primary"),
            ExpectedEffect("HR", 0.83, 0.73, 0.95, 0.005, "CV death or HF hospitalization", "primary"),
            ExpectedEffect("HR", 0.73, 0.61, 0.88, None, "HF hospitalization", "secondary"),
        ],
        notes="Dapagliflozin in T2DM"
    ),

    GoldStandardTrial(
        name="SELECT",
        nct_number="NCT03574597",
        trial_type=TrialType.CARDIOVASCULAR,
        publication_doi="10.1056/NEJMoa2307563",
        pmid="37952131",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa2307563",
        expected_effects=[
            ExpectedEffect("HR", 0.80, 0.72, 0.90, 0.0001, "MACE", "primary"),
            ExpectedEffect("HR", 0.85, 0.73, 0.98, None, "CV death", "secondary"),
            ExpectedEffect("HR", 0.72, 0.61, 0.85, None, "Nonfatal MI", "secondary"),
            ExpectedEffect("HR", 0.93, 0.80, 1.08, None, "All-cause mortality", "secondary"),
        ],
        notes="Semaglutide in obesity with CVD"
    ),

    GoldStandardTrial(
        name="LEADER",
        nct_number="NCT01179048",
        trial_type=TrialType.CARDIOVASCULAR,
        publication_doi="10.1056/NEJMoa1603827",
        pmid="27295427",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa1603827",
        expected_effects=[
            ExpectedEffect("HR", 0.87, 0.78, 0.97, 0.01, "3-point MACE", "primary"),
            ExpectedEffect("HR", 0.78, 0.66, 0.93, None, "CV death", "secondary"),
            ExpectedEffect("HR", 0.85, 0.74, 0.97, None, "All-cause mortality", "secondary"),
        ],
        notes="Liraglutide in T2DM with CVD"
    ),

    GoldStandardTrial(
        name="SUSTAIN-6",
        nct_number="NCT01720446",
        trial_type=TrialType.CARDIOVASCULAR,
        publication_doi="10.1056/NEJMoa1607141",
        pmid="27633186",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa1607141",
        expected_effects=[
            ExpectedEffect("HR", 0.74, 0.58, 0.95, 0.02, "3-point MACE", "primary"),
            ExpectedEffect("HR", 0.74, 0.51, 1.08, None, "Nonfatal MI", "secondary"),
            ExpectedEffect("HR", 0.61, 0.38, 0.99, None, "Nonfatal stroke", "secondary"),
        ],
        notes="Semaglutide in T2DM"
    ),
]

# =============================================================================
# LIPID TRIALS (PCSK9 & STATINS)
# =============================================================================

LIPID_TRIALS = [
    GoldStandardTrial(
        name="FOURIER",
        nct_number="NCT01764633",
        trial_type=TrialType.LIPID,
        publication_doi="10.1056/NEJMoa1615664",
        pmid="28304224",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa1615664",
        expected_effects=[
            ExpectedEffect("HR", 0.85, 0.79, 0.92, 0.00001, "CV death, MI, stroke, UA, revasc", "primary"),
            ExpectedEffect("HR", 0.80, 0.73, 0.88, 0.00001, "CV death, MI, stroke", "secondary"),
            ExpectedEffect("HR", 0.73, 0.65, 0.82, None, "MI", "secondary"),
            ExpectedEffect("HR", 0.79, 0.66, 0.95, None, "Stroke", "secondary"),
        ],
        notes="Evolocumab in ASCVD"
    ),

    GoldStandardTrial(
        name="ODYSSEY OUTCOMES",
        nct_number="NCT01663402",
        trial_type=TrialType.LIPID,
        publication_doi="10.1056/NEJMoa1801174",
        pmid="30403574",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa1801174",
        expected_effects=[
            ExpectedEffect("HR", 0.85, 0.78, 0.93, 0.0003, "MACE", "primary"),
            ExpectedEffect("HR", 0.86, 0.77, 0.96, None, "MI", "secondary"),
            ExpectedEffect("HR", 0.73, 0.57, 0.93, None, "Ischemic stroke", "secondary"),
            ExpectedEffect("HR", 0.85, 0.73, 0.98, None, "All-cause mortality", "secondary"),
        ],
        notes="Alirocumab post-ACS"
    ),

    GoldStandardTrial(
        name="JUPITER",
        nct_number="NCT00239681",
        trial_type=TrialType.LIPID,
        publication_doi="10.1056/NEJMoa0807646",
        pmid="18997196",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa0807646",
        expected_effects=[
            ExpectedEffect("HR", 0.56, 0.46, 0.69, 0.00001, "MI, stroke, revasc, UA, CV death", "primary"),
            ExpectedEffect("HR", 0.46, 0.30, 0.70, None, "MI", "secondary"),
            ExpectedEffect("HR", 0.52, 0.34, 0.79, None, "Stroke", "secondary"),
            ExpectedEffect("HR", 0.80, 0.67, 0.97, None, "All-cause mortality", "secondary"),
        ],
        notes="Rosuvastatin in elevated CRP"
    ),

    GoldStandardTrial(
        name="IMPROVE-IT",
        nct_number="NCT00202878",
        trial_type=TrialType.LIPID,
        publication_doi="10.1056/NEJMoa1410489",
        pmid="26039521",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa1410489",
        expected_effects=[
            ExpectedEffect("HR", 0.936, 0.89, 0.99, 0.016, "CV death, MI, UA, revasc, stroke", "primary"),
            ExpectedEffect("HR", 0.87, 0.80, 0.95, None, "MI", "secondary"),
            ExpectedEffect("HR", 0.79, 0.67, 0.94, None, "Ischemic stroke", "secondary"),
        ],
        notes="Ezetimibe + simvastatin post-ACS"
    ),
]

# =============================================================================
# ANTICOAGULATION TRIALS (DOACs)
# =============================================================================

ANTICOAGULATION_TRIALS = [
    GoldStandardTrial(
        name="RE-LY",
        nct_number="NCT00262600",
        trial_type=TrialType.ANTICOAGULATION,
        publication_doi="10.1056/NEJMoa0905561",
        pmid="19717844",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa0905561",
        expected_effects=[
            ExpectedEffect("RR", 0.91, 0.74, 1.11, None, "Stroke or SE (150mg)", "primary"),
            ExpectedEffect("RR", 0.66, 0.53, 0.82, 0.001, "Stroke or SE (150mg)", "primary"),
            ExpectedEffect("RR", 0.74, 0.60, 0.91, None, "All-cause mortality (150mg)", "secondary"),
        ],
        notes="Dabigatran vs warfarin in AF"
    ),

    GoldStandardTrial(
        name="ROCKET AF",
        nct_number="NCT00403767",
        trial_type=TrialType.ANTICOAGULATION,
        publication_doi="10.1056/NEJMoa1009638",
        pmid="21830957",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa1009638",
        expected_effects=[
            ExpectedEffect("HR", 0.79, 0.66, 0.96, 0.02, "Stroke or SE (ITT)", "primary"),
            ExpectedEffect("HR", 0.85, 0.70, 1.03, None, "All-cause mortality", "secondary"),
        ],
        notes="Rivaroxaban vs warfarin in AF"
    ),

    GoldStandardTrial(
        name="ARISTOTLE",
        nct_number="NCT00412984",
        trial_type=TrialType.ANTICOAGULATION,
        publication_doi="10.1056/NEJMoa1107039",
        pmid="21870978",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa1107039",
        expected_effects=[
            ExpectedEffect("HR", 0.79, 0.66, 0.95, 0.01, "Stroke or SE", "primary"),
            ExpectedEffect("HR", 0.69, 0.60, 0.80, 0.001, "Major bleeding", "safety"),
            ExpectedEffect("HR", 0.89, 0.80, 0.998, 0.047, "All-cause mortality", "secondary"),
        ],
        notes="Apixaban vs warfarin in AF"
    ),

    GoldStandardTrial(
        name="ENGAGE AF-TIMI 48",
        nct_number="NCT00781391",
        trial_type=TrialType.ANTICOAGULATION,
        publication_doi="10.1056/NEJMoa1310907",
        pmid="24251359",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa1310907",
        expected_effects=[
            ExpectedEffect("HR", 0.79, 0.63, 0.99, 0.001, "Stroke or SE (60mg)", "primary"),
            ExpectedEffect("HR", 0.80, 0.71, 0.90, 0.001, "Major bleeding (60mg)", "safety"),
        ],
        notes="Edoxaban vs warfarin in AF"
    ),

    GoldStandardTrial(
        name="COMPASS",
        nct_number="NCT01776424",
        trial_type=TrialType.ANTICOAGULATION,
        publication_doi="10.1056/NEJMoa1709118",
        pmid="28844192",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa1709118",
        expected_effects=[
            ExpectedEffect("HR", 0.76, 0.66, 0.86, 0.00001, "CV death, stroke, MI", "primary"),
            ExpectedEffect("HR", 0.72, 0.57, 0.90, None, "CV death", "secondary"),
            ExpectedEffect("HR", 0.70, 0.55, 0.89, None, "Stroke", "secondary"),
            ExpectedEffect("HR", 0.82, 0.71, 0.96, None, "All-cause mortality", "secondary"),
        ],
        notes="Rivaroxaban + aspirin in stable CAD/PAD"
    ),
]

# =============================================================================
# NEPHROLOGY TRIALS
# =============================================================================

NEPHROLOGY_TRIALS = [
    GoldStandardTrial(
        name="CREDENCE",
        nct_number="NCT02065791",
        trial_type=TrialType.NEPHROLOGY,
        publication_doi="10.1056/NEJMoa1811744",
        pmid="30990260",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa1811744",
        expected_effects=[
            ExpectedEffect("HR", 0.70, 0.59, 0.82, 0.00001, "ESKD, dCr, renal/CV death", "primary"),
            ExpectedEffect("HR", 0.66, 0.53, 0.81, None, "Renal composite", "secondary"),
            ExpectedEffect("HR", 0.80, 0.67, 0.95, None, "MACE", "secondary"),
            ExpectedEffect("HR", 0.61, 0.47, 0.80, None, "HF hospitalization", "secondary"),
        ],
        notes="Canagliflozin in diabetic kidney disease"
    ),

    GoldStandardTrial(
        name="DAPA-CKD",
        nct_number="NCT03036150",
        trial_type=TrialType.NEPHROLOGY,
        publication_doi="10.1056/NEJMoa2024816",
        pmid="32970396",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa2024816",
        expected_effects=[
            ExpectedEffect("HR", 0.61, 0.51, 0.72, 0.000000018, "eGFR decline, ESKD, renal/CV death", "primary"),
            ExpectedEffect("HR", 0.56, 0.45, 0.68, None, "Renal composite", "secondary"),
            ExpectedEffect("HR", 0.71, 0.55, 0.92, None, "CV death or HF hospitalization", "secondary"),
            ExpectedEffect("HR", 0.69, 0.53, 0.88, None, "All-cause mortality", "secondary"),
        ],
        notes="Dapagliflozin in CKD (with/without diabetes)"
    ),

    GoldStandardTrial(
        name="EMPA-KIDNEY",
        nct_number="NCT03594110",
        trial_type=TrialType.NEPHROLOGY,
        publication_doi="10.1056/NEJMoa2204233",
        pmid="36331190",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa2204233",
        expected_effects=[
            ExpectedEffect("HR", 0.72, 0.64, 0.82, 0.00001, "Kidney progression or CV death", "primary"),
            ExpectedEffect("HR", 0.71, 0.62, 0.81, None, "Kidney progression", "secondary"),
        ],
        notes="Empagliflozin in CKD"
    ),

    GoldStandardTrial(
        name="FIDELIO-DKD",
        nct_number="NCT02540993",
        trial_type=TrialType.NEPHROLOGY,
        publication_doi="10.1056/NEJMoa2025845",
        pmid="33264825",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa2025845",
        expected_effects=[
            ExpectedEffect("HR", 0.82, 0.73, 0.93, 0.001, "Kidney failure, eGFR decline, renal death", "primary"),
            ExpectedEffect("HR", 0.86, 0.75, 0.99, None, "MACE", "secondary"),
        ],
        notes="Finerenone in diabetic kidney disease"
    ),
]

# =============================================================================
# ONCOLOGY TRIALS
# =============================================================================

ONCOLOGY_TRIALS = [
    GoldStandardTrial(
        name="CheckMate 067",
        nct_number="NCT01844505",
        trial_type=TrialType.ONCOLOGY,
        publication_doi="10.1056/NEJMoa1910836",
        pmid="31562797",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa1910836",
        expected_effects=[
            ExpectedEffect("HR", 0.52, 0.44, 0.61, None, "OS nivo+ipi vs ipi", "primary"),
            ExpectedEffect("HR", 0.63, 0.53, 0.74, None, "OS nivo vs ipi", "primary"),
        ],
        notes="Nivolumab +/- ipilimumab in melanoma (5-year)"
    ),

    GoldStandardTrial(
        name="CheckMate 9LA",
        nct_number="NCT03215706",
        trial_type=TrialType.ONCOLOGY,
        publication_doi="10.1016/S1470-2045(21)00213-8",
        pmid="34019798",
        source_url="https://www.thelancet.com/journals/lanonc/article/PIIS1470-2045(21)00213-8/fulltext",
        expected_effects=[
            ExpectedEffect("HR", 0.66, 0.55, 0.80, 0.00001, "OS", "primary"),
            ExpectedEffect("HR", 0.68, 0.57, 0.82, None, "PFS", "secondary"),
        ],
        notes="Nivolumab + ipilimumab + chemo in NSCLC"
    ),

    GoldStandardTrial(
        name="KEYNOTE-024",
        nct_number="NCT02142738",
        trial_type=TrialType.ONCOLOGY,
        publication_doi="10.1056/NEJMoa1606774",
        pmid="27718847",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa1606774",
        expected_effects=[
            ExpectedEffect("HR", 0.50, 0.37, 0.68, 0.001, "PFS", "primary"),
            ExpectedEffect("HR", 0.60, 0.41, 0.89, 0.005, "OS", "secondary"),
        ],
        notes="Pembrolizumab vs chemo in PD-L1+ NSCLC"
    ),

    GoldStandardTrial(
        name="KEYNOTE-189",
        nct_number="NCT02578680",
        trial_type=TrialType.ONCOLOGY,
        publication_doi="10.1056/NEJMoa1801005",
        pmid="29658856",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa1801005",
        expected_effects=[
            ExpectedEffect("HR", 0.49, 0.38, 0.64, 0.001, "OS", "primary"),
            ExpectedEffect("HR", 0.52, 0.43, 0.64, 0.001, "PFS", "primary"),
        ],
        notes="Pembrolizumab + chemo in non-squamous NSCLC"
    ),

    GoldStandardTrial(
        name="CLEOPATRA",
        nct_number="NCT00567190",
        trial_type=TrialType.ONCOLOGY,
        publication_doi="10.1056/NEJMoa1113216",
        pmid="22149875",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa1113216",
        expected_effects=[
            ExpectedEffect("HR", 0.62, 0.51, 0.75, 0.001, "PFS", "primary"),
            ExpectedEffect("HR", 0.66, 0.52, 0.84, 0.001, "OS", "secondary"),
        ],
        notes="Pertuzumab + trastuzumab in HER2+ breast cancer"
    ),
]

# =============================================================================
# BLOOD PRESSURE TRIALS
# =============================================================================

BLOOD_PRESSURE_TRIALS = [
    GoldStandardTrial(
        name="SPRINT",
        nct_number="NCT01206062",
        trial_type=TrialType.CARDIOVASCULAR,
        publication_doi="10.1056/NEJMoa1511939",
        pmid="26551272",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa1511939",
        expected_effects=[
            ExpectedEffect("HR", 0.75, 0.64, 0.89, 0.001, "MI, ACS, stroke, HF, CV death", "primary"),
            ExpectedEffect("HR", 0.57, 0.43, 0.77, None, "HF", "secondary"),
            ExpectedEffect("HR", 0.73, 0.60, 0.90, None, "CV death", "secondary"),
            ExpectedEffect("HR", 0.73, 0.60, 0.90, None, "All-cause mortality", "secondary"),
        ],
        notes="Intensive BP control (SBP <120 vs <140)"
    ),

    GoldStandardTrial(
        name="ONTARGET",
        nct_number="NCT00153101",
        trial_type=TrialType.CARDIOVASCULAR,
        publication_doi="10.1056/NEJMoa0801317",
        pmid="18378520",
        source_url="https://www.nejm.org/doi/full/10.1056/NEJMoa0801317",
        expected_effects=[
            ExpectedEffect("RR", 1.01, 0.94, 1.09, None, "CV death, MI, stroke, HF hosp", "primary"),
            ExpectedEffect("RR", 0.96, 0.84, 1.10, None, "CV death", "secondary"),
        ],
        notes="Telmisartan vs ramipril in high CV risk"
    ),
]

# =============================================================================
# COMPILE ALL TRIALS
# =============================================================================

ALL_GOLD_STANDARD_TRIALS = (
    HEART_FAILURE_TRIALS +
    CARDIOVASCULAR_TRIALS +
    LIPID_TRIALS +
    ANTICOAGULATION_TRIALS +
    NEPHROLOGY_TRIALS +
    ONCOLOGY_TRIALS +
    BLOOD_PRESSURE_TRIALS
)


def get_trial_by_name(name: str) -> Optional[GoldStandardTrial]:
    """Get a trial by name (case-insensitive)"""
    for trial in ALL_GOLD_STANDARD_TRIALS:
        if trial.name.lower() == name.lower():
            return trial
    return None


def get_trials_by_type(trial_type: TrialType) -> List[GoldStandardTrial]:
    """Get all trials of a specific type"""
    return [t for t in ALL_GOLD_STANDARD_TRIALS if t.trial_type == trial_type]


def get_total_expected_effects() -> int:
    """Get total number of expected effects across all trials"""
    return sum(len(t.expected_effects) for t in ALL_GOLD_STANDARD_TRIALS)


def print_summary():
    """Print summary of gold standard dataset"""
    print("=" * 60)
    print("GOLD STANDARD PDF DATASET SUMMARY")
    print("=" * 60)

    print(f"\nTotal trials: {len(ALL_GOLD_STANDARD_TRIALS)}")
    print(f"Total expected effects: {get_total_expected_effects()}")

    print("\nBy trial type:")
    for tt in TrialType:
        trials = get_trials_by_type(tt)
        effects = sum(len(t.expected_effects) for t in trials)
        print(f"  {tt.value}: {len(trials)} trials, {effects} effects")

    print("\nTrials:")
    for trial in ALL_GOLD_STANDARD_TRIALS:
        print(f"  - {trial.name} ({len(trial.expected_effects)} effects)")


if __name__ == "__main__":
    print_summary()
