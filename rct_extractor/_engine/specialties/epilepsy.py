"""
Epilepsy / antiepileptic-drug (AED) Subspecialty Patterns and Endpoints

Built for the same African-student meta-analysis workflow as the malaria, HIV,
typhoid and cholera profiles. Epilepsy carries a huge treatment gap in Africa
(an estimated 60-90% of people with epilepsy in sub-Saharan Africa receive no
appropriate treatment), and the AED / treatment-gap RCT literature reports a
distinct endpoint vocabulary the generic effect-size engine does not recognise
on its own.

Subspecialties:
- Efficacy (AED seizure control): seizure freedom, >=50% responder rate, seizure
  frequency (counts / monthly rate), time to first seizure / time to treatment
  failure. Drugs: carbamazepine, valproate, levetiracetam, phenobarbital,
  lamotrigine, phenytoin, topiramate, oxcarbazepine, gabapentin, lacosamide,
  zonisamide, perampanel, brivaracetam, ethosuximide, clobazam, pregabalin,
  vigabatrin, eslicarbazepine, cenobamate.
- Tolerability (safety / retention): treatment withdrawal / discontinuation (incl.
  withdrawal due to adverse events), retention / treatment failure, any adverse
  event, serious adverse event, drug rash (lamotrigine / carbamazepine).
- Status epilepticus (emergency): clinical seizure cessation / termination,
  time to seizure cessation, seizure recurrence, need for rescue / additional
  anticonvulsant, intubation / respiratory depression. Arms: lorazepam, diazepam,
  midazolam, (fos)phenytoin, valproate, levetiracetam, phenobarbital.
- Treatment gap / adherence (closing the gap): medication adherence, the epilepsy
  treatment gap (proportion untreated), retention in care / loss to follow-up,
  quality of life (QOLIE). Interventions: phenobarbital primary-care delivery,
  task-shifting / community health workers, WHO mhGAP, mobile-health reminders.

Effect measures follow what these trials report: binary (seizure freedom,
responder, withdrawal, adverse event, cessation, recurrence, adherence) -> RR/OR/
RD; time-to-event (time to first seizure / treatment failure) -> HR; continuous
(seizure frequency -> log-normal / count, pool as ratio; time to cessation,
quality of life -> MD/SMD).
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# EPILEPSY ENDPOINTS
# ============================================================

EPILEPSY_ENDPOINTS = {
    # --- AED efficacy (seizure control) ---
    'SEIZURE_FREEDOM': {
        'aliases': ['seizure freedom', 'seizure-free', 'seizure free',
                    'freedom from seizures', 'free of seizures',
                    'complete seizure freedom', 'complete seizure control',
                    'seizure-free rate', 'terminal seizure freedom'],
        'subspecialty': 'efficacy',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'RESPONDER_50': {
        'aliases': ['50% responder', '>=50% responder', 'responder rate',
                    '50 percent responder', 'fifty percent responder',
                    '50% reduction in seizure frequency',
                    'at least 50% reduction', 'seizure response',
                    '>=50% reduction in seizures'],
        'subspecialty': 'efficacy',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'SEIZURE_FREQUENCY': {
        'aliases': ['seizure frequency', 'seizure rate', 'monthly seizure frequency',
                    'seizures per month', 'seizures per 28 days',
                    'seizure frequency per 28 days', 'seizure count',
                    'percentage reduction in seizure frequency',
                    'percent reduction in seizure frequency', 'seizure frequency reduction'],
        'subspecialty': 'efficacy',
        'measure_types': ['MD', 'SMD', 'RR']
    },
    'TIME_TO_SEIZURE': {
        'aliases': ['time to first seizure', 'time to twelve-month remission',
                    'time to 12-month remission', 'time to treatment failure',
                    'time to first treatment failure', 'time to withdrawal',
                    'time to exit', 'retention time'],
        'subspecialty': 'efficacy',
        'measure_types': ['HR', 'RR']
    },

    # --- Tolerability (safety / retention) ---
    'TREATMENT_WITHDRAWAL': {
        'aliases': ['treatment withdrawal', 'withdrawal due to adverse events',
                    'treatment discontinuation', 'discontinuation due to adverse events',
                    'drug withdrawal', 'study withdrawal', 'premature withdrawal',
                    'withdrawal for adverse events', 'treatment failure'],
        'subspecialty': 'tolerability',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'ADVERSE_EVENTS': {
        'aliases': ['adverse events', 'any adverse event', 'treatment-emergent adverse events',
                    'treatment emergent adverse events', 'adverse event rate',
                    'patients with adverse events'],
        'subspecialty': 'tolerability',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'SERIOUS_ADVERSE_EVENTS': {
        'aliases': ['serious adverse events', 'serious adverse event',
                    'serious treatment-emergent adverse events', 'sae'],
        'subspecialty': 'tolerability',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'DRUG_RASH': {
        'aliases': ['rash', 'skin rash', 'cutaneous reaction', 'drug rash',
                    'serious skin reaction', 'stevens-johnson', 'hypersensitivity rash'],
        'subspecialty': 'tolerability',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Status epilepticus (emergency) ---
    'SEIZURE_CESSATION': {
        'aliases': ['clinical seizure cessation', 'seizure cessation',
                    'cessation of seizures', 'termination of status epilepticus',
                    'seizure termination', 'clinical cessation of seizure activity',
                    'cessation of status epilepticus', 'seizure control'],
        'subspecialty': 'status_epilepticus',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'TIME_TO_CESSATION': {
        'aliases': ['time to seizure cessation', 'time to cessation of seizures',
                    'time to termination', 'time to seizure termination',
                    'seizure cessation time', 'latency to seizure cessation'],
        'subspecialty': 'status_epilepticus',
        'measure_types': ['MD', 'SMD', 'HR']
    },
    'SEIZURE_RECURRENCE': {
        'aliases': ['seizure recurrence', 'recurrence of seizures',
                    'recurrent seizure', 'seizure relapse',
                    'recurrence of status epilepticus'],
        'subspecialty': 'status_epilepticus',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'RESCUE_THERAPY': {
        'aliases': ['rescue therapy', 'rescue medication', 'need for additional anticonvulsant',
                    'need for further anticonvulsant', 'additional antiseizure medication',
                    'need for rescue treatment', 'need for intubation',
                    'endotracheal intubation', 'respiratory depression'],
        'subspecialty': 'status_epilepticus',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Treatment gap / adherence ---
    'ADHERENCE': {
        'aliases': ['medication adherence', 'treatment adherence', 'adherence',
                    'drug adherence', 'adherence rate', 'optimal adherence',
                    'compliance', 'medication compliance'],
        'subspecialty': 'treatment_gap',
        'measure_types': ['RR', 'OR', 'MD']
    },
    'TREATMENT_GAP': {
        'aliases': ['treatment gap', 'epilepsy treatment gap', 'proportion untreated',
                    'untreated epilepsy', 'receiving no treatment', 'treatment coverage',
                    'antiepileptic drug coverage'],
        'subspecialty': 'treatment_gap',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'RETENTION_IN_CARE': {
        'aliases': ['retention in care', 'retention', 'loss to follow-up',
                    'lost to follow-up', 'retained in care', 'follow-up completion',
                    'remained in treatment'],
        'subspecialty': 'treatment_gap',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'QUALITY_OF_LIFE': {
        'aliases': ['quality of life', 'qolie', 'qolie-31', 'qolie-10',
                    'quality of life in epilepsy', 'health-related quality of life',
                    'hrqol'],
        'subspecialty': 'treatment_gap',
        'measure_types': ['MD', 'SMD']
    },
}


# ============================================================
# EFFICACY PATTERNS (AED seizure control)
# ============================================================

EFFICACY_PATTERNS = {
    'detection_keywords': [
        r'carbamazepine', r'valproate|valproic|divalproex|sodium\s+valproate',
        r'levetiracetam', r'phenobarbit(?:al|one)', r'lamotrigine', r'phenytoin',
        r'topiramate', r'oxcarbazepine', r'eslicarbazepine', r'gabapentin',
        r'pregabalin', r'lacosamide', r'zonisamide', r'perampanel', r'brivaracetam',
        r'ethosuximide', r'clobazam', r'vigabatrin', r'cenobamate',
        r'anti[- ]?epileptic\s+drug|antiseizure\s+(?:medication|drug)|anticonvulsant',
        r'\baed\b|\basm\b', r'seizure\s+freedom|seizure[- ]free',
        r'responder\s+rate|50%\s+(?:responder|reduction)',
        r'seizure\s+frequency|seizures\s+per\s+(?:month|28\s+days)',
        r'focal\s+(?:onset\s+)?seizure|generali[sz]ed\s+(?:tonic[- ]clonic|seizure)',
    ],
    'endpoint_patterns': [
        (r'seizure\s+freedom|seizure[- ]free|freedom\s+from\s+seizures|'
         r'free\s+of\s+seizures|complete\s+seizure\s+control', 'SEIZURE_FREEDOM'),
        (r'(?:>=|≥|at\s+least\s+)?50%?\s*(?:percent\s+)?responder|responder\s+rate|'
         r'(?:>=|≥|at\s+least\s+)?50%?\s+reduction\s+in\s+seizure', 'RESPONDER_50'),
        (r'seizure\s+frequency|seizure\s+rate|seizures\s+per\s+(?:month|28\s+days)|'
         r'seizure\s+count|reduction\s+in\s+seizure\s+frequency', 'SEIZURE_FREQUENCY'),
        (r'time\s+to\s+(?:first\s+seizure|(?:first\s+)?treatment\s+failure|'
         r'(?:12|twelve)[- ]month\s+remission|withdrawal|exit)', 'TIME_TO_SEIZURE'),
    ],
    'context_patterns': [
        r'per[- ]protocol|intention[- ]to[- ]treat', r'monotherapy|adjunctive|add[- ]on',
        r'baseline\s+seizure\s+frequency', r'titration\s+(?:period|phase)|maintenance\s+phase',
    ]
}


# ============================================================
# TOLERABILITY PATTERNS (safety / retention)
# ============================================================

TOLERABILITY_PATTERNS = {
    'detection_keywords': [
        r'treatment\s+withdrawal|withdrawal\s+(?:due\s+to|for)\s+adverse',
        r'discontinuation\s+(?:due\s+to|for)\s+adverse', r'treatment\s+retention',
        r'adverse\s+events?', r'serious\s+adverse\s+events?|\bsae\b',
        r'treatment[- ]emergent', r'\brash\b|skin\s+reaction|stevens[- ]johnson',
        r'tolerability', r'somnolence|dizziness|fatigue|drop[- ]out',
    ],
    'endpoint_patterns': [
        (r'(?:treatment|drug|study|premature)\s+withdrawal|withdrawal\s+(?:due\s+to|for)\s+'
         r'adverse|(?:treatment\s+)?discontinuation\s+(?:due\s+to|for)\s+adverse|'
         r'treatment\s+failure', 'TREATMENT_WITHDRAWAL'),
        (r'serious\s+(?:treatment[- ]emergent\s+)?adverse\s+events?|\bsae\b',
         'SERIOUS_ADVERSE_EVENTS'),
        (r'(?:any\s+|treatment[- ]emergent\s+)?adverse\s+events?|adverse\s+event\s+rate',
         'ADVERSE_EVENTS'),
        (r'(?:skin\s+|drug\s+|serious\s+skin\s+)?rash|cutaneous\s+reaction|'
         r'stevens[- ]johnson|hypersensitivity\s+reaction', 'DRUG_RASH'),
    ],
    'context_patterns': [
        r'safety\s+population', r'treatment[- ]emergent', r'dose[- ]related',
    ]
}


# ============================================================
# STATUS EPILEPTICUS PATTERNS (emergency)
# ============================================================

STATUS_EPILEPTICUS_PATTERNS = {
    'detection_keywords': [
        r'status\s+epilepticus', r'convulsive\s+status', r'refractory\s+status',
        r'established\s+status\s+epilepticus', r'\brse\b|\bcse\b|\bese\b',
        r'lorazepam', r'diazepam', r'midazolam', r'fos?phenytoin',
        r'seizure\s+(?:cessation|termination)', r'clinical\s+cessation',
        r'benzodiazepine', r'second[- ]line\s+(?:agent|anticonvulsant)',
    ],
    'endpoint_patterns': [
        (r'time\s+to\s+(?:seizure\s+)?(?:cessation|termination)|latency\s+to\s+'
         r'(?:seizure\s+)?cessation|seizure\s+cessation\s+time', 'TIME_TO_CESSATION'),
        (r'(?:clinical\s+)?(?:seizure\s+)?cessation(?:\s+of\s+(?:seizures?|status))?|'
         r'(?:seizure|status\s+epilepticus)\s+termination|seizure\s+control', 'SEIZURE_CESSATION'),
        (r'(?:seizure|status\s+epilepticus)\s+recurrence|recurren(?:ce|t)\s+(?:of\s+)?seizure|'
         r'seizure\s+relapse', 'SEIZURE_RECURRENCE'),
        (r'rescue\s+(?:therapy|medication|treatment)|need\s+for\s+(?:additional|further|rescue)\s+'
         r'anticonvulsant|(?:endotracheal\s+)?intubation|respiratory\s+depression',
         'RESCUE_THERAPY'),
    ],
    'context_patterns': [
        r'pre[- ]hospital|emergency\s+department', r'intramuscular|intravenous|buccal|rectal',
        r'intensive\s+care',
    ]
}


# ============================================================
# TREATMENT GAP / ADHERENCE PATTERNS (closing the gap)
# ============================================================

TREATMENT_GAP_PATTERNS = {
    'detection_keywords': [
        r'treatment\s+gap', r'epilepsy\s+treatment\s+gap', r'untreated\s+epilepsy',
        r'medication\s+adherence|treatment\s+adherence|drug\s+adherence',
        r'retention\s+in\s+care|loss\s+to\s+follow[- ]up',
        r'task[- ]shifting|community\s+health\s+worker|primary[- ]care\s+delivery',
        r'\bmhgap\b|mobile[- ]health|\bmhealth\b|\bsms\b\s+reminder',
        r'quality\s+of\s+life|qolie',
    ],
    'endpoint_patterns': [
        (r'(?:epilepsy\s+)?treatment\s+gap|proportion\s+untreated|untreated\s+epilepsy|'
         r'receiving\s+no\s+treatment|(?:antiepileptic\s+drug\s+|treatment\s+)coverage',
         'TREATMENT_GAP'),
        (r'(?:medication|treatment|drug)\s+adherence|adherence\s+rate|optimal\s+adherence|'
         r'medication\s+compliance', 'ADHERENCE'),
        (r'retention\s+in\s+care|retained\s+in\s+care|loss\s+to\s+follow[- ]up|'
         r'lost\s+to\s+follow[- ]up|remained\s+in\s+treatment', 'RETENTION_IN_CARE'),
        (r'quality\s+of\s+life|qolie(?:-\d+)?|health[- ]related\s+quality\s+of\s+life|'
         r'\bhrqol\b', 'QUALITY_OF_LIFE'),
    ],
    'context_patterns': [
        r'low[- ]\s?and\s+middle[- ]income|sub[- ]saharan', r'rural', r'self[- ]report',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_epilepsy_subspecialty(text: str) -> Tuple[str, float]:
    """Detect epilepsy trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: efficacy, tolerability, status_epilepticus, treatment_gap,
    general_epilepsy."""
    text_lower = text.lower()
    scores = {'efficacy': 0, 'tolerability': 0, 'status_epilepticus': 0, 'treatment_gap': 0}
    for kw in EFFICACY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['efficacy'] += 1
    for kw in TOLERABILITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['tolerability'] += 1
    for kw in STATUS_EPILEPTICUS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['status_epilepticus'] += 1
    for kw in TREATMENT_GAP_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['treatment_gap'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_epilepsy', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_epilepsy_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'efficacy': EFFICACY_PATTERNS['endpoint_patterns'],
        'tolerability': TOLERABILITY_PATTERNS['endpoint_patterns'],
        'status_epilepticus': STATUS_EPILEPTICUS_PATTERNS['endpoint_patterns'],
        'treatment_gap': TREATMENT_GAP_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_epilepsy_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical epilepsy endpoint, preferring the LONGEST matching
    alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in EPILEPSY_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
