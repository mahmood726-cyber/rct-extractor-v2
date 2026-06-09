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

# HCV DAA components that combine into fixed-dose regimens. A singleton component
# is suppressed when it sits next to a joiner+partner (so "sofosbuvir-velpatasvir"
# is labelled as the combo, not fragmented into two arms that then fail to pair --
# audit P1-6), but plain "sofosbuvir-based" still matches (the suppressor requires
# a *partner* after the joiner, not any hyphenated word). _tag_arm uses NEAREST
# match, not longest, so without this a combo would lose to its leftmost component.
_DAA_PARTNER = (r"sofosbuvir|velpatasvir|ledipasvir|voxilaprevir|glecaprevir|pibrentasvir|"
                r"daclatasvir|grazoprevir|elbasvir|ombitasvir|paritaprevir|dasabuvir|ritonavir|"
                r"SOF|VEL|LDV|VOX|GLE|PIB|DCV|GZR|EBR")
_J = r"[/\-+ ]"   # combo joiner in text: slash, hyphen, plus, or space
_JLB = r"[/\-+]"  # joiner for the lookbehind ONLY -- excludes space (a leading
                  # space is normal word separation, not a combo boundary)


def _solo(drug):
    """A combinable DAA matched only when NOT part of a hyphen/slash/plus combo.
    Suppressed as the 2nd component (preceded by a joiner) or the 1st component
    (followed by joiner+partner); plain 'sofosbuvir-based' still matches."""
    return rf"(?<!{_JLB}){drug}(?!{_J}(?:{_DAA_PARTNER}))"


# Antiviral / vaccine arm labels. Full names case-insensitive; bare UPPERCASE
# drug abbreviations CASE-SENSITIVE (so SOF/ETV/TDF etc. only match uppercase).
_HEP_ARM_FULL = [
    # HCV fixed-dose combination regimens (match as a unit; brand names are common
    # in abstracts and often the only form spelled out).
    (rf"sofosbuvir{_J}velpatasvir{_J}voxilaprevir|\bvosevi\b",
     "sofosbuvir-velpatasvir-voxilaprevir"),
    (rf"sofosbuvir{_J}velpatasvir|\bepclusa\b", "sofosbuvir-velpatasvir"),
    (rf"ledipasvir{_J}sofosbuvir|sofosbuvir{_J}ledipasvir|\bharvoni\b", "ledipasvir-sofosbuvir"),
    (rf"glecaprevir{_J}pibrentasvir|\bmavyret\b|\bmaviret\b", "glecaprevir-pibrentasvir"),
    (rf"elbasvir{_J}grazoprevir|grazoprevir{_J}elbasvir|\bzepatier\b", "elbasvir-grazoprevir"),
    (rf"ombitasvir{_J}paritaprevir(?:{_J}ritonavir)?(?:\s*(?:\+|plus|and)\s*dasabuvir)?|"
     r"\bviekira\w*\b|\bviekirax\b|\btechnivie\b|\b[23]d\s+regimen\b",
     "ombitasvir-paritaprevir-ritonavir"),
    # HCV direct-acting antivirals (combinable singletons -- combo-suppressed)
    (_solo("sofosbuvir"), "sofosbuvir"),
    (_solo("ledipasvir"), "ledipasvir"),
    (_solo("velpatasvir"), "velpatasvir"),
    (_solo("voxilaprevir"), "voxilaprevir"),
    (_solo("glecaprevir"), "glecaprevir"),
    (_solo("pibrentasvir"), "pibrentasvir"),
    (_solo("daclatasvir"), "daclatasvir"),
    (_solo("grazoprevir"), "grazoprevir"),
    (_solo("elbasvir"), "elbasvir"),
    (_solo("ombitasvir"), "ombitasvir"),
    (_solo("paritaprevir"), "paritaprevir"),
    (_solo("dasabuvir"), "dasabuvir"),
    (r"simeprevir", "simeprevir"),
    (r"\britonavir\b", "ritonavir"),
    (r"ribavirin", "ribavirin"),
    (r"peg(?:ylated)?[- ]?interferon(?:\s+alf?a(?:-2[ab])?)?", "peg-interferon"),
    # HBV nucleos(t)ides
    (r"entecavir", "entecavir"),
    (r"tenofovir\s+alafenamide", "tenofovir-alafenamide"),
    (r"tenofovir(?:\s+disoproxil(?:\s+fumarate)?)?", "tenofovir"),
    (r"besifovir(?:\s+dipivoxil)?", "besifovir"),
    (r"telbivudine", "telbivudine"),
    (r"adefovir", "adefovir"),
    (r"lamivudine", "lamivudine"),
    # Prevention / PMTCT
    (r"hepatitis\s+b\s+immunoglobulin|\bhbig\b", "HBIG"),
    (r"(?:recombinant\s+)?hepatitis\s+b\s+vaccine|hbv\s+vaccine|\bengerix\b|\brecombivax\b",
     "hepatitis-b-vaccine"),
    # Generic
    (r"\bplacebo\b", "placebo"),
    (r"standard\s+(?:of\s+)?care|usual\s+care", "standard-of-care"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"control\s+(?:group|arm|subjects?)", "control"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_HEP_ARM_ABBREV = [   # case-sensitive uppercase
    # combo abbreviations first (suppress the singleton abbrevs below)
    (rf"\bSOF{_J}VEL{_J}VOX\b", "sofosbuvir-velpatasvir-voxilaprevir"),
    (rf"\bSOF{_J}VEL\b", "sofosbuvir-velpatasvir"),
    (rf"\b(?:LDV{_J}SOF|SOF{_J}LDV)\b", "ledipasvir-sofosbuvir"),
    (rf"\b(?:GLE{_J}PIB|G{_J}P)\b", "glecaprevir-pibrentasvir"),
    (rf"\bEBR{_J}GZR\b", "elbasvir-grazoprevir"),
    (rf"\bSOF\b(?!{_J}(?:{_DAA_PARTNER}))", "sofosbuvir"),
    (rf"\bLDV\b(?!{_J}(?:{_DAA_PARTNER}))", "ledipasvir"),
    (rf"\bVEL\b(?!{_J}(?:{_DAA_PARTNER}))", "velpatasvir"),
    (rf"\bVOX\b(?!{_J}(?:{_DAA_PARTNER}))", "voxilaprevir"),
    (rf"\bGLE\b(?!{_J}(?:{_DAA_PARTNER}))", "glecaprevir"),
    (rf"\bPIB\b(?!{_J}(?:{_DAA_PARTNER}))", "pibrentasvir"),
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

# Hepatitis continuous outcomes; viral loads (HBV DNA, HCV RNA) and antibody
# titres (anti-HBs GMT) are log-normal -- pool on the log scale.
_HEP_CONTINUOUS = {"HBV_DNA_LEVEL", "HCV_RNA_LEVEL", "ALT_LEVEL", "LIVER_STIFFNESS", "ANTI_HBS_TITRE"}
_HEP_LOGNORMAL = {"HBV_DNA_LEVEL", "HCV_RNA_LEVEL", "ANTI_HBS_TITRE"}


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
