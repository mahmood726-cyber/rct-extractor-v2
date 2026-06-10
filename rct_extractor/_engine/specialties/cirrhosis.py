"""
Cirrhosis / Decompensated Liver Disease Subspecialty Patterns and Endpoints

Built for the same meta-analysis extraction workflow as the malaria / TB / HIV
profiles. Cirrhosis RCTs report a distinct endpoint vocabulary (variceal
bleeding / rebleeding, ascites control, hepatorenal syndrome reversal,
spontaneous bacterial peritonitis, hepatic encephalopathy recurrence/reversal,
transplant-free survival, ACLF) that the generic effect-size engine — and the
hepatitis profile (which only keys on the bare word "cirrhosis") — do not capture.

Subspecialties (mapped onto the registry's generic pattern slots):
- portal_hypertension (TREATMENT slot): variceal haemorrhage primary/secondary
  prophylaxis and acute bleeding — variceal bleeding, rebleeding, non-selective
  beta-blockers (carvedilol/propranolol/nadolol), band ligation, TIPS, HVPG.
- decompensation (DRUG_RESISTANT slot): ascites / hepatorenal syndrome / SBP —
  refractory ascites, HRS-AKI reversal, terlipressin + albumin, large-volume
  paracentesis, SBP prevention (norfloxacin/rifaximin).
- encephalopathy (PREVENTION slot): hepatic encephalopathy — HE recurrence /
  reversal, rifaximin, lactulose, L-ornithine L-aspartate.
- progression (LATENT slot): ACLF / transplant-free survival / overall mortality;
  MELD; statins; albumin (ANSWER/ATTIRE-type).

British/American spelling handled (haemorrhage/hemorrhage via `ha?emorrhage`,
oesophageal/esophageal via `o?esophageal`). Effect measures: bleeding /
rebleeding / HRS reversal / HE recurrence / SBP / survival -> RR/OR/HR; MELD and
HVPG change -> mean difference via the core engine.
"""
from typing import Dict, List, Tuple, Optional
import re

CIRRHOSIS_ENDPOINTS = {
    'VARICEAL_BLEEDING': {
        'aliases': ['variceal bleeding', 'variceal haemorrhage', 'variceal hemorrhage',
                    'oesophageal variceal bleeding', 'esophageal variceal bleeding',
                    'first variceal bleed', 'gastrointestinal bleeding', 'acute variceal'],
        'subspecialty': 'portal_hypertension',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'REBLEEDING': {
        'aliases': ['rebleeding', 're-bleeding', 'variceal rebleeding',
                    'recurrent variceal bleeding', 'rebleeding rate'],
        'subspecialty': 'portal_hypertension',
        'measure_types': ['RR', 'HR', 'OR']
    },
    'HVPG': {
        'aliases': ['hvpg', 'hepatic venous pressure gradient', 'portal pressure',
                    'hvpg response', 'reduction in hvpg'],
        'subspecialty': 'portal_hypertension',
        'measure_types': ['MD', 'RR']
    },
    'ASCITES_CONTROL': {
        'aliases': ['ascites', 'refractory ascites', 'control of ascites',
                    'recurrence of ascites', 'ascites resolution', 'tense ascites'],
        'subspecialty': 'decompensation',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'HRS_REVERSAL': {
        'aliases': ['hepatorenal syndrome', 'hrs reversal', 'reversal of hrs',
                    'hrs-aki', 'hepatorenal syndrome reversal', 'complete response of hrs',
                    'hrs response'],
        'subspecialty': 'decompensation',
        'measure_types': ['RR', 'OR']
    },
    'SBP': {
        'aliases': ['spontaneous bacterial peritonitis', 'sbp', 'bacterial peritonitis',
                    'sbp prevention', 'infection prevention'],
        'subspecialty': 'decompensation',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'HE_RECURRENCE': {
        'aliases': ['hepatic encephalopathy recurrence', 'recurrence of hepatic encephalopathy',
                    'he recurrence', 'breakthrough hepatic encephalopathy',
                    'overt hepatic encephalopathy', 'recurrence of overt he'],
        'subspecialty': 'encephalopathy',
        'measure_types': ['RR', 'HR', 'OR']
    },
    'HE_REVERSAL': {
        'aliases': ['hepatic encephalopathy reversal', 'reversal of hepatic encephalopathy',
                    'he reversal', 'improvement in hepatic encephalopathy',
                    'he resolution', 'time to he resolution'],
        'subspecialty': 'encephalopathy',
        'measure_types': ['RR', 'OR']
    },
    'TRANSPLANT_FREE_SURVIVAL': {
        'aliases': ['transplant-free survival', 'transplant free survival',
                    'liver transplant-free survival', 'transplantation-free survival'],
        'subspecialty': 'progression',
        'measure_types': ['HR', 'RR']
    },
    'ACLF': {
        'aliases': ['acute-on-chronic liver failure', 'aclf', 'acute on chronic liver failure',
                    'aclf development', 'progression to aclf'],
        'subspecialty': 'progression',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'MELD': {
        'aliases': ['meld score', 'meld', 'meld-na', 'change in meld',
                    'model for end-stage liver disease', 'child-pugh score'],
        'subspecialty': 'progression',
        'measure_types': ['MD']
    },
    'MORTALITY': {
        'aliases': ['mortality', 'death', 'all-cause mortality', 'overall survival',
                    'liver-related mortality', '90-day mortality', '28-day mortality',
                    'survival'],
        'subspecialty': 'progression',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'READMISSION': {
        'aliases': ['readmission', 'hospital readmission', 'rehospitalization',
                    'liver-related readmission', '30-day readmission'],
        'subspecialty': 'progression',
        'measure_types': ['RR', 'HR', 'OR']
    },
    'ADVERSE_EVENTS': {
        'aliases': ['adverse events', 'serious adverse events', 'serious adverse event',
                    'treatment-emergent adverse events', 'acute kidney injury',
                    'discontinuation due to adverse'],
        'subspecialty': 'decompensation',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


TREATMENT_PATTERNS = {  # = portal_hypertension
    'detection_keywords': [
        r'variceal\s+(?:bleed|haemorrhage|hemorrhage)|o?esophageal\s+varices|gastric\s+varices',
        r'portal\s+hypertension|\bhvpg\b|hepatic\s+venous\s+pressure',
        r'non[- ]selective\s+beta[- ]?blocker|\bnsbb\b|carvedilol|propranolol|nadolol',
        r'(?:endoscopic\s+)?(?:band\s+)?ligation|\bevl\b|sclerotherapy',
        r'\btips\b|transjugular\s+intrahepatic|rebleed',
    ],
    'endpoint_patterns': [
        (r'(?:variceal\s+)?rebleed(?:ing)?|re[- ]bleeding|recurrent\s+variceal', 'REBLEEDING'),
        (r'variceal\s+(?:bleed\w*|haemorrhage|hemorrhage)|o?esophageal\s+variceal|'
         r'acute\s+variceal|first\s+variceal\s+bleed|gastrointestinal\s+bleeding', 'VARICEAL_BLEEDING'),
        (r'\bhvpg\b|hepatic\s+venous\s+pressure|portal\s+pressure', 'HVPG'),
        (r'(?:all[- ]cause\s+)?(?:mortality|death)|survival', 'MORTALITY'),
        (r'serious\s+adverse\s+events?|\badverse\s+events?\b', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'primary\s+prophylaxis|secondary\s+prophylaxis', r'child[- ]pugh|\bmeld\b',
    ]
}


DRUG_RESISTANT_PATTERNS = {  # = decompensation (ascites / HRS / SBP)
    'detection_keywords': [
        r'refractory\s+ascites|\bascites\b|large[- ]volume\s+paracentesis',
        r'hepatorenal\s+syndrome|\bhrs[- ]?aki?\b|\bhrs\b',
        r'spontaneous\s+bacterial\s+peritonitis|\bsbp\b',
        r'terlipressin|midodrine|octreotide|nor(?:floxacin)?|albumin\s+infusion',
        r'paracentesis|tolvaptan|cefotaxime',
    ],
    'endpoint_patterns': [
        (r'hepatorenal\s+syndrome|\bhrs[- ]?aki?\b|reversal\s+of\s+hrs|hrs\s+(?:reversal|response)|'
         r'complete\s+response\s+of\s+hrs', 'HRS_REVERSAL'),
        (r'spontaneous\s+bacterial\s+peritonitis|\bsbp\b|bacterial\s+peritonitis', 'SBP'),
        (r'refractory\s+ascites|recurrence\s+of\s+ascites|control\s+of\s+ascites|'
         r'ascites\s+resolution|\bascites\b', 'ASCITES_CONTROL'),
        (r'acute\s+kidney\s+injury|serious\s+adverse\s+events?|\badverse\s+events?\b',
         'ADVERSE_EVENTS'),
        (r'(?:all[- ]cause\s+)?(?:mortality|death)|survival', 'MORTALITY'),
    ],
    'context_patterns': [
        r'albumin', r'creatinine', r'\bmeld\b', r'90[- ]day|28[- ]day',
    ]
}


PREVENTION_PATTERNS = {  # = encephalopathy
    'detection_keywords': [
        r'hepatic\s+encephalopathy|\bhe\b\s+(?:recurrence|reversal|episode)|overt\s+he',
        r'rifaximin|lactulose|l[- ]ornithine\s+l[- ]aspartate|\blola\b',
        r'covert\s+(?:hepatic\s+)?encephalopathy|minimal\s+hepatic\s+encephalopathy',
        r'ammonia|west[- ]haven',
    ],
    'endpoint_patterns': [
        (r'recurrence\s+of\s+(?:overt\s+)?hepatic\s+encephalopathy|hepatic\s+encephalopathy\s+recurrence|'
         r'breakthrough\s+(?:hepatic\s+)?encephalopathy|he\s+recurrence|recurrence\s+of\s+overt\s+he',
         'HE_RECURRENCE'),
        (r'reversal\s+of\s+hepatic\s+encephalopathy|hepatic\s+encephalopathy\s+reversal|'
         r'improvement\s+in\s+(?:hepatic\s+)?encephalopathy|he\s+(?:reversal|resolution)', 'HE_REVERSAL'),
        (r'readmission|rehospitali[sz]ation', 'READMISSION'),
        (r'(?:all[- ]cause\s+)?(?:mortality|death)|survival', 'MORTALITY'),
        (r'serious\s+adverse\s+events?|\badverse\s+events?\b', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'time\s+to\s+(?:first\s+)?(?:breakthrough|recurrence)', r'number\s+connection\s+test',
    ]
}


LATENT_PATTERNS = {  # = progression / ACLF / survival
    'detection_keywords': [
        r'acute[- ]on[- ]chronic\s+liver\s+failure|\baclf\b',
        r'transplant[- ]free\s+survival|liver\s+transplant',
        r'decompensated\s+cirrhosis|compensated\s+(?:advanced\s+)?(?:chronic\s+liver|cirrhosis)',
        r'\bmeld\b|child[- ]pugh|model\s+for\s+end[- ]stage',
        r'statin|simvastatin|albumin\s+(?:infusion|administration)|long[- ]term\s+albumin',
    ],
    'endpoint_patterns': [
        (r'transplant[- ]free\s+survival|transplantation[- ]free\s+survival', 'TRANSPLANT_FREE_SURVIVAL'),
        (r'acute[- ]on[- ]chronic\s+liver\s+failure|\baclf\b|progression\s+to\s+aclf', 'ACLF'),
        (r'\bmeld(?:-na)?\b|child[- ]pugh\s+score|model\s+for\s+end[- ]stage', 'MELD'),
        (r'readmission|rehospitali[sz]ation', 'READMISSION'),
        (r'(?:all[- ]cause\s+|liver[- ]related\s+)?(?:mortality|death)|overall\s+survival|'
         r'90[- ]day\s+(?:mortality|survival)|28[- ]day\s+(?:mortality|survival)|\bsurvival\b',
         'MORTALITY'),
    ],
    'context_patterns': [
        r'cirrhosis', r'portal\s+hypertension', r'\bnafld\b|\bmash\b|alcohol',
    ]
}


def detect_cirrhosis_subspecialty(text: str) -> Tuple[str, float]:
    """Detect cirrhosis trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: portal_hypertension, decompensation, encephalopathy,
    progression, general_cirrhosis."""
    text_lower = text.lower()
    scores = {'portal_hypertension': 0, 'decompensation': 0, 'encephalopathy': 0,
              'progression': 0}
    for kw in TREATMENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['portal_hypertension'] += 1
    for kw in DRUG_RESISTANT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['decompensation'] += 1
    for kw in PREVENTION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['encephalopathy'] += 1
    for kw in LATENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['progression'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_cirrhosis', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_cirrhosis_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'portal_hypertension': TREATMENT_PATTERNS['endpoint_patterns'],
        'decompensation': DRUG_RESISTANT_PATTERNS['endpoint_patterns'],
        'encephalopathy': PREVENTION_PATTERNS['endpoint_patterns'],
        'progression': LATENT_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_cirrhosis_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical cirrhosis endpoint, preferring the LONGEST alias."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in CIRRHOSIS_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
