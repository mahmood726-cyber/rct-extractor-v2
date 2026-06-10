"""
Ophthalmology (eye) Subspecialty Patterns and Endpoints.

Built for the same meta-analysis workflow as the malaria / HIV / hepatitis /
respiratory / stroke / nephrology profiles. Ophthalmology RCTs report an endpoint
vocabulary anchored on a handful of standardised measures (best-corrected visual
acuity in ETDRS letters, central retinal thickness on OCT, intraocular pressure
in mmHg, OSDI / corneal-staining / Schirmer for dry eye) that the generic
effect-size engine does not recognise on its own.

Subspecialties:
- AMD (neovascular age-related macular degeneration):
    BCVA change (ETDRS letters; MD), >=15-letter vision gain (RR/OR), <15-letter
    vision loss / avoidance of loss (RR/OR), central retinal/subfield thickness
    change on OCT (MD).
- DME (diabetic macular edema):
    same retina family (BCVA change, >=15-letter gain, CRT change) plus >=2-step
    diabetic-retinopathy severity improvement (RR/OR).
- Glaucoma:
    intraocular-pressure reduction (mmHg; MD), reaching target IOP (RR/OR),
    visual-field progression (HR/RR).
- Dry eye:
    Ocular Surface Disease Index (OSDI; MD), corneal staining (MD), Schirmer
    test (MD).

Effect measures follow what these trials report: binary (>=15-letter gain,
avoidance of >=15-letter loss, target IOP, >=2-step DR improvement) -> RR/OR/RD;
time-to-event (visual-field progression) -> HR; continuous (BCVA letters, CRT,
IOP, OSDI, corneal staining, Schirmer) -> MD/SMD. None of the ophthalmology
continuous measures are treated as log-normal (letters, microns, mmHg and the
bounded dry-eye scores are pooled on the raw scale).

Routing note (coordinated with diabetes): a DIABETIC MACULAR EDEMA or DIABETIC
RETINOPATHY trial is eye-primary and routes here because it carries eye-specific
anchors (macular edema, retinal thickness, OCT, intravitreal, anti-VEGF, BCVA,
ETDRS letters). A PURE glycaemic diabetes trial (HbA1c / hypoglycaemia / weight
loss with no eye primary outcome) stays with diabetes. We deliberately do NOT
claim bare 'diabetes' / 'diabetic' as ophthalmology detection keywords -- only
the compound eye terms 'diabetic macular edema' / 'diabetic retinopathy'.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# OPHTHALMOLOGY ENDPOINTS
# ============================================================

OPHTHALMOLOGY_ENDPOINTS = {
    # --- Retina (shared by AMD + DME); declared once under 'amd', patterns are
    #     wired into BOTH the amd and dme pattern blocks below. ---
    'BCVA_CHANGE': {
        'aliases': ['best-corrected visual acuity', 'best corrected visual acuity',
                    'change in bcva', 'bcva change', 'bcva', 'visual acuity change',
                    'change in visual acuity', 'mean change in bcva',
                    'etdrs letters', 'letters of visual acuity', 'letter score change',
                    'mean bcva change'],
        'subspecialty': 'amd',
        'measure_types': ['MD', 'SMD']
    },
    'VISION_GAIN_15': {
        'aliases': ['gain of at least 15 letters', 'gained at least 15 letters',
                    '>=15-letter gain', '15-letter gain', 'gain of 15 letters or more',
                    'three-line gain', '3-line gain', 'proportion gaining 15 letters',
                    'gaining >=15 letters', 'gain of >=15 letters'],
        'subspecialty': 'amd',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'VISION_LOSS_15': {
        'aliases': ['loss of fewer than 15 letters', 'lost fewer than 15 letters',
                    'avoidance of loss', 'avoided loss of 15 letters',
                    '<15-letter loss', 'loss of less than 15 letters',
                    'losing fewer than 15 letters', 'prevention of vision loss',
                    'avoidance of moderate vision loss', 'less than 15-letter loss'],
        'subspecialty': 'amd',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'CRT_CHANGE': {
        'aliases': ['central retinal thickness', 'central subfield thickness',
                    'central macular thickness', 'change in central retinal thickness',
                    'change in central subfield thickness', 'crt change',
                    'cst change', 'retinal thickness change', 'change in crt',
                    'reduction in central subfield thickness'],
        'subspecialty': 'amd',
        'measure_types': ['MD', 'SMD']
    },

    # --- DME-specific ---
    'DR_IMPROVEMENT': {
        'aliases': ['2-step improvement', 'two-step improvement',
                    '>=2-step diabetic retinopathy improvement',
                    'diabetic retinopathy severity improvement',
                    '2-step improvement in diabetic retinopathy severity',
                    'improvement in drss', 'drss improvement',
                    'two-step improvement in diabetic retinopathy severity scale',
                    '2-step drss improvement'],
        'subspecialty': 'dme',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Glaucoma ---
    'IOP_CHANGE': {
        'aliases': ['intraocular pressure reduction', 'iop reduction',
                    'change in intraocular pressure', 'change in iop',
                    'mean iop reduction', 'reduction in intraocular pressure',
                    'iop lowering', 'intraocular pressure lowering',
                    'mean diurnal iop', 'mean intraocular pressure change'],
        'subspecialty': 'glaucoma',
        'measure_types': ['MD', 'SMD']
    },
    'IOP_TARGET': {
        'aliases': ['target intraocular pressure', 'target iop',
                    'reaching target iop', 'achieved target iop',
                    'iop target attainment', 'proportion reaching target iop',
                    'iop below 18', 'iop <=18', 'target pressure achievement'],
        'subspecialty': 'glaucoma',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'VF_PROGRESSION': {
        'aliases': ['visual field progression', 'glaucoma progression',
                    'progression of visual field loss', 'visual field deterioration',
                    'perimetric progression', 'progression of glaucomatous visual field',
                    'visual field defect progression'],
        'subspecialty': 'glaucoma',
        'measure_types': ['HR', 'RR', 'OR']
    },

    # --- Dry eye ---
    'OSDI_CHANGE': {
        'aliases': ['ocular surface disease index', 'osdi', 'osdi score',
                    'change in osdi', 'osdi total score', 'change in ocular surface disease index',
                    'mean osdi change'],
        'subspecialty': 'dry_eye',
        'measure_types': ['MD', 'SMD']
    },
    'CORNEAL_STAINING': {
        'aliases': ['corneal staining', 'corneal fluorescein staining',
                    'total corneal staining score', 'change in corneal staining',
                    'corneal staining score', 'ocular surface staining',
                    'fluorescein staining score'],
        'subspecialty': 'dry_eye',
        'measure_types': ['MD', 'SMD']
    },
    'SCHIRMER': {
        'aliases': ['schirmer test', 'schirmer score', 'schirmer i test',
                    'change in schirmer score', 'schirmer test score',
                    'tear production', 'schirmer test without anesthesia',
                    'anesthetized schirmer'],
        'subspecialty': 'dry_eye',
        'measure_types': ['MD', 'SMD']
    },
}


# ============================================================
# SHARED RETINA ENDPOINT PATTERNS (AMD + DME)
# ============================================================
# Defined once and spliced into both amd and dme endpoint_patterns. Specific
# binary endpoints (gain / loss) precede the generic BCVA continuous so the
# longest/nearest match wins.
_RETINA_PATTERNS = [
    (r'gain(?:ed|ing)?\s+(?:of\s+)?(?:at\s+least\s+|>=?\s*|≥\s*)?15\s+letters(?:\s+or\s+more)?|'
     r'(?:three|3)[- ]line\s+gain|gain\s+of\s+(?:>=?\s*|≥\s*)?15\s+letters', 'VISION_GAIN_15'),
    (r'(?:loss|lost|losing)\s+(?:of\s+)?(?:fewer|less)\s+than\s+15\s+letters|'
     r'avoidance\s+of\s+(?:moderate\s+)?(?:vision\s+)?loss|avoided\s+loss\s+of\s+15\s+letters|'
     r'prevention\s+of\s+vision\s+loss', 'VISION_LOSS_15'),
    (r'central\s+(?:retinal|subfield|macular)\s+thickness|change\s+in\s+(?:crt|cst)|'
     r'\bcrt\s+change\b|\bcst\s+change\b|retinal\s+thickness\s+change', 'CRT_CHANGE'),
    (r'best[- ]corrected\s+visual\s+acuity|change\s+in\s+bcva|\bbcva\b|'
     r'(?:change\s+in\s+)?visual\s+acuity\s+change|etdrs\s+letters|letters\s+of\s+visual\s+acuity',
     'BCVA_CHANGE'),
]


# ============================================================
# AMD PATTERNS (neovascular age-related macular degeneration)
# ============================================================

AMD_PATTERNS = {
    'detection_keywords': [
        r'age[- ]related\s+macular\s+degeneration', r'\bamd\b|\bnamd\b|\bwamd\b',
        r'neovascular(?:\s+amd)?', r'choroidal\s+neovascular\w*|\bcnv\b',
        r'wet\s+(?:age[- ]related\s+macular\s+degeneration|amd|macular\s+degeneration)',
        r'anti[- ]vegf', r'intravitreal', r'ranibizumab|aflibercept|bevacizumab|brolucizumab|faricimab',
        r'best[- ]corrected\s+visual\s+acuity|\bbcva\b', r'etdrs\s+letters',
        r'central\s+(?:retinal|subfield)\s+thickness',
    ],
    'endpoint_patterns': list(_RETINA_PATTERNS),
    'context_patterns': [
        r'\boct\b|optical\s+coherence\s+tomography', r'at\s+week\s+(?:52|96)',
        r'monthly\s+injections?', r'treat[- ]and[- ]extend',
    ]
}


# ============================================================
# DME PATTERNS (diabetic macular edema)
# ============================================================

DME_PATTERNS = {
    'detection_keywords': [
        r'diabetic\s+macular\s+(?:edema|oedema)|\bdme\b|\bdmo\b',
        r'diabetic\s+retinopathy|\bdr\b\s+severity|drss',
        r'center[- ]involved\s+(?:diabetic\s+)?macular\s+edema|\bci[- ]?dme\b',
        r'anti[- ]vegf', r'intravitreal',
        r'ranibizumab|aflibercept|bevacizumab|faricimab',
        r'best[- ]corrected\s+visual\s+acuity|\bbcva\b',
        r'central\s+(?:retinal|subfield)\s+thickness',
    ],
    'endpoint_patterns': [
        (r'(?:>=?\s*|≥\s*)?(?:two|2)[- ]step\s+improvement(?:\s+in\s+diabetic\s+retinopathy'
         r'(?:\s+severity)?(?:\s+scale)?)?|diabetic\s+retinopathy\s+severity\s+improvement|'
         r'improvement\s+in\s+drss|drss\s+improvement', 'DR_IMPROVEMENT'),
    ] + list(_RETINA_PATTERNS),
    'context_patterns': [
        r'\boct\b|optical\s+coherence\s+tomography', r'center[- ]involved',
        r'hba1c', r'at\s+(?:week|year)\s+\d+',
    ]
}


# ============================================================
# GLAUCOMA PATTERNS
# ============================================================

GLAUCOMA_PATTERNS = {
    'detection_keywords': [
        r'glaucoma', r'open[- ]angle\s+glaucoma|\bpoag\b', r'ocular\s+hypertension',
        r'intraocular\s+pressure|\biop\b', r'visual\s+field',
        r'latanoprost|bimatoprost|travoprost|timolol|brinzolamide|dorzolamide|brimonidine|netarsudil',
        r'prostaglandin\s+analog', r'trabecul\w+', r'aqueous\s+humo(?:u)?r',
    ],
    'endpoint_patterns': [
        (r'target\s+(?:intraocular\s+pressure|iop)|reaching\s+target\s+iop|'
         r'achieved\s+target\s+iop|iop\s+target\s+attainment|iop\s*(?:<=|≤)\s*18', 'IOP_TARGET'),
        (r'visual\s+field\s+(?:progression|deterioration|defect\s+progression)|'
         r'glaucoma(?:tous)?\s+(?:visual\s+field\s+)?progression|perimetric\s+progression', 'VF_PROGRESSION'),
        (r'intraocular\s+pressure\s+(?:reduction|lowering)|iop\s+(?:reduction|lowering)|'
         r'change\s+in\s+(?:intraocular\s+pressure|iop)|mean\s+(?:diurnal\s+)?iop|'
         r'reduction\s+in\s+intraocular\s+pressure', 'IOP_CHANGE'),
    ],
    'context_patterns': [
        r'\bmmhg\b', r'diurnal', r'at\s+(?:week|month)\s+\d+', r'humphrey\s+(?:visual\s+field|hfa)',
    ]
}


# ============================================================
# DRY EYE PATTERNS
# ============================================================

DRY_EYE_PATTERNS = {
    'detection_keywords': [
        r'dry\s+eye(?:\s+disease)?|\bded\b', r'keratoconjunctivitis\s+sicca',
        r'ocular\s+surface\s+disease', r'\bosdi\b',
        r'corneal\s+(?:fluorescein\s+)?staining', r'schirmer',
        r'tear\s+(?:film|break[- ]up|production)|\btbut\b',
        r'cyclosporine|cyclosporin|lifitegrast|varenicline\s+nasal',
    ],
    'endpoint_patterns': [
        (r'ocular\s+surface\s+disease\s+index|\bosdi\b(?:\s+(?:score|total))?', 'OSDI_CHANGE'),
        (r'corneal\s+(?:fluorescein\s+)?staining(?:\s+score)?|ocular\s+surface\s+staining|'
         r'fluorescein\s+staining\s+score', 'CORNEAL_STAINING'),
        (r'schirmer(?:\s+(?:i\s+)?test|\s+score)?|tear\s+production', 'SCHIRMER'),
    ],
    'context_patterns': [
        r'tear\s+break[- ]up\s+time', r'at\s+(?:week|day)\s+\d+', r'symptom\s+score',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_ophthalmology_subspecialty(text: str) -> Tuple[str, float]:
    """Detect ophthalmology trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: amd, dme, glaucoma, dry_eye."""
    text_lower = text.lower()
    scores = {'amd': 0, 'dme': 0, 'glaucoma': 0, 'dry_eye': 0}
    for kw in AMD_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['amd'] += 1
    for kw in DME_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['dme'] += 1
    for kw in GLAUCOMA_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['glaucoma'] += 1
    for kw in DRY_EYE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['dry_eye'] += 1

    # DME and AMD share the retina anti-VEGF / BCVA / thickness keywords; a
    # diabetic-macular-edema anchor must tip the tie toward dme rather than amd.
    if re.search(r'diabetic\s+macular\s+(?:edema|oedema)|\bdme\b|\bdmo\b|diabetic\s+retinopathy',
                 text_lower):
        scores['dme'] += 1
    elif re.search(r'age[- ]related\s+macular\s+degeneration|neovascular|\bnamd\b|\bwamd\b|'
                   r'choroidal\s+neovascular', text_lower):
        scores['amd'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('amd', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_ophthalmology_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'amd': AMD_PATTERNS['endpoint_patterns'],
        'dme': DME_PATTERNS['endpoint_patterns'],
        'glaucoma': GLAUCOMA_PATTERNS['endpoint_patterns'],
        'dry_eye': DRY_EYE_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_ophthalmology_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical ophthalmology endpoint, preferring the LONGEST
    matching alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in OPHTHALMOLOGY_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
