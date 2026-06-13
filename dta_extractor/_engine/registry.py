"""
DTA domain registry.

Analogous to the RCT engine's specialty registry, but DTA is organised by
*target-condition family* rather than therapeutic specialty. Each domain bundles
vocabulary used to recognise the target condition and the typical index tests /
reference standards, so a caller can scope or auto-detect a domain the same way
`rct_extractor` scopes a specialty.

The registry is data only (no compiled regex held globally beyond detection) to
keep import side-effects minimal. British/American spellings handled with `a?`
insert-vowel forms per rules/lessons.md.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

# domain -> dict(target_terms, index_tests, reference_standards)
DTA_REGISTRY: Dict[str, dict] = {
    "infectious_disease": {
        "target_terms": [
            r"sars[- ]?cov[- ]?2", r"covid[- ]?19", r"tuberculosis", r"\bTB\b",
            r"malaria", r"influenza", r"hepatitis", r"\bHIV\b", r"sepsis",
            r"pneumonia", r"streptococc\w+", r"helicobacter",
        ],
        "index_tests": [
            r"rapid\s+antigen\s+test", r"\bRDT\b", r"lateral\s+flow",
            r"\bGeneXpert\b", r"\bPCR\b", r"smear\s+microscopy", r"serolog\w+",
        ],
        "reference_standards": [
            r"\bRT[- ]?PCR\b", r"culture", r"\bNAAT\b", r"viral\s+culture",
        ],
    },
    "oncology": {
        "target_terms": [
            # tumour/tumor: UK inserts a vowel -> tumou?r
            r"tumou?r", r"cancer", r"carcinoma", r"malignan\w+", r"metasta\w+",
            r"o?esophageal", r"colorectal", r"prostate", r"breast", r"lung",
            r"melanoma", r"lymphoma",
        ],
        "index_tests": [
            r"\bPSA\b", r"mammograph\w+", r"\bMRI\b", r"\bCT\b", r"\bPET\b",
            r"colonoscopy", r"biomarker", r"liquid\s+biopsy", r"\bFIT\b",
        ],
        "reference_standards": [
            r"histopatholog\w+", r"biopsy", r"surgical\s+pathology", r"histolog\w+",
        ],
    },
    "cardiology": {
        "target_terms": [
            r"myocardial\s+infarction", r"\bMI\b", r"\bNSTEMI\b", r"\bSTEMI\b",
            r"acute\s+coronary\s+syndrome", r"\bACS\b", r"heart\s+failure",
            r"pulmonary\s+embolism", r"\bPE\b", r"coronary\s+artery\s+disease",
        ],
        "index_tests": [
            r"(?:high[- ]sensitivity\s+)?troponin", r"\bhs[- ]?cTn\b", r"\bD[- ]?dimer\b",
            r"\bECG\b", r"\bBNP\b", r"\bNT[- ]?proBNP\b", r"CT\s+angiograph\w+",
        ],
        "reference_standards": [
            r"coronary\s+angiograph\w+", r"adjudicated\s+diagnosis",
            r"\bCTPA\b", r"clinical\s+follow[- ]up",
        ],
    },
    "neurology": {
        "target_terms": [
            r"alzheimer\w*", r"dementia", r"mild\s+cognitive\s+impairment",
            r"\bMCI\b", r"stroke", r"parkinson\w*", r"multiple\s+sclerosis",
            # paediatric (UK) inserts a/e
            r"p?a?ediatric\s+\w+",
        ],
        "index_tests": [
            r"\bMMSE\b", r"\bMoCA\b", r"\bIQCODE\b", r"amyloid\s+PET",
            r"\bp[- ]?tau\s*217\b", r"CSF\s+biomarker", r"\bMRI\b",
        ],
        "reference_standards": [
            r"clinical\s+diagnosis", r"autopsy", r"\bNINCDS[- ]?ADRDA\b",
            r"consensus\s+diagnosis",
        ],
    },
    "gastroenterology": {
        "target_terms": [
            r"co?eliac\s+disease", r"inflammatory\s+bowel\s+disease", r"\bIBD\b",
            r"colorectal\s+(?:cancer|neoplasia)", r"o?esophageal\s+\w+",
            r"liver\s+fibrosis", r"cirrhosis",
        ],
        "index_tests": [
            r"\bFIT\b", r"calprotectin", r"\btTG[- ]?IgA\b", r"FibroScan",
            r"transient\s+elastography", r"CT\s+colonography",
        ],
        "reference_standards": [
            r"endoscop\w+", r"colonoscopy", r"liver\s+biopsy", r"histolog\w+",
        ],
    },
}


def list_domains() -> List[str]:
    return sorted(DTA_REGISTRY.keys())


_DETECT = {
    dom: re.compile("|".join(cfg["target_terms"]), re.IGNORECASE)
    for dom, cfg in DTA_REGISTRY.items()
}


def detect_domain(text: str) -> Optional[str]:
    """Return the domain whose target vocabulary matches `text` most often."""
    best_dom, best_n = None, 0
    for dom, pat in _DETECT.items():
        n = len(pat.findall(text))
        if n > best_n:
            best_dom, best_n = dom, n
    return best_dom
