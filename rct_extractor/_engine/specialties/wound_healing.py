"""
Burns / Wound Healing Subspecialty Patterns and Endpoints

Built for the same meta-analysis workflow as the tuberculosis / ARDS profiles.
Burns and wound-healing RCTs report a distinct endpoint vocabulary (complete
wound closure / healing, time to healing, wound-area reduction, healing rate,
amputation, graft take, scar quality, wound infection) that the generic
effect-size engine does not recognise on its own.

Subspecialties:
- Burns: burn-wound care, early excision and grafting, skin substitutes /
  dermal templates, fluid resuscitation, debridement (enzymatic / bromelain),
  scar management, length of stay, re-epithelialisation.
- Chronic wounds: diabetic foot ulcer, venous leg ulcer, pressure ulcer /
  injury, dressings, negative-pressure wound therapy (NPWT), compression.
- Surgical wounds: surgical-wound healing, dehiscence, closed-incision NPWT,
  closure technique, surgical-site infection / occurrence.
- Adjuncts / biologics: hyperbaric oxygen, growth factors (PDGF, EGF),
  cellular / tissue-engineered products, debriding agents, antimicrobials.

Effect measures follow what these trials report: binary (complete wound healing
/ closure, amputation, infection, dehiscence, graft take) -> RR/OR/HR;
count/continuous (time to healing, wound-area reduction, scar score, pain,
length of stay) -> mean difference, handled by the shared continuous augmenter.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# WOUND HEALING ENDPOINTS
# ============================================================

WOUND_HEALING_ENDPOINTS = {
    'COMPLETE_HEALING': {
        'aliases': ['complete wound healing', 'complete healing', 'complete wound closure',
                    'complete closure', 'wound closure', 'healed', 'wounds healed',
                    'proportion healed', 'full healing', 'complete re-epithelialization',
                    'complete re-epithelialisation', 'incidence of healing'],
        'subspecialty': 'chronic_wounds',
        'measure_types': ['RR', 'OR', 'HR', 'RD']
    },
    'TIME_TO_HEALING': {
        'aliases': ['time to healing', 'time to complete healing', 'time to wound closure',
                    'time to complete closure', 'healing time', 'time to re-epithelialization',
                    'time to re-epithelialisation', 'days to healing',
                    'time to complete re-epithelialization'],
        'subspecialty': 'burns',
        'measure_types': ['MD', 'HR']
    },
    'WOUND_AREA_REDUCTION': {
        'aliases': ['wound area reduction', 'percentage area reduction', 'wound size reduction',
                    'reduction in wound area', 'change in wound area', 'percent area reduction',
                    'wound surface area', 'ulcer area reduction'],
        'subspecialty': 'chronic_wounds',
        'measure_types': ['MD']
    },
    'HEALING_RATE': {
        'aliases': ['healing rate', 'wound healing rate', 'rate of healing',
                    'proportion with healing', 'healing at 12 weeks', 'healing at 24 weeks'],
        'subspecialty': 'chronic_wounds',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'AMPUTATION': {
        'aliases': ['amputation', 'major amputation', 'minor amputation', 'lower limb amputation',
                    'amputation-free survival', 'limb salvage'],
        'subspecialty': 'chronic_wounds',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'INFECTION': {
        'aliases': ['wound infection', 'surgical site infection', 'surgical-site infection',
                    'ssi', 'wound colonization', 'infection', 'clinical infection',
                    'osteomyelitis'],
        'subspecialty': 'surgical_wounds',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'DEHISCENCE': {
        'aliases': ['wound dehiscence', 'dehiscence', 'wound breakdown',
                    'surgical wound dehiscence', 'wound complications', 'wound disruption'],
        'subspecialty': 'surgical_wounds',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'GRAFT_TAKE': {
        'aliases': ['graft take', 'graft survival', 'skin graft take', 'graft loss',
                    'graft failure', 'engraftment', 'percentage graft take'],
        'subspecialty': 'burns',
        'measure_types': ['RR', 'OR', 'MD']
    },
    'SCAR_SCORE': {
        'aliases': ['scar score', 'vancouver scar scale', 'posas', 'patient and observer scar',
                    'scar quality', 'hypertrophic scar', 'scar assessment'],
        'subspecialty': 'burns',
        'measure_types': ['MD', 'RR']
    },
    'PAIN_SCORE': {
        'aliases': ['pain score', 'pain at dressing change', 'visual analogue scale',
                    'vas pain', 'wound pain', 'procedural pain'],
        'subspecialty': 'burns',
        'measure_types': ['MD']
    },
    'LENGTH_OF_STAY': {
        'aliases': ['length of stay', 'hospital length of stay', 'length of hospital stay',
                    'duration of hospitalization', 'time to discharge'],
        'subspecialty': 'burns',
        'measure_types': ['MD']
    },
    'RECURRENCE': {
        'aliases': ['ulcer recurrence', 'recurrence', 'wound recurrence', 'reulceration',
                    're-ulceration', 'recurrent ulcer'],
        'subspecialty': 'chronic_wounds',
        'measure_types': ['RR', 'OR', 'HR']
    },
}


# ============================================================
# BURNS PATTERNS
# ============================================================

BURNS_PATTERNS = {
    'detection_keywords': [
        r'\bburn\b|burns|burn\s+(?:wound|injury|patient)|thermal\s+injury|scald',
        r'(?:total\s+body\s+surface\s+area|tbsa)|partial[- ]thickness|full[- ]thickness',
        r'early\s+excision|skin\s+graft|split[- ]thickness\s+skin\s+graft|\bstsg\b|autograft',
        r'skin\s+substitute|dermal\s+(?:template|substitute|matrix)|biobrane|integra',
        r'enzymatic\s+debridement|bromelain|nexobrid|re[- ]?epitheliali[sz]ation',
        r'fluid\s+resuscitation|parkland',
    ],
    'endpoint_patterns': [
        (r'time\s+to\s+(?:complete\s+)?(?:healing|wound\s+closure|re[- ]?epitheliali[sz]ation)|'
         r'healing\s+time|days\s+to\s+healing', 'TIME_TO_HEALING'),
        (r'graft\s+(?:take|survival|loss|failure)|engraftment', 'GRAFT_TAKE'),
        (r'(?:vancouver\s+scar\s+scale|posas|patient\s+and\s+observer\s+scar|scar\s+score|'
         r'scar\s+quality|hypertrophic\s+scar)', 'SCAR_SCORE'),
        (r'complete\s+(?:wound\s+)?(?:healing|closure|re[- ]?epitheliali[sz]ation)|wounds?\s+healed',
         'COMPLETE_HEALING'),
        (r'(?:wound\s+)?infection|wound\s+colonization', 'INFECTION'),
        (r'pain\s+(?:score|at\s+dressing\s+change)|visual\s+analogue|\bvas\b', 'PAIN_SCORE'),
        (r'(?:hospital\s+)?length\s+of\s+stay|duration\s+of\s+hospitali[sz]ation|time\s+to\s+discharge',
         'LENGTH_OF_STAY'),
    ],
    'context_patterns': [
        r'\d+%\s*tbsa', r'donor\s+site', r'laser\s+doppler',
    ]
}


# ============================================================
# CHRONIC WOUNDS PATTERNS
# ============================================================

CHRONIC_WOUNDS_PATTERNS = {
    'detection_keywords': [
        r'diabetic\s+foot\s+ulcer|\bdfu\b', r'venous\s+leg\s+ulcer|\bvlu\b',
        r'pressure\s+(?:ulcer|injury|sore)|decubitus',
        r'chronic\s+wound|non[- ]healing\s+(?:wound|ulcer)|leg\s+ulcer',
        r'negative[- ]pressure\s+wound\s+therapy|\bnpwt\b|vacuum[- ]assisted\s+closure|\bvac\b',
        r'compression\s+(?:therapy|bandaging|stocking)|dressing',
    ],
    'endpoint_patterns': [
        (r'complete\s+(?:wound\s+)?(?:healing|closure)|wound\s+closure|proportion\s+healed|'
         r'wounds?\s+healed|incidence\s+of\s+healing', 'COMPLETE_HEALING'),
        (r'(?:percentage\s+|percent\s+)?(?:wound\s+|ulcer\s+)?area\s+reduction|'
         r'reduction\s+in\s+wound\s+area|change\s+in\s+wound\s+area|wound\s+surface\s+area',
         'WOUND_AREA_REDUCTION'),
        (r'healing\s+rate|rate\s+of\s+healing|healing\s+at\s+\d+\s+weeks', 'HEALING_RATE'),
        (r'(?:major\s+|minor\s+|lower[- ]limb\s+)?amputation|limb\s+salvage|amputation[- ]free',
         'AMPUTATION'),
        (r'time\s+to\s+(?:complete\s+)?(?:healing|wound\s+closure)|healing\s+time', 'TIME_TO_HEALING'),
        (r'(?:ulcer\s+)?recurrence|re[- ]?ulceration', 'RECURRENCE'),
        (r'(?:wound\s+)?infection|osteomyelitis|clinical\s+infection', 'INFECTION'),
    ],
    'context_patterns': [
        r'wagner\s+grade|university\s+of\s+texas', r'ankle[- ]brachial\s+index', r'12[- ]week',
    ]
}


# ============================================================
# SURGICAL WOUNDS PATTERNS
# ============================================================

SURGICAL_WOUNDS_PATTERNS = {
    'detection_keywords': [
        r'surgical\s+wound|surgical[- ]site\s+(?:infection|occurrence)|\bssi\b|\bsso\b',
        r'closed[- ]incision\s+(?:npwt|negative[- ]pressure)|incisional\s+npwt|prophylactic\s+npwt',
        r'wound\s+dehiscence|wound\s+(?:closure|complications)',
        r'(?:skin\s+)?closure\s+(?:technique|method)|sutures?\s+(?:vs\.?\s+)?staples?',
        r'laparotomy|caesarean\s+(?:section\s+)?(?:wound|closure)',
    ],
    'endpoint_patterns': [
        (r'surgical[- ]site\s+(?:infection|occurrence)|\bssi\b|\bsso\b|wound\s+infection', 'INFECTION'),
        (r'(?:wound\s+|surgical\s+wound\s+)?dehiscence|wound\s+breakdown|wound\s+disruption|'
         r'wound\s+complications', 'DEHISCENCE'),
        (r'complete\s+(?:wound\s+)?(?:healing|closure)|wounds?\s+healed', 'COMPLETE_HEALING'),
        (r'time\s+to\s+(?:complete\s+)?(?:healing|wound\s+closure)|healing\s+time', 'TIME_TO_HEALING'),
        (r'(?:hospital\s+)?length\s+of\s+stay|time\s+to\s+discharge', 'LENGTH_OF_STAY'),
        (r'pain\s+(?:score|at\s+dressing)|visual\s+analogue|\bvas\b', 'PAIN_SCORE'),
    ],
    'context_patterns': [
        r'high[- ]risk\s+(?:incision|patient)', r'class\s+(?:i{1,3}|iv)\s+wound',
    ]
}


# ============================================================
# ADJUNCTS / BIOLOGICS PATTERNS
# ============================================================

ADJUNCTS_PATTERNS = {
    'detection_keywords': [
        r'hyperbaric\s+oxygen|\bhbot\b', r'growth\s+factor|platelet[- ]derived\s+growth\s+factor|\bpdgf\b|becaplermin',
        r'epidermal\s+growth\s+factor|\begf\b|platelet[- ]rich\s+plasma|\bprp\b',
        r'cellular\s+(?:and\s+)?tissue[- ]engineered|skin\s+substitute|amniotic\s+membrane',
        r'(?:silver|honey|iodine)\s+dressing|antimicrobial\s+dressing|collagen\s+dressing',
        r'debriding\s+agent|maggot\s+(?:therapy|debridement)',
    ],
    'endpoint_patterns': [
        (r'complete\s+(?:wound\s+)?(?:healing|closure)|proportion\s+healed|wounds?\s+healed',
         'COMPLETE_HEALING'),
        (r'(?:percentage\s+)?(?:wound\s+|ulcer\s+)?area\s+reduction|reduction\s+in\s+wound\s+area',
         'WOUND_AREA_REDUCTION'),
        (r'time\s+to\s+(?:complete\s+)?(?:healing|closure)|healing\s+time', 'TIME_TO_HEALING'),
        (r'healing\s+rate|rate\s+of\s+healing', 'HEALING_RATE'),
        (r'(?:major\s+|minor\s+)?amputation|limb\s+salvage', 'AMPUTATION'),
        (r'(?:wound\s+)?infection', 'INFECTION'),
        (r'graft\s+(?:take|survival)|engraftment', 'GRAFT_TAKE'),
    ],
    'context_patterns': [
        r'\d+\s+atmospheres|\d+\s+sessions', r'twice\s+weekly\s+application',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_wound_healing_subspecialty(text: str) -> Tuple[str, float]:
    """Detect burns / wound-healing trial subspecialty.
    Returns (subspecialty, confidence). Subspecialties: burns, chronic_wounds,
    surgical_wounds, adjuncts, general_wound."""
    text_lower = text.lower()
    scores = {'burns': 0, 'chronic_wounds': 0, 'surgical_wounds': 0, 'adjuncts': 0}
    for kw in BURNS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['burns'] += 1
    for kw in CHRONIC_WOUNDS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['chronic_wounds'] += 1
    for kw in SURGICAL_WOUNDS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['surgical_wounds'] += 1
    for kw in ADJUNCTS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['adjuncts'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_wound', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_wound_healing_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'burns': BURNS_PATTERNS['endpoint_patterns'],
        'chronic_wounds': CHRONIC_WOUNDS_PATTERNS['endpoint_patterns'],
        'surgical_wounds': SURGICAL_WOUNDS_PATTERNS['endpoint_patterns'],
        'adjuncts': ADJUNCTS_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_wound_healing_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical wound-healing endpoint, preferring the LONGEST
    matching alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in WOUND_HEALING_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
