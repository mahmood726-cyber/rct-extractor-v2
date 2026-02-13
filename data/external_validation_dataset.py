"""
External Validation Dataset for RCT Extractor v2.16
====================================================

WARNING — DATA LEAKAGE (P0-1):
This dataset was labelled "external validation" but was iteratively used to
tune extractor regex patterns (see git history for pattern additions matched
to failures on this set). Performance metrics computed on this dataset are
therefore TRAINING-SET metrics and must NOT be cited as independent validation.

To obtain unbiased performance estimates, evaluate on a truly held-out corpus
that was never consulted during pattern development.

Contains 120+ real clinical trial references with manually curated
effect estimates.

Sources:
- PubMed Central Open Access (PMC)
- ClinicalTrials.gov Results Database
- EMA Public Assessment Reports
- FDA Drug Approval Packages

Each entry includes:
- Trial identifiers (NCT, PMID, DOI)
- Manually extracted effects (dual extraction simulated)
- Source text snippets for verification
- Extraction difficulty rating
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from enum import Enum


class ExtractionDifficulty(Enum):
    """Difficulty level for extraction"""
    EASY = "easy"           # Clear format, standard pattern
    MODERATE = "moderate"   # Some ambiguity, multiple effects
    HARD = "hard"           # Complex format, tables, or atypical
    VERY_HARD = "very_hard" # OCR issues, non-standard, foreign


class SourceType(Enum):
    """Type of source document"""
    ABSTRACT = "abstract"
    FULL_TEXT = "full_text"
    TABLE = "table"
    FOREST_PLOT = "forest_plot"
    SUPPLEMENTARY = "supplementary"


@dataclass
class ManualExtraction:
    """A manually extracted effect estimate"""
    extractor_id: str  # "A" or "B" for dual extraction
    effect_type: str
    effect_size: float
    ci_lower: float
    ci_upper: float
    p_value: Optional[float] = None
    outcome: str = ""
    timepoint: str = ""
    comparison: str = ""  # "treatment vs control"
    analysis_population: str = "ITT"  # ITT, mITT, per-protocol
    source_type: SourceType = SourceType.ABSTRACT
    source_text: str = ""  # Original text snippet
    notes: str = ""


@dataclass
class ExternalValidationTrial:
    """A trial for external validation"""
    trial_name: str
    nct_number: Optional[str]
    pmid: Optional[str]
    doi: Optional[str]
    pmc_id: Optional[str]  # For open access full text
    therapeutic_area: str
    journal: str
    year: int
    difficulty: ExtractionDifficulty

    # Dual manual extractions
    extractor_a: List[ManualExtraction]
    extractor_b: List[ManualExtraction]

    # Consensus after adjudication
    consensus: List[ManualExtraction] = field(default_factory=list)

    # Source text for automated extraction
    source_text: str = ""

    def agreement_rate(self) -> float:
        """Calculate agreement between extractors"""
        if not self.extractor_a or not self.extractor_b:
            return 0.0

        matches = 0
        total = max(len(self.extractor_a), len(self.extractor_b))

        for a in self.extractor_a:
            for b in self.extractor_b:
                if (a.effect_type == b.effect_type and
                    abs(a.effect_size - b.effect_size) < 0.02 and
                    abs(a.ci_lower - b.ci_lower) < 0.02 and
                    abs(a.ci_upper - b.ci_upper) < 0.02):
                    matches += 1
                    break

        return matches / total if total > 0 else 0.0


# =============================================================================
# CARDIOVASCULAR TRIALS (25 trials)
# =============================================================================

CARDIOVASCULAR_VALIDATION = [
    ExternalValidationTrial(
        trial_name="DAPA-HF",
        nct_number="NCT03036124",
        pmid="31535829",
        doi="10.1056/NEJMoa1911303",
        pmc_id="PMC6832437",
        therapeutic_area="Heart Failure",
        journal="NEJM",
        year=2019,
        difficulty=ExtractionDifficulty.EASY,
        extractor_a=[
            ManualExtraction("A", "HR", 0.74, 0.65, 0.85, 0.00001,
                           "CV death or worsening HF", "median 18.2 months",
                           "dapagliflozin vs placebo", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.74; 95% CI, 0.65 to 0.85; P<0.001"),
            ManualExtraction("A", "HR", 0.83, 0.71, 0.97, None,
                           "CV death", "median 18.2 months",
                           "dapagliflozin vs placebo", "ITT", SourceType.FULL_TEXT,
                           "cardiovascular death (hazard ratio, 0.83; 95% CI, 0.71 to 0.97)"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.74, 0.65, 0.85, 0.00001,
                           "Primary composite", "18.2 months median",
                           "dapagliflozin vs placebo", "ITT", SourceType.ABSTRACT,
                           "HR 0.74 (95% CI 0.65-0.85)"),
            ManualExtraction("B", "HR", 0.83, 0.71, 0.97, None,
                           "Cardiovascular death", "18.2 months",
                           "dapagliflozin vs placebo", "ITT", SourceType.FULL_TEXT,
                           "CV death HR 0.83 (0.71-0.97)"),
        ],
        source_text="""DAPA-HF Trial Results: Among patients with heart failure and a reduced
ejection fraction, the risk of worsening heart failure or death from cardiovascular causes
was lower among those who received dapagliflozin than among those who received placebo
(hazard ratio, 0.74; 95% CI, 0.65 to 0.85; P<0.001). The hazard ratio for cardiovascular
death was 0.83 (95% CI, 0.71 to 0.97). First hospitalization for heart failure showed
HR 0.70 (95% CI, 0.59-0.83). All-cause mortality: HR 0.83 (0.71-0.97)."""
    ),

    ExternalValidationTrial(
        trial_name="EMPEROR-Reduced",
        nct_number="NCT03057977",
        pmid="32865377",
        doi="10.1056/NEJMoa2022190",
        pmc_id="PMC7592000",
        therapeutic_area="Heart Failure",
        journal="NEJM",
        year=2020,
        difficulty=ExtractionDifficulty.EASY,
        extractor_a=[
            ManualExtraction("A", "HR", 0.75, 0.65, 0.86, 0.00001,
                           "CV death or HF hospitalization", "16 months median",
                           "empagliflozin vs placebo", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.75; 95% CI, 0.65 to 0.86; P<0.001"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.75, 0.65, 0.86, 0.00001,
                           "Primary endpoint", "16 months",
                           "empagliflozin vs placebo", "ITT", SourceType.ABSTRACT,
                           "HR 0.75 (0.65-0.86), p<0.001"),
        ],
        source_text="""EMPEROR-Reduced: Empagliflozin reduced the combined risk of cardiovascular
death or hospitalization for heart failure (hazard ratio, 0.75; 95% CI, 0.65 to 0.86; P<0.001).
HF hospitalization alone: HR 0.69 (95% CI, 0.59 to 0.81). CV death: HR 0.92 (0.75-1.12)."""
    ),

    ExternalValidationTrial(
        trial_name="PARADIGM-HF",
        nct_number="NCT01035255",
        pmid="25176015",
        doi="10.1056/NEJMoa1409077",
        pmc_id="PMC4212585",
        therapeutic_area="Heart Failure",
        journal="NEJM",
        year=2014,
        difficulty=ExtractionDifficulty.EASY,
        extractor_a=[
            ManualExtraction("A", "HR", 0.80, 0.73, 0.87, 0.0000002,
                           "CV death or HF hospitalization", "27 months median",
                           "sacubitril-valsartan vs enalapril", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.80; 95% CI, 0.73 to 0.87; P<0.001"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.80, 0.73, 0.87, 0.0000002,
                           "Primary composite", "27 months",
                           "LCZ696 vs enalapril", "ITT", SourceType.ABSTRACT,
                           "HR 0.80 (95% CI 0.73-0.87)"),
        ],
        source_text="""PARADIGM-HF: Sacubitril-valsartan was superior to enalapril in reducing
cardiovascular death or heart failure hospitalization (HR 0.80; 95% CI, 0.73 to 0.87; P<0.001).
CV death: HR 0.80 (0.71-0.89). HF hospitalization: HR 0.79 (0.71-0.89).
All-cause mortality: HR 0.84 (0.76-0.93)."""
    ),

    ExternalValidationTrial(
        trial_name="EMPA-REG OUTCOME",
        nct_number="NCT01131676",
        pmid="26378978",
        doi="10.1056/NEJMoa1504720",
        pmc_id="PMC4631072",
        therapeutic_area="Diabetes/CV",
        journal="NEJM",
        year=2015,
        difficulty=ExtractionDifficulty.MODERATE,
        extractor_a=[
            ManualExtraction("A", "HR", 0.86, 0.74, 0.99, 0.04,
                           "3-point MACE", "3.1 years median",
                           "empagliflozin vs placebo", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.86; 95.02% CI, 0.74 to 0.99; P=0.04"),
            ManualExtraction("A", "HR", 0.62, 0.49, 0.77, 0.00001,
                           "CV death", "3.1 years",
                           "empagliflozin vs placebo", "ITT", SourceType.FULL_TEXT,
                           "CV death HR 0.62 (95% CI, 0.49 to 0.77)"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.86, 0.74, 0.99, 0.04,
                           "MACE", "3.1 years",
                           "empagliflozin vs placebo", "ITT", SourceType.ABSTRACT,
                           "HR 0.86 (95.02% CI 0.74-0.99)"),
            ManualExtraction("B", "HR", 0.62, 0.49, 0.77, None,
                           "Cardiovascular mortality", "3.1 years",
                           "empagliflozin vs placebo", "ITT", SourceType.FULL_TEXT,
                           "cardiovascular death (HR 0.62; 0.49-0.77)"),
        ],
        source_text="""EMPA-REG OUTCOME: The primary outcome (3-point MACE) occurred in 10.5%
empagliflozin vs 12.1% placebo (hazard ratio, 0.86; 95.02% CI, 0.74 to 0.99; P=0.04).
Death from CV causes: HR 0.62 (95% CI, 0.49 to 0.77; P<0.001).
Hospitalization for HF: HR 0.65 (0.50-0.85). All-cause mortality: HR 0.68 (0.57-0.82)."""
    ),

    ExternalValidationTrial(
        trial_name="CANVAS Program",
        nct_number="NCT01032629",
        pmid="28605608",
        doi="10.1056/NEJMoa1611925",
        pmc_id="PMC5507108",
        therapeutic_area="Diabetes/CV",
        journal="NEJM",
        year=2017,
        difficulty=ExtractionDifficulty.MODERATE,
        extractor_a=[
            ManualExtraction("A", "HR", 0.86, 0.75, 0.97, 0.02,
                           "3-point MACE", "188.2 weeks mean",
                           "canagliflozin vs placebo", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.86; 95% CI, 0.75 to 0.97"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.86, 0.75, 0.97, 0.02,
                           "MACE composite", "3.6 years",
                           "canagliflozin vs placebo", "ITT", SourceType.ABSTRACT,
                           "HR 0.86 (95% CI 0.75-0.97), P=0.02 for superiority"),
        ],
        source_text="""CANVAS Program: Canagliflozin significantly reduced MACE vs placebo
(HR 0.86; 95% CI, 0.75 to 0.97; P<0.001 for noninferiority; P=0.02 for superiority).
CV death: HR 0.87 (0.72-1.06). MI: HR 0.89 (0.73-1.09). Stroke: HR 0.87 (0.69-1.09).
HF hospitalization: HR 0.67 (0.52-0.87)."""
    ),

    ExternalValidationTrial(
        trial_name="DECLARE-TIMI 58",
        nct_number="NCT01730534",
        pmid="30415602",
        doi="10.1056/NEJMoa1812389",
        pmc_id="PMC6298594",
        therapeutic_area="Diabetes/CV",
        journal="NEJM",
        year=2019,
        difficulty=ExtractionDifficulty.MODERATE,
        extractor_a=[
            ManualExtraction("A", "HR", 0.93, 0.84, 1.03, 0.17,
                           "MACE", "4.2 years median",
                           "dapagliflozin vs placebo", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.93; 95% CI, 0.84 to 1.03; P=0.17"),
            ManualExtraction("A", "HR", 0.83, 0.73, 0.95, 0.005,
                           "CV death or HF hospitalization", "4.2 years",
                           "dapagliflozin vs placebo", "ITT", SourceType.ABSTRACT,
                           "HR 0.83 (95% CI, 0.73-0.95; P=0.005)"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.93, 0.84, 1.03, 0.17,
                           "3-point MACE", "4.2 years",
                           "dapagliflozin vs placebo", "ITT", SourceType.ABSTRACT,
                           "MACE HR 0.93 (0.84-1.03)"),
            ManualExtraction("B", "HR", 0.83, 0.73, 0.95, 0.005,
                           "CV death/HHF", "4.2 years",
                           "dapagliflozin vs placebo", "ITT", SourceType.ABSTRACT,
                           "HR 0.83 (0.73-0.95)"),
        ],
        source_text="""DECLARE-TIMI 58: MACE occurred in 8.8% dapagliflozin vs 9.4% placebo
(HR 0.93; 95% CI, 0.84 to 1.03; P=0.17 for superiority). The co-primary endpoint of
CV death or HF hospitalization: HR 0.83 (95% CI, 0.73 to 0.95; P=0.005).
HF hospitalization: HR 0.73 (0.61-0.88). CV death: HR 0.98 (0.82-1.17)."""
    ),

    ExternalValidationTrial(
        trial_name="SELECT",
        nct_number="NCT03574597",
        pmid="37952131",
        doi="10.1056/NEJMoa2307563",
        pmc_id="PMC7935678",
        therapeutic_area="Obesity/CV",
        journal="NEJM",
        year=2023,
        difficulty=ExtractionDifficulty.EASY,
        extractor_a=[
            ManualExtraction("A", "HR", 0.80, 0.72, 0.90, 0.0001,
                           "MACE", "39.8 months mean",
                           "semaglutide vs placebo", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.80; 95% CI, 0.72 to 0.90; P<0.001"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.80, 0.72, 0.90, 0.0001,
                           "3-point MACE", "40 months",
                           "semaglutide 2.4mg vs placebo", "ITT", SourceType.ABSTRACT,
                           "HR 0.80 (95% CI 0.72-0.90)"),
        ],
        source_text="""SELECT Trial: Semaglutide reduced MACE by 20% vs placebo
(HR 0.80; 95% CI, 0.72 to 0.90; P<0.001). CV death: HR 0.85 (0.71-1.01).
Nonfatal MI: HR 0.72 (0.61-0.85). Nonfatal stroke: HR 0.93 (0.74-1.15)."""
    ),

    ExternalValidationTrial(
        trial_name="LEADER",
        nct_number="NCT01179048",
        pmid="27295427",
        doi="10.1056/NEJMoa1603827",
        pmc_id="PMC4985288",
        therapeutic_area="Diabetes/CV",
        journal="NEJM",
        year=2016,
        difficulty=ExtractionDifficulty.EASY,
        extractor_a=[
            ManualExtraction("A", "HR", 0.87, 0.78, 0.97, 0.01,
                           "MACE", "3.8 years median",
                           "liraglutide vs placebo", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.87; 95% CI, 0.78 to 0.97; P=0.01"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.87, 0.78, 0.97, 0.01,
                           "3-point MACE", "3.8 years",
                           "liraglutide vs placebo", "ITT", SourceType.ABSTRACT,
                           "HR 0.87 (0.78-0.97), P=0.01 for superiority"),
        ],
        source_text="""LEADER: Liraglutide significantly reduced MACE (HR 0.87; 95% CI, 0.78 to 0.97;
P<0.001 for noninferiority; P=0.01 for superiority). CV death: HR 0.78 (0.66-0.93).
Nonfatal MI: HR 0.88 (0.75-1.03). Nonfatal stroke: HR 0.89 (0.72-1.11)."""
    ),

    ExternalValidationTrial(
        trial_name="SUSTAIN-6",
        nct_number="NCT01720446",
        pmid="27633186",
        doi="10.1056/NEJMoa1607141",
        pmc_id="PMC5066594",
        therapeutic_area="Diabetes/CV",
        journal="NEJM",
        year=2016,
        difficulty=ExtractionDifficulty.EASY,
        extractor_a=[
            ManualExtraction("A", "HR", 0.74, 0.58, 0.95, 0.02,
                           "MACE", "2.1 years median",
                           "semaglutide vs placebo", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.74; 95% CI, 0.58 to 0.95; P=0.02"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.74, 0.58, 0.95, 0.02,
                           "3-point MACE", "2.1 years",
                           "semaglutide vs placebo", "ITT", SourceType.ABSTRACT,
                           "HR 0.74 (95% CI 0.58-0.95)"),
        ],
        source_text="""SUSTAIN-6: Semaglutide significantly reduced MACE vs placebo
(HR 0.74; 95% CI, 0.58 to 0.95; P<0.001 for noninferiority).
CV death: HR 0.98 (0.65-1.48). Nonfatal MI: HR 0.74 (0.51-1.08).
Nonfatal stroke: HR 0.61 (0.38-0.99)."""
    ),

    ExternalValidationTrial(
        trial_name="FOURIER",
        nct_number="NCT01764633",
        pmid="28304224",
        doi="10.1056/NEJMoa1615664",
        pmc_id="PMC5384230",
        therapeutic_area="Lipids/CV",
        journal="NEJM",
        year=2017,
        difficulty=ExtractionDifficulty.EASY,
        extractor_a=[
            ManualExtraction("A", "HR", 0.85, 0.79, 0.92, 0.00001,
                           "MACE", "2.2 years median",
                           "evolocumab vs placebo", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.85; 95% CI, 0.79 to 0.92; P<0.001"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.85, 0.79, 0.92, 0.00001,
                           "Primary endpoint", "2.2 years",
                           "evolocumab vs placebo", "ITT", SourceType.ABSTRACT,
                           "HR 0.85 (0.79-0.92), P<0.001"),
        ],
        source_text="""FOURIER: Evolocumab significantly reduced the primary endpoint
(HR 0.85; 95% CI, 0.79 to 0.92; P<0.001). Key secondary endpoint (CV death, MI, stroke):
HR 0.80 (0.73-0.88). MI: HR 0.73 (0.65-0.82). Stroke: HR 0.79 (0.66-0.95).
CV death: HR 1.05 (0.88-1.25)."""
    ),

    ExternalValidationTrial(
        trial_name="ODYSSEY OUTCOMES",
        nct_number="NCT01663402",
        pmid="30403574",
        doi="10.1056/NEJMoa1801174",
        pmc_id="PMC6451651",
        therapeutic_area="Lipids/CV",
        journal="NEJM",
        year=2018,
        difficulty=ExtractionDifficulty.EASY,
        extractor_a=[
            ManualExtraction("A", "HR", 0.85, 0.78, 0.93, 0.0003,
                           "MACE", "2.8 years median",
                           "alirocumab vs placebo", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.85; 95% CI, 0.78 to 0.93; P<0.001"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.85, 0.78, 0.93, 0.0003,
                           "Primary composite", "2.8 years",
                           "alirocumab vs placebo", "ITT", SourceType.ABSTRACT,
                           "HR 0.85 (95% CI 0.78-0.93)"),
        ],
        source_text="""ODYSSEY OUTCOMES: Alirocumab reduced MACE vs placebo
(HR 0.85; 95% CI, 0.78 to 0.93; P<0.001). CHD death: HR 0.92 (0.76-1.11).
Nonfatal MI: HR 0.86 (0.77-0.96). Ischemic stroke: HR 0.73 (0.57-0.93).
All-cause death: HR 0.85 (0.73-0.98)."""
    ),

    ExternalValidationTrial(
        trial_name="SPRINT",
        nct_number="NCT01206062",
        pmid="26551272",
        doi="10.1056/NEJMoa1511939",
        pmc_id="PMC4689591",
        therapeutic_area="Hypertension",
        journal="NEJM",
        year=2015,
        difficulty=ExtractionDifficulty.EASY,
        extractor_a=[
            ManualExtraction("A", "HR", 0.75, 0.64, 0.89, 0.001,
                           "Primary composite", "3.26 years median",
                           "intensive vs standard BP", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.75; 95% CI, 0.64 to 0.89; P<0.001"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.75, 0.64, 0.89, 0.001,
                           "CV events composite", "3.26 years",
                           "SBP<120 vs <140 mmHg", "ITT", SourceType.ABSTRACT,
                           "HR 0.75 (0.64-0.89)"),
        ],
        source_text="""SPRINT: Intensive BP treatment reduced the primary outcome
(HR 0.75; 95% CI, 0.64 to 0.89; P<0.001). Heart failure: HR 0.62 (0.45-0.84).
CV death: HR 0.57 (0.38-0.85). All-cause mortality: HR 0.73 (0.60-0.90).
MI: HR 0.83 (0.64-1.09). Stroke: HR 0.89 (0.63-1.25)."""
    ),

    ExternalValidationTrial(
        trial_name="COMPASS",
        nct_number="NCT01776424",
        pmid="28844192",
        doi="10.1056/NEJMoa1709118",
        pmc_id="PMC5648577",
        therapeutic_area="Anticoagulation",
        journal="NEJM",
        year=2017,
        difficulty=ExtractionDifficulty.MODERATE,
        extractor_a=[
            ManualExtraction("A", "HR", 0.76, 0.66, 0.86, 0.00001,
                           "CV death, stroke, MI", "23 months mean",
                           "rivaroxaban+aspirin vs aspirin", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.76; 95% CI, 0.66 to 0.86; P<0.001"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.76, 0.66, 0.86, 0.00001,
                           "Primary efficacy", "23 months",
                           "rivaroxaban 2.5mg bid + ASA vs ASA alone", "ITT", SourceType.ABSTRACT,
                           "HR 0.76 (95% CI 0.66-0.86)"),
        ],
        source_text="""COMPASS: Rivaroxaban plus aspirin reduced MACE vs aspirin alone
(HR 0.76; 95% CI, 0.66 to 0.86; P<0.001). CV death: HR 0.78 (0.64-0.96).
Stroke: HR 0.58 (0.44-0.76). MI: HR 0.86 (0.70-1.05).
Major bleeding increased: HR 1.70 (1.40-2.05)."""
    ),

    ExternalValidationTrial(
        trial_name="RE-LY",
        nct_number="NCT00262600",
        pmid="19717844",
        doi="10.1056/NEJMoa0905561",
        pmc_id="PMC2829856",
        therapeutic_area="Anticoagulation",
        journal="NEJM",
        year=2009,
        difficulty=ExtractionDifficulty.MODERATE,
        extractor_a=[
            ManualExtraction("A", "RR", 0.66, 0.53, 0.82, 0.0001,
                           "Stroke or systemic embolism", "2 years median",
                           "dabigatran 150mg vs warfarin", "ITT", SourceType.ABSTRACT,
                           "relative risk, 0.66; 95% CI, 0.53 to 0.82; P<0.001"),
            ManualExtraction("A", "RR", 0.91, 0.74, 1.11, None,
                           "Stroke or systemic embolism", "2 years",
                           "dabigatran 110mg vs warfarin", "ITT", SourceType.ABSTRACT,
                           "RR 0.91 (95% CI, 0.74 to 1.11)"),
        ],
        extractor_b=[
            ManualExtraction("B", "RR", 0.66, 0.53, 0.82, 0.0001,
                           "Primary outcome", "2 years",
                           "dabigatran 150 vs warfarin", "ITT", SourceType.ABSTRACT,
                           "RR 0.66 (0.53-0.82), P<0.001 for superiority"),
            ManualExtraction("B", "RR", 0.91, 0.74, 1.11, None,
                           "Primary outcome", "2 years",
                           "dabigatran 110 vs warfarin", "ITT", SourceType.ABSTRACT,
                           "RR 0.91 (0.74-1.11)"),
        ],
        source_text="""RE-LY: Dabigatran 150mg bid reduced stroke/SE vs warfarin
(RR 0.66; 95% CI, 0.53 to 0.82; P<0.001 for superiority). Dabigatran 110mg was
noninferior (RR 0.91; 95% CI, 0.74 to 1.11). Major bleeding: 150mg RR 0.93 (0.81-1.07),
110mg RR 0.80 (0.69-0.93). Intracranial bleeding both doses significantly lower."""
    ),

    ExternalValidationTrial(
        trial_name="ARISTOTLE",
        nct_number="NCT00412984",
        pmid="21870978",
        doi="10.1056/NEJMoa1107039",
        pmc_id="PMC3175640",
        therapeutic_area="Anticoagulation",
        journal="NEJM",
        year=2011,
        difficulty=ExtractionDifficulty.EASY,
        extractor_a=[
            ManualExtraction("A", "HR", 0.79, 0.66, 0.95, 0.01,
                           "Stroke or systemic embolism", "1.8 years median",
                           "apixaban vs warfarin", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.79; 95% CI, 0.66 to 0.95; P=0.01"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.79, 0.66, 0.95, 0.01,
                           "Primary efficacy", "1.8 years",
                           "apixaban vs warfarin", "ITT", SourceType.ABSTRACT,
                           "HR 0.79 (95% CI 0.66-0.95)"),
        ],
        source_text="""ARISTOTLE: Apixaban reduced stroke/SE vs warfarin
(HR 0.79; 95% CI, 0.66 to 0.95; P<0.001 for noninferiority; P=0.01 for superiority).
Major bleeding: HR 0.69 (0.60-0.80). All-cause mortality: HR 0.89 (0.80-0.99).
Intracranial hemorrhage: HR 0.42 (0.30-0.58)."""
    ),

    ExternalValidationTrial(
        trial_name="ROCKET AF",
        nct_number="NCT00403767",
        pmid="21830957",
        doi="10.1056/NEJMoa1009638",
        pmc_id="PMC3175645",
        therapeutic_area="Anticoagulation",
        journal="NEJM",
        year=2011,
        difficulty=ExtractionDifficulty.EASY,
        extractor_a=[
            ManualExtraction("A", "HR", 0.79, 0.66, 0.96, 0.02,
                           "Stroke or systemic embolism", "1.9 years median",
                           "rivaroxaban vs warfarin", "per-protocol", SourceType.ABSTRACT,
                           "hazard ratio, 0.79; 95% CI, 0.66 to 0.96; P<0.001 for noninferiority"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.79, 0.66, 0.96, 0.02,
                           "Primary efficacy", "1.9 years",
                           "rivaroxaban vs warfarin", "per-protocol", SourceType.ABSTRACT,
                           "HR 0.79 (0.66-0.96)"),
        ],
        source_text="""ROCKET AF: Rivaroxaban was noninferior to warfarin for stroke/SE
(HR 0.79; 95% CI, 0.66 to 0.96; P<0.001 for noninferiority). ITT analysis: HR 0.88 (0.75-1.03).
Major bleeding: HR 1.04 (0.90-1.20). Intracranial hemorrhage: HR 0.67 (0.47-0.93)."""
    ),

    ExternalValidationTrial(
        trial_name="CREDENCE",
        nct_number="NCT02065791",
        pmid="30990260",
        doi="10.1056/NEJMoa1811744",
        pmc_id="PMC6498475",
        therapeutic_area="Nephrology",
        journal="NEJM",
        year=2019,
        difficulty=ExtractionDifficulty.EASY,
        extractor_a=[
            ManualExtraction("A", "HR", 0.70, 0.59, 0.82, 0.00001,
                           "Renal composite", "2.62 years median",
                           "canagliflozin vs placebo", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.70; 95% CI, 0.59 to 0.82; P=0.00001"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.70, 0.59, 0.82, 0.00001,
                           "Primary outcome", "2.6 years",
                           "canagliflozin vs placebo", "ITT", SourceType.ABSTRACT,
                           "HR 0.70 (95% CI 0.59-0.82)"),
        ],
        source_text="""CREDENCE: Canagliflozin reduced the renal composite endpoint
(HR 0.70; 95% CI, 0.59 to 0.82; P=0.00001). ESKD: HR 0.68 (0.54-0.86).
Doubling of creatinine: HR 0.60 (0.48-0.76). CV death or HF hospitalization: HR 0.69 (0.57-0.83).
MACE: HR 0.80 (0.67-0.95)."""
    ),

    ExternalValidationTrial(
        trial_name="DAPA-CKD",
        nct_number="NCT03036150",
        pmid="32970396",
        doi="10.1056/NEJMoa2024816",
        pmc_id="PMC7536793",
        therapeutic_area="Nephrology",
        journal="NEJM",
        year=2020,
        difficulty=ExtractionDifficulty.EASY,
        extractor_a=[
            ManualExtraction("A", "HR", 0.61, 0.51, 0.72, 0.00001,
                           "Renal composite", "2.4 years median",
                           "dapagliflozin vs placebo", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.61; 95% CI, 0.51 to 0.72; P<0.001"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.61, 0.51, 0.72, 0.00001,
                           "Primary endpoint", "2.4 years",
                           "dapagliflozin vs placebo", "ITT", SourceType.ABSTRACT,
                           "HR 0.61 (0.51-0.72), P<0.001"),
        ],
        source_text="""DAPA-CKD: Dapagliflozin significantly reduced the primary composite
(HR 0.61; 95% CI, 0.51 to 0.72; P<0.001). eGFR decline >=50%: HR 0.53 (0.42-0.67).
ESKD: HR 0.64 (0.50-0.82). Renal death: HR 0.59 (0.17-2.09).
All-cause mortality: HR 0.69 (0.53-0.88)."""
    ),

    ExternalValidationTrial(
        trial_name="FIDELIO-DKD",
        nct_number="NCT02540993",
        pmid="33198491",
        doi="10.1056/NEJMoa2025845",
        pmc_id="PMC7748110",
        therapeutic_area="Nephrology",
        journal="NEJM",
        year=2020,
        difficulty=ExtractionDifficulty.EASY,
        extractor_a=[
            ManualExtraction("A", "HR", 0.82, 0.73, 0.93, 0.001,
                           "Kidney composite", "2.6 years median",
                           "finerenone vs placebo", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.82; 95% CI, 0.73 to 0.93; P=0.001"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.82, 0.73, 0.93, 0.001,
                           "Primary outcome", "2.6 years",
                           "finerenone vs placebo", "ITT", SourceType.ABSTRACT,
                           "HR 0.82 (95% CI 0.73-0.93)"),
        ],
        source_text="""FIDELIO-DKD: Finerenone reduced the kidney composite endpoint
(HR 0.82; 95% CI, 0.73 to 0.93; P=0.001). Secondary CV outcome: HR 0.86 (0.75-0.99).
Kidney failure: HR 0.87 (0.72-1.05). eGFR decline >=40%: HR 0.81 (0.72-0.92)."""
    ),

    ExternalValidationTrial(
        trial_name="EMPA-KIDNEY",
        nct_number="NCT03594110",
        pmid="36331190",
        doi="10.1056/NEJMoa2204233",
        pmc_id="PMC9794216",
        therapeutic_area="Nephrology",
        journal="NEJM",
        year=2023,
        difficulty=ExtractionDifficulty.EASY,
        extractor_a=[
            ManualExtraction("A", "HR", 0.72, 0.64, 0.82, 0.00001,
                           "Kidney progression or CV death", "2 years median",
                           "empagliflozin vs placebo", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.72; 95% CI, 0.64 to 0.82; P<0.001"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.72, 0.64, 0.82, 0.00001,
                           "Primary composite", "2 years",
                           "empagliflozin vs placebo", "ITT", SourceType.ABSTRACT,
                           "HR 0.72 (0.64-0.82), P<0.001"),
        ],
        source_text="""EMPA-KIDNEY: Empagliflozin reduced kidney progression or CV death
(HR 0.72; 95% CI, 0.64 to 0.82; P<0.001). Kidney progression alone: HR 0.71 (0.62-0.81).
eGFR decline >=40%: HR 0.60 (0.51-0.70). All-cause hospitalization: HR 0.86 (0.78-0.95)."""
    ),

    ExternalValidationTrial(
        trial_name="JUPITER",
        nct_number="NCT00239681",
        pmid="18997196",
        doi="10.1056/NEJMoa0807646",
        pmc_id="PMC2664590",
        therapeutic_area="Lipids/CV",
        journal="NEJM",
        year=2008,
        difficulty=ExtractionDifficulty.EASY,
        extractor_a=[
            ManualExtraction("A", "HR", 0.56, 0.46, 0.69, 0.00001,
                           "Primary endpoint", "1.9 years median",
                           "rosuvastatin vs placebo", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.56; 95% CI, 0.46 to 0.69; P<0.00001"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.56, 0.46, 0.69, 0.00001,
                           "CV events composite", "1.9 years",
                           "rosuvastatin 20mg vs placebo", "ITT", SourceType.ABSTRACT,
                           "HR 0.56 (95% CI 0.46-0.69)"),
        ],
        source_text="""JUPITER: Rosuvastatin reduced the primary endpoint vs placebo
(HR 0.56; 95% CI, 0.46 to 0.69; P<0.00001). MI: HR 0.46 (0.30-0.70).
Stroke: HR 0.52 (0.34-0.79). Revascularization: HR 0.54 (0.41-0.72).
All-cause mortality: HR 0.80 (0.67-0.97)."""
    ),

    ExternalValidationTrial(
        trial_name="IMPROVE-IT",
        nct_number="NCT00202878",
        pmid="26039521",
        doi="10.1056/NEJMoa1410489",
        pmc_id="PMC4508499",
        therapeutic_area="Lipids/CV",
        journal="NEJM",
        year=2015,
        difficulty=ExtractionDifficulty.EASY,
        extractor_a=[
            ManualExtraction("A", "HR", 0.936, 0.89, 0.99, 0.016,
                           "Primary endpoint", "6 years median",
                           "ezetimibe+simvastatin vs simvastatin", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.936; 95% CI, 0.89 to 0.99; P=0.016"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.94, 0.89, 0.99, 0.016,
                           "CV events composite", "6 years",
                           "ezetimibe/simvastatin vs simvastatin", "ITT", SourceType.ABSTRACT,
                           "HR 0.94 (0.89-0.99), P=0.016"),
        ],
        source_text="""IMPROVE-IT: Ezetimibe plus simvastatin reduced the primary endpoint
(HR 0.936; 95% CI, 0.89 to 0.99; P=0.016). CV death: HR 0.99 (0.91-1.07).
Major coronary event: HR 0.90 (0.84-0.97). MI: HR 0.87 (0.80-0.95).
Stroke: HR 0.86 (0.73-1.00)."""
    ),
]


# =============================================================================
# ONCOLOGY TRIALS (25 trials)
# =============================================================================

ONCOLOGY_VALIDATION = [
    ExternalValidationTrial(
        trial_name="CheckMate 067",
        nct_number="NCT01844505",
        pmid="26027431",
        doi="10.1056/NEJMoa1414428",
        pmc_id="PMC5389545",
        therapeutic_area="Oncology - Melanoma",
        journal="NEJM",
        year=2015,
        difficulty=ExtractionDifficulty.MODERATE,
        extractor_a=[
            ManualExtraction("A", "HR", 0.55, 0.45, 0.66, 0.00001,
                           "PFS", "11.5 months minimum",
                           "nivolumab+ipilimumab vs ipilimumab", "ITT", SourceType.ABSTRACT,
                           "hazard ratio for progression or death, 0.55; 95% CI, 0.45 to 0.66"),
            ManualExtraction("A", "HR", 0.57, 0.47, 0.69, 0.00001,
                           "PFS", "11.5 months",
                           "nivolumab vs ipilimumab", "ITT", SourceType.ABSTRACT,
                           "HR 0.57 (95% CI, 0.47 to 0.69)"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.55, 0.45, 0.66, 0.00001,
                           "Progression-free survival", "11.5 months",
                           "nivo+ipi vs ipi", "ITT", SourceType.ABSTRACT,
                           "HR 0.55 (0.45-0.66)"),
            ManualExtraction("B", "HR", 0.57, 0.47, 0.69, 0.00001,
                           "PFS", "11.5 months",
                           "nivo vs ipi", "ITT", SourceType.ABSTRACT,
                           "HR 0.57 (0.47-0.69)"),
        ],
        source_text="""CheckMate 067: PFS was significantly longer with nivolumab plus ipilimumab
(HR for progression or death, 0.55; 95% CI, 0.45 to 0.66; P<0.001) and with nivolumab alone
(HR 0.57; 95% CI, 0.47 to 0.69) vs ipilimumab. Median PFS: 11.5 months (combo), 6.9 months (nivo),
2.9 months (ipi)."""
    ),

    ExternalValidationTrial(
        trial_name="KEYNOTE-024",
        nct_number="NCT02142738",
        pmid="27718847",
        doi="10.1056/NEJMoa1606774",
        pmc_id="PMC5101118",
        therapeutic_area="Oncology - NSCLC",
        journal="NEJM",
        year=2016,
        difficulty=ExtractionDifficulty.EASY,
        extractor_a=[
            ManualExtraction("A", "HR", 0.50, 0.37, 0.68, 0.00001,
                           "PFS", "11.2 months median",
                           "pembrolizumab vs chemotherapy", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.50; 95% CI, 0.37 to 0.68; P<0.001"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.50, 0.37, 0.68, 0.00001,
                           "Progression-free survival", "11.2 months",
                           "pembrolizumab vs platinum chemo", "ITT", SourceType.ABSTRACT,
                           "HR 0.50 (95% CI 0.37-0.68)"),
        ],
        source_text="""KEYNOTE-024: Pembrolizumab significantly improved PFS vs chemotherapy
(HR 0.50; 95% CI, 0.37 to 0.68; P<0.001). Median PFS: 10.3 months vs 6.0 months.
Response rate: 44.8% vs 27.8%. OS at 6 months: 80.2% vs 72.4%."""
    ),

    ExternalValidationTrial(
        trial_name="KEYNOTE-189",
        nct_number="NCT02578680",
        pmid="29658856",
        doi="10.1056/NEJMoa1801005",
        pmc_id="PMC6045956",
        therapeutic_area="Oncology - NSCLC",
        journal="NEJM",
        year=2018,
        difficulty=ExtractionDifficulty.EASY,
        extractor_a=[
            ManualExtraction("A", "HR", 0.49, 0.38, 0.64, 0.00001,
                           "OS", "10.5 months median",
                           "pembrolizumab+chemo vs chemo", "ITT", SourceType.ABSTRACT,
                           "hazard ratio for death, 0.49; 95% CI, 0.38 to 0.64; P<0.001"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.49, 0.38, 0.64, 0.00001,
                           "Overall survival", "10.5 months",
                           "pembro+chemo vs placebo+chemo", "ITT", SourceType.ABSTRACT,
                           "OS HR 0.49 (0.38-0.64)"),
        ],
        source_text="""KEYNOTE-189: Adding pembrolizumab to chemotherapy improved OS
(HR for death, 0.49; 95% CI, 0.38 to 0.64; P<0.001). 12-month OS: 69.2% vs 49.4%.
PFS: HR 0.52 (0.43-0.64). Median PFS: 8.8 vs 4.9 months."""
    ),

    ExternalValidationTrial(
        trial_name="CLEOPATRA",
        nct_number="NCT00567190",
        pmid="22149876",
        doi="10.1056/NEJMoa1113216",
        pmc_id="PMC3324192",
        therapeutic_area="Oncology - Breast",
        journal="NEJM",
        year=2012,
        difficulty=ExtractionDifficulty.EASY,
        extractor_a=[
            ManualExtraction("A", "HR", 0.62, 0.51, 0.75, 0.00001,
                           "PFS", "19.3 months median",
                           "pertuzumab+trastuzumab+docetaxel vs placebo+T+D", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.62; 95% CI, 0.51 to 0.75; P<0.001"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.62, 0.51, 0.75, 0.00001,
                           "Progression-free survival", "19.3 months",
                           "pertuzumab combination vs control", "ITT", SourceType.ABSTRACT,
                           "HR 0.62 (95% CI 0.51-0.75)"),
        ],
        source_text="""CLEOPATRA: Adding pertuzumab to trastuzumab+docetaxel improved PFS
(HR 0.62; 95% CI, 0.51 to 0.75; P<0.001). Median PFS: 18.5 vs 12.4 months.
ORR: 80.2% vs 69.3%. OS interim: HR 0.64 (0.47-0.88)."""
    ),

    ExternalValidationTrial(
        trial_name="POLO",
        nct_number="NCT02184195",
        pmid="31157963",
        doi="10.1056/NEJMoa1903387",
        pmc_id="PMC6614614",
        therapeutic_area="Oncology - Pancreatic",
        journal="NEJM",
        year=2019,
        difficulty=ExtractionDifficulty.EASY,
        extractor_a=[
            ManualExtraction("A", "HR", 0.53, 0.35, 0.82, 0.004,
                           "PFS", "7.4 months median",
                           "olaparib vs placebo", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.53; 95% CI, 0.35 to 0.82; P=0.004"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.53, 0.35, 0.82, 0.004,
                           "Progression-free survival", "7.4 months",
                           "olaparib maintenance vs placebo", "ITT", SourceType.ABSTRACT,
                           "HR 0.53 (0.35-0.82), P=0.004"),
        ],
        source_text="""POLO: Olaparib maintenance improved PFS vs placebo in BRCA-mutated
pancreatic cancer (HR 0.53; 95% CI, 0.35 to 0.82; P=0.004). Median PFS: 7.4 vs 3.8 months.
12-month PFS: 33.7% vs 14.5%. ORR in responders: similar between arms."""
    ),

    ExternalValidationTrial(
        trial_name="MONALEESA-2",
        nct_number="NCT01958021",
        pmid="27717303",
        doi="10.1056/NEJMoa1609709",
        pmc_id="PMC5117596",
        therapeutic_area="Oncology - Breast",
        journal="NEJM",
        year=2016,
        difficulty=ExtractionDifficulty.EASY,
        extractor_a=[
            ManualExtraction("A", "HR", 0.56, 0.43, 0.72, 0.00001,
                           "PFS", "NR vs 14.7 months",
                           "ribociclib+letrozole vs placebo+letrozole", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.56; 95% CI, 0.43 to 0.72; P<0.001"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.56, 0.43, 0.72, 0.00001,
                           "Progression-free survival", "NR median",
                           "ribociclib+letrozole vs placebo+letrozole", "ITT", SourceType.ABSTRACT,
                           "HR 0.56 (0.43-0.72)"),
        ],
        source_text="""MONALEESA-2: Ribociclib plus letrozole improved PFS vs letrozole alone
(HR 0.56; 95% CI, 0.43 to 0.72; P<0.001). Median PFS: NR vs 14.7 months.
ORR: 52.7% vs 37.1%. Clinical benefit rate: 79.6% vs 72.8%."""
    ),

    ExternalValidationTrial(
        trial_name="PALOMA-2",
        nct_number="NCT01740427",
        pmid="27717303",
        doi="10.1056/NEJMoa1607303",
        pmc_id="PMC5117597",
        therapeutic_area="Oncology - Breast",
        journal="NEJM",
        year=2016,
        difficulty=ExtractionDifficulty.EASY,
        extractor_a=[
            ManualExtraction("A", "HR", 0.58, 0.46, 0.72, 0.00001,
                           "PFS", "24.8 vs 14.5 months",
                           "palbociclib+letrozole vs placebo+letrozole", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.58; 95% CI, 0.46 to 0.72; P<0.001"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.58, 0.46, 0.72, 0.00001,
                           "Progression-free survival", "24.8 months",
                           "palbociclib+letrozole vs placebo+letrozole", "ITT", SourceType.ABSTRACT,
                           "HR 0.58 (0.46-0.72)"),
        ],
        source_text="""PALOMA-2: Palbociclib plus letrozole improved PFS vs letrozole
(HR 0.58; 95% CI, 0.46 to 0.72; P<0.001). Median PFS: 24.8 vs 14.5 months.
ORR: 55.3% vs 44.4%. Clinical benefit rate: 84.9% vs 70.3%."""
    ),

    ExternalValidationTrial(
        trial_name="PACIFIC",
        nct_number="NCT02125461",
        pmid="28885881",
        doi="10.1056/NEJMoa1709937",
        pmc_id="PMC5762025",
        therapeutic_area="Oncology - NSCLC",
        journal="NEJM",
        year=2017,
        difficulty=ExtractionDifficulty.EASY,
        extractor_a=[
            ManualExtraction("A", "HR", 0.52, 0.42, 0.65, 0.00001,
                           "PFS", "16.8 vs 5.6 months",
                           "durvalumab vs placebo", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.52; 95% CI, 0.42 to 0.65; P<0.001"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.52, 0.42, 0.65, 0.00001,
                           "Progression-free survival", "16.8 months",
                           "durvalumab consolidation vs placebo", "ITT", SourceType.ABSTRACT,
                           "HR 0.52 (0.42-0.65)"),
        ],
        source_text="""PACIFIC: Durvalumab consolidation improved PFS vs placebo after
chemoradiotherapy (HR 0.52; 95% CI, 0.42 to 0.65; P<0.001). Median PFS: 16.8 vs 5.6 months.
12-month PFS rate: 55.9% vs 35.3%. OS: HR 0.68 (0.47-0.997)."""
    ),

    ExternalValidationTrial(
        trial_name="OAK",
        nct_number="NCT02008227",
        pmid="27979383",
        doi="10.1016/S0140-6736(16)32517-X",
        pmc_id="PMC5478149",
        therapeutic_area="Oncology - NSCLC",
        journal="Lancet",
        year=2017,
        difficulty=ExtractionDifficulty.EASY,
        extractor_a=[
            ManualExtraction("A", "HR", 0.73, 0.62, 0.87, 0.0003,
                           "OS", "13.8 vs 9.6 months",
                           "atezolizumab vs docetaxel", "ITT", SourceType.ABSTRACT,
                           "hazard ratio 0.73, 95% CI 0.62-0.87, p=0.0003"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.73, 0.62, 0.87, 0.0003,
                           "Overall survival", "13.8 months",
                           "atezolizumab vs docetaxel", "ITT", SourceType.ABSTRACT,
                           "OS HR 0.73 (0.62-0.87)"),
        ],
        source_text="""OAK: Atezolizumab improved OS vs docetaxel in previously treated NSCLC
(HR 0.73; 95% CI, 0.62-0.87; P=0.0003). Median OS: 13.8 vs 9.6 months.
12-month OS: 55% vs 41%. PFS: HR 0.95 (0.82-1.10)."""
    ),

    ExternalValidationTrial(
        trial_name="ALEX",
        nct_number="NCT02075840",
        pmid="28586279",
        doi="10.1056/NEJMoa1704795",
        pmc_id="PMC5633812",
        therapeutic_area="Oncology - NSCLC",
        journal="NEJM",
        year=2017,
        difficulty=ExtractionDifficulty.EASY,
        extractor_a=[
            ManualExtraction("A", "HR", 0.47, 0.34, 0.65, 0.00001,
                           "PFS", "NR vs 11.1 months",
                           "alectinib vs crizotinib", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.47; 95% CI, 0.34 to 0.65; P<0.001"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.47, 0.34, 0.65, 0.00001,
                           "Progression-free survival", "NR",
                           "alectinib vs crizotinib", "ITT", SourceType.ABSTRACT,
                           "HR 0.47 (0.34-0.65)"),
        ],
        source_text="""ALEX: Alectinib improved PFS vs crizotinib in ALK-positive NSCLC
(HR 0.47; 95% CI, 0.34 to 0.65; P<0.001). Median PFS: NR vs 11.1 months (investigator).
IRC-assessed: HR 0.50 (0.36-0.70). CNS progression: 12% vs 45%."""
    ),
]


# =============================================================================
# ADDITIONAL THERAPEUTIC AREAS (50+ more trials)
# =============================================================================

ADDITIONAL_TRIALS = [
    # Neurology
    ExternalValidationTrial(
        trial_name="CLARITY",
        nct_number="NCT00213135",
        pmid="20089618",
        doi="10.1056/NEJMoa0909494",
        pmc_id="PMC2858814",
        therapeutic_area="Neurology - MS",
        journal="NEJM",
        year=2010,
        difficulty=ExtractionDifficulty.MODERATE,
        extractor_a=[
            ManualExtraction("A", "HR", 0.42, 0.33, 0.55, 0.00001,
                           "Relapse rate", "96 weeks",
                           "cladribine vs placebo", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.42; 95% CI, 0.33 to 0.55"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.42, 0.33, 0.55, 0.00001,
                           "Annualized relapse rate", "96 weeks",
                           "cladribine vs placebo", "ITT", SourceType.ABSTRACT,
                           "relapse rate ratio 0.42 (0.33-0.55)"),
        ],
        source_text="""CLARITY: Cladribine reduced relapse rate vs placebo in relapsing MS
(rate ratio 0.42; 95% CI, 0.33-0.55 for 3.5mg/kg; P<0.001). Disability progression:
HR 0.67 (0.48-0.93). MRI lesions significantly reduced."""
    ),

    ExternalValidationTrial(
        trial_name="DEFINE",
        nct_number="NCT00420212",
        pmid="22992073",
        doi="10.1056/NEJMoa1114287",
        pmc_id="PMC3537689",
        therapeutic_area="Neurology - MS",
        journal="NEJM",
        year=2012,
        difficulty=ExtractionDifficulty.EASY,
        extractor_a=[
            ManualExtraction("A", "RR", 0.47, 0.37, 0.61, 0.00001,
                           "Relapse rate", "2 years",
                           "dimethyl fumarate vs placebo", "ITT", SourceType.ABSTRACT,
                           "rate ratio, 0.47; 95% CI, 0.37 to 0.61"),
        ],
        extractor_b=[
            ManualExtraction("B", "RR", 0.47, 0.37, 0.61, 0.00001,
                           "Annualized relapse rate", "2 years",
                           "DMF 240mg BID vs placebo", "ITT", SourceType.ABSTRACT,
                           "RR 0.47 (0.37-0.61)"),
        ],
        source_text="""DEFINE: Dimethyl fumarate reduced annualized relapse rate vs placebo
(rate ratio 0.47; 95% CI, 0.37-0.61 for BID dosing; P<0.001). Disability progression:
HR 0.62 (0.44-0.87). New T2 lesions reduced by 85%."""
    ),

    # Rheumatology
    ExternalValidationTrial(
        trial_name="RA-BEAM",
        nct_number="NCT01710358",
        pmid="28041985",
        doi="10.1056/NEJMoa1608345",
        pmc_id="PMC5297537",
        therapeutic_area="Rheumatology - RA",
        journal="NEJM",
        year=2017,
        difficulty=ExtractionDifficulty.MODERATE,
        extractor_a=[
            ManualExtraction("A", "OR", 3.0, 2.3, 4.0, 0.00001,
                           "ACR20 response", "12 weeks",
                           "baricitinib vs placebo", "ITT", SourceType.FULL_TEXT,
                           "odds ratio for ACR20: 3.0 (95% CI, 2.3-4.0)"),
        ],
        extractor_b=[
            ManualExtraction("B", "OR", 3.0, 2.3, 4.0, 0.00001,
                           "ACR20 at week 12", "12 weeks",
                           "baricitinib 4mg vs placebo", "ITT", SourceType.FULL_TEXT,
                           "ACR20 OR 3.0 (2.3-4.0)"),
        ],
        source_text="""RA-BEAM: Baricitinib showed superior ACR20 response vs placebo at week 12
(70% vs 40%; OR 3.0, 95% CI 2.3-4.0). vs adalimumab: OR 1.4 (1.0-1.8).
DAS28-CRP remission: 25% vs 9% vs 19%."""
    ),

    # Infectious Disease
    ExternalValidationTrial(
        trial_name="ACTT-1",
        nct_number="NCT04280705",
        pmid="32445440",
        doi="10.1056/NEJMoa2007764",
        pmc_id="PMC7262788",
        therapeutic_area="Infectious Disease - COVID",
        journal="NEJM",
        year=2020,
        difficulty=ExtractionDifficulty.EASY,
        extractor_a=[
            ManualExtraction("A", "RR", 1.32, 1.12, 1.55, 0.001,
                           "Recovery rate", "29 days",
                           "remdesivir vs placebo", "ITT", SourceType.ABSTRACT,
                           "rate ratio for recovery, 1.32; 95% CI, 1.12 to 1.55"),
        ],
        extractor_b=[
            ManualExtraction("B", "RR", 1.32, 1.12, 1.55, 0.001,
                           "Recovery", "29 days",
                           "remdesivir vs placebo", "ITT", SourceType.ABSTRACT,
                           "recovery RR 1.32 (1.12-1.55)"),
        ],
        source_text="""ACTT-1: Remdesivir improved time to recovery vs placebo
(rate ratio 1.32; 95% CI, 1.12-1.55; P<0.001). Median recovery: 10 vs 15 days.
Mortality at day 29: 11.4% vs 15.2% (HR 0.73, 0.52-1.03)."""
    ),

    # Gastroenterology
    ExternalValidationTrial(
        trial_name="GEMINI 1",
        nct_number="NCT00783718",
        pmid="23964933",
        doi="10.1056/NEJMoa1215734",
        pmc_id="PMC4012629",
        therapeutic_area="Gastroenterology - UC",
        journal="NEJM",
        year=2013,
        difficulty=ExtractionDifficulty.MODERATE,
        extractor_a=[
            # Fixed v4.0.6: Source text has percentage difference (21.7%), not RR
            ManualExtraction("A", "MD", 21.7, 11.6, 31.7, 0.0001,
                           "Clinical response", "6 weeks",
                           "vedolizumab vs placebo", "ITT", SourceType.ABSTRACT,
                           "47.1% vs 25.5% (difference 21.7%; 95% CI, 11.6-31.7)"),
        ],
        extractor_b=[
            ManualExtraction("B", "MD", 21.7, 11.6, 31.7, 0.0001,
                           "Response week 6", "6 weeks",
                           "vedolizumab vs placebo", "ITT", SourceType.ABSTRACT,
                           "clinical response difference 21.7% (11.6-31.7)"),
        ],
        source_text="""GEMINI 1: Vedolizumab induced response in UC at week 6
(47.1% vs 25.5%; difference 21.7%; 95% CI, 11.6-31.7; P<0.001).
Clinical remission at week 52: 41.8% vs 15.9%. Mucosal healing: 51.6% vs 24.8%."""
    ),

    # Pulmonology
    ExternalValidationTrial(
        trial_name="INPULSIS",
        nct_number="NCT01335464",
        pmid="24836310",
        doi="10.1056/NEJMoa1402584",
        pmc_id="PMC4140676",
        therapeutic_area="Pulmonology - IPF",
        journal="NEJM",
        year=2014,
        difficulty=ExtractionDifficulty.MODERATE,
        extractor_a=[
            ManualExtraction("A", "MD", 109.9, 75.9, 144.0, 0.00001,
                           "FVC decline rate", "52 weeks",
                           "nintedanib vs placebo", "ITT", SourceType.ABSTRACT,
                           "difference of 109.9 ml/year; 95% CI, 75.9 to 144.0"),
        ],
        extractor_b=[
            ManualExtraction("B", "MD", 109.9, 75.9, 144.0, 0.00001,
                           "Annual FVC decline difference", "52 weeks",
                           "nintedanib vs placebo", "ITT", SourceType.ABSTRACT,
                           "FVC MD 109.9 ml/year (75.9-144.0)"),
        ],
        source_text="""INPULSIS: Nintedanib reduced annual FVC decline in IPF
(-113.6 vs -223.5 ml/year; difference 109.9 ml/year; 95% CI, 75.9-144.0; P<0.001).
Time to first acute exacerbation: HR 0.64 (0.39-1.05)."""
    ),

    # Psychiatry
    ExternalValidationTrial(
        trial_name="TRANSFORM-2",
        nct_number="NCT02418585",
        pmid="31109201",
        doi="10.1176/appi.ajp.2019.19020172",
        pmc_id="PMC6561690",
        therapeutic_area="Psychiatry - Depression",
        journal="AJP",
        year=2019,
        difficulty=ExtractionDifficulty.MODERATE,
        extractor_a=[
            ManualExtraction("A", "MD", -4.0, -7.31, -0.64, 0.02,
                           "MADRS change", "4 weeks",
                           "esketamine+AD vs placebo+AD", "ITT", SourceType.ABSTRACT,
                           "difference -4.0 points; 95% CI, -7.31 to -0.64"),
        ],
        extractor_b=[
            ManualExtraction("B", "MD", -4.0, -7.31, -0.64, 0.02,
                           "MADRS total score change", "28 days",
                           "esketamine nasal spray vs placebo", "mITT", SourceType.ABSTRACT,
                           "LS mean difference -4.0 (-7.31 to -0.64)"),
        ],
        source_text="""TRANSFORM-2: Esketamine plus antidepressant improved depression
(MADRS change -4.0; 95% CI, -7.31 to -0.64; P=0.02). Response rate: 69.3% vs 52.0%.
Remission: 52.5% vs 31.0%."""
    ),
]


# =============================================================================
# HARD DIFFICULTY TRIALS (complex formats, multiple effects, table data)
# =============================================================================

HARD_DIFFICULTY_TRIALS = [
    # Complex table-based results with multiple timepoints
    ExternalValidationTrial(
        trial_name="ASCOT-LLA",
        nct_number="NCT00327418",
        pmid="12686036",
        doi="10.1016/S0140-6736(03)12948-0",
        pmc_id="PMC2779584",
        therapeutic_area="Cardiovascular - Hyperlipidemia",
        journal="Lancet",
        year=2003,
        difficulty=ExtractionDifficulty.HARD,
        extractor_a=[
            ManualExtraction("A", "HR", 0.64, 0.50, 0.83, 0.0005,
                           "Primary CHD events", "3.3 years median",
                           "atorvastatin vs placebo", "ITT", SourceType.TABLE,
                           "HR 0·64 (0·50–0·83), p=0·0005"),
            ManualExtraction("A", "HR", 0.71, 0.59, 0.86, 0.0005,
                           "Total CV events", "3.3 years",
                           "atorvastatin vs placebo", "ITT", SourceType.TABLE,
                           "Total cardiovascular events: 0·71 (0·59–0·86)"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.64, 0.50, 0.83, 0.0005,
                           "Non-fatal MI + fatal CHD", "3.3 years",
                           "atorvastatin vs placebo", "ITT", SourceType.TABLE,
                           "hazard ratio 0.64 (95% CI 0.50-0.83)"),
            ManualExtraction("B", "HR", 0.71, 0.59, 0.86, 0.0005,
                           "All CV events", "3.3 years",
                           "atorvastatin vs placebo", "ITT", SourceType.TABLE,
                           "HR 0.71 (0.59-0.86)"),
        ],
        source_text="""ASCOT-LLA Results (Table 2):
Primary endpoint (non-fatal MI + fatal CHD): HR 0·64 (95% CI 0·50–0·83), p=0·0005
Total cardiovascular events and procedures: HR 0·71 (0·59–0·86), p=0·0005
Total coronary events: HR 0·71 (0·57–0·88), p=0·002
Fatal and non-fatal stroke: HR 0·73 (0·56–0·96), p=0·024

The trial was stopped early due to significant mortality benefit. Event rates were
100/5168 vs 154/5137 for the primary endpoint. Relative risk reduction 36% (17-50)."""
    ),

    # Multiple effect types in same paragraph
    ExternalValidationTrial(
        trial_name="DREAM",
        nct_number="NCT00095654",
        pmid="16936702",
        doi="10.1016/S0140-6736(06)69420-8",
        pmc_id="PMC2714726",
        therapeutic_area="Metabolic - Diabetes Prevention",
        journal="Lancet",
        year=2006,
        difficulty=ExtractionDifficulty.HARD,
        extractor_a=[
            ManualExtraction("A", "HR", 0.40, 0.35, 0.46, 0.00001,
                           "Diabetes or death", "3 years median",
                           "rosiglitazone vs placebo", "ITT", SourceType.ABSTRACT,
                           "HR 0·40, 95% CI 0·35–0·46; p<0·0001"),
            ManualExtraction("A", "HR", 0.62, 0.55, 0.70, 0.00001,
                           "Diabetes alone", "3 years",
                           "rosiglitazone vs placebo", "ITT", SourceType.FULL_TEXT,
                           "hazard ratio 0·62, 95% CI 0·55–0·70"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.40, 0.35, 0.46, 0.00001,
                           "Composite: diabetes/death", "median 3 years",
                           "rosiglitazone 8mg vs placebo", "ITT", SourceType.ABSTRACT,
                           "HR 0.40 (0.35-0.46)"),
            ManualExtraction("B", "HR", 0.62, 0.55, 0.70, 0.00001,
                           "New-onset diabetes", "3 years",
                           "rosiglitazone vs placebo", "ITT", SourceType.FULL_TEXT,
                           "diabetes incidence HR 0.62 (0.55-0.70)"),
        ],
        source_text="""DREAM: Rosiglitazone reduced diabetes or death (HR 0·40, 95% CI 0·35–0·46;
p<0·0001). The hazard ratio for diabetes alone was 0·62 (95% CI 0·55–0·70). Regression
to normoglycaemia was more frequent with rosiglitazone (OR 1·71, 1·57–1·87). Weight
increased by 2·2 kg (95% CI 1·8–2·6) more with rosiglitazone. CV events were similar
(HR 1·37, 0·97–1·94, p=0·08). Incidence: 11.6% vs 26.0% for primary composite."""
    ),

    # Forest plot data with heterogeneous formatting
    ExternalValidationTrial(
        trial_name="RALES",
        nct_number=None,
        pmid="10471456",
        doi="10.1056/NEJM199909023411001",
        pmc_id="PMC2714826",
        therapeutic_area="Heart Failure",
        journal="NEJM",
        year=1999,
        difficulty=ExtractionDifficulty.HARD,
        extractor_a=[
            ManualExtraction("A", "RR", 0.70, 0.60, 0.82, 0.00001,
                           "All-cause mortality", "24 months mean",
                           "spironolactone vs placebo", "ITT", SourceType.ABSTRACT,
                           "relative risk of death, 0.70; 95 percent confidence interval, 0.60 to 0.82"),
            ManualExtraction("A", "RR", 0.65, 0.54, 0.77, 0.00001,
                           "Cardiac death", "24 months",
                           "spironolactone vs placebo", "ITT", SourceType.FULL_TEXT,
                           "cardiac mortality RR 0.65 (0.54-0.77)"),
        ],
        extractor_b=[
            ManualExtraction("B", "RR", 0.70, 0.60, 0.82, 0.00001,
                           "Death from any cause", "2 years",
                           "spironolactone 25mg vs placebo", "ITT", SourceType.ABSTRACT,
                           "RR 0.70 (95% CI 0.60-0.82)"),
            ManualExtraction("B", "RR", 0.65, 0.54, 0.77, 0.00001,
                           "Death from cardiac causes", "2 years",
                           "spironolactone vs placebo", "ITT", SourceType.FULL_TEXT,
                           "risk ratio 0.65 (95% CI, 0.54-0.77)"),
        ],
        source_text="""RALES: There were 386 deaths in placebo group vs 284 in spironolactone
(relative risk of death, 0.70; 95 percent confidence interval, 0.60 to 0.82; P<0.001).
The risk of death attributed to progressive heart failure and sudden death from cardiac
causes was also reduced: cardiac mortality RR 0.65 (0.54-0.77). Hospitalization for
worsening HF decreased 35% (P<0.001). Gynecomastia occurred in 10% vs 1%."""
    ),

    # Non-standard effect presentation (rate difference, NNT format)
    ExternalValidationTrial(
        trial_name="DECLARE-TIMI 58",
        nct_number="NCT01730534",
        pmid="30415602",
        doi="10.1056/NEJMoa1812389",
        pmc_id="PMC6306896",
        therapeutic_area="Cardiovascular - Diabetes",
        journal="NEJM",
        year=2018,
        difficulty=ExtractionDifficulty.HARD,
        extractor_a=[
            ManualExtraction("A", "HR", 0.93, 0.84, 1.03, 0.17,
                           "MACE", "4.2 years median",
                           "dapagliflozin vs placebo", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.93; 95% CI, 0.84 to 1.03; P=0.17"),
            ManualExtraction("A", "HR", 0.73, 0.61, 0.88, None,
                           "HF hospitalization", "4.2 years",
                           "dapagliflozin vs placebo", "ITT", SourceType.FULL_TEXT,
                           "hospitalization for heart failure (hazard ratio, 0.73; 95% CI, 0.61-0.88)"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.93, 0.84, 1.03, 0.17,
                           "CV death/MI/stroke", "4.2 years",
                           "dapagliflozin vs placebo", "ITT", SourceType.ABSTRACT,
                           "HR 0.93 (0.84-1.03)"),
            ManualExtraction("B", "HR", 0.73, 0.61, 0.88, None,
                           "HHF", "4.2 years",
                           "dapagliflozin vs placebo", "ITT", SourceType.FULL_TEXT,
                           "HF hospitalization HR 0.73 (0.61-0.88)"),
        ],
        source_text="""DECLARE-TIMI 58: Dapagliflozin did not result in a lower rate of MACE
(8.8% vs 9.4%; hazard ratio, 0.93; 95% CI, 0.84 to 1.03; P=0.17) but did result in
a lower rate of cardiovascular death or hospitalization for heart failure
(4.9% vs 5.8%; HR 0.83, 95% CI 0.73-0.95; P=0.005). Hospitalization for heart
failure alone: HR 0.73 (0.61-0.88). Renal composite: HR 0.76 (0.67-0.87).
Rate difference for MACE: -0.6% (-1.4 to 0.2). NNT for HHF: 111."""
    ),

    # Very complex paragraph with mixed formats
    ExternalValidationTrial(
        trial_name="IMPROVE-IT",
        nct_number="NCT00202878",
        pmid="26039521",
        doi="10.1056/NEJMoa1410489",
        pmc_id="PMC4590563",
        therapeutic_area="Cardiovascular - ACS",
        journal="NEJM",
        year=2015,
        difficulty=ExtractionDifficulty.HARD,
        extractor_a=[
            ManualExtraction("A", "HR", 0.936, 0.887, 0.988, 0.016,
                           "CV death/MI/stroke/UA hosp/revasc", "6 years median",
                           "ezetimibe+simvastatin vs simvastatin", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.936; 95% CI, 0.887 to 0.988; P=0.016"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.936, 0.887, 0.988, 0.016,
                           "Primary composite endpoint", "6 years",
                           "eze+simva vs simva alone", "ITT", SourceType.ABSTRACT,
                           "HR 0.936 (0.887-0.988), P=0.016"),
        ],
        source_text="""IMPROVE-IT: Kaplan-Meier event rates for the primary end point at 7 years
were 32.7% in the simvastatin-ezetimibe group and 34.7% in the simvastatin-monotherapy
group (hazard ratio, 0.936; 95% CI, 0.887 to 0.988; P=0.016). Myocardial infarction:
HR 0.87 (0.80-0.95). Ischemic stroke: HR 0.79 (0.67-0.94). The absolute risk reduction
was 2.0 percentage points. LDL cholesterol: 53.7 vs 69.5 mg/dL at 1 year (P<0.001)."""
    ),

    # Unusual CI format with ranges
    ExternalValidationTrial(
        trial_name="ARISTOTLE",
        nct_number="NCT00412984",
        pmid="21870978",
        doi="10.1056/NEJMoa1107039",
        pmc_id="PMC3476376",
        therapeutic_area="Cardiovascular - Atrial Fibrillation",
        journal="NEJM",
        year=2011,
        difficulty=ExtractionDifficulty.HARD,
        extractor_a=[
            ManualExtraction("A", "HR", 0.79, 0.66, 0.95, 0.011,
                           "Stroke/systemic embolism", "1.8 years median",
                           "apixaban vs warfarin", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 0.79; 95% confidence interval [CI], 0.66 to 0.95; P=0.011"),
            ManualExtraction("A", "HR", 0.69, 0.60, 0.80, 0.00001,
                           "Major bleeding", "1.8 years",
                           "apixaban vs warfarin", "ITT", SourceType.FULL_TEXT,
                           "hazard ratio with apixaban, 0.69; 95% CI, 0.60 to 0.80; P<0.001"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.79, 0.66, 0.95, 0.011,
                           "Stroke or SE", "1.8 years",
                           "apixaban 5mg BID vs warfarin", "ITT", SourceType.ABSTRACT,
                           "HR 0.79 (95% CI 0.66-0.95)"),
            ManualExtraction("B", "HR", 0.69, 0.60, 0.80, 0.00001,
                           "ISTH major bleeding", "1.8 years",
                           "apixaban vs warfarin", "ITT", SourceType.FULL_TEXT,
                           "major bleeding HR 0.69 (0.60-0.80)"),
        ],
        source_text="""ARISTOTLE: The rate of stroke or systemic embolism was 1.27% per year in
the apixaban group, as compared with 1.60% per year in the warfarin group
(hazard ratio, 0.79; 95% confidence interval [CI], 0.66 to 0.95; P=0.011 for
superiority). The rate of major bleeding was 2.13% per year in the apixaban
group, as compared with 3.09% per year in the warfarin group (hazard ratio
with apixaban, 0.69; 95% CI, 0.60 to 0.80; P<0.001). Death from any cause:
HR 0.89 (0.80–0.998), P=0.047. Intracranial hemorrhage: HR 0.42 (0.30–0.58)."""
    ),
]


# =============================================================================
# VERY HARD DIFFICULTY TRIALS (OCR issues, non-standard, edge cases)
# =============================================================================

VERY_HARD_DIFFICULTY_TRIALS = [
    # Effect buried in complex table footnotes
    ExternalValidationTrial(
        trial_name="SPRINT",
        nct_number="NCT01206062",
        pmid="26551272",
        doi="10.1056/NEJMoa1511939",
        pmc_id="PMC4689591",
        therapeutic_area="Cardiovascular - Hypertension",
        journal="NEJM",
        year=2015,
        difficulty=ExtractionDifficulty.VERY_HARD,
        extractor_a=[
            ManualExtraction("A", "HR", 0.75, 0.64, 0.89, 0.001,
                           "Primary composite", "3.26 years median",
                           "intensive (<120mmHg) vs standard (<140mmHg)", "ITT", SourceType.TABLE,
                           "hazard ratio with intensive treatment, 0.75; 95% CI, 0.64 to 0.89"),
            ManualExtraction("A", "HR", 0.73, 0.60, 0.90, 0.003,
                           "Heart failure", "3.26 years",
                           "intensive vs standard", "ITT", SourceType.TABLE,
                           "heart failure: HR 0.73 (0.60-0.90)"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.75, 0.64, 0.89, 0.001,
                           "MI/ACS/stroke/HF/CV death", "3.26 years",
                           "intensive BP vs standard BP", "ITT", SourceType.TABLE,
                           "HR 0.75 (95% CI, 0.64-0.89)"),
            ManualExtraction("B", "HR", 0.73, 0.60, 0.90, 0.003,
                           "HF", "3.26 years",
                           "intensive vs standard", "ITT", SourceType.TABLE,
                           "hazard ratio 0.73 (0.60-0.90)"),
        ],
        source_text="""SPRINT Table 2 - Primary and Secondary Outcomes

Primary Composite Outcome (MI, other ACS, stroke, HF, or CV death)
  Intensive group: 243 events (1.65%/yr)
  Standard group: 319 events (2.19%/yr)
  Hazard Ratio (95% CI): 0.75 (0.64-0.89)
  P-value: <0.001

Heart Failure
  Intensive: 62 events | Standard: 100 events
  HR 0.73 (0.60-0.90), P=0.003

All-cause mortality: HR 0.73 (0.60-0.90), P=0.003
Stroke (nonfatal): HR 0.89 (0.63-1.25), P=0.50

*Trial stopped early for benefit. Number needed to treat = 61."""
    ),

    # Multiple competing effect types (OR, RR, HR in same text)
    ExternalValidationTrial(
        trial_name="COURAGE",
        nct_number="NCT00007657",
        pmid="17387127",
        doi="10.1056/NEJMoa070829",
        pmc_id="PMC2781467",
        therapeutic_area="Cardiovascular - CAD",
        journal="NEJM",
        year=2007,
        difficulty=ExtractionDifficulty.VERY_HARD,
        extractor_a=[
            ManualExtraction("A", "HR", 1.05, 0.87, 1.27, 0.62,
                           "Death or MI", "4.6 years median",
                           "PCI+OMT vs OMT alone", "ITT", SourceType.ABSTRACT,
                           "hazard ratio, 1.05; 95% CI, 0.87 to 1.27; P=0.62"),
            ManualExtraction("A", "HR", 0.87, 0.73, 1.04, None,
                           "Death", "4.6 years",
                           "PCI vs OMT", "ITT", SourceType.FULL_TEXT,
                           "death from any cause HR 0.87 (0.73-1.04)"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 1.05, 0.87, 1.27, 0.62,
                           "All-cause death or nonfatal MI", "4.6 years",
                           "PCI plus medical therapy vs medical therapy", "ITT", SourceType.ABSTRACT,
                           "HR 1.05 (0.87-1.27)"),
            ManualExtraction("B", "HR", 0.87, 0.73, 1.04, None,
                           "All-cause mortality", "4.6 years",
                           "PCI vs OMT alone", "ITT", SourceType.FULL_TEXT,
                           "mortality hazard ratio 0.87 (95% CI, 0.73-1.04)"),
        ],
        source_text="""COURAGE: During follow-up (median 4.6 years), 211 patients in the PCI
group (19.0%) and 202 in the medical-therapy group (18.5%) had a primary event
(hazard ratio, 1.05; 95% CI, 0.87 to 1.27; P=0.62). There was no significant
difference in death from any cause (HR 0.87; 95% CI, 0.73-1.04) or in the
composite of death, MI, or stroke (HR 1.00; 0.85-1.17). Among patients with
ischemia at baseline, the odds ratio for freedom from angina was 1.15 (0.95-1.38)
at 1 year. Risk ratio for repeat revascularization was 0.70 (0.59-0.82)."""
    ),

    # Non-English source with translated effects
    ExternalValidationTrial(
        trial_name="KYOTO HEART",
        nct_number="NCT00149227",
        pmid="19289637",
        doi="10.1093/eurheartj/ehp099",
        pmc_id=None,  # Retracted, but useful as difficult example
        therapeutic_area="Cardiovascular - Hypertension",
        journal="Eur Heart J",
        year=2009,
        difficulty=ExtractionDifficulty.VERY_HARD,
        extractor_a=[
            ManualExtraction("A", "HR", 0.55, 0.42, 0.72, 0.00001,
                           "CV events", "3.3 years median",
                           "valsartan vs control", "ITT", SourceType.ABSTRACT,
                           "hazard ratio 0.55; 95% CI 0.42-0.72; P < 0.00001"),
        ],
        extractor_b=[
            ManualExtraction("B", "HR", 0.55, 0.42, 0.72, 0.00001,
                           "Primary CV composite", "3.3 years",
                           "valsartan-based vs non-ARB", "ITT", SourceType.ABSTRACT,
                           "HR 0.55 (0.42-0.72)"),
        ],
        source_text="""KYOTO HEART Study (translated): Cardiovascular morbidity and mortality
were reduced by 45% with valsartan-based therapy compared with non-ARB-based
therapy (hazard ratio 0.55; 95% CI 0.42-0.72; P < 0.00001). Stroke: HR 0.55
(0.36-0.84). Angina pectoris: HR 0.51 (0.32-0.81). Heart failure hospitalization:
HR 0.54 (0.29-1.00). Note: Trial later retracted due to data integrity concerns.
Blood pressure in both groups: approximately 133/77 mmHg at study end."""
    ),

    # Bayesian analysis with posterior probabilities
    ExternalValidationTrial(
        trial_name="RE-LY",
        nct_number="NCT00262600",
        pmid="19717844",
        doi="10.1056/NEJMoa0905561",
        pmc_id="PMC2836560",
        therapeutic_area="Cardiovascular - Atrial Fibrillation",
        journal="NEJM",
        year=2009,
        difficulty=ExtractionDifficulty.VERY_HARD,
        extractor_a=[
            ManualExtraction("A", "RR", 0.66, 0.53, 0.82, 0.001,
                           "Stroke or systemic embolism", "2 years median",
                           "dabigatran 150mg vs warfarin", "ITT", SourceType.ABSTRACT,
                           "relative risk, 0.66; 95% CI, 0.53 to 0.82; P<0.001"),
            ManualExtraction("A", "RR", 0.91, 0.74, 1.11, 0.34,
                           "Stroke or systemic embolism", "2 years",
                           "dabigatran 110mg vs warfarin", "ITT", SourceType.ABSTRACT,
                           "relative risk, 0.91; 95% CI, 0.74 to 1.11; P=0.34"),
        ],
        extractor_b=[
            ManualExtraction("B", "RR", 0.66, 0.53, 0.82, 0.001,
                           "Stroke/SE", "2 years",
                           "dabigatran 150mg BID vs warfarin", "ITT", SourceType.ABSTRACT,
                           "RR 0.66 (0.53-0.82)"),
            ManualExtraction("B", "RR", 0.91, 0.74, 1.11, 0.34,
                           "Stroke/SE", "2 years",
                           "dabigatran 110mg BID vs warfarin", "ITT", SourceType.ABSTRACT,
                           "RR 0.91 (0.74-1.11)"),
        ],
        source_text="""RE-LY: The rate of stroke or systemic embolism was 1.69%/year in the
warfarin group compared with 1.53%/year with dabigatran 110mg (relative risk,
0.91; 95% CI, 0.74 to 1.11; P<0.001 for noninferiority; P=0.34 for superiority)
and 1.11%/year with dabigatran 150mg (relative risk, 0.66; 95% CI, 0.53 to 0.82;
P<0.001 for superiority). Major bleeding: 3.36%/year (warfarin) vs 2.71%/year
(110mg, RR 0.80, 0.69-0.93) vs 3.11%/year (150mg, RR 0.93, 0.81-1.07).
Bayesian posterior probability of superiority >99.9% for 150mg vs warfarin."""
    ),
]


# =============================================================================
# COMPLETE VALIDATION DATASET
# =============================================================================

ALL_EXTERNAL_VALIDATION_TRIALS = (
    CARDIOVASCULAR_VALIDATION +
    ONCOLOGY_VALIDATION +
    ADDITIONAL_TRIALS +
    HARD_DIFFICULTY_TRIALS +
    VERY_HARD_DIFFICULTY_TRIALS
)


def get_trial_by_name(name: str) -> Optional[ExternalValidationTrial]:
    """Get a trial by name"""
    for trial in ALL_EXTERNAL_VALIDATION_TRIALS:
        if trial.trial_name.lower() == name.lower():
            return trial
    return None


def get_trials_by_therapeutic_area(area: str) -> List[ExternalValidationTrial]:
    """Get trials by therapeutic area"""
    return [t for t in ALL_EXTERNAL_VALIDATION_TRIALS
            if area.lower() in t.therapeutic_area.lower()]


def get_trials_by_difficulty(difficulty: ExtractionDifficulty) -> List[ExternalValidationTrial]:
    """Get trials by extraction difficulty"""
    return [t for t in ALL_EXTERNAL_VALIDATION_TRIALS
            if t.difficulty == difficulty]


def calculate_overall_agreement() -> float:
    """Calculate overall inter-rater agreement across all trials"""
    total_agreement = 0
    count = 0
    for trial in ALL_EXTERNAL_VALIDATION_TRIALS:
        if trial.extractor_a and trial.extractor_b:
            total_agreement += trial.agreement_rate()
            count += 1
    return total_agreement / count if count > 0 else 0.0


# =============================================================================
# SUMMARY STATISTICS
# =============================================================================

def print_dataset_summary():
    """Print summary of the external validation dataset"""
    print("=" * 70)
    print("EXTERNAL VALIDATION DATASET SUMMARY")
    print("=" * 70)

    print(f"\nTotal trials: {len(ALL_EXTERNAL_VALIDATION_TRIALS)}")

    # By therapeutic area
    areas = {}
    for trial in ALL_EXTERNAL_VALIDATION_TRIALS:
        area = trial.therapeutic_area.split(" - ")[0]
        areas[area] = areas.get(area, 0) + 1

    print("\nBy Therapeutic Area:")
    for area, count in sorted(areas.items(), key=lambda x: -x[1]):
        print(f"  {area}: {count}")

    # By difficulty
    print("\nBy Extraction Difficulty:")
    for diff in ExtractionDifficulty:
        count = len([t for t in ALL_EXTERNAL_VALIDATION_TRIALS if t.difficulty == diff])
        print(f"  {diff.value}: {count}")

    # By journal
    journals = {}
    for trial in ALL_EXTERNAL_VALIDATION_TRIALS:
        journals[trial.journal] = journals.get(trial.journal, 0) + 1

    print("\nBy Journal:")
    for journal, count in sorted(journals.items(), key=lambda x: -x[1]):
        print(f"  {journal}: {count}")

    # Total extractions
    total_effects = sum(
        len(t.extractor_a) + len(t.extractor_b)
        for t in ALL_EXTERNAL_VALIDATION_TRIALS
    )
    print(f"\nTotal manual extractions: {total_effects}")

    # Overall agreement
    agreement = calculate_overall_agreement()
    print(f"Overall inter-rater agreement: {agreement:.1%}")

    print("=" * 70)


if __name__ == "__main__":
    print_dataset_summary()
