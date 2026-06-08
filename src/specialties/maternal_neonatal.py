"""
Maternal & Neonatal Health Subspecialty Patterns and Endpoints

Built for the same African-student meta-analysis workflow as the malaria, HIV and
typhoid profiles. Maternal and newborn health is the single largest contributor
to the sub-Saharan disease burden among reproductive-age women and under-fives,
and its RCTs report a distinct obstetric / neonatal endpoint vocabulary the
generic effect-size engine does not recognise on its own.

Subspecialties:
- Maternal (peripartum maternal outcomes): maternal mortality, postpartum
  haemorrhage (PPH), blood loss, blood transfusion, maternal sepsis / infection,
  caesarean section, maternal anaemia, duration of labour. Interventions:
  uterotonics (oxytocin, carbetocin, misoprostol, ergometrine, syntometrine,
  carboprost), tranexamic acid, active vs expectant management of the third stage.
- Hypertensive (pre-eclampsia / eclampsia): pre-eclampsia, eclampsia, severe
  pre-eclampsia / HELLP, gestational hypertension. Interventions: magnesium
  sulphate, antihypertensives (labetalol, nifedipine, hydralazine, methyldopa),
  low-dose aspirin and calcium for prevention.
- Neonatal (newborn outcomes): neonatal mortality, stillbirth, perinatal
  mortality, neonatal sepsis, birth asphyxia / hypoxic-ischaemic encephalopathy,
  NICU admission, Apgar score. Interventions: neonatal resuscitation,
  chlorhexidine cord care, kangaroo mother care, early breastfeeding.
- Preterm (prematurity & growth): preterm birth, low birth weight, neonatal
  respiratory distress syndrome, small-for-gestational-age / IUGR, gestational
  age at delivery, birth weight. Interventions: antenatal corticosteroids
  (dexamethasone, betamethasone), tocolytics (nifedipine, atosiban),
  progesterone.

Effect measures follow what these trials report: binary outcomes (PPH, mortality,
stillbirth, pre-eclampsia, sepsis, preterm birth, LBW) -> RR/OR/RD; time-to-event
-> HR; continuous (blood loss, birth weight, gestational age, Apgar, labour
duration) -> MD/SMD.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# MATERNAL & NEONATAL ENDPOINTS
# ============================================================

MATERNAL_NEONATAL_ENDPOINTS = {
    # --- Maternal (peripartum) ---
    'MATERNAL_MORTALITY': {
        'aliases': ['maternal mortality', 'maternal death', 'maternal deaths',
                    'pregnancy-related death', 'pregnancy-related mortality',
                    'death of the mother'],
        'subspecialty': 'maternal',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'POSTPARTUM_HAEMORRHAGE': {
        'aliases': ['postpartum haemorrhage', 'postpartum hemorrhage',
                    'post-partum haemorrhage', 'post-partum hemorrhage',
                    'primary postpartum haemorrhage', 'severe postpartum haemorrhage',
                    'severe postpartum hemorrhage', 'obstetric haemorrhage',
                    'obstetric hemorrhage'],
        'subspecialty': 'maternal',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'BLOOD_LOSS': {
        'aliases': ['blood loss', 'estimated blood loss', 'mean blood loss',
                    'peripartum blood loss', 'measured blood loss',
                    'intrapartum blood loss'],
        'subspecialty': 'maternal',
        'measure_types': ['MD', 'SMD']
    },
    'BLOOD_TRANSFUSION': {
        'aliases': ['blood transfusion', 'need for transfusion', 'red cell transfusion',
                    'red-cell transfusion', 'packed cell transfusion',
                    'requirement for transfusion'],
        'subspecialty': 'maternal',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'MATERNAL_SEPSIS': {
        'aliases': ['maternal sepsis', 'puerperal sepsis', 'maternal infection',
                    'postpartum infection', 'puerperal infection', 'endometritis',
                    'maternal morbidity'],
        'subspecialty': 'maternal',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'CAESAREAN': {
        'aliases': ['caesarean section', 'cesarean section', 'caesarean delivery',
                    'cesarean delivery', 'caesarean birth', 'cesarean birth',
                    'c-section', 'caesarean'],
        'subspecialty': 'maternal',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'MATERNAL_ANAEMIA': {
        'aliases': ['maternal anaemia', 'maternal anemia', 'postpartum anaemia',
                    'postpartum anemia', 'antenatal anaemia', 'antenatal anemia'],
        'subspecialty': 'maternal',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'LABOUR_DURATION': {
        'aliases': ['duration of labour', 'duration of labor', 'length of labour',
                    'length of labor', 'labour duration', 'labor duration',
                    'duration of the first stage', 'duration of the second stage'],
        'subspecialty': 'maternal',
        'measure_types': ['MD', 'SMD']
    },

    # --- Hypertensive (pre-eclampsia / eclampsia) ---
    'PRE_ECLAMPSIA': {
        'aliases': ['pre-eclampsia', 'preeclampsia', 'pre eclampsia',
                    'pre-eclampsia or eclampsia', 'pre-eclampsia/eclampsia',
                    'proteinuric hypertension'],
        'subspecialty': 'hypertensive',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'ECLAMPSIA': {
        'aliases': ['eclampsia', 'eclamptic seizure', 'eclamptic convulsion',
                    'eclamptic fit', 'recurrence of convulsions', 'recurrent seizure',
                    'recurrent convulsion'],
        'subspecialty': 'hypertensive',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'SEVERE_PREECLAMPSIA': {
        'aliases': ['severe pre-eclampsia', 'severe preeclampsia',
                    'severe pre eclampsia', 'hellp syndrome', 'hellp',
                    'pre-eclampsia with severe features', 'severe features'],
        'subspecialty': 'hypertensive',
        'measure_types': ['RR', 'OR']
    },
    'GESTATIONAL_HYPERTENSION': {
        'aliases': ['gestational hypertension', 'pregnancy-induced hypertension',
                    'pregnancy induced hypertension', 'severe hypertension',
                    'severe maternal hypertension', 'hypertensive disorder of pregnancy',
                    'hypertensive disorders of pregnancy'],
        'subspecialty': 'hypertensive',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Neonatal (newborn outcomes) ---
    'NEONATAL_MORTALITY': {
        'aliases': ['neonatal mortality', 'neonatal death', 'neonatal deaths',
                    'early neonatal death', 'early neonatal mortality',
                    'newborn death', 'newborn mortality', 'death of the newborn'],
        'subspecialty': 'neonatal',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'STILLBIRTH': {
        'aliases': ['stillbirth', 'stillbirths', 'fetal death', 'foetal death',
                    'intrauterine death', 'intrauterine fetal death',
                    'intra-uterine death', 'fresh stillbirth'],
        'subspecialty': 'neonatal',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'PERINATAL_MORTALITY': {
        'aliases': ['perinatal mortality', 'perinatal death', 'perinatal deaths',
                    'perinatal loss'],
        'subspecialty': 'neonatal',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'NEONATAL_SEPSIS': {
        'aliases': ['neonatal sepsis', 'newborn sepsis', 'neonatal infection',
                    'early-onset sepsis', 'early-onset neonatal sepsis',
                    'late-onset sepsis', 'neonatal bacterial infection',
                    'serious neonatal infection'],
        'subspecialty': 'neonatal',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'BIRTH_ASPHYXIA': {
        'aliases': ['birth asphyxia', 'perinatal asphyxia',
                    'hypoxic-ischaemic encephalopathy', 'hypoxic ischemic encephalopathy',
                    'hypoxic-ischemic encephalopathy', 'neonatal encephalopathy',
                    'hie'],
        'subspecialty': 'neonatal',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'NICU_ADMISSION': {
        'aliases': ['nicu admission', 'admission to nicu', 'neonatal intensive care',
                    'admission to neonatal intensive care', 'special care nursery',
                    'admission to special care', 'neonatal unit admission'],
        'subspecialty': 'neonatal',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'APGAR_SCORE': {
        'aliases': ['apgar score', 'apgar', '5-minute apgar', 'five-minute apgar',
                    '5 minute apgar', 'apgar score at 5 minutes',
                    'mean apgar score'],
        'subspecialty': 'neonatal',
        'measure_types': ['MD', 'SMD']
    },

    # --- Preterm (prematurity & growth) ---
    'PRETERM_BIRTH': {
        'aliases': ['preterm birth', 'preterm delivery', 'premature birth',
                    'premature delivery', 'preterm labour', 'preterm labor',
                    'birth before 37 weeks', 'spontaneous preterm birth'],
        'subspecialty': 'preterm',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'LOW_BIRTH_WEIGHT': {
        'aliases': ['low birth weight', 'low birthweight', 'very low birth weight',
                    'very low birthweight', 'lbw', 'vlbw'],
        'subspecialty': 'preterm',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'BIRTH_WEIGHT': {
        'aliases': ['birth weight', 'birthweight', 'mean birth weight',
                    'mean birthweight', 'infant birth weight',
                    'neonatal birth weight'],
        'subspecialty': 'preterm',
        'measure_types': ['MD', 'SMD']
    },
    'RESPIRATORY_DISTRESS': {
        'aliases': ['respiratory distress syndrome', 'neonatal respiratory distress',
                    'hyaline membrane disease', 'rds',
                    'neonatal respiratory distress syndrome'],
        'subspecialty': 'preterm',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'SMALL_FOR_GESTATIONAL_AGE': {
        'aliases': ['small for gestational age', 'small-for-gestational-age',
                    'intrauterine growth restriction', 'intra-uterine growth restriction',
                    'fetal growth restriction', 'foetal growth restriction',
                    'sga', 'iugr', 'fgr'],
        'subspecialty': 'preterm',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'GESTATIONAL_AGE': {
        'aliases': ['gestational age at delivery', 'gestational age at birth',
                    'gestation at delivery', 'mean gestational age',
                    'gestational age at randomisation', 'gestational age at randomization'],
        'subspecialty': 'preterm',
        'measure_types': ['MD', 'SMD']
    },
}


# ============================================================
# MATERNAL PATTERNS (peripartum)
# ============================================================

MATERNAL_PATTERNS = {
    'detection_keywords': [
        r'oxytocin', r'carbetocin', r'misoprostol', r'ergometrine|ergometrine',
        r'syntometrine', r'carboprost', r'tranexamic\s+acid|\btxa\b',
        r'uterotonic', r'postpartum\s+ha?emorrhage|\bpph\b',
        r'(?:estimated\s+)?blood\s+loss', r'blood\s+transfusion',
        r'maternal\s+(?:mortalit|death|sepsis|infection)',
        r'caesarean|cesarean', r'third\s+stage\s+of\s+labou?r',
        r'active\s+management|expectant\s+management',
    ],
    'endpoint_patterns': [
        (r'maternal\s+(?:mortalit|death)|pregnancy-related\s+(?:death|mortalit)',
         'MATERNAL_MORTALITY'),
        (r'(?:primary\s+|severe\s+|obstetric\s+|post[- ]?partum\s+)?ha?emorrhage|\bpph\b',
         'POSTPARTUM_HAEMORRHAGE'),
        (r'(?:estimated\s+|measured\s+|mean\s+|peripartum\s+|intrapartum\s+)?blood\s+loss',
         'BLOOD_LOSS'),
        (r'blood\s+transfusion|red[- ]?cell\s+transfusion|need\s+for\s+transfusion',
         'BLOOD_TRANSFUSION'),
        (r'maternal\s+sepsis|puerperal\s+(?:sepsis|infection)|postpartum\s+infection|'
         r'endometritis', 'MATERNAL_SEPSIS'),
        (r'caesarean(?:\s+section|\s+delivery)?|cesarean(?:\s+section|\s+delivery)?|'
         r'c[- ]section', 'CAESAREAN'),
        (r'maternal\s+ana?emia|postpartum\s+ana?emia|antenatal\s+ana?emia',
         'MATERNAL_ANAEMIA'),
        (r'duration\s+of\s+labou?r|length\s+of\s+labou?r|labou?r\s+duration',
         'LABOUR_DURATION'),
    ],
    'context_patterns': [
        r'intention[- ]to[- ]treat|per[- ]protocol', r'third\s+stage',
        r'\biu\b|international\s+units?', r'vaginal\s+(?:birth|delivery)',
    ]
}


# ============================================================
# HYPERTENSIVE PATTERNS (pre-eclampsia / eclampsia)
# ============================================================

HYPERTENSIVE_PATTERNS = {
    'detection_keywords': [
        r'pre[- ]?eclampsia', r'eclampsia', r'eclamptic',
        r'magnesium\s+sul(?:f|ph)ate|\bmgso4\b', r'\bhellp\b',
        r'gestational\s+hypertension', r'pregnancy[- ]induced\s+hypertension',
        r'hypertensive\s+disorders?\s+of\s+pregnancy',
        r'labetalol', r'hydralazine', r'methyldopa', r'nifedipine',
        r'low[- ]dose\s+aspirin|\baspirin\b', r'\bproteinuria\b',
    ],
    'endpoint_patterns': [
        (r'severe\s+pre[- ]?eclampsia|hellp(?:\s+syndrome)?|severe\s+features',
         'SEVERE_PREECLAMPSIA'),
        (r'pre[- ]?eclampsia', 'PRE_ECLAMPSIA'),
        (r'eclampsia|eclamptic\s+(?:seizure|convulsion|fit)|recurren(?:ce|t)\s+'
         r'(?:of\s+)?(?:convulsion|seizure)', 'ECLAMPSIA'),
        (r'gestational\s+hypertension|pregnancy[- ]induced\s+hypertension|'
         r'severe\s+(?:maternal\s+)?hypertension|hypertensive\s+disorder', 'GESTATIONAL_HYPERTENSION'),
    ],
    'context_patterns': [
        r'systolic\s+blood\s+pressure|diastolic\s+blood\s+pressure', r'mmhg',
        r'loading\s+dose|maintenance\s+dose', r'\d+\s*weeks?\s+(?:gestation|of\s+pregnancy)',
    ]
}


# ============================================================
# NEONATAL PATTERNS (newborn outcomes)
# ============================================================

NEONATAL_PATTERNS = {
    'detection_keywords': [
        r'neonatal\s+(?:mortalit|death|sepsis|infection|encephalopathy)',
        r'stillbirth|fetal\s+death|foetal\s+death|intrauterine\s+death',
        r'perinatal\s+(?:mortalit|death)', r'birth\s+asphyxia|perinatal\s+asphyxia',
        r'hypoxic[- ]ischa?emic\s+encephalopathy|\bhie\b',
        r'\bnicu\b|neonatal\s+intensive\s+care|special\s+care\s+nursery',
        r'\bapgar\b', r'neonatal\s+resuscitation', r'chlorhexidine',
        r'kangaroo\s+mother\s+care|\bkmc\b', r'\bnewborn\b|\bneonate',
    ],
    'endpoint_patterns': [
        (r'neonatal\s+(?:mortalit|death)|newborn\s+(?:mortalit|death)', 'NEONATAL_MORTALITY'),
        (r'stillbirth|fetal\s+death|foetal\s+death|intra[- ]?uterine\s+(?:fetal\s+|foetal\s+)?death',
         'STILLBIRTH'),
        (r'perinatal\s+(?:mortalit|death|loss)', 'PERINATAL_MORTALITY'),
        (r'neonatal\s+sepsis|newborn\s+sepsis|(?:early|late)[- ]onset\s+sepsis|'
         r'neonatal\s+(?:bacterial\s+)?infection', 'NEONATAL_SEPSIS'),
        (r'birth\s+asphyxia|perinatal\s+asphyxia|hypoxic[- ]ischa?emic\s+encephalopathy|'
         r'neonatal\s+encephalopathy|\bhie\b', 'BIRTH_ASPHYXIA'),
        (r'nicu\s+admission|admission\s+to\s+(?:the\s+)?(?:nicu|neonatal\s+intensive)|'
         r'special\s+care\s+nursery|neonatal\s+unit\s+admission', 'NICU_ADMISSION'),
        (r'(?:5[- ]?minute\s+|five[- ]?minute\s+|mean\s+)?apgar(?:\s+score)?', 'APGAR_SCORE'),
    ],
    'context_patterns': [
        r'per\s+1,?000\s+(?:live\s+)?births?', r'within\s+\d+\s+days?\s+of\s+(?:birth|life)',
        r'cord\s+care', r'\d+\s+minutes?\s+of\s+(?:birth|life)',
    ]
}


# ============================================================
# PRETERM PATTERNS (prematurity & growth)
# ============================================================

PRETERM_PATTERNS = {
    'detection_keywords': [
        r'preterm\s+(?:birth|delivery|labou?r)|premature\s+(?:birth|delivery)',
        r'low\s+birth\s?weight|\blbw\b|\bvlbw\b', r'birth\s?weight',
        r'respiratory\s+distress\s+syndrome|\brds\b|hyaline\s+membrane',
        r'small[- ]for[- ]gestational[- ]age|\bsga\b',
        r'(?:intra[- ]?uterine|fetal|foetal)\s+growth\s+(?:restriction|retardation)|\biugr\b|\bfgr\b',
        r'antenatal\s+cortico?steroids?|\bacs\b', r'dexamethasone|betamethasone',
        r'tocolytic|tocolysis|atosiban', r'progesterone',
        r'gestational\s+age', r'\d+\s*weeks?\s+(?:of\s+)?gestation',
    ],
    'endpoint_patterns': [
        (r'preterm\s+(?:birth|delivery|labou?r)|premature\s+(?:birth|delivery)|'
         r'birth\s+before\s+37', 'PRETERM_BIRTH'),
        (r'(?:very\s+)?low\s+birth\s?weight|\bv?lbw\b', 'LOW_BIRTH_WEIGHT'),
        (r'(?<!low\s)(?:mean\s+|infant\s+|neonatal\s+)?birth\s?weight', 'BIRTH_WEIGHT'),
        (r'respiratory\s+distress\s+syndrome|\brds\b|hyaline\s+membrane\s+disease',
         'RESPIRATORY_DISTRESS'),
        (r'small[- ]for[- ]gestational[- ]age|\bsga\b|'
         r'(?:intra[- ]?uterine|fetal|foetal)\s+growth\s+restriction|\biugr\b|\bfgr\b',
         'SMALL_FOR_GESTATIONAL_AGE'),
        (r'gestational\s+age\s+at\s+(?:delivery|birth|randomi)|mean\s+gestational\s+age|'
         r'gestation\s+at\s+delivery', 'GESTATIONAL_AGE'),
    ],
    'context_patterns': [
        r'<\s*37\s+weeks|<\s*34\s+weeks|<\s*32\s+weeks|<\s*28\s+weeks',
        r'<\s*2500\s*g|<\s*1500\s*g', r'grams?|\bg\b', r'centile|percentile',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_maternal_neonatal_subspecialty(text: str) -> Tuple[str, float]:
    """Detect maternal/neonatal trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: maternal, hypertensive, neonatal, preterm, general_maternal_neonatal."""
    text_lower = text.lower()
    scores = {'maternal': 0, 'hypertensive': 0, 'neonatal': 0, 'preterm': 0}
    for kw in MATERNAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['maternal'] += 1
    for kw in HYPERTENSIVE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['hypertensive'] += 1
    for kw in NEONATAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['neonatal'] += 1
    for kw in PRETERM_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['preterm'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_maternal_neonatal', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_maternal_neonatal_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'maternal': MATERNAL_PATTERNS['endpoint_patterns'],
        'hypertensive': HYPERTENSIVE_PATTERNS['endpoint_patterns'],
        'neonatal': NEONATAL_PATTERNS['endpoint_patterns'],
        'preterm': PRETERM_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_maternal_neonatal_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical maternal/neonatal endpoint, preferring the LONGEST
    matching alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in MATERNAL_NEONATAL_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
