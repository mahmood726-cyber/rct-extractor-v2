"""
Arm-level / 2x2 + continuous extraction for hepatitis (HBV/HCV) trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with hepatitis
endpoints and antiviral arm labels:

  binary outcomes (SVR, HBsAg loss, HBV DNA suppression, seroprotection, MTCT,
    HCC, discontinuation) -> 2x2 events/N per arm
  continuous (HBV DNA level, ALT, liver stiffness) -> mean+SD / median+IQR;
    HBV DNA is log-normal (pool on the log scale).
"""
import re
from typing import Dict, List

from .hepatitis import get_hepatitis_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# Hepatitis endpoint patterns (string, endpoint) across all subspecialties.
_HEP_ENDPOINT_PATTERNS = []
for _sub in ("treatment", "prevention", "pmtct", "outcomes"):
    _HEP_ENDPOINT_PATTERNS.extend(get_hepatitis_endpoint_patterns(_sub))

# Antiviral / vaccine arm labels. Full names case-insensitive; bare UPPERCASE
# drug abbreviations CASE-SENSITIVE (so SOF/ETV/TDF etc. only match uppercase).
_HEP_ARM_FULL = [
    # HCV direct-acting antivirals
    (r"sofosbuvir", "sofosbuvir"),
    (r"ledipasvir", "ledipasvir"),
    (r"velpatasvir", "velpatasvir"),
    (r"voxilaprevir", "voxilaprevir"),
    (r"glecaprevir", "glecaprevir"),
    (r"pibrentasvir", "pibrentasvir"),
    (r"daclatasvir", "daclatasvir"),
    (r"grazoprevir", "grazoprevir"),
    (r"elbasvir", "elbasvir"),
    (r"simeprevir", "simeprevir"),
    (r"ombitasvir", "ombitasvir"),
    (r"paritaprevir", "paritaprevir"),
    (r"ribavirin", "ribavirin"),
    (r"peg(?:ylated)?[- ]?interferon(?:\s+alfa(?:-2[ab])?)?", "peg-interferon"),
    # HBV nucleos(t)ides
    (r"entecavir", "entecavir"),
    (r"tenofovir\s+alafenamide", "tenofovir-alafenamide"),
    (r"tenofovir(?:\s+disoproxil)?", "tenofovir"),
    (r"telbivudine", "telbivudine"),
    (r"adefovir", "adefovir"),
    (r"lamivudine", "lamivudine"),
    # Prevention / PMTCT
    (r"hepatitis\s+b\s+immunoglobulin|\bhbig\b", "HBIG"),
    (r"(?:recombinant\s+)?hepatitis\s+b\s+vaccine|hbv\s+vaccine", "hepatitis-b-vaccine"),
    # Generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control(?:\s+group|\s+arm)?", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_HEP_ARM_ABBREV = [   # case-sensitive uppercase
    (r"\bSOF\b", "sofosbuvir"),
    (r"\bLDV\b", "ledipasvir"),
    (r"\bVEL\b", "velpatasvir"),
    (r"\bVOX\b", "voxilaprevir"),
    (r"\bGLE\b", "glecaprevir"),
    (r"\bPIB\b", "pibrentasvir"),
    (r"\bDCV\b", "daclatasvir"),
    (r"\bGZR\b", "grazoprevir"),
    (r"\bEBR\b", "elbasvir"),
    (r"\bRBV\b", "ribavirin"),
    (r"\bETV\b", "entecavir"),
    (r"\bTAF\b", "tenofovir-alafenamide"),
    (r"\bTDF\b", "tenofovir"),
    (r"\bLdT\b", "telbivudine"),
    (r"\bADV\b", "adefovir"),
    (r"\bLAM\b", "lamivudine"),
    (r"\bPEG[- ]?IFN\b", "peg-interferon"),
    (r"\bHBIG\b", "HBIG"),
]
_HEP_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _HEP_ARM_FULL]
                     + [(re.compile(p), n) for p, n in _HEP_ARM_ABBREV])

# Hepatitis continuous outcomes; HBV DNA (viral load) is log-normal.
_HEP_CONTINUOUS = {"HBV_DNA_LEVEL", "ALT_LEVEL", "LIVER_STIFFNESS"}
_HEP_LOGNORMAL = {"HBV_DNA_LEVEL"}


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_HEP_ENDPOINT_PATTERNS,
                                arm_compiled=_HEP_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_HEP_ENDPOINT_PATTERNS,
                               arm_compiled=_HEP_ARM_COMPILED,
                               continuous_endpoints=_HEP_CONTINUOUS,
                               lognormal_endpoints=_HEP_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_HEP_ENDPOINT_PATTERNS,
                              arm_compiled=_HEP_ARM_COMPILED,
                              continuous_endpoints=_HEP_CONTINUOUS,
                              lognormal_endpoints=_HEP_LOGNORMAL)
