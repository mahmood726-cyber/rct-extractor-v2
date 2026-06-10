"""
Gastroenterology (luminal / hepato-luminal) Subspecialty Patterns and Endpoints.

Built for the same meta-analysis workflow as the malaria / HIV / hepatitis /
respiratory / stroke / nephrology profiles. Gastroenterology RCTs report an
endpoint vocabulary anchored on disease-activity indices (CDAI, Mayo score),
mucosal/endoscopic outcomes, eradication rates, oesophagitis healing, and
histological resolution that the generic effect-size engine does not recognise on
its own.

Subspecialties:
- IBD (ulcerative colitis / Crohn's disease):
    clinical remission (RR/OR), clinical response (RR/OR), endoscopic remission /
    mucosal healing (RR/OR), steroid-free remission (RR/OR), CDAI change (MD),
    Mayo score (MD).
- H. pylori (Helicobacter pylori eradication):
    eradication rate (RR/OR).
- GERD (gastro-oesophageal reflux disease):
    erosive-oesophagitis healing (RR/OR), heartburn-free days / symptom
    resolution (RR/OR/MD).
- MASH (metabolic dysfunction-associated steatohepatitis / NAFLD/NASH):
    NASH/MASH resolution without worsening fibrosis (RR/OR), >=1-stage fibrosis
    improvement (RR/OR), MRI-PDFF liver-fat reduction (MD).

Effect measures follow what these trials report: binary (clinical/endoscopic
remission, eradication, oesophagitis healing, NASH resolution, fibrosis
improvement) -> RR/OR; continuous (CDAI, Mayo score, MRI-PDFF liver fat) -> MD.

Routing note (coordinated with the existing hepatitis specialty): gastroenterology
anchors strictly on luminal-GI and MASH-specific terms (ulcerative colitis,
Crohn's disease, IBD, Mayo score, CDAI, mucosal healing, Helicobacter pylori,
erosive oesophagitis, GERD, NASH, MASH, NAFLD, MAFLD). We deliberately do NOT
claim bare 'hepatitis', 'cirrhosis', 'HCC', or 'liver fibrosis' alone -- a VIRAL
hepatitis trial (HBV/HCV, SVR, HBsAg) routes to the existing `hepatitis`
specialty. Only MASH/NASH/NAFLD-specific liver terms count here. We also prefer
'ulcerative colitis' over bare 'colitis' to avoid colliding with unrelated
colitides.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# GASTROENTEROLOGY ENDPOINTS
# ============================================================

GASTROENTEROLOGY_ENDPOINTS = {
    # --- IBD (ulcerative colitis / Crohn's disease) ---
    'CLINICAL_REMISSION': {
        'aliases': ['clinical remission', 'clinical and endoscopic remission',
                    'remission', 'symptomatic remission', 'corticosteroid-free clinical remission'],
        'subspecialty': 'ibd',
        'measure_types': ['RR', 'OR']
    },
    'CLINICAL_RESPONSE': {
        'aliases': ['clinical response', 'symptomatic response', 'clinical improvement'],
        'subspecialty': 'ibd',
        'measure_types': ['RR', 'OR']
    },
    'ENDOSCOPIC_REMISSION': {
        'aliases': ['endoscopic remission', 'mucosal healing', 'endoscopic improvement',
                    'endoscopic healing', 'endoscopic response', 'mucosal remission'],
        'subspecialty': 'ibd',
        'measure_types': ['RR', 'OR']
    },
    'STEROID_FREE_REMISSION': {
        'aliases': ['steroid-free remission', 'steroid free remission',
                    'corticosteroid-free remission', 'corticosteroid free remission',
                    'steroid-free clinical remission'],
        'subspecialty': 'ibd',
        'measure_types': ['RR', 'OR']
    },
    'CDAI_CHANGE': {
        'aliases': ["crohn's disease activity index", 'crohn disease activity index',
                    'cdai', 'change in cdai', 'cdai score', 'cdai reduction'],
        'subspecialty': 'ibd',
        'measure_types': ['MD', 'SMD']
    },
    'MAYO_SCORE': {
        'aliases': ['mayo score', 'total mayo score', 'partial mayo score',
                    'mayo clinic score', 'change in mayo score'],
        'subspecialty': 'ibd',
        'measure_types': ['MD', 'SMD']
    },

    # --- H. pylori eradication ---
    'ERADICATION': {
        'aliases': ['eradication', 'eradication rate', 'h. pylori eradication',
                    'helicobacter pylori eradication', 'h pylori eradication',
                    'successful eradication', 'cure rate'],
        'subspecialty': 'hpylori',
        'measure_types': ['RR', 'OR']
    },

    # --- GERD ---
    'HEALING_ESOPHAGITIS': {
        'aliases': ['healing of erosive esophagitis', 'erosive esophagitis healing',
                    'esophagitis healing', 'oesophagitis healing', 'mucosal healing of esophagitis',
                    'endoscopic healing of esophagitis', 'healed esophagitis'],
        'subspecialty': 'gerd',
        'measure_types': ['RR', 'OR']
    },
    'HEARTBURN_FREE': {
        'aliases': ['heartburn-free days', 'heartburn free days', 'heartburn-free',
                    'symptom resolution', 'heartburn relief', 'sustained heartburn resolution',
                    'complete resolution of heartburn', 'symptomatic relief'],
        'subspecialty': 'gerd',
        'measure_types': ['RR', 'OR', 'MD']
    },

    # --- MASH / NASH / NAFLD ---
    'NASH_RESOLUTION': {
        'aliases': ['nash resolution', 'mash resolution', 'resolution of nash',
                    'resolution of mash', 'nash resolution without worsening of fibrosis',
                    'resolution of steatohepatitis', 'steatohepatitis resolution'],
        'subspecialty': 'mash',
        'measure_types': ['RR', 'OR']
    },
    'FIBROSIS_IMPROVEMENT': {
        'aliases': ['fibrosis improvement', 'improvement in fibrosis',
                    'at least 1 stage fibrosis improvement', '1-stage fibrosis improvement',
                    'one-stage improvement in fibrosis', 'fibrosis improvement without worsening of nash',
                    'fibrosis regression'],
        'subspecialty': 'mash',
        'measure_types': ['RR', 'OR']
    },
    'LIVER_FAT': {
        'aliases': ['mri-pdff', 'mri pdff', 'liver fat', 'liver fat content',
                    'hepatic fat fraction', 'proton density fat fraction',
                    'reduction in liver fat', 'liver fat reduction', 'relative liver fat reduction'],
        'subspecialty': 'mash',
        'measure_types': ['MD', 'SMD']
    },
}


# ============================================================
# IBD PATTERNS (ulcerative colitis / Crohn's disease)
# ============================================================

IBD_PATTERNS = {
    'detection_keywords': [
        r'ulcerative\s+colitis|\buc\b',
        r"crohn'?s?\s+disease|crohn\s+disease",
        r'inflammatory\s+bowel\s+disease|\bibd\b',
        r'mayo\s+(?:clinic\s+)?score', r'\bcdai\b|crohn\W*\s+disease\s+activity\s+index',
        r'mucosal\s+healing', r'endoscopic\s+(?:remission|improvement|healing)',
        r'steroid[- ]free\s+remission|corticosteroid[- ]free\s+remission',
        r'\bcalprotectin\b', r'\bvedolizumab\b|\bustekinumab\b|\binfliximab\b',
    ],
    'endpoint_patterns': [
        # endoscopic/mucosal BEFORE bare clinical remission so the more specific
        # estimand wins when both terms sit near the same proportion.
        (r'endoscopic\s+(?:remission|improvement|healing|response)|mucosal\s+healing|'
         r'mucosal\s+remission', 'ENDOSCOPIC_REMISSION'),
        (r'steroid[- ]free\s+(?:clinical\s+)?remission|'
         r'corticosteroid[- ]free\s+(?:clinical\s+)?remission', 'STEROID_FREE_REMISSION'),
        (r'\bcdai\b|crohn\W*\s+disease\s+activity\s+index|change\s+in\s+cdai', 'CDAI_CHANGE'),
        (r'(?:total\s+|partial\s+)?mayo\s+(?:clinic\s+)?score|change\s+in\s+mayo', 'MAYO_SCORE'),
        (r'clinical\s+remission|symptomatic\s+remission|\bremission\b', 'CLINICAL_REMISSION'),
        (r'clinical\s+response|symptomatic\s+response|clinical\s+improvement', 'CLINICAL_RESPONSE'),
    ],
    'context_patterns': [
        r'week\s+(?:8|12|52)', r'induction|maintenance', r'biologic[- ]naive',
    ]
}


# ============================================================
# H. PYLORI PATTERNS (eradication)
# ============================================================

HPYLORI_PATTERNS = {
    'detection_keywords': [
        r'helicobacter\s+pylori|\bh\.?\s*pylori\b',
        r'eradication(?:\s+rate)?', r'triple\s+therapy|quadruple\s+therapy',
        r'bismuth(?:\s+quadruple)?\s+therapy', r'vonoprazan',
        r'urea\s+breath\s+test|\bubt\b', r'clarithromycin\s+resistance',
    ],
    'endpoint_patterns': [
        (r'(?:h\.?\s*pylori\s+|helicobacter\s+pylori\s+)?eradication(?:\s+rate)?|'
         r'successful\s+eradication|cure\s+rate', 'ERADICATION'),
    ],
    'context_patterns': [
        r'urea\s+breath\s+test', r'per[- ]protocol|intention[- ]to[- ]treat', r'14[- ]day',
    ]
}


# ============================================================
# GERD PATTERNS (gastro-oesophageal reflux)
# ============================================================

GERD_PATTERNS = {
    'detection_keywords': [
        r'gastro[- ]?esophageal\s+reflux|gastro[- ]?oesophageal\s+reflux|\bgerd\b|\bgord\b',
        r'erosive\s+(?:o?esophagitis|reflux)', r'reflux\s+(?:disease|esophagitis|oesophagitis)',
        r'heartburn', r'\bla\s+grade\b|los\s+angeles\s+(?:grade|classification)',
        r'proton[- ]pump\s+inhibitor|\bppi\b', r'vonoprazan',
    ],
    'endpoint_patterns': [
        (r'(?:erosive\s+)?(?:o?esophagitis|reflux)\s+healing|healing\s+of\s+erosive\s+'
         r'(?:o?esophagitis|reflux)|healed\s+(?:o?esophagitis)|endoscopic\s+healing\s+of\s+'
         r'(?:o?esophagitis)', 'HEALING_ESOPHAGITIS'),
        (r'heartburn[- ]free(?:\s+days)?|heartburn\s+(?:relief|resolution)|'
         r'(?:symptom|symptomatic)\s+(?:resolution|relief)', 'HEARTBURN_FREE'),
    ],
    'context_patterns': [
        r'week\s+(?:4|8)', r'\bla\s+grade\s+[a-d]\b', r'24[- ]hour\s+ph',
    ]
}


# ============================================================
# MASH PATTERNS (metabolic dysfunction-associated steatohepatitis)
# ============================================================

MASH_PATTERNS = {
    'detection_keywords': [
        r'nonalcoholic\s+steatohepatitis|non[- ]alcoholic\s+steatohepatitis|\bnash\b',
        r'metabolic\s+dysfunction[- ]associated\s+steatohepatitis|\bmash\b',
        r'nonalcoholic\s+fatty\s+liver\s+disease|non[- ]alcoholic\s+fatty\s+liver|\bnafld\b',
        r'metabolic\s+dysfunction[- ]associated\s+(?:fatty\s+liver|steatotic\s+liver)|\bmafld\b|\bmasld\b',
        r'hepatic\s+steatosis|liver\s+steatosis', r'mri[- ]?pdff|proton\s+density\s+fat\s+fraction',
        r'\bresmetirom\b', r'nash\s+resolution|mash\s+resolution',
    ],
    'endpoint_patterns': [
        (r'(?:nash|mash|steatohepatitis)\s+resolution|resolution\s+of\s+(?:nash|mash|steatohepatitis)',
         'NASH_RESOLUTION'),
        (r'fibrosis\s+improvement|improvement\s+in\s+fibrosis|'
         r'(?:at\s+least\s+|>=?\s*|≥\s*)?(?:1|one)[- ]stage\s+(?:improvement\s+in\s+)?fibrosis|'
         r'fibrosis\s+regression', 'FIBROSIS_IMPROVEMENT'),
        (r'mri[- ]?pdff|proton\s+density\s+fat\s+fraction|liver\s+fat(?:\s+content)?|'
         r'hepatic\s+fat\s+fraction', 'LIVER_FAT'),
    ],
    'context_patterns': [
        r'week\s+(?:48|52|72)', r'biopsy|histolog', r'fibrosis\s+stage\s+f[1-4]',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_gastroenterology_subspecialty(text: str) -> Tuple[str, float]:
    """Detect gastroenterology trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: ibd, hpylori, gerd, mash."""
    text_lower = text.lower()
    scores = {'ibd': 0, 'hpylori': 0, 'gerd': 0, 'mash': 0}
    for kw in IBD_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['ibd'] += 1
    for kw in HPYLORI_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['hpylori'] += 1
    for kw in GERD_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['gerd'] += 1
    for kw in MASH_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mash'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('ibd', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_gastroenterology_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'ibd': IBD_PATTERNS['endpoint_patterns'],
        'hpylori': HPYLORI_PATTERNS['endpoint_patterns'],
        'gerd': GERD_PATTERNS['endpoint_patterns'],
        'mash': MASH_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_gastroenterology_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical gastroenterology endpoint, preferring the LONGEST
    matching alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in GASTROENTEROLOGY_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
