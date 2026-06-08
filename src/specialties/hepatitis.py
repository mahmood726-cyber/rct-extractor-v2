"""
Hepatitis (viral) Subspecialty Patterns and Endpoints

Built for the same African-student meta-analysis workflow as the malaria and HIV
profiles. Viral-hepatitis RCTs (HBV and HCV, with HAV/HDV/HEV at the margins)
report a distinct endpoint vocabulary the generic effect-size engine does not
recognise on its own.

Subspecialties:
- Treatment (antiviral efficacy):
    HCV direct-acting antivirals -> sustained virologic response (SVR12/SVR24),
      virologic relapse, on-treatment virologic failure.
    HBV nucleos(t)ide / peg-interferon -> HBV DNA suppression, HBeAg
      seroconversion, HBsAg loss (functional cure), ALT normalization,
      treatment discontinuation.
- Prevention (vaccine / immunoglobulin): seroprotection (anti-HBs >=10 mIU/mL),
  incident HBV infection.
- PMTCT (prevention of mother-to-child transmission of HBV): perinatal /
  vertical transmission, infant HBsAg positivity.
- Outcomes (liver-disease progression): hepatocellular carcinoma, cirrhosis /
  hepatic decompensation, liver-related mortality, all-cause mortality, liver
  transplantation.

Effect measures follow what these trials report: binary (SVR, HBsAg loss,
seroprotection, MTCT) -> RR/OR/RD; incidence / time-to-event (HCC, mortality,
HBV infection) -> IRR/HR; continuous (HBV DNA log10 IU/mL, ALT, liver stiffness)
-> MD/SMD (HBV DNA is log-scale).
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# HEPATITIS ENDPOINTS
# ============================================================

HEPATITIS_ENDPOINTS = {
    # --- HCV treatment efficacy ---
    'SVR': {
        'aliases': ['sustained virologic response', 'sustained virological response',
                    'svr12', 'svr 12', 'svr24', 'svr 24', 'svr4', 'svr', 'hcv cure', 'viral cure',
                    'undetectable hcv rna 12 weeks', 'sustained viral response', 'sustained response'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'RD', 'OR']
    },
    # Interferon-era HCV milestones (still common in older / genotype-4 / African
    # trials). Distinct endpoints -- pooling them into SVR would corrupt the estimand.
    'RVR': {
        'aliases': ['rapid virologic response', 'rapid virological response', 'rvr'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR']
    },
    'EVR': {
        'aliases': ['early virologic response', 'early virological response', 'evr',
                    'complete early virologic response', 'partial early virologic response',
                    'cevr', 'pevr'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR']
    },
    'ETR': {
        'aliases': ['end-of-treatment response', 'end of treatment response',
                    'end-of-treatment virologic response', 'etr'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR']
    },
    'VIROLOGIC_RELAPSE': {
        'aliases': ['virologic relapse', 'virological relapse',
                    'post-treatment relapse', 'viral relapse'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR']
    },
    'ON_TREATMENT_FAILURE': {
        'aliases': ['on-treatment virologic failure', 'virologic failure',
                    'virological failure', 'null response', 'non-response',
                    'treatment failure', 'non-responder'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR']
    },
    'VIROLOGIC_BREAKTHROUGH': {
        'aliases': ['virologic breakthrough', 'virological breakthrough', 'viral breakthrough',
                    'biochemical breakthrough', 'hepatic flare', 'alt flare'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR']
    },
    'DRUG_RESISTANCE': {
        'aliases': ['genotypic resistance', 'antiviral resistance', 'drug resistance',
                    'resistance mutation', 'resistance-associated mutation', 'rtm204',
                    'ymdd', 'resistant virus'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR']
    },
    'SERIOUS_AE': {
        'aliases': ['serious adverse event', 'serious adverse events', 'sae', 'saes'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'HCV_RNA_LEVEL': {
        'aliases': ['hcv rna level', 'change in hcv rna', 'hcv rna reduction',
                    'hcv rna decline', 'baseline hcv rna', 'mean hcv rna'],
        'subspecialty': 'treatment',
        'measure_types': ['MD', 'SMD', 'GMR']
    },

    # --- HBV treatment efficacy ---
    'HBV_DNA_SUPPRESSION': {
        'aliases': ['hbv dna suppression', 'undetectable hbv dna', 'hbv dna negativity',
                    'undetectable hepatitis b virus dna', 'complete virologic response'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'RD', 'OR']
    },
    'HBEAG_SEROCONVERSION': {
        'aliases': ['hbeag seroconversion', 'e antigen seroconversion',
                    'e-antigen seroconversion', 'hbeag loss', 'hbeag clearance',
                    'loss of hbeag'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR']
    },
    'HBSAG_LOSS': {
        'aliases': ['hbsag loss', 'hbsag seroclearance', 'surface antigen loss',
                    'functional cure', 'hbsag clearance', 'loss of hbsag',
                    'hbsag seroconversion'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR']
    },
    'ALT_NORMALIZATION': {
        'aliases': ['alt normalization', 'alt normalisation', 'biochemical response',
                    'normalization of alt', 'normalisation of alt', 'alanine aminotransferase normalization'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR']
    },
    'HBV_DNA_LEVEL': {
        'aliases': ['hbv dna level', 'change in hbv dna', 'log10 iu/ml', 'log iu/ml',
                    'hbv dna reduction', 'mean hbv dna', 'serum hbv dna'],
        'subspecialty': 'treatment',
        'measure_types': ['MD', 'SMD', 'GMR']
    },
    'ALT_LEVEL': {
        'aliases': ['alt level', 'change in alt', 'mean alt', 'serum alt',
                    'alanine aminotransferase level', 'change in alanine aminotransferase'],
        'subspecialty': 'treatment',
        'measure_types': ['MD', 'SMD']
    },
    'LIVER_STIFFNESS': {
        'aliases': ['liver stiffness', 'fibroscan', 'transient elastography',
                    'liver stiffness measurement', 'kpa', 'fibrosis regression'],
        'subspecialty': 'treatment',
        'measure_types': ['MD', 'SMD']
    },
    'TREATMENT_DISCONTINUATION': {
        'aliases': ['discontinuation', 'treatment discontinuation', 'treatment-limiting',
                    'discontinuation due to adverse events', 'drug discontinuation',
                    'premature discontinuation'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Prevention (vaccine / immunoglobulin) ---
    'SEROPROTECTION': {
        'aliases': ['seroprotection', 'seroprotective', 'anti-hbs >=10', 'anti-hbs >10',
                    'protective antibody', 'seroconversion rate', 'vaccine seroconversion',
                    'protective anti-hbs titre', 'seroprotection rate'],
        'subspecialty': 'prevention',
        'measure_types': ['RR', 'RD', 'OR']
    },
    'HBV_INFECTION': {
        'aliases': ['hbv infection', 'incident hepatitis b', 'new hbv infection',
                    'hepatitis b infection', 'incidence of hepatitis b', 'hbsag positivity',
                    'chronic hbv infection', 'breakthrough hepatitis b'],
        'subspecialty': 'prevention',
        'measure_types': ['RR', 'IRR', 'HR']
    },
    'ANTI_HBS_TITRE': {
        'aliases': ['geometric mean titre', 'geometric mean titer', 'geometric mean concentration',
                    'gmt', 'gmc', 'anti-hbs titre', 'anti-hbs titer', 'anti-hbs concentration',
                    'geometric mean antibody'],
        'subspecialty': 'prevention',
        'measure_types': ['MD', 'SMD', 'GMR']
    },

    # --- PMTCT (HBV vertical transmission) ---
    'PERINATAL_TRANSMISSION': {
        'aliases': ['mother-to-child transmission', 'mtct', 'vertical transmission',
                    'perinatal transmission', 'infant hbsag', 'infant infection',
                    'transmission to infant', 'intrauterine transmission',
                    'mother to child transmission of hepatitis b'],
        'subspecialty': 'pmtct',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Outcomes (liver-disease progression) ---
    'HCC': {
        'aliases': ['hepatocellular carcinoma', 'liver cancer', 'hcc',
                    'incident hcc', 'hcc incidence', 'primary liver cancer'],
        'subspecialty': 'outcomes',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'CIRRHOSIS': {
        'aliases': ['cirrhosis', 'hepatic decompensation', 'decompensation',
                    'fibrosis progression', 'progression to cirrhosis',
                    'decompensated liver disease', 'liver failure'],
        'subspecialty': 'outcomes',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'LIVER_MORTALITY': {
        'aliases': ['liver-related death', 'liver-related mortality', 'hepatic death',
                    'liver-related deaths', 'death from liver disease'],
        'subspecialty': 'outcomes',
        'measure_types': ['HR', 'RR']
    },
    'MORTALITY': {
        'aliases': ['all-cause mortality', 'all-cause death', 'overall survival',
                    'mortality', 'death'],
        'subspecialty': 'outcomes',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'LIVER_TRANSPLANT': {
        'aliases': ['liver transplantation', 'liver transplant', 'transplant-free survival',
                    'need for transplantation'],
        'subspecialty': 'outcomes',
        'measure_types': ['HR', 'RR']
    },
}


# ============================================================
# TREATMENT PATTERNS (HCV DAA + HBV nucleos(t)ide / peg-IFN)
# ============================================================

TREATMENT_PATTERNS = {
    'detection_keywords': [
        r'direct[- ]acting\s+antiviral|\bdaa\b', r'sustained\s+virologic\w*\s+response|\bsvr\b',
        r'sofosbuvir|ledipasvir|velpatasvir|voxilaprevir|glecaprevir|pibrentasvir',
        r'daclatasvir|grazoprevir|elbasvir|simeprevir|ombitasvir|paritaprevir|ribavirin',
        r'peg(?:ylated)?[- ]?interferon|peg[- ]?ifn',
        r'entecavir|tenofovir|telbivudine|adefovir|lamivudine',
        r'hbv\s+dna|hbeag|hbsag|alt\s+normali[sz]ation',
        r'\bSOF\b|\bLDV\b|\bVEL\b|\bGLE\b|\bPIB\b|\bDCV\b|\bETV\b|\bTDF\b|\bTAF\b|\bLAM\b',
    ],
    'endpoint_patterns': [
        (r'sustained\s+virologic\w*\s+response|\bsvr\s*-?\s*(?:4|12|24)\b|\bsvr\b|hcv\s+cure',
         'SVR'),
        (r'rapid\s+virologic\w*\s+response|\brvr\b', 'RVR'),
        (r'(?:complete\s+|partial\s+)?early\s+virologic\w*\s+response|\b[cp]?evr\b', 'EVR'),
        (r'end[- ]of[- ]treatment\s+(?:virologic\w*\s+)?response|\betr\b', 'ETR'),
        (r'virologic\w*\s+relapse|post[- ]treatment\s+relapse', 'VIROLOGIC_RELAPSE'),
        (r'on[- ]treatment\s+virologic\w*\s+failure|null\s+response|non[- ]respon(?:se|der)|'
         r'virologic\w*\s+failure', 'ON_TREATMENT_FAILURE'),
        (r'virologic\w*\s+breakthrough|viral\s+breakthrough|biochemical\s+breakthrough|'
         r'hepatic\s+flare|alt\s+flare', 'VIROLOGIC_BREAKTHROUGH'),
        (r'genotypic\s+resistance|antiviral\s+resistance|drug\s+resistance|'
         r'resistance[- ]associated\s+mutation|resistance\s+mutation|rtm204|\bymdd\b', 'DRUG_RESISTANCE'),
        (r'serious\s+adverse\s+events?|\bsaes?\b', 'SERIOUS_AE'),
        (r'undetectable\s+hbv\s+dna|hbv\s+dna\s+suppression|hbv\s+dna\s+negativ|'
         r'complete\s+virologic\w*\s+response', 'HBV_DNA_SUPPRESSION'),
        (r'hbeag\s+seroconversion|hbeag\s+(?:loss|clearance)|e[- ]antigen\s+seroconversion',
         'HBEAG_SEROCONVERSION'),
        (r'hbsag\s+(?:loss|seroclearance|clearance|seroconversion)|functional\s+cure|'
         r'surface\s+antigen\s+loss', 'HBSAG_LOSS'),
        (r'alt\s+normali[sz]ation|biochemical\s+response|normali[sz]ation\s+of\s+alt',
         'ALT_NORMALIZATION'),
        (r'hbv\s+dna\s+(?:level|reduction|decline)|change\s+in\s+hbv\s+dna|'
         r'serum\s+hbv\s+dna|mean\s+hbv\s+dna', 'HBV_DNA_LEVEL'),
        (r'hcv\s+rna\s+(?:level|reduction|decline)|change\s+in\s+hcv\s+rna|'
         r'baseline\s+hcv\s+rna|mean\s+hcv\s+rna', 'HCV_RNA_LEVEL'),
        (r'change\s+in\s+alt|mean\s+alt|serum\s+alt\b|alanine\s+aminotransferase\s+level',
         'ALT_LEVEL'),
        (r'liver\s+stiffness|fibroscan|transient\s+elastography|fibrosis\s+regression',
         'LIVER_STIFFNESS'),
        (r'treatment\s+discontinuation|discontinuation\s+due\s+to|treatment[- ]limiting|'
         r'drug\s+discontinuation|premature\s+discontinuation', 'TREATMENT_DISCONTINUATION'),
    ],
    'context_patterns': [
        r'week\s+12\s+(?:after|post)', r'intention[- ]to[- ]treat|per[- ]protocol',
        r'genotype\s+[1-6]', r'treatment[- ]naive|treatment[- ]experienced',
    ]
}


# ============================================================
# PREVENTION PATTERNS (HBV vaccine / immunoglobulin)
# ============================================================

PREVENTION_PATTERNS = {
    'detection_keywords': [
        r'hepatitis\s+b\s+vaccine|hbv\s+vaccine|recombinant\s+(?:hepatitis\s+b\s+)?vaccine',
        r'birth\s+dose|birth[- ]dose\s+vaccine', r'anti[- ]?hbs',
        r'seroprotection|seroprotective', r'hepatitis\s+b\s+immunoglobulin|\bhbig\b',
        r'\bhbvax\b|\bengerix\b|three[- ]dose\s+schedule',
    ],
    'endpoint_patterns': [
        (r'geometric\s+mean\s+(?:titre|titer|concentration|antibody)|\bgm[tc]\b|'
         r'anti[- ]?hbs\s+(?:titre|titer|concentration)', 'ANTI_HBS_TITRE'),
        (r'seroprotection|seroprotective|anti[- ]?hbs[^.\n]{0,12}?(?:>=?|>|≥)\s*10|'
         r'protective\s+antibody|vaccine\s+seroconversion', 'SEROPROTECTION'),
        (r'incident\s+hepatitis\s+b|new\s+hbv\s+infection|hbv\s+infection|'
         r'incidence\s+of\s+hepatitis\s+b|breakthrough\s+hepatitis\s+b', 'HBV_INFECTION'),
    ],
    'context_patterns': [
        r'\bmiu/ml\b', r'three[- ]dose|0,\s*1,\s*6\s+month', r'per\s+protocol\s+immunogenicity',
    ]
}


# ============================================================
# PMTCT PATTERNS (HBV vertical transmission)
# ============================================================

PMTCT_PATTERNS = {
    'detection_keywords': [
        r'mother[- ]to[- ]child\s+transmission|\bmtct\b|\bpmtct\b',
        r'vertical\s+transmission', r'perinatal\s+transmission',
        r'infant\s+hbsag', r'hbeag[- ]positive\s+mothers?', r'pregnant\s+women\s+with\s+(?:chronic\s+)?hepatitis\s+b',
        r'maternal\s+(?:tenofovir|antiviral)', r'birth[- ]dose\s+vaccine\s+(?:plus|and)\s+hbig',
    ],
    'endpoint_patterns': [
        (r'mother[- ]to[- ]child\s+transmission|\bmtct\b|vertical\s+transmission|'
         r'perinatal\s+transmission|infant\s+hbsag|intrauterine\s+transmission', 'PERINATAL_TRANSMISSION'),
    ],
    'context_patterns': [
        r'at\s+(?:6|7|12)\s+months', r'infant\s+(?:hbsag|hbv\s+dna)', r'hbeag[- ]positive',
    ]
}


# ============================================================
# OUTCOMES PATTERNS (liver-disease progression)
# ============================================================

OUTCOMES_PATTERNS = {
    'detection_keywords': [
        r'hepatocellular\s+carcinoma|\bhcc\b|liver\s+cancer',
        r'cirrhosis|decompensation|hepatic\s+decompensation|liver\s+failure',
        r'fibrosis\s+progression', r'liver\s+transplant',
        r'liver[- ]related\s+(?:death|mortality)', r'child[- ]pugh|meld\s+score',
    ],
    'endpoint_patterns': [
        (r'hepatocellular\s+carcinoma|\bhcc\b|liver\s+cancer|primary\s+liver\s+cancer', 'HCC'),
        (r'hepatic\s+decompensation|decompensation|progression\s+to\s+cirrhosis|'
         r'fibrosis\s+progression|liver\s+failure|decompensated\s+liver', 'CIRRHOSIS'),
        (r'liver[- ]related\s+(?:death|mortality)|hepatic\s+death|death\s+from\s+liver',
         'LIVER_MORTALITY'),
        (r'liver\s+transplant\w*|transplant[- ]free\s+survival', 'LIVER_TRANSPLANT'),
        # Generic mortality, but NOT when qualified as liver-related/hepatic (those
        # are LIVER_MORTALITY; without the guards the bare word "death" sits closer
        # to the proportion and steals the tag -- audit P0-3).
        (r'(?<!liver[- ]related )(?<!hepatic )(?:all[- ]cause\s+)?(?:mortality|death)\b|'
         r'overall\s+survival', 'MORTALITY'),
    ],
    'context_patterns': [
        r'cumulative\s+incidence', r'per\s+(?:100\s+)?person[- ]years', r'kaplan[- ]meier',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_hepatitis_subspecialty(text: str) -> Tuple[str, float]:
    """Detect hepatitis trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: treatment, prevention, pmtct, outcomes, general_hepatitis."""
    text_lower = text.lower()
    scores = {'treatment': 0, 'prevention': 0, 'pmtct': 0, 'outcomes': 0}
    for kw in TREATMENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['treatment'] += 1
    for kw in PREVENTION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['prevention'] += 1
    for kw in PMTCT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['pmtct'] += 1
    for kw in OUTCOMES_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['outcomes'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_hepatitis', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_hepatitis_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'treatment': TREATMENT_PATTERNS['endpoint_patterns'],
        'prevention': PREVENTION_PATTERNS['endpoint_patterns'],
        'pmtct': PMTCT_PATTERNS['endpoint_patterns'],
        'outcomes': OUTCOMES_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_hepatitis_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical hepatitis endpoint, preferring the LONGEST matching
    alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in HEPATITIS_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
