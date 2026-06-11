"""
Arm-level / 2x2 + continuous extraction for ARDS / acute-respiratory-failure trials.

Thin wrapper over the shared arm-data engine in malaria_arm_data (same proportion
patterns, 2x2 pairing, Wan IQR->SD, poolable gate) configured with ARDS endpoints
and critical-care arm labels:

  binary outcomes (mortality, barotrauma/pneumothorax, successful extubation,
    treatment failure / intubation) -> 2x2 events/N per arm;
  continuous outcomes (ventilator-free days, ICU-/hospital-free days, PaO2:FiO2
    oxygenation, length of stay, duration of ventilation, driving pressure)
    -> per-arm mean+SD (Wan IQR->SD when reported as median/IQR).

ARDS comparisons are typically strategy-vs-strategy (prone vs supine, low vs
traditional tidal volume, higher vs lower PEEP, ECMO vs conventional ventilation)
or drug-vs-placebo (cisatracurium, dexamethasone, inhaled nitric oxide).
"""
import re
from typing import Dict, List

from .ards import get_ards_endpoint_patterns
from .malaria_arm_data import (
    extract_proportions as _extract_proportions,
    extract_continuous as _extract_continuous,
    extract_arm_level as _extract_arm_level,
    pair_2x2, poolable_ready,
)

# ARDS endpoint patterns (string, endpoint) across all subspecialties.
_ARDS_ENDPOINT_PATTERNS = []
for _sub in ("ventilation", "pharmacotherapy", "rescue", "supportive"):
    _ARDS_ENDPOINT_PATTERNS.extend(get_ards_endpoint_patterns(_sub))

# Critical-care arm labels. Full descriptive names case-insensitive; bare drug/
# device abbreviations (ECMO, HFOV, NIV, HFNC, iNO) matched case-sensitively so
# the common words don't collide.
_ARDS_ARM_FULL = [
    (r"prone\s+position(?:ing)?|proning|\bprone\b", "prone"),
    (r"supine\s+position(?:ing)?|\bsupine\b", "supine"),
    (r"low(?:er)?[\s-]tidal[\s-]volume|lung[- ]protective\s+ventilation", "low-tidal-volume"),
    (r"(?:traditional|conventional|higher)[\s-]tidal[\s-]volume", "high-tidal-volume"),
    (r"higher\s+peep|high\s+peep|open[- ]lung", "higher-PEEP"),
    (r"lower\s+peep|low\s+peep", "lower-PEEP"),
    (r"recruitment\s+man(?:o?eu|eu)vre|recruitment\s+maneuver", "recruitment"),
    (r"cisatracurium|neuromuscular\s+block\w+|muscle\s+relaxant", "neuromuscular-blockade"),
    (r"dexamethasone", "dexamethasone"),
    (r"methylprednisolone", "methylprednisolone"),
    (r"hydrocortisone", "hydrocortisone"),
    (r"corticosteroid|glucocorticoid", "corticosteroid"),
    (r"inhaled\s+nitric\s+oxide", "inhaled-nitric-oxide"),
    (r"epoprostenol|inhaled\s+prostacyclin", "epoprostenol"),
    (r"surfactant", "surfactant"),
    (r"extracorporeal\s+membrane\s+oxygenation|veno[- ]venous\s+ecmo", "ECMO"),
    (r"conventional\s+(?:mechanical\s+)?ventilation|conventional\s+management", "conventional-ventilation"),
    (r"high[- ]flow\s+nasal\s+(?:oxygen|cannula)", "high-flow-nasal-oxygen"),
    (r"non[- ]invasive\s+ventilation", "non-invasive-ventilation"),
    (r"conservative\s+oxygen|conservative\s+fluid|conservative\s+strategy", "conservative"),
    (r"liberal\s+oxygen|liberal\s+fluid|liberal\s+strategy", "liberal"),
    (r"standard\s+oxygen\s+therapy|standard\s+oxygen", "standard-oxygen"),
    (r"\bplacebo\b", "placebo"),
    (r"standard[\s-]+(?:of[\s-]+)?care|usual\s+care|standard\s+(?:treatment|therapy)",
     "standard-of-care"),
    (r"control\s+(?:group|arm)|control(?:\s+group|\s+arm)?", "control"),
    (r"intervention\s+(?:group|arm)", "intervention"),
    (r"\bgroup\s+(?:1|i|a)\b|\barm\s+(?:1|i|a)\b", "group_1"),
    (r"\bgroup\s+(?:2|ii|b)\b|\barm\s+(?:2|ii|b)\b", "group_2"),
]
_ARDS_ARM_ABBREV = [   # case-sensitive
    (r"\bECMO\b", "ECMO"),
    (r"\bVV[- ]?ECMO\b", "ECMO"),
    (r"\bECCO2R\b", "ECCO2R"),
    (r"\bHFOV\b", "HFOV"),
    (r"\bHFNC\b|\bHFNO\b", "high-flow-nasal-oxygen"),
    (r"\bNIV\b", "non-invasive-ventilation"),
    (r"\bCPAP\b", "CPAP"),
    (r"\biNO\b", "inhaled-nitric-oxide"),
    (r"\bNMBA\b", "neuromuscular-blockade"),
    (r"\bPEEP\b", "PEEP"),
]
_ARDS_ARM_COMPILED = ([(re.compile(p, re.I), n) for p, n in _ARDS_ARM_FULL]
                      + [(re.compile(p), n) for p, n in _ARDS_ARM_ABBREV])

# Continuous (mean+SD poolable) ARDS endpoints. Ventilator-/ICU-free days,
# oxygenation, length of stay, ventilation duration and driving pressure are
# reported as means (or median/IQR -> Wan SD). None are log-normal.
_ARDS_CONTINUOUS = {
    "VENTILATOR_FREE_DAYS", "ICU_FREE_DAYS", "LENGTH_OF_STAY",
    "DURATION_VENTILATION", "OXYGENATION", "DRIVING_PRESSURE",
}
_ARDS_LOGNORMAL = set()


def extract_proportions(text: str, pct_tol: float = 1.5) -> List[Dict]:
    return _extract_proportions(text, pct_tol, endpoint_patterns=_ARDS_ENDPOINT_PATTERNS,
                                arm_compiled=_ARDS_ARM_COMPILED)


def extract_continuous(text: str) -> List[Dict]:
    return _extract_continuous(text, endpoint_patterns=_ARDS_ENDPOINT_PATTERNS,
                               arm_compiled=_ARDS_ARM_COMPILED,
                               continuous_endpoints=_ARDS_CONTINUOUS,
                               lognormal_endpoints=_ARDS_LOGNORMAL)


def extract_arm_level(text: str) -> Dict:
    return _extract_arm_level(text, endpoint_patterns=_ARDS_ENDPOINT_PATTERNS,
                              arm_compiled=_ARDS_ARM_COMPILED,
                              continuous_endpoints=_ARDS_CONTINUOUS,
                              lognormal_endpoints=_ARDS_LOGNORMAL)
