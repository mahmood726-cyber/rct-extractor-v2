"""
Otitis media (middle-ear) Subspecialty Patterns and Endpoints.

Built for the same meta-analysis workflow as the pneumonia / allergic_rhinitis
profiles, but for OTITIS MEDIA specifically -- a distinct ENT disease (middle-ear
inflammation) not targeted by any existing profile. Otitis-media RCTs report an
endpoint vocabulary anchored on clinical treatment failure / cure, recurrence,
middle-ear effusion resolution, otorrho?ea (ear discharge), hearing level on
audiometry and the need for tympanostomy tubes (grommets).

Subspecialties:
- aom (acute otitis media):
    clinical treatment failure (RR/OR), clinical cure / resolution (RR/OR),
    recurrence (RR/OR), tympanic-membrane perforation / otorrho?ea (RR/OR),
    ear pain (MD). Antibiotic vs placebo / watchful waiting.
- ome (otitis media with effusion / "glue ear"):
    middle-ear effusion resolution (RR/OR), hearing level on audiometry (dB; MD),
    need for tympanostomy tubes (RR/OR).
- prevention (recurrent AOM / vaccines / tubes):
    AOM recurrence (RR/OR), tympanostomy-tube insertion (RR/OR). Pneumococcal
    conjugate vaccine, xylitol, prophylaxis.

Effect measures: binary (treatment failure, cure, recurrence, effusion
resolution, perforation/otorrho?ea, tube insertion) -> RR/OR/RD; continuous
(hearing level in dB, ear-pain score) -> MD/SMD. None is log-normal.

British/American spelling: ear discharge is OTORRHOEA (British) vs OTORRHEA
(American) -- the British form inserts an extra 'o' before 'ea' -> 'otorrho?ea',
NOT '[oe]a'. 'tympanostomy tube' (US) == 'grommet' / 'ventilation tube' (UK).
Both handled below.

Routing note: this profile claims the middle-ear anchors (otitis media, AOM, OME,
glue ear, tympanostomy tube / grommet, myringotomy, middle-ear effusion,
otorrho?ea, tympanic membrane) that no existing profile claims.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# OTITIS MEDIA ENDPOINTS
# ============================================================

OTITIS_MEDIA_ENDPOINTS = {
    'TREATMENT_FAILURE': {
        'aliases': ['clinical treatment failure', 'treatment failure', 'clinical failure',
                    'failure rate', 'overall treatment failure', 'persistent symptoms',
                    'symptomatic failure'],
        'subspecialty': 'aom',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'CLINICAL_CURE': {
        'aliases': ['clinical cure', 'clinical resolution', 'clinical success',
                    'cure rate', 'symptom resolution', 'clinical recovery',
                    'resolution of symptoms', 'clinical response'],
        'subspecialty': 'aom',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'AOM_RECURRENCE': {
        'aliases': ['recurrence', 'aom recurrence', 'recurrent acute otitis media',
                    'recurrent otitis media', 'recurrence rate', 'recurrent aom',
                    'number of recurrences', 'episodes of acute otitis media'],
        'subspecialty': 'prevention',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'EFFUSION_RESOLUTION': {
        'aliases': ['middle ear effusion', 'effusion resolution', 'resolution of effusion',
                    'middle-ear effusion', 'persistent effusion', 'effusion clearance',
                    'resolution of middle ear effusion', 'tympanometry resolution'],
        'subspecialty': 'ome',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'OTORRHOEA': {
        'aliases': ['otorrhoea', 'otorrhea', 'ear discharge', 'tympanic membrane perforation',
                    'tympanic-membrane perforation', 'perforation', 'acute otorrhoea',
                    'acute otorrhea', 'tube otorrhoea', 'tube otorrhea'],
        'subspecialty': 'aom',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'HEARING_LEVEL': {
        'aliases': ['hearing level', 'hearing threshold', 'audiometry',
                    'pure-tone average', 'pure tone average', 'air conduction threshold',
                    'mean hearing level', 'hearing loss', 'pta'],
        'subspecialty': 'ome',
        'measure_types': ['MD', 'SMD']
    },
    'EAR_PAIN': {
        'aliases': ['ear pain', 'otalgia', 'pain score', 'ear pain score',
                    'pain resolution', 'earache', 'otalgia score'],
        'subspecialty': 'aom',
        'measure_types': ['MD', 'SMD']
    },
    'TUBE_INSERTION': {
        'aliases': ['tympanostomy tube', 'tympanostomy tubes', 'ventilation tube',
                    'grommet', 'grommets', 'tube insertion', 'need for tympanostomy tubes',
                    'ear tube insertion', 'myringotomy with tubes'],
        'subspecialty': 'ome',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# AOM PATTERNS (acute otitis media)
# ============================================================

AOM_PATTERNS = {
    'detection_keywords': [
        r'acute\s+otitis\s+media|\baom\b', r'otitis\s+media',
        r'ear\s+infection', r'otalgia|ear\s+pain',
        r'otorrho?ea|ear\s+discharge', r'tympanic\s+membrane',
        r'amoxicillin(?:[- ]clavulanate)?', r'watchful\s+waiting|observation',
    ],
    'endpoint_patterns': [
        (r'clinical\s+(?:treatment\s+)?failure|treatment\s+failure|failure\s+rate|'
         r'persistent\s+symptoms|symptomatic\s+failure', 'TREATMENT_FAILURE'),
        (r'clinical\s+(?:cure|resolution|success|recovery|response)|cure\s+rate|'
         r'(?:symptom|resolution\s+of\s+symptoms)', 'CLINICAL_CURE'),
        (r'otorrho?ea|ear\s+discharge|tympanic[- ]membrane\s+perforation|perforation', 'OTORRHOEA'),
        (r'ear\s+pain(?:\s+score)?|otalgia(?:\s+score)?|\bearache\b|pain\s+resolution', 'EAR_PAIN'),
    ],
    'context_patterns': [
        r'\bfever\b', r'tympanocentesis', r'at\s+(?:day)\s+\d+', r'children',
    ]
}


# ============================================================
# OME PATTERNS (otitis media with effusion)
# ============================================================

OME_PATTERNS = {
    'detection_keywords': [
        r'otitis\s+media\s+with\s+effusion|\bome\b', r'glue\s+ear',
        r'middle[- ]ear\s+effusion', r'tympanostomy\s+tube|grommet|ventilation\s+tube',
        r'myringotomy', r'tympanometry', r'hearing\s+(?:level|threshold|loss)|audiometry',
    ],
    'endpoint_patterns': [
        (r'middle[- ]ear\s+effusion|effusion\s+(?:resolution|clearance)|resolution\s+of\s+effusion|'
         r'persistent\s+effusion', 'EFFUSION_RESOLUTION'),
        (r'tympanostomy\s+tubes?|ventilation\s+tubes?|grommets?|tube\s+insertion|'
         r'myringotomy\s+with\s+tubes', 'TUBE_INSERTION'),
        (r'hearing\s+(?:level|threshold|loss)|pure[- ]tone\s+average|audiometry|'
         r'air\s+conduction\s+threshold|\bpta\b', 'HEARING_LEVEL'),
    ],
    'context_patterns': [
        r'\bdecibels?\b|\bdb\b', r'tympanogram', r'at\s+(?:month|week)\s+\d+',
    ]
}


# ============================================================
# PREVENTION PATTERNS (recurrent AOM / vaccines / prophylaxis)
# ============================================================

PREVENTION_PATTERNS = {
    'detection_keywords': [
        r'recurrent\s+(?:acute\s+)?otitis\s+media', r'recurrence',
        r'pneumococcal\s+conjugate\s+vaccine|\bpcv\b', r'prophylaxis',
        r'xylitol', r'tympanostomy\s+tube|grommet',
    ],
    'endpoint_patterns': [
        (r'(?:aom\s+)?recurrence(?:\s+rate)?|recurrent\s+(?:acute\s+)?otitis\s+media|'
         r'number\s+of\s+recurrences|episodes\s+of\s+acute\s+otitis\s+media', 'AOM_RECURRENCE'),
        (r'tympanostomy\s+tubes?|ventilation\s+tubes?|grommets?|tube\s+insertion', 'TUBE_INSERTION'),
    ],
    'context_patterns': [
        r'per[- ]child[- ]year', r'incidence\s+rate', r'at\s+(?:month|year)\s+\d+',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_otitis_media_subspecialty(text: str) -> Tuple[str, float]:
    """Detect otitis-media trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: aom, ome, prevention."""
    text_lower = text.lower()
    scores = {'aom': 0, 'ome': 0, 'prevention': 0}
    for kw in AOM_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['aom'] += 1
    for kw in OME_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['ome'] += 1
    for kw in PREVENTION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['prevention'] += 1

    # An "otitis media with effusion" / "glue ear" anchor must beat the generic
    # AOM overlap; a "recurrent" anchor tips toward prevention.
    if re.search(r'otitis\s+media\s+with\s+effusion|\bome\b|glue\s+ear|middle[- ]ear\s+effusion',
                 text_lower):
        scores['ome'] += 1
    elif re.search(r'recurrent\s+(?:acute\s+)?otitis\s+media|prophylaxis|'
                   r'pneumococcal\s+conjugate\s+vaccine', text_lower):
        scores['prevention'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('aom', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_otitis_media_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'aom': AOM_PATTERNS['endpoint_patterns'],
        'ome': OME_PATTERNS['endpoint_patterns'],
        'prevention': PREVENTION_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_otitis_media_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical endpoint, preferring the LONGEST matching alias so
    specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in OTITIS_MEDIA_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
