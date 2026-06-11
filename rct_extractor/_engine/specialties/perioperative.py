"""
Perioperative & Anaesthesia Subspecialty Patterns and Endpoints

Built for the same meta-analysis workflow as the tuberculosis / ARDS profiles.
Perioperative-medicine and anaesthesia RCTs report a distinct endpoint
vocabulary (30-day / postoperative mortality, major adverse cardiac events,
postoperative nausea and vomiting, postoperative delirium, acute kidney injury,
surgical-site infection, time to recovery, length of stay) that the generic
effect-size engine does not recognise on its own.

Subspecialties:
- Anaesthetic technique: regional / neuraxial (spinal, epidural, peripheral
  nerve block) vs general anaesthesia, total intravenous (TIVA / propofol) vs
  volatile/inhalational, depth-of-anaesthesia titration.
- PONV (postoperative nausea & vomiting): antiemetic prophylaxis (ondansetron,
  dexamethasone, droperidol, aprepitant), early/late PONV, rescue antiemetic.
- Organ protection: cardiac (perioperative myocardial infarction / injury,
  MACE, troponin, atrial fibrillation), renal (acute kidney injury), neuro
  (postoperative delirium, postoperative cognitive dysfunction).
- Recovery: postoperative complications, surgical-site infection, length of
  hospital/ICU stay, time to extubation / discharge, mortality.

Effect measures follow what these trials report: binary (mortality, MACE, PONV,
delirium, AKI, SSI, complications) -> RR/OR/RD/HR; count/time/score outcomes
(length of stay, time to recovery, pain score, opioid consumption) -> mean
difference, handled by the shared continuous augmenter.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# PERIOPERATIVE ENDPOINTS
# ============================================================

PERIOPERATIVE_ENDPOINTS = {
    # --- Mortality / cardiac ---
    'MORTALITY': {
        'aliases': ['mortality', 'death', 'all-cause mortality', '30-day mortality',
                    '30 day mortality', 'postoperative mortality', '90-day mortality',
                    'in-hospital mortality', 'perioperative mortality',
                    'one-year mortality', '1-year mortality', 'overall survival'],
        'subspecialty': 'recovery',
        'measure_types': ['RR', 'OR', 'HR', 'RD']
    },
    'MACE': {
        'aliases': ['major adverse cardiac events', 'major adverse cardiovascular events',
                    'mace', 'cardiovascular death', 'cardiac death',
                    'major cardiovascular complications'],
        'subspecialty': 'organ_protection',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'MYOCARDIAL_INJURY': {
        'aliases': ['myocardial infarction', 'perioperative myocardial infarction',
                    'myocardial injury', 'myocardial injury after non-cardiac surgery',
                    'mins', 'troponin elevation', 'postoperative troponin',
                    'cardiac injury'],
        'subspecialty': 'organ_protection',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'ATRIAL_FIBRILLATION': {
        'aliases': ['atrial fibrillation', 'postoperative atrial fibrillation',
                    'new-onset atrial fibrillation', 'poaf', 'arrhythmia'],
        'subspecialty': 'organ_protection',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- PONV ---
    'PONV': {
        'aliases': ['postoperative nausea and vomiting', 'ponv', 'nausea and vomiting',
                    'postoperative nausea', 'postoperative vomiting', 'early ponv',
                    'late ponv', 'nausea', 'vomiting', 'retching'],
        'subspecialty': 'ponv',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'RESCUE_ANTIEMETIC': {
        'aliases': ['rescue antiemetic', 'need for rescue antiemetic',
                    'rescue antiemetic use', 'rescue medication for nausea'],
        'subspecialty': 'ponv',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Neuro ---
    'DELIRIUM': {
        'aliases': ['postoperative delirium', 'delirium', 'incident delirium',
                    'emergence delirium', 'acute confusion'],
        'subspecialty': 'organ_protection',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'COGNITIVE_DYSFUNCTION': {
        'aliases': ['postoperative cognitive dysfunction', 'pocd',
                    'cognitive decline', 'cognitive impairment',
                    'neurocognitive disorder'],
        'subspecialty': 'organ_protection',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Renal ---
    'AKI': {
        'aliases': ['acute kidney injury', 'aki', 'postoperative acute kidney injury',
                    'renal failure', 'acute renal failure', 'renal replacement therapy'],
        'subspecialty': 'organ_protection',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- Recovery / complications ---
    'COMPLICATIONS': {
        'aliases': ['postoperative complications', 'major complications',
                    'overall complications', 'postoperative morbidity',
                    'serious complications', 'clavien-dindo',
                    'composite of complications', 'any complication'],
        'subspecialty': 'recovery',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'SSI': {
        'aliases': ['surgical site infection', 'surgical-site infection', 'ssi',
                    'wound infection', 'postoperative infection',
                    'deep wound infection'],
        'subspecialty': 'recovery',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'PULMONARY_COMPLICATIONS': {
        'aliases': ['postoperative pulmonary complications', 'pulmonary complications',
                    'ppc', 'pneumonia', 'respiratory failure', 'atelectasis'],
        'subspecialty': 'recovery',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'LENGTH_OF_STAY': {
        'aliases': ['length of stay', 'hospital length of stay', 'length of hospital stay',
                    'duration of hospital stay', 'icu length of stay',
                    'time to discharge', 'hospital stay'],
        'subspecialty': 'recovery',
        'measure_types': ['MD']
    },
    'TIME_TO_RECOVERY': {
        'aliases': ['time to recovery', 'recovery time', 'time to extubation',
                    'time to emergence', 'time to discharge from pacu',
                    'quality of recovery', 'qor-40', 'qor-15'],
        'subspecialty': 'recovery',
        'measure_types': ['MD']
    },

    # --- Anaesthetic technique ---
    'PAIN_SCORE': {
        'aliases': ['pain score', 'postoperative pain', 'pain intensity',
                    'visual analogue scale', 'vas pain', 'numeric rating scale',
                    'nrs pain', 'pain at rest', 'pain on movement'],
        'subspecialty': 'anaesthetic_technique',
        'measure_types': ['MD']
    },
    'OPIOID_CONSUMPTION': {
        'aliases': ['opioid consumption', 'morphine consumption',
                    'cumulative opioid consumption', 'morphine equivalent',
                    'postoperative opioid use', 'opioid requirement'],
        'subspecialty': 'anaesthetic_technique',
        'measure_types': ['MD']
    },
}


# ============================================================
# ANAESTHETIC TECHNIQUE PATTERNS
# ============================================================

ANAESTHETIC_TECHNIQUE_PATTERNS = {
    'detection_keywords': [
        r'regional\s+an(?:ae|e)sthesia|neuraxial|spinal\s+an(?:ae|e)sthesia|epidural',
        r'peripheral\s+nerve\s+block|nerve\s+block|fascial\s+plane\s+block',
        r'general\s+an(?:ae|e)sthesia|\bga\b|endotracheal',
        r'total\s+intravenous\s+an(?:ae|e)sthesia|\btiva\b|propofol',
        r'volatile\s+an(?:ae|e)sthe\w+|inhalational\s+an(?:ae|e)sthesia|sevoflurane|desflurane',
        r'depth\s+of\s+an(?:ae|e)sthesia|bispectral|\bbis\b',
        r'pain\s+score|opioid\s+consumption|morphine\s+consumption',
    ],
    'endpoint_patterns': [
        (r'pain\s+(?:score|intensity)|postoperative\s+pain|visual\s+analogue|\bvas\b|'
         r'numeric\s+rating\s+scale|\bnrs\b|pain\s+(?:at\s+rest|on\s+movement)', 'PAIN_SCORE'),
        (r'(?:cumulative\s+)?opioid\s+consumption|morphine\s+(?:consumption|equivalent)|'
         r'opioid\s+(?:use|requirement)', 'OPIOID_CONSUMPTION'),
        (r'postoperative\s+nausea\s+and\s+vomiting|\bponv\b', 'PONV'),
        (r'time\s+to\s+(?:recovery|extubation|emergence)|quality\s+of\s+recovery|qor[- ]?\d+',
         'TIME_TO_RECOVERY'),
        (r'(?:30[- ]day|postoperative|perioperative|in[- ]hospital)\s+(?:mortality|death)|'
         r'\bmortality\b|\bdeath\b', 'MORTALITY'),
    ],
    'context_patterns': [
        r'mg\s+morphine\s+equivalent', r'first\s+24\s+hours', r'at\s+rest\s+and\s+on\s+movement',
    ]
}


# ============================================================
# PONV PATTERNS
# ============================================================

PONV_PATTERNS = {
    'detection_keywords': [
        r'postoperative\s+nausea\s+and\s+vomiting|\bponv\b',
        r'antiemetic|anti[- ]emetic|ondansetron|dexamethasone|droperidol|aprepitant',
        r'palonosetron|granisetron|metoclopramide|scopolamine',
        r'rescue\s+antiemetic|nausea|vomiting|retching',
    ],
    'endpoint_patterns': [
        (r'rescue\s+antiemetic|need\s+for\s+rescue|rescue\s+medication\s+for\s+nausea',
         'RESCUE_ANTIEMETIC'),
        (r'postoperative\s+nausea\s+and\s+vomiting|\bponv\b|(?:early|late)\s+ponv|'
         r'\bnausea\b|\bvomiting\b|retching', 'PONV'),
        (r'(?:postoperative|perioperative)\s+(?:mortality|death)|\bmortality\b', 'MORTALITY'),
    ],
    'context_patterns': [
        r'0\s*[-–]\s*24\s*h|24[- ]hour|within\s+24\s+hours', r'apfel\s+score',
    ]
}


# ============================================================
# ORGAN PROTECTION PATTERNS
# ============================================================

ORGAN_PROTECTION_PATTERNS = {
    'detection_keywords': [
        r'myocardial\s+(?:infarction|injury)|\bmins\b|troponin|perioperative\s+cardiac',
        r'major\s+adverse\s+cardiac|\bmace\b',
        r'postoperative\s+atrial\s+fibrillation|\bpoaf\b|new[- ]onset\s+atrial',
        r'acute\s+kidney\s+injury|\baki\b|renal\s+replacement',
        r'postoperative\s+delirium|\bdelirium\b|cognitive\s+dysfunction|\bpocd\b',
        r'goal[- ]directed\s+(?:h(?:ae|e)modynamic\s+)?therapy|h(?:ae|e)modynamic',
    ],
    'endpoint_patterns': [
        (r'major\s+adverse\s+(?:cardiac|cardiovascular)\s+events?|\bmace\b|'
         r'cardiovascular\s+death|cardiac\s+death', 'MACE'),
        (r'(?:perioperative\s+)?myocardial\s+(?:infarction|injury)|\bmins\b|'
         r'troponin\s+elevation|cardiac\s+injury', 'MYOCARDIAL_INJURY'),
        (r'(?:postoperative|new[- ]onset)\s+atrial\s+fibrillation|\bpoaf\b|atrial\s+fibrillation',
         'ATRIAL_FIBRILLATION'),
        (r'acute\s+kidney\s+injury|\baki\b|renal\s+replacement\s+therapy|acute\s+renal\s+failure',
         'AKI'),
        (r'postoperative\s+delirium|emergence\s+delirium|\bdelirium\b', 'DELIRIUM'),
        (r'postoperative\s+cognitive\s+dysfunction|\bpocd\b|cognitive\s+(?:decline|impairment)',
         'COGNITIVE_DYSFUNCTION'),
        (r'(?:30[- ]day|postoperative|perioperative)\s+(?:mortality|death)|\bmortality\b',
         'MORTALITY'),
    ],
    'context_patterns': [
        r'fourth[- ]generation\s+troponin', r'cam[- ]icu|confusion\s+assessment',
        r'kdigo|akin\s+criteria',
    ]
}


# ============================================================
# RECOVERY PATTERNS
# ============================================================

RECOVERY_PATTERNS = {
    'detection_keywords': [
        r'postoperative\s+complications?|surgical[- ]site\s+infection|\bssi\b',
        r'postoperative\s+pulmonary\s+complications?|\bppc\b',
        r'length\s+of\s+(?:hospital\s+)?stay|time\s+to\s+discharge|hospital\s+stay',
        r'enhanced\s+recovery|\beras\b|clavien[- ]dindo',
        r'30[- ]day\s+(?:mortality|readmission)|postoperative\s+mortality',
    ],
    'endpoint_patterns': [
        (r'surgical[- ]site\s+infection|\bssi\b|wound\s+infection|deep\s+wound\s+infection',
         'SSI'),
        (r'postoperative\s+pulmonary\s+complications?|\bppc\b|atelectasis', 'PULMONARY_COMPLICATIONS'),
        (r'postoperative\s+complications?|major\s+complications?|postoperative\s+morbidity|'
         r'serious\s+complications?|clavien[- ]dindo|any\s+complication', 'COMPLICATIONS'),
        (r'(?:hospital\s+|icu\s+)?length\s+of\s+stay|length\s+of\s+(?:hospital|icu)\s+stay|'
         r'duration\s+of\s+hospital\s+stay|time\s+to\s+discharge', 'LENGTH_OF_STAY'),
        (r'time\s+to\s+(?:recovery|extubation|emergence)|quality\s+of\s+recovery', 'TIME_TO_RECOVERY'),
        (r'(?:30[- ]day|postoperative|perioperative|in[- ]hospital|one[- ]year|1[- ]year)\s+'
         r'(?:mortality|death)|\bmortality\b|\bdeath\b', 'MORTALITY'),
    ],
    'context_patterns': [
        r'enhanced\s+recovery\s+after\s+surgery', r'clavien[- ]dindo\s+grade',
        r'30[- ]day\s+readmission',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_perioperative_subspecialty(text: str) -> Tuple[str, float]:
    """Detect perioperative / anaesthesia trial subspecialty.
    Returns (subspecialty, confidence).
    Subspecialties: anaesthetic_technique, ponv, organ_protection, recovery,
    general_perioperative."""
    text_lower = text.lower()
    scores = {'anaesthetic_technique': 0, 'ponv': 0,
              'organ_protection': 0, 'recovery': 0}
    for kw in ANAESTHETIC_TECHNIQUE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['anaesthetic_technique'] += 1
    for kw in PONV_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['ponv'] += 1
    for kw in ORGAN_PROTECTION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['organ_protection'] += 1
    for kw in RECOVERY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['recovery'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_perioperative', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_perioperative_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'anaesthetic_technique': ANAESTHETIC_TECHNIQUE_PATTERNS['endpoint_patterns'],
        'ponv': PONV_PATTERNS['endpoint_patterns'],
        'organ_protection': ORGAN_PROTECTION_PATTERNS['endpoint_patterns'],
        'recovery': RECOVERY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_perioperative_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical perioperative endpoint, preferring the LONGEST
    matching alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in PERIOPERATIVE_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
