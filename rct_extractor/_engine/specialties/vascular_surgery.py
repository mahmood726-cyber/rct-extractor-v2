"""
Vascular Surgery Subspecialty Patterns and Endpoints

Built on the same meta-analysis workflow. This profile deliberately covers the
vascular-surgery space NOT already handled by peripheral_artery_disease (lower-
limb claudication / ABI / femoropopliteal patency / amputation-free survival) or
venous_thromboembolism (DVT/PE): abdominal aortic aneurysm repair, carotid
revascularisation, haemodialysis access, and superficial-venous intervention.

Subspecialties:
- aneurysm: abdominal aortic aneurysm repair (EVAR vs open), aneurysm-related
  mortality, endoleak, reintervention, post-repair rupture.
- carotid: carotid endarterectomy / stenting, peri-procedural stroke, stroke or
  death, myocardial infarction, carotid restenosis.
- access: haemodialysis arteriovenous fistula / graft - access patency,
  maturation, thrombosis.
- venous: superficial-venous (varicose vein) ablation - anatomical occlusion /
  closure, varicose-vein recurrence, venous-ulcer healing.

Drug / procedure classes (arm labels): EVAR / open aneurysm repair, carotid
endarterectomy (CEA) / carotid artery stenting (CAS), arteriovenous fistula /
graft, endovenous laser / radiofrequency ablation, foam sclerotherapy, surgery /
stripping, balloon angioplasty, stent, placebo.

Effect measures: all vascular-surgery endpoints -> RR/OR/HR.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# VASCULAR-SURGERY ENDPOINTS
# ============================================================

VASCULAR_SURGERY_ENDPOINTS = {
    # --- aneurysm ---
    'ANEURYSM_MORTALITY': {
        'aliases': ['aneurysm-related mortality', 'aneurysm related mortality',
                    'aneurysm-related death', '30-day mortality', '30 day mortality',
                    'all-cause mortality', 'all cause mortality', 'perioperative mortality'],
        'subspecialty': 'aneurysm',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'ENDOLEAK': {
        'aliases': ['endoleak', 'type i endoleak', 'type ii endoleak', 'type 2 endoleak',
                    'type ia endoleak'],
        'subspecialty': 'aneurysm',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'REINTERVENTION': {
        'aliases': ['reintervention', 're-intervention', 'secondary intervention',
                    'aneurysm-related reintervention', 'secondary procedure'],
        'subspecialty': 'aneurysm',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'ANEURYSM_RUPTURE': {
        'aliases': ['aneurysm rupture', 'post-repair rupture', 'secondary rupture',
                    'aneurysm sac rupture'],
        'subspecialty': 'aneurysm',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- carotid ---
    'STROKE': {
        'aliases': ['ipsilateral stroke', 'periprocedural stroke', 'peri-procedural stroke',
                    'any stroke', 'stroke', 'disabling stroke'],
        'subspecialty': 'carotid',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'STROKE_OR_DEATH': {
        'aliases': ['stroke or death', 'death or stroke', 'stroke and death',
                    'any stroke or death', 'periprocedural stroke or death',
                    'stroke, death or myocardial infarction'],
        'subspecialty': 'carotid',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'MYOCARDIAL_INFARCTION': {
        'aliases': ['periprocedural myocardial infarction', 'myocardial infarction',
                    'peri-procedural myocardial infarction', 'mi'],
        'subspecialty': 'carotid',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'CAROTID_RESTENOSIS': {
        'aliases': ['carotid restenosis', 'restenosis', 'in-stent restenosis',
                    'recurrent stenosis'],
        'subspecialty': 'carotid',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- haemodialysis access ---
    'ACCESS_PATENCY': {
        'aliases': ['primary patency', 'access patency', 'fistula patency',
                    'secondary patency', 'primary access patency', 'graft patency'],
        'subspecialty': 'access',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'ACCESS_MATURATION': {
        'aliases': ['fistula maturation', 'access maturation', 'successful maturation',
                    'unassisted maturation', 'clinical maturation'],
        'subspecialty': 'access',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'ACCESS_THROMBOSIS': {
        'aliases': ['access thrombosis', 'fistula thrombosis', 'graft thrombosis',
                    'access failure'],
        'subspecialty': 'access',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- superficial venous ---
    'VENOUS_OCCLUSION': {
        'aliases': ['anatomical occlusion', 'complete occlusion', 'vein occlusion',
                    'anatomical closure', 'occlusion rate', 'vein closure'],
        'subspecialty': 'venous',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'VARICOSE_RECURRENCE': {
        'aliases': ['varicose vein recurrence', 'recurrent varicose veins',
                    'clinical recurrence', 'recurrence of varicose veins', 'recurrence'],
        'subspecialty': 'venous',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'VENOUS_ULCER_HEALING': {
        'aliases': ['venous ulcer healing', 'ulcer healing', 'leg ulcer healing',
                    'complete ulcer healing'],
        'subspecialty': 'venous',
        'measure_types': ['RR', 'OR', 'HR']
    },
}


# ============================================================
# ANEURYSM PATTERNS
# ============================================================

ANEURYSM_PATTERNS = {
    'detection_keywords': [
        r'abdominal\s+aortic\s+aneurysm|\baaa\b', r'endovascular\s+aneurysm\s+repair|\bevar\b',
        r'open\s+(?:aneurysm\s+|surgical\s+)?repair', r'\bendoleak\b',
        r'aneurysm\s+(?:sac|rupture)', r'reintervention|re[- ]intervention',
    ],
    'endpoint_patterns': [
        (r'type\s+(?:i{1,2}|1|2|ia|iii)\s+endoleak|\bendoleak\b', 'ENDOLEAK'),
        (r'(?:secondary\s+|post[- ]repair\s+|aneurysm\s+sac\s+)?(?:aneurysm\s+)?rupture',
         'ANEURYSM_RUPTURE'),
        (r'aneurysm[- ]related\s+(?:reintervention|reoperation)|reintervention|re[- ]intervention|'
         r'secondary\s+(?:intervention|procedure)', 'REINTERVENTION'),
        (r'aneurysm[- ]related\s+(?:mortality|death)|30[- ]day\s+mortality|'
         r'perioperative\s+mortality|all[- ]cause\s+mortality', 'ANEURYSM_MORTALITY'),
    ],
    'context_patterns': [
        r'aortic\s+diameter', r'sac\s+(?:expansion|shrinkage)', r'fenestrated',
    ]
}


# ============================================================
# CAROTID PATTERNS
# ============================================================

CAROTID_PATTERNS = {
    'detection_keywords': [
        r'carotid\s+endarterectomy|\bcea\b', r'carotid\s+(?:artery\s+)?stenting|\bcas\b',
        r'carotid\s+(?:stenosis|revascular[is]ation|artery\s+disease)',
        r'ipsilateral\s+stroke|periprocedural\s+stroke', r'\b(?:stroke|death)\s+or\s+(?:death|stroke)\b',
    ],
    'endpoint_patterns': [
        (r'(?:peri[- ]?procedural\s+)?stroke,?\s+(?:or\s+)?death(?:\s+or\s+myocardial\s+infarction)?|'
         r'death\s+or\s+stroke|any\s+stroke\s+or\s+death', 'STROKE_OR_DEATH'),
        (r'(?:carotid\s+|in[- ]stent\s+|recurrent\s+)restenosis|recurrent\s+stenosis',
         'CAROTID_RESTENOSIS'),
        (r'(?:peri[- ]?procedural\s+)?myocardial\s+infarction', 'MYOCARDIAL_INFARCTION'),
        (r'(?:ipsilateral|peri[- ]?procedural|disabling|any)\s+stroke|\bstroke\b', 'STROKE'),
    ],
    'context_patterns': [
        r'symptomatic\s+(?:carotid\s+)?stenosis', r'degree\s+of\s+stenosis', r'plaque',
    ]
}


# ============================================================
# ACCESS PATTERNS (haemodialysis)
# ============================================================

ACCESS_PATTERNS = {
    'detection_keywords': [
        r'arteriovenous\s+fistula|\bavf\b|av\s+fistula', r'arteriovenous\s+graft|av\s+graft',
        r'(?:h[ae]modialysis|vascular|dialysis)\s+access', r'fistula\s+(?:maturation|patency)',
        r'access\s+(?:patency|thrombosis|maturation|failure)',
    ],
    'endpoint_patterns': [
        (r'(?:unassisted\s+|successful\s+|clinical\s+)?(?:fistula\s+|access\s+)?maturation',
         'ACCESS_MATURATION'),
        (r'(?:access|fistula|graft)\s+thrombosis|access\s+failure', 'ACCESS_THROMBOSIS'),
        (r'(?:primary|secondary|access|fistula|graft)\s+patency', 'ACCESS_PATENCY'),
    ],
    'context_patterns': [
        r'end[- ]stage\s+(?:kidney|renal)\s+disease', r'cannulation', r'radiocephalic|brachiocephalic',
    ]
}


# ============================================================
# VENOUS PATTERNS (superficial venous)
# ============================================================

VENOUS_PATTERNS = {
    'detection_keywords': [
        r'varicose\s+veins?', r'great\s+saphenous\s+vein|small\s+saphenous\s+vein|saphenous',
        r'endovenous\s+(?:laser|thermal|ablation)|\bevla\b|\bevlt\b',
        r'(?:radiofrequency|foam\s+sclerotherapy)\s*(?:ablation)?', r'venous\s+(?:reflux|ulcer)',
    ],
    'endpoint_patterns': [
        (r'venous\s+ulcer\s+healing|(?:leg\s+|complete\s+)?ulcer\s+healing', 'VENOUS_ULCER_HEALING'),
        (r'(?:varicose[- ]vein\s+|clinical\s+)?recurrence(?:\s+of\s+varicose\s+veins)?|'
         r'recurrent\s+varicose\s+veins', 'VARICOSE_RECURRENCE'),
        (r'(?:anatomical|complete|vein)\s+(?:occlusion|closure)|occlusion\s+rate', 'VENOUS_OCCLUSION'),
    ],
    'context_patterns': [
        r'ceap', r'venous\s+clinical\s+severity\s+score|\bvcss\b', r'aberdeen',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_vascular_surgery_subspecialty(text: str) -> Tuple[str, float]:
    """Detect vascular-surgery trial subspecialty. Returns (subspecialty,
    confidence). Subspecialties: aneurysm, carotid, access, venous,
    general_vascular."""
    text_lower = text.lower()
    scores = {'aneurysm': 0, 'carotid': 0, 'access': 0, 'venous': 0}
    for kw in ANEURYSM_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['aneurysm'] += 1
    for kw in CAROTID_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['carotid'] += 1
    for kw in ACCESS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['access'] += 1
    for kw in VENOUS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['venous'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_vascular', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_vascular_surgery_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'aneurysm': ANEURYSM_PATTERNS['endpoint_patterns'],
        'carotid': CAROTID_PATTERNS['endpoint_patterns'],
        'access': ACCESS_PATTERNS['endpoint_patterns'],
        'venous': VENOUS_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_vascular_surgery_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical vascular-surgery endpoint, preferring the LONGEST
    matching alias."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in VASCULAR_SURGERY_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
