"""
Trachoma Subspecialty Patterns and Endpoints

Built for the same African-student meta-analysis workflow as the malaria, HIV,
typhoid and schistosomiasis profiles. Trachoma (ocular *Chlamydia trachomatis*)
is the leading infectious cause of blindness and a top-priority African
neglected tropical disease; control follows the WHO SAFE strategy
(Surgery, Antibiotics, Facial cleanliness, Environmental improvement). Trachoma
RCTs report a distinct endpoint vocabulary (the WHO simplified grading codes TF,
TI, TS, TT, CO) the generic effect-size engine does not recognise on its own.

Subspecialties:
- Antibiotic MDA (mass drug administration): active-trachoma / TF prevalence
  (trachomatous inflammation-follicular), TI (intense), and ocular-chlamydia
  infection prevalence / chlamydial load (qPCR). Drugs: azithromycin (single
  oral dose, the mainstay), tetracycline 1% eye ointment, doxycycline,
  erythromycin; annual vs biannual MDA rounds.
- Surgery for trichiasis: trachomatous trichiasis (TT) prevalence and
  post-operative trichiasis recurrence, corneal opacity (CO) / blindness, visual
  acuity. Procedures: bilamellar tarsal rotation (BLTR), posterior lamellar
  tarsal rotation (PLTR), epilation.
- Transmission (F&E): reinfection / re-emergence of infection, facial
  cleanliness ("clean face", ocular/nasal discharge), fly density / fly-eye
  contact (Musca sorbens), latrine coverage.
- Mortality / safety of MDA: all-cause childhood mortality (the MORDOR signal
  that azithromycin MDA reduces under-5 mortality), adverse events, and
  macrolide (azithromycin) antimicrobial resistance.

Effect measures follow what these trials report: binary (active trachoma / TF,
TT, ocular infection prevalence, reinfection, clean face, corneal opacity,
mortality, adverse events, resistance) -> RR/OR/RD; incidence / reinfection /
mortality -> IRR/HR; continuous (visual acuity -> MD/SMD; chlamydial load and
fly counts are right-skewed -> log scale / GMR).
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# TRACHOMA ENDPOINTS
# ============================================================

TRACHOMA_ENDPOINTS = {
    # --- Antibiotic MDA (active trachoma + ocular chlamydia) ---
    'ACTIVE_TRACHOMA': {
        'aliases': ['active trachoma', 'trachomatous inflammation-follicular',
                    'trachomatous inflammation follicular', 'follicular trachoma',
                    'tf prevalence', 'active trachoma prevalence', 'tf', 'follicular',
                    'trachomatous inflammation'],
        'subspecialty': 'mda',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'INTENSE_TRACHOMA': {
        'aliases': ['intense trachoma', 'trachomatous inflammation-intense',
                    'trachomatous inflammation intense', 'ti prevalence', 'ti'],
        'subspecialty': 'mda',
        'measure_types': ['RR', 'OR']
    },
    'OCULAR_CHLAMYDIA': {
        'aliases': ['ocular chlamydia', 'ocular chlamydial infection',
                    'chlamydia trachomatis infection', 'chlamydial infection',
                    'ocular infection', 'infection prevalence', 'chlamydial prevalence',
                    'c. trachomatis', 'pcr-positive', 'pcr positive'],
        'subspecialty': 'mda',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'INFECTION_LOAD': {
        'aliases': ['chlamydial load', 'infection load', 'organism load',
                    'ocular chlamydial load', 'chlamydia load', 'bacterial load',
                    'load of infection'],
        'subspecialty': 'mda',
        'measure_types': ['GMR', 'MD', 'SMD']
    },

    # --- Surgery for trichiasis ---
    'TRICHIASIS': {
        'aliases': ['trachomatous trichiasis', 'trichiasis', 'tt prevalence',
                    'in-turned eyelash', 'in-turned eyelashes', 'entropion', 'tt'],
        'subspecialty': 'surgery',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'TRICHIASIS_RECURRENCE': {
        'aliases': ['trichiasis recurrence', 'recurrent trichiasis',
                    'tt recurrence', 'postoperative trichiasis',
                    'post-operative trichiasis', 'recurrence of trichiasis',
                    'recurrence'],
        'subspecialty': 'surgery',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'CORNEAL_OPACITY': {
        'aliases': ['corneal opacity', 'corneal opacification', 'corneal scarring',
                    'corneal scar', 'trachomatous corneal', 'blindness',
                    'visual impairment'],
        'subspecialty': 'surgery',
        'measure_types': ['RR', 'OR']
    },
    'VISUAL_ACUITY': {
        'aliases': ['visual acuity', 'logmar', 'best-corrected visual acuity',
                    'best corrected visual acuity', 'bcva', 'acuity'],
        'subspecialty': 'surgery',
        'measure_types': ['MD', 'SMD']
    },

    # --- Transmission (F&E: facial cleanliness + environment) ---
    'REINFECTION': {
        'aliases': ['reinfection', 're-infection', 're-emergence', 'reemergence',
                    'return of infection', 'incidence of infection',
                    'incident infection', 'new infection', 'infection incidence'],
        'subspecialty': 'transmission',
        'measure_types': ['IRR', 'HR', 'RR']
    },
    'CLEAN_FACE': {
        'aliases': ['clean face', 'facial cleanliness', 'unclean face',
                    'ocular discharge', 'nasal discharge', 'face washing',
                    'dirty face'],
        'subspecialty': 'transmission',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'FLY_DENSITY': {
        'aliases': ['fly density', 'fly-eye contact', 'fly eye contact',
                    'musca sorbens', 'fly count', 'fly population', 'fly-eye'],
        'subspecialty': 'transmission',
        'measure_types': ['IRR', 'MD', 'GMR']
    },

    # --- Mortality / safety of MDA ---
    'MORTALITY': {
        'aliases': ['all-cause mortality', 'childhood mortality', 'child mortality',
                    'under-5 mortality', 'under-five mortality', 'mortality',
                    'death', 'survival', 'all cause mortality'],
        'subspecialty': 'mortality_safety',
        'measure_types': ['RR', 'OR', 'IRR', 'HR']
    },
    'ADVERSE_EVENTS': {
        'aliases': ['adverse event', 'adverse events', 'serious adverse event',
                    'side effect', 'side effects', 'gastrointestinal',
                    'adverse reaction', 'tolerability'],
        'subspecialty': 'mortality_safety',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'MACROLIDE_RESISTANCE': {
        'aliases': ['macrolide resistance', 'azithromycin resistance',
                    'antimicrobial resistance', 'antibiotic resistance',
                    'macrolide-resistant', 'resistant', 'resistance'],
        'subspecialty': 'mortality_safety',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# MDA PATTERNS (antibiotic mass drug administration)
# ============================================================

MDA_PATTERNS = {
    'detection_keywords': [
        r'azithromycin', r'\bmda\b', r'mass\s+drug\s+administration',
        r'mass\s+(?:antibiotic\s+)?(?:treatment|distribution)',
        r'tetracycline\s+(?:eye\s+)?ointment', r'doxycycline', r'erythromycin',
        r'active\s+trachoma', r'trachomatous\s+inflammation',
        r'follicular\s+trachoma', r'\btf\b', r'\bti\b',
        r'ocular\s+chlamydia', r'chlamydia(?:l)?\s+(?:trachomatis\s+)?infection',
        r'chlamydial\s+load', r'\bpcr\b', r'annual\s+(?:treatment|mda|round)',
        r'biannual|bi-annual|twice[- ]yearly', r'antibiotic',
    ],
    'endpoint_patterns': [
        (r'active\s+trachoma|trachomatous\s+inflammation[\s-]*follicular|'
         r'follicular\s+trachoma|\btf\b', 'ACTIVE_TRACHOMA'),
        (r'intense\s+trachoma|trachomatous\s+inflammation[\s-]*intense|\bti\b',
         'INTENSE_TRACHOMA'),
        (r'ocular\s+chlamydia(?:l)?(?:\s+infection)?|chlamydia(?:l)?\s+'
         r'(?:trachomatis\s+)?infection|infection\s+prevalence|'
         r'pcr[- ]?positive|c\.\s*trachomatis', 'OCULAR_CHLAMYDIA'),
        (r'chlamydial?\s+load|organism\s+load|infection\s+load|bacterial\s+load',
         'INFECTION_LOAD'),
    ],
    'context_patterns': [
        r'single\s+(?:oral\s+)?dose', r'\d+\s*mg\/kg', r'who\s+grading',
        r'upper\s+tarsal\s+conjunctiva', r'baseline\s+prevalence',
    ]
}


# ============================================================
# SURGERY PATTERNS (trichiasis surgery)
# ============================================================

SURGERY_PATTERNS = {
    'detection_keywords': [
        r'trichiasis', r'\btt\b', r'bilamellar\s+tarsal\s+rotation', r'\bbltr\b',
        r'posterior\s+lamellar\s+tarsal\s+rotation', r'\bpltr\b', r'epilation',
        r'eyelid\s+surgery', r'lid\s+surgery', r'entropion', r'in-turned\s+eyelash',
        r'trichiasis\s+surgery', r'corneal\s+opacity', r'recurren',
        r'visual\s+acuity', r'blindness',
    ],
    'endpoint_patterns': [
        (r'trichiasis\s+recurrence|recurren\w*\s+trichiasis|tt\s+recurrence|'
         r'post[- ]?operative\s+trichiasis|recurrence', 'TRICHIASIS_RECURRENCE'),
        (r'trachomatous\s+trichiasis|trichiasis|in[- ]turned\s+eyelash|'
         r'entropion|\btt\b', 'TRICHIASIS'),
        (r'corneal\s+opacit\w*|corneal\s+scar\w*|blindness|visual\s+impairment',
         'CORNEAL_OPACITY'),
        (r'visual\s+acuity|logmar|best[- ]corrected\s+visual\s+acuity|\bbcva\b',
         'VISUAL_ACUITY'),
    ],
    'context_patterns': [
        r'tarsal\s+plate', r'eyelash', r'follow[- ]up\s+at\s+\d+\s+months?',
        r'\blogmar\b', r'epilation',
    ]
}


# ============================================================
# TRANSMISSION PATTERNS (facial cleanliness + environment)
# ============================================================

TRANSMISSION_PATTERNS = {
    'detection_keywords': [
        r'facial\s+cleanliness', r'face[- ]washing', r'clean\s+face',
        r'ocular\s+discharge', r'nasal\s+discharge', r'\bfly\b|flies',
        r'musca\s+sorbens', r'fly\s+control', r'environmental\s+improvement',
        r'\blatrine', r'\bf\s*(?:&|and)\s*e\b', r'reinfection|re-?infection',
        r'transmission', r'water\s+(?:supply|access)', r'sanitation',
    ],
    'endpoint_patterns': [
        (r're[- ]?infection|re[- ]?emergence|return\s+of\s+infection|'
         r'incidence\s+of\s+infection|incident\s+infection|new\s+infection',
         'REINFECTION'),
        (r'clean\s+face|facial\s+cleanliness|unclean\s+face|dirty\s+face|'
         r'(?:ocular|nasal)\s+discharge', 'CLEAN_FACE'),
        (r'fly[- ]eye\s+contact|fly\s+density|fly\s+count|fly\s+population|'
         r'musca\s+sorbens', 'FLY_DENSITY'),
    ],
    'context_patterns': [
        r'per\s+(?:100\s+)?person[- ]years', r'cluster[- ]randomi[sz]ed',
        r'\bfly[- ]eye\b', r'months?\s+of\s+follow[- ]up',
    ]
}


# ============================================================
# MORTALITY / SAFETY PATTERNS (safety of MDA)
# ============================================================

MORTALITY_SAFETY_PATTERNS = {
    'detection_keywords': [
        r'childhood\s+mortality', r'child\s+mortality', r'all[- ]cause\s+mortality',
        r'under[- ](?:5|five)\s+mortality', r'\bmordor\b', r'mortality', r'\bdeath',
        r'adverse\s+event', r'serious\s+adverse', r'side\s+effect',
        r'macrolide\s+resistance', r'azithromycin\s+resistance',
        r'antimicrobial\s+resistance', r'antibiotic\s+resistance', r'safety',
        r'tolerability', r'vomiting',
    ],
    'endpoint_patterns': [
        (r'(?:all[- ]cause|child(?:hood)?|under[- ](?:5|five))\s+mortality|'
         r'mortality|\bdeaths?\b|survival', 'MORTALITY'),
        (r'serious\s+adverse\s+events?|adverse\s+events?|adverse\s+reactions?|'
         r'side[- ]effects?|tolerability', 'ADVERSE_EVENTS'),
        (r'macrolide[- ]resistan\w*|azithromycin[- ]resistan\w*|'
         r'anti(?:microbial|biotic)[- ]resistan\w*|resistance', 'MACROLIDE_RESISTANCE'),
    ],
    'context_patterns': [
        r'per\s+1000\s+(?:child[- ]years|person[- ]years)', r'nasopharyngeal',
        r'\bmordor\b', r'community[- ]randomi[sz]ed',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_trachoma_subspecialty(text: str) -> Tuple[str, float]:
    """Detect trachoma trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: mda, surgery, transmission, mortality_safety,
    general_trachoma."""
    text_lower = text.lower()
    scores = {'mda': 0, 'surgery': 0, 'transmission': 0, 'mortality_safety': 0}
    for kw in MDA_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mda'] += 1
    for kw in SURGERY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['surgery'] += 1
    for kw in TRANSMISSION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['transmission'] += 1
    for kw in MORTALITY_SAFETY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mortality_safety'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_trachoma', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_trachoma_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'mda': MDA_PATTERNS['endpoint_patterns'],
        'surgery': SURGERY_PATTERNS['endpoint_patterns'],
        'transmission': TRANSMISSION_PATTERNS['endpoint_patterns'],
        'mortality_safety': MORTALITY_SAFETY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_trachoma_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical trachoma endpoint, preferring the LONGEST matching
    alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in TRACHOMA_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
