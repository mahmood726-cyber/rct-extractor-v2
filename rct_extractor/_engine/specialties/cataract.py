"""
Cataract / lens-surgery Subspecialty Patterns and Endpoints.

Built for the same meta-analysis workflow as the ophthalmology / malaria / HIV
profiles, but for CATARACT trials specifically -- a domain the generic
ophthalmology profile does not target (it covers AMD / DME / glaucoma / dry eye,
not lens extraction, IOLs, posterior-capsule opacification or surgical
complications). Cataract RCTs report a distinct endpoint vocabulary anchored on
corrected/uncorrected visual acuity (logMAR or letters), spectacle independence,
surgically induced astigmatism (dioptres), corneal endothelial cell loss
(cells/mm^2), posterior-capsule opacification / Nd:YAG capsulotomy, cystoid
macular o?edema and post-operative endophthalmitis.

Subspecialties:
- surgery (phacoemulsification / FLACS / MSICS technique):
    corrected-distance visual acuity (CDVA/BCVA; logMAR or letters; MD),
    surgically induced astigmatism (SIA, dioptres; MD), corneal endothelial cell
    loss (cells/mm^2; MD), central corneal thickness (MD).
- iol (intraocular-lens type: monofocal / multifocal / trifocal / EDOF / toric):
    uncorrected distance/intermediate/near visual acuity (UDVA/UIVA/UNVA; MD),
    spectacle independence (RR/OR/RD), dysphotopsia / halos / glare (RR/OR).
- pco (posterior-capsule opacification):
    PCO incidence and Nd:YAG capsulotomy rate (RR/OR/RD).
- complications:
    cystoid macular o?edema (CMO/CME; RR/OR), post-operative endophthalmitis
    (RR/OR), central macular/retinal thickness on OCT (MD).

Effect measures follow what these trials report: binary (spectacle independence,
PCO / Nd:YAG, cystoid macular o?edema, endophthalmitis, dysphotopsia) -> RR/OR/RD;
continuous (CDVA/UDVA in logMAR or letters, SIA in dioptres, endothelial cell
density in cells/mm^2, corneal/macular thickness in microns) -> MD/SMD. None of
the cataract continuous measures is treated as log-normal (logMAR, letters,
dioptres, cells/mm^2 and microns are pooled on the raw scale).

British/American spelling: cystoid macular EDEMA vs OEDEMA (the British form
inserts an extra vowel -> 'o?edema', NOT '[oe]dema'); anaesthesia vs anesthesia
('ana?esthesia'); both are handled in the patterns below.

Routing note: this profile claims the specific lens-surgery anchors
(phacoemulsification, intraocular lens / IOL, posterior capsule, capsulotomy,
spectacle independence, cataract surgery) that the generic ophthalmology profile
does NOT, so a cataract-surgery trial routes here rather than to ophthalmology.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# CATARACT ENDPOINTS
# ============================================================

CATARACT_ENDPOINTS = {
    # --- Surgery (technique) ---
    'CDVA_CHANGE': {
        'aliases': ['corrected distance visual acuity', 'cdva', 'bcva',
                    'best-corrected visual acuity', 'best corrected visual acuity',
                    'corrected visual acuity', 'postoperative visual acuity',
                    'logmar visual acuity', 'change in cdva', 'mean cdva'],
        'subspecialty': 'surgery',
        'measure_types': ['MD', 'SMD']
    },
    'SIA': {
        'aliases': ['surgically induced astigmatism', 'sia',
                    'surgically-induced astigmatism', 'induced astigmatism',
                    'corneal astigmatism change', 'change in astigmatism',
                    'mean surgically induced astigmatism'],
        'subspecialty': 'surgery',
        'measure_types': ['MD', 'SMD']
    },
    'ENDOTHELIAL_CELL_LOSS': {
        'aliases': ['endothelial cell loss', 'corneal endothelial cell loss',
                    'endothelial cell density', 'ecd loss', 'cell density loss',
                    'percentage endothelial cell loss', 'corneal endothelial cell density',
                    'mean endothelial cell loss'],
        'subspecialty': 'surgery',
        'measure_types': ['MD', 'SMD']
    },
    'CCT_CHANGE': {
        'aliases': ['central corneal thickness', 'cct', 'change in central corneal thickness',
                    'corneal thickness change', 'mean central corneal thickness'],
        'subspecialty': 'surgery',
        'measure_types': ['MD', 'SMD']
    },

    # --- IOL ---
    'UDVA_CHANGE': {
        'aliases': ['uncorrected distance visual acuity', 'udva',
                    'uncorrected visual acuity', 'uncorrected near visual acuity',
                    'unva', 'uncorrected intermediate visual acuity', 'uiva',
                    'uncorrected distance acuity', 'mean udva'],
        'subspecialty': 'iol',
        'measure_types': ['MD', 'SMD']
    },
    'SPECTACLE_INDEPENDENCE': {
        'aliases': ['spectacle independence', 'spectacle freedom',
                    'complete spectacle independence', 'freedom from spectacles',
                    'spectacle-free', 'no longer needing glasses',
                    'proportion achieving spectacle independence',
                    'spectacle independence rate'],
        'subspecialty': 'iol',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'DYSPHOTOPSIA': {
        'aliases': ['dysphotopsia', 'photic phenomena', 'halos', 'glare',
                    'positive dysphotopsia', 'negative dysphotopsia',
                    'halos and glare', 'visual disturbances', 'starbursts'],
        'subspecialty': 'iol',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- PCO ---
    'PCO': {
        'aliases': ['posterior capsule opacification', 'posterior capsular opacification',
                    'pco', 'pco incidence', 'posterior capsule opacity',
                    'pco rate', 'incidence of posterior capsule opacification'],
        'subspecialty': 'pco',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'YAG_CAPSULOTOMY': {
        'aliases': ['nd:yag capsulotomy', 'yag capsulotomy', 'nd-yag capsulotomy',
                    'laser capsulotomy', 'capsulotomy rate', 'yag laser capsulotomy',
                    'neodymium:yag capsulotomy', 'rate of nd:yag capsulotomy'],
        'subspecialty': 'pco',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Complications ---
    'CMO': {
        'aliases': ['cystoid macular edema', 'cystoid macular oedema',
                    'cystoid macular o?edema', 'cmo', 'cme', 'macular edema',
                    'macular oedema', 'pseudophakic cystoid macular edema',
                    'pseudophakic cystoid macular oedema', 'incidence of cystoid macular edema'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'ENDOPHTHALMITIS': {
        'aliases': ['endophthalmitis', 'postoperative endophthalmitis',
                    'acute endophthalmitis', 'post-cataract endophthalmitis',
                    'incidence of endophthalmitis', 'endophthalmitis rate'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'CMT_CHANGE': {
        'aliases': ['central macular thickness', 'central retinal thickness',
                    'central subfield thickness', 'macular thickness change',
                    'change in central macular thickness', 'mean central macular thickness'],
        'subspecialty': 'complications',
        'measure_types': ['MD', 'SMD']
    },
}


# ============================================================
# SURGERY PATTERNS (phacoemulsification / FLACS / MSICS)
# ============================================================

SURGERY_PATTERNS = {
    'detection_keywords': [
        r'cataract\s+surgery', r'phacoemulsification|\bphaco\b',
        r'femtosecond\s+laser[- ]assisted\s+cataract\s+surgery|\bflacs\b',
        r'manual\s+small[- ]incision\s+cataract\s+surgery|\bmsics\b|\bsics\b',
        r'lens\s+extraction', r'capsulorhexis|capsulotomy',
        r'corrected[- ]distance\s+visual\s+acuity|\bcdva\b',
        r'surgically[- ]induced\s+astigmatism|\bsia\b',
        r'endothelial\s+cell', r'\blogmar\b',
    ],
    'endpoint_patterns': [
        (r'surgically[- ]induced\s+astigmatism|\bsia\b|induced\s+astigmatism|'
         r'change\s+in\s+astigmatism', 'SIA'),
        (r'(?:corneal\s+)?endothelial\s+cell\s+(?:loss|density)|\becd\s+loss\b|'
         r'cell\s+density\s+loss', 'ENDOTHELIAL_CELL_LOSS'),
        (r'central\s+corneal\s+thickness|\bcct\b|corneal\s+thickness\s+change',
         'CCT_CHANGE'),
        (r'corrected[- ]distance\s+visual\s+acuity|\bcdva\b|best[- ]corrected\s+visual\s+acuity|'
         r'\bbcva\b|logmar\s+visual\s+acuity', 'CDVA_CHANGE'),
    ],
    'context_patterns': [
        r'\bdioptres?\b|\bd\b\s+of\s+astigmatism', r'cells?/mm', r'\blogmar\b',
        r'at\s+(?:week|month)\s+\d+', r'topical\s+ana?esthesia',
    ]
}


# ============================================================
# IOL PATTERNS (intraocular-lens type)
# ============================================================

IOL_PATTERNS = {
    'detection_keywords': [
        r'intraocular\s+lens(?:es)?|\biol\b', r'monofocal', r'multifocal',
        r'trifocal', r'extended\s+depth\s+of\s+focus|\bedof\b|\bedf\b',
        r'toric', r'accommodating\s+(?:iol|lens)', r'pseudophakic',
        r'spectacle\s+independence', r'uncorrected\s+(?:distance|near|intermediate)\s+visual\s+acuity',
        r'\budva\b|\bunva\b|\buiva\b', r'panoptix|symfony|tecnis|acrysof|vivity|synergy',
    ],
    'endpoint_patterns': [
        (r'spectacle\s+(?:independence|freedom)|freedom\s+from\s+spectacles|'
         r'spectacle[- ]free', 'SPECTACLE_INDEPENDENCE'),
        (r'dysphotopsia|photic\s+phenomena|\bhalos?\b|\bglare\b|starbursts?|'
         r'visual\s+disturbances?', 'DYSPHOTOPSIA'),
        (r'uncorrected\s+(?:distance|near|intermediate)\s+visual\s+acuity|'
         r'\budva\b|\bunva\b|\buiva\b|uncorrected\s+visual\s+acuity', 'UDVA_CHANGE'),
    ],
    'context_patterns': [
        r'defocus\s+curve', r'\blogmar\b', r'contrast\s+sensitivity',
        r'at\s+(?:week|month)\s+\d+', r'near\s+vision|intermediate\s+vision',
    ]
}


# ============================================================
# PCO PATTERNS (posterior-capsule opacification)
# ============================================================

PCO_PATTERNS = {
    'detection_keywords': [
        r'posterior\s+capsul(?:e|ar)\s+opacification|\bpco\b',
        r'nd:?[- ]?yag\s+capsulotomy|yag\s+capsulotomy|laser\s+capsulotomy',
        r'square[- ]edge', r'capsular\s+bag', r'posterior\s+capsule',
    ],
    'endpoint_patterns': [
        (r'nd:?[- ]?yag\s+(?:laser\s+)?capsulotomy|yag\s+capsulotomy|'
         r'laser\s+capsulotomy|capsulotomy\s+rate', 'YAG_CAPSULOTOMY'),
        (r'posterior\s+capsul(?:e|ar)\s+opacification|\bpco\b(?:\s+(?:incidence|rate))?|'
         r'posterior\s+capsule\s+opacity', 'PCO'),
    ],
    'context_patterns': [
        r'\beposcale\b|\baqua\b\s+score', r'square[- ]edge\s+design',
        r'at\s+(?:year|month)\s+\d+', r'hydrophobic|hydrophilic',
    ]
}


# ============================================================
# COMPLICATIONS PATTERNS
# ============================================================

COMPLICATIONS_PATTERNS = {
    'detection_keywords': [
        r'cystoid\s+macular\s+o?edema|\bcmo\b|\bcme\b',
        r'endophthalmitis', r'macular\s+o?edema',
        r'intracameral\s+(?:cefuroxime|moxifloxacin|antibiotic)',
        r'central\s+macular\s+thickness', r'\bnsaid\b|nepafenac|ketorolac|bromfenac',
    ],
    'endpoint_patterns': [
        (r'(?:pseudophakic\s+)?cystoid\s+macular\s+o?edema|\bcmo\b|\bcme\b|'
         r'macular\s+o?edema', 'CMO'),
        (r'(?:postoperative\s+|acute\s+|post[- ]cataract\s+)?endophthalmitis', 'ENDOPHTHALMITIS'),
        (r'central\s+(?:macular|retinal|subfield)\s+thickness|macular\s+thickness\s+change',
         'CMT_CHANGE'),
    ],
    'context_patterns': [
        r'\boct\b|optical\s+coherence\s+tomography', r'intracameral',
        r'at\s+(?:week|month)\s+\d+', r'prophylaxis',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_cataract_subspecialty(text: str) -> Tuple[str, float]:
    """Detect cataract trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: surgery, iol, pco, complications."""
    text_lower = text.lower()
    scores = {'surgery': 0, 'iol': 0, 'pco': 0, 'complications': 0}
    for kw in SURGERY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['surgery'] += 1
    for kw in IOL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['iol'] += 1
    for kw in PCO_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['pco'] += 1
    for kw in COMPLICATIONS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['complications'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('surgery', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_cataract_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'surgery': SURGERY_PATTERNS['endpoint_patterns'],
        'iol': IOL_PATTERNS['endpoint_patterns'],
        'pco': PCO_PATTERNS['endpoint_patterns'],
        'complications': COMPLICATIONS_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_cataract_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical cataract endpoint, preferring the LONGEST matching
    alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in CATARACT_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
