"""
Sickle Cell Disease (SCD) Subspecialty Patterns and Endpoints

Built for the same African-student meta-analysis workflow as the malaria, HIV and
typhoid profiles. Sickle cell disease is an Africa-priority hemoglobinopathy
(the great majority of births with SCD occur in sub-Saharan Africa) whose RCTs
report a distinct endpoint vocabulary the generic effect-size engine does not
recognise on its own.

Subspecialties:
- Disease-modifying therapy (hydroxyurea/hydroxycarbamide, voxelotor,
  crizanlizumab, L-glutamine, gene/curative therapy): vaso-occlusive crisis (VOC)
  rate, acute chest syndrome, hospitalisation, total-haemoglobin change, fetal
  haemoglobin (HbF), transfusion requirement, dactylitis, mortality.
- Acute pain (vaso-occlusive crisis management): crisis duration / time to
  resolution, length of hospital stay, opioid/analgesic consumption, pain
  intensity (VAS), readmission.
- Prevention (stroke and infection prevention): overt stroke, silent cerebral
  infarct, transcranial Doppler (TCD) velocity, invasive bacterial infection.
  Interventions: chronic transfusion, hydroxyurea, penicillin prophylaxis,
  pneumococcal vaccination.
- Transfusion / iron (chronic transfusion and iron management): serum ferritin,
  liver iron concentration (LIC), red-cell alloimmunisation. Chelators:
  deferasirox, deferiprone, deferoxamine.

Effect measures follow what these trials report: binary (VOC, ACS, stroke,
dactylitis, infection, alloimmunisation) -> RR/OR/RD; recurrent events / rates
(VOC rate, hospitalisation, transfusion) -> IRR/HR; continuous (haemoglobin and
HbF change, crisis duration, length of stay, pain score, TCD velocity, ferritin,
LIC) -> MD/SMD.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# SICKLE CELL DISEASE ENDPOINTS
# ============================================================

SICKLE_CELL_ENDPOINTS = {
    # --- Disease-modifying therapy ---
    'VASO_OCCLUSIVE_CRISIS': {
        'aliases': ['vaso-occlusive crisis', 'vaso occlusive crisis',
                    'vasoocclusive crisis', 'vaso-occlusive event',
                    'vaso-occlusive pain crisis', 'painful crisis', 'pain crisis',
                    'painful episode', 'sickle cell crisis', 'sickle cell pain crisis',
                    'voc', 'annual rate of crises', 'crisis rate'],
        'subspecialty': 'disease_modifying',
        'measure_types': ['RR', 'IRR', 'HR']
    },
    'ACUTE_CHEST_SYNDROME': {
        'aliases': ['acute chest syndrome', 'acute chest syndrome event',
                    'acute chest syndrome episode', 'acs'],
        'subspecialty': 'disease_modifying',
        'measure_types': ['RR', 'OR', 'IRR']
    },
    'HOSPITALIZATION': {
        'aliases': ['hospitalization', 'hospitalisation', 'hospital admission',
                    'hospital admissions', 'rate of hospitalization',
                    'rate of hospitalisation', 'inpatient admission',
                    'number of hospitalizations'],
        'subspecialty': 'disease_modifying',
        'measure_types': ['RR', 'IRR', 'HR']
    },
    'TOTAL_HEMOGLOBIN': {
        'aliases': ['total haemoglobin', 'total hemoglobin', 'haemoglobin level',
                    'hemoglobin level', 'haemoglobin concentration',
                    'hemoglobin concentration', 'change in haemoglobin',
                    'change in hemoglobin', 'haemoglobin response',
                    'hemoglobin response'],
        'subspecialty': 'disease_modifying',
        'measure_types': ['MD', 'SMD']
    },
    'FETAL_HEMOGLOBIN': {
        'aliases': ['fetal haemoglobin', 'fetal hemoglobin', 'foetal haemoglobin',
                    'hbf', 'hb f', 'fetal haemoglobin percentage',
                    'fetal hemoglobin percentage', 'percentage of fetal haemoglobin'],
        'subspecialty': 'disease_modifying',
        'measure_types': ['MD', 'SMD']
    },
    'BLOOD_TRANSFUSION': {
        'aliases': ['blood transfusion', 'transfusion requirement',
                    'transfusion rate', 'number of transfusions',
                    'red cell transfusion', 'packed red cell transfusion',
                    'transfusion need', 'rate of transfusion'],
        'subspecialty': 'disease_modifying',
        'measure_types': ['RR', 'IRR', 'HR']
    },
    'DACTYLITIS': {
        'aliases': ['dactylitis', 'hand-foot syndrome', 'hand foot syndrome'],
        'subspecialty': 'disease_modifying',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'MORTALITY': {
        'aliases': ['mortality', 'death', 'all-cause mortality', 'survival',
                    'case fatality', 'sickle cell-related death'],
        'subspecialty': 'disease_modifying',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- Acute pain (vaso-occlusive crisis management) ---
    'CRISIS_DURATION': {
        'aliases': ['duration of crisis', 'crisis duration', 'time to crisis resolution',
                    'time to resolution of crisis', 'duration of vaso-occlusive crisis',
                    'duration of painful crisis', 'time to crisis resolution',
                    'duration of hospitalization for crisis', 'time to pain resolution'],
        'subspecialty': 'acute_pain',
        'measure_types': ['MD', 'SMD']
    },
    'LENGTH_OF_STAY': {
        'aliases': ['length of hospital stay', 'length of stay',
                    'duration of hospitalization', 'duration of hospitalisation',
                    'hospital length of stay', 'time to discharge'],
        'subspecialty': 'acute_pain',
        'measure_types': ['MD', 'SMD']
    },
    'OPIOID_USE': {
        'aliases': ['opioid use', 'opioid consumption', 'analgesic consumption',
                    'analgesic use', 'total opioid dose', 'cumulative opioid use',
                    'morphine consumption', 'morphine equivalent'],
        'subspecialty': 'acute_pain',
        'measure_types': ['MD', 'SMD']
    },
    'PAIN_INTENSITY': {
        'aliases': ['pain intensity', 'pain score', 'pain severity',
                    'visual analogue scale', 'visual analog scale', 'vas score',
                    'pain visual analogue', 'mean pain score'],
        'subspecialty': 'acute_pain',
        'measure_types': ['MD', 'SMD']
    },
    'READMISSION': {
        'aliases': ['readmission', 'hospital readmission', 'readmission rate',
                    '30-day readmission', 'recurrent admission'],
        'subspecialty': 'acute_pain',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Prevention (stroke and infection prevention) ---
    'STROKE': {
        'aliases': ['stroke', 'overt stroke', 'first stroke', 'recurrent stroke',
                    'ischaemic stroke', 'ischemic stroke', 'cerebrovascular accident',
                    'clinical stroke', 'primary stroke'],
        'subspecialty': 'prevention',
        'measure_types': ['RR', 'HR', 'IRR']
    },
    'SILENT_INFARCT': {
        'aliases': ['silent cerebral infarct', 'silent infarct',
                    'silent cerebral infarction', 'new silent infarct',
                    'silent stroke', 'silent cerebral ischaemia'],
        'subspecialty': 'prevention',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'TCD_VELOCITY': {
        'aliases': ['transcranial doppler velocity', 'tcd velocity',
                    'time-averaged mean velocity', 'time averaged maximum velocity',
                    'tamv', 'tammv', 'transcranial doppler', 'cerebral blood flow velocity'],
        'subspecialty': 'prevention',
        'measure_types': ['MD', 'SMD']
    },
    'INFECTION': {
        'aliases': ['invasive bacterial infection', 'invasive pneumococcal infection',
                    'pneumococcal infection', 'pneumococcal sepsis', 'septicaemia',
                    'septicemia', 'bacteraemia', 'bacteremia', 'serious infection',
                    'invasive pneumococcal disease'],
        'subspecialty': 'prevention',
        'measure_types': ['RR', 'IRR', 'HR']
    },

    # --- Transfusion / iron ---
    'SERUM_FERRITIN': {
        'aliases': ['serum ferritin', 'ferritin level', 'ferritin concentration',
                    'serum ferritin level', 'change in ferritin'],
        'subspecialty': 'transfusion',
        'measure_types': ['MD', 'SMD']
    },
    'LIVER_IRON': {
        'aliases': ['liver iron concentration', 'liver iron content', 'lic',
                    'hepatic iron concentration', 'hepatic iron content'],
        'subspecialty': 'transfusion',
        'measure_types': ['MD', 'SMD']
    },
    'ALLOIMMUNIZATION': {
        'aliases': ['alloimmunization', 'alloimmunisation', 'red cell alloimmunization',
                    'red cell alloimmunisation', 'red-cell alloimmunization',
                    'alloantibody formation', 'rbc alloimmunization'],
        'subspecialty': 'transfusion',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# DISEASE-MODIFYING PATTERNS
# ============================================================

DISEASE_MODIFYING_PATTERNS = {
    'detection_keywords': [
        r'hydroxyurea', r'hydroxycarbamide', r'voxelotor', r'crizanlizumab',
        r'l[- ]?glutamine', r'\bglutamine\b', r'gene\s+therapy',
        r'vaso[- ]?occlusive', r'painful\s+(?:crisis|episode)', r'pain\s+crisis',
        r'acute\s+chest\s+syndrome', r'fetal\s+ha?emoglobin|\bhbf\b',
        r'dactylitis|hand[- ]foot\s+syndrome', r'sickle\s+cell\s+crisis',
        r'p[- ]selectin', r'haemoglobin\s+response|hemoglobin\s+response',
    ],
    'endpoint_patterns': [
        (r'vaso[- ]?occlusive\s+(?:crisis|crises|event|pain)|painful\s+(?:crisis|crises|episode)|'
         r'pain\s+crisis|sickle\s+cell\s+(?:pain\s+)?crisis|\bvoc\b|crisis\s+rate',
         'VASO_OCCLUSIVE_CRISIS'),
        (r'acute\s+chest\s+syndrome|\bacs\b', 'ACUTE_CHEST_SYNDROME'),
        (r'hospitali[sz]ation|hospital\s+admission|inpatient\s+admission', 'HOSPITALIZATION'),
        (r'(?:total\s+)?ha?emoglobin\s+(?:level|concentration|response)|'
         r'change\s+in\s+(?:total\s+)?ha?emoglobin', 'TOTAL_HEMOGLOBIN'),
        (r'fetal\s+ha?emoglobin|foetal\s+ha?emoglobin|\bhbf\b|\bhb\s*f\b', 'FETAL_HEMOGLOBIN'),
        (r'(?:blood|red\s+cell|packed\s+red\s+cell)\s+transfusion|transfusion\s+(?:requirement|rate|need)',
         'BLOOD_TRANSFUSION'),
        (r'dactylitis|hand[- ]foot\s+syndrome', 'DACTYLITIS'),
        (r'(?:all[- ]cause\s+)?mortality|case\s+fatality|\bdeath\b|survival', 'MORTALITY'),
    ],
    'context_patterns': [
        r'per[- ]protocol|intention[- ]to[- ]treat', r'annuali[sz]ed\s+rate',
        r'\bhbss\b|\bhbsc\b|sickle[- ]?β', r'median\s+follow[- ]up',
    ]
}


# ============================================================
# ACUTE PAIN PATTERNS (vaso-occlusive crisis management)
# ============================================================

ACUTE_PAIN_PATTERNS = {
    'detection_keywords': [
        r'time\s+to\s+(?:crisis|pain)\s+resolution', r'duration\s+of\s+(?:crisis|vaso)',
        r'length\s+of\s+(?:hospital\s+)?stay', r'opioid\s+(?:use|consumption)',
        r'analgesic\s+(?:use|consumption)', r'morphine\s+(?:consumption|equivalent)',
        r'pain\s+(?:score|intensity|severity)', r'visual\s+analog(?:ue)?\s+scale',
        r'\bvas\b', r'readmission',
    ],
    'endpoint_patterns': [
        (r'duration\s+of\s+(?:the\s+)?(?:vaso[- ]?occlusive\s+)?(?:painful\s+)?cris[ie]s|'
         r'crisis\s+duration|time\s+to\s+(?:crisis|pain)\s+resolution|'
         r'time\s+to\s+resolution\s+of\s+(?:the\s+)?cris[ie]s', 'CRISIS_DURATION'),
        (r'length\s+of\s+(?:hospital\s+)?stay|duration\s+of\s+hospitali[sz]ation|'
         r'time\s+to\s+discharge', 'LENGTH_OF_STAY'),
        (r'opioid\s+(?:use|consumption|dose)|analgesic\s+(?:use|consumption)|'
         r'morphine\s+(?:consumption|equivalent)', 'OPIOID_USE'),
        (r'pain\s+(?:intensity|score|severity)|visual\s+analog(?:ue)?\s+scale|\bvas\s+score',
         'PAIN_INTENSITY'),
        (r'readmission|recurrent\s+admission', 'READMISSION'),
    ],
    'context_patterns': [
        r'emergency\s+department', r'patient[- ]controlled\s+analgesia|\bpca\b',
        r'days?|hours?',
    ]
}


# ============================================================
# PREVENTION PATTERNS (stroke and infection prevention)
# ============================================================

PREVENTION_PATTERNS = {
    'detection_keywords': [
        r'\bstroke\b', r'silent\s+(?:cerebral\s+)?infarct', r'transcranial\s+doppler',
        r'\btcd\b', r'time[- ]averaged\s+(?:mean|maximum)\s+velocity', r'\btamm?v\b',
        r'chronic\s+transfusion|regular\s+transfusion', r'penicillin\s+prophylaxis',
        r'pneumococcal', r'invasive\s+(?:bacterial|pneumococcal)', r'septica?emia',
        r'bactera?emia',
    ],
    'endpoint_patterns': [
        (r'(?:overt|first|recurrent|ischa?emic|clinical|primary)\s+stroke|\bstroke\b|'
         r'cerebrovascular\s+accident', 'STROKE'),
        (r'silent\s+(?:cerebral\s+)?infarct(?:ion)?|silent\s+stroke|new\s+silent\s+infarct',
         'SILENT_INFARCT'),
        (r'transcranial\s+doppler(?:\s+velocity)?|\btcd\s+velocity|time[- ]averaged\s+'
         r'(?:mean|maximum)\s+velocity|\btamm?v\b|cerebral\s+blood\s+flow\s+velocity',
         'TCD_VELOCITY'),
        (r'invasive\s+(?:bacterial|pneumococcal)\s+(?:infection|disease)|pneumococcal\s+'
         r'(?:infection|sepsis|disease)|septica?emia|bactera?emia|serious\s+infection',
         'INFECTION'),
    ],
    'context_patterns': [
        r'per\s+(?:100\s+)?patient[- ]years', r'\bcm\/s\b|centimet(?:er|re)s?\s+per\s+second',
        r'incidence\s+rate\s+ratio|\birr\b',
    ]
}


# ============================================================
# TRANSFUSION / IRON PATTERNS
# ============================================================

TRANSFUSION_PATTERNS = {
    'detection_keywords': [
        r'serum\s+ferritin|ferritin\s+(?:level|concentration)',
        r'liver\s+iron\s+(?:concentration|content)|hepatic\s+iron', r'\blic\b',
        r'deferasirox', r'deferiprone', r'deferoxamine|desferrioxamine',
        r'iron\s+chelation', r'alloimmuni[sz]ation|alloantibody',
        r'iron\s+overload',
    ],
    'endpoint_patterns': [
        (r'serum\s+ferritin|ferritin\s+(?:level|concentration)|change\s+in\s+ferritin',
         'SERUM_FERRITIN'),
        (r'liver\s+iron\s+(?:concentration|content)|hepatic\s+iron\s+(?:concentration|content)|'
         r'\blic\b', 'LIVER_IRON'),
        (r'(?:red[- ]?cell\s+|rbc\s+)?alloimmuni[sz]ation|alloantibody\s+formation',
         'ALLOIMMUNIZATION'),
    ],
    'context_patterns': [
        r'\bmg\/g\b|milligram\s+per\s+gram', r'\bng\/ml\b', r't2\*?\s*mri|r2\*?\s*mri',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_sickle_cell_subspecialty(text: str) -> Tuple[str, float]:
    """Detect sickle cell trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: disease_modifying, acute_pain, prevention, transfusion,
    general_sickle_cell."""
    text_lower = text.lower()
    scores = {'disease_modifying': 0, 'acute_pain': 0, 'prevention': 0, 'transfusion': 0}
    for kw in DISEASE_MODIFYING_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['disease_modifying'] += 1
    for kw in ACUTE_PAIN_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['acute_pain'] += 1
    for kw in PREVENTION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['prevention'] += 1
    for kw in TRANSFUSION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['transfusion'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_sickle_cell', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_sickle_cell_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'disease_modifying': DISEASE_MODIFYING_PATTERNS['endpoint_patterns'],
        'acute_pain': ACUTE_PAIN_PATTERNS['endpoint_patterns'],
        'prevention': PREVENTION_PATTERNS['endpoint_patterns'],
        'transfusion': TRANSFUSION_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_sickle_cell_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical sickle cell endpoint, preferring the LONGEST matching
    alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in SICKLE_CELL_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
